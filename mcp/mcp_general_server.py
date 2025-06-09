from typing import Any
import httpx
from mcp.server.fastmcp import FastMCP
import logging
from dotenv import load_dotenv
import json
import os

# Load environment variables from .env file
load_dotenv()

# Initialize FastMCP server
mcp = FastMCP("ag-general")

# GitHub Models configuration
GITHUB_ENDPOINT = os.getenv("GITHUB_MODEL_ENDPOINT", "https://models.github.ai/inference")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_API_VERSION = os.getenv("GITHUB_API_VERSION", "2024-12-01-preview")

# Model configurations
MODELS = {
    "gpt4": {
        "name": os.getenv("GITHUB_MODEL_GPT4", "openai/gpt-4.1"),
        "endpoint": GITHUB_ENDPOINT,
        "api_version": GITHUB_API_VERSION
    },
    "o4mini": {
        "name": os.getenv("GITHUB_MODEL_O4MINI", "openai/o4-mini"),
        "endpoint": GITHUB_ENDPOINT,
        "api_version": GITHUB_API_VERSION
    }
}

async def call_github_model(model_name: str, messages: list, temperature: float = 1.0, top_p: float = 1.0) -> str:
    """
    Call GitHub model API with the given messages.
    
    Args:
        model_name: Name of the model to use (gpt4 or o4mini)
        messages: List of message dictionaries
        temperature: Temperature parameter for generation
        top_p: Top-p parameter for generation
        
    Returns:
        str: Model's response
    """
    if not GITHUB_TOKEN:
        raise ValueError("GITHUB_TOKEN environment variable is not set")
        
    model_config = MODELS.get(model_name)
    if not model_config:
        raise ValueError(f"Unknown model: {model_name}")
        
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "messages": messages,
        "model": model_config["name"],
        "temperature": temperature,
        "top_p": top_p
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{model_config['endpoint']}/chat/completions",
            headers=headers,
            json=payload
        )
        
        if response.status_code != 200:
            raise Exception(f"Model API error: {response.text}")
            
        return response.json()["choices"][0]["message"]["content"]

@mcp.tool()
async def mailer(
    to_address: str = "",
    subject: str = "",
    plain_text: str = "",
    html_content: str = ""
) -> str:
    """
    Sends an email using GitHub models to generate and send the email content.

    Args:
        to_address (str): Recipient email address.
        subject (str): Email subject.
        plain_text (str): Plain text content.
        html_content (str): HTML content (optional).
    Returns:
        str: Result of the send operation or error message.
    """
    logger = logging.getLogger("mailer")
    logger.info(f"Sending email to {to_address} with subject: {subject}")
    
    try:
        # Generate email content using GitHub model
        messages = [
            {"role": "system", "content": "You are an email assistant. Generate a professional email."},
            {"role": "user", "content": f"Generate an email with subject: {subject}\nContent: {plain_text}"}
        ]
        
        email_content = await call_github_model("gpt4", messages)
        
        # Here you would implement the actual email sending logic
        # For now, we'll just return the generated content
        return f"Email content generated successfully:\n\n{email_content}"
        
    except Exception as e:
        logger.error(f"Failed to generate email: {e}")
        return f"Failed to generate email: {e}"

@mcp.tool()
async def data_provider(tablename: str) -> str:
    """A tool that provides data from database based on given table name as parameter.
    
    Args:
        tablename (str): The table to read data from.
        
    Returns:
        str: The content of the file.
    """
    logger = logging.getLogger("data_provider")
    try:
        tablename = tablename.strip() + ".csv"
        _file_json = find_file(tablename)
        _file_info = json.loads(_file_json)
        _file_path = _file_info["path"]
        
        if not _file_path:
            logger.error(f"File '{tablename}' not found.")
            return f"File '{tablename}' not found."
            
        logger.info(f"File '{tablename}' found at '{_file_path}'.")
        
        with open(_file_path, "r") as file:
            data = file.read()
            
        # Use GitHub model to analyze the data
        messages = [
            {"role": "system", "content": "You are a data analyst. Analyze the following data and provide insights."},
            {"role": "user", "content": f"Analyze this data:\n{data}"}
        ]
        
        analysis = await call_github_model("o4mini", messages)
        return f"Data Analysis:\n{analysis}\n\nRaw Data:\n{data}"
        
    except Exception as e:
        logger.error(f"Error processing data: {e}")
        return f"Error processing data: {e}"

def find_file(filename: str) -> str:
    """
    Searches recursively within the ./data folder for an exact filename match.
    Returns a JSON string with the full relative path and the original filename.
    """
    logger = logging.getLogger("find_file")
    for root, _, files in os.walk("./data"):
        if filename in files:
            full_path = os.path.join(root, filename)
            logger.info(f"Found file: {full_path}")
            return json.dumps({
                "path": full_path,
                "filename": filename
            })
    logger.warning(f"File '{filename}' not found in './data' directory.")
    return json.dumps({
        "path": None,
        "filename": filename
    })

@mcp.tool()
async def show_tables() -> list:
    """
    Searches for all CSV files in the ./data folder and returns a list of table names (without .csv extension).
    Returns:
        list: List of table names found in the ./data directory.
    """
    logger = logging.getLogger("show_tables")
    table_names = []
    for root, _, files in os.walk("./data"):
        for file in files:
            if file.lower().endswith(".csv"):
                table_name = file[:-4]  # Remove .csv extension
                table_names.append(table_name)
                logger.info(f"Found table: {table_name}")
                
    if not table_names:
        logger.warning("No CSV tables found in './data' directory.")
        
    return table_names

if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport='stdio')
