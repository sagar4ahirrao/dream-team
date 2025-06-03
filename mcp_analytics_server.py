import os
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Union, Any
from fastapi import FastAPI, HTTPException, Query, Depends, Request
from pydantic import BaseModel
import json
from datetime import datetime
import asyncio
from sse_starlette.sse import EventSourceResponse
from fastapi.middleware.cors import CORSMiddleware
import plotly.express as px
import plotly.graph_objects as go
from io import StringIO
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from autogen_ext.models.openai import AzureOpenAIChatCompletionClient
import re
from mcp.server.fastmcp import FastMCP
from mcp.server.sse import SseServerTransport
from starlette.routing import Mount
from api_key_auth import ensure_valid_api_key

# Initialize FastMCP server
mcp = FastMCP("analytics")

app = FastAPI(docs_url=None, redoc_url=None, dependencies=[Depends(ensure_valid_api_key)])

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize SSE transport
sse = SseServerTransport("/messages/")
app.router.routes.append(Mount("/messages", app=sse.handle_post_message))

# Data directory path
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "mcp", "data")

# Initialize Azure OpenAI client
azure_credential = DefaultAzureCredential()
token_provider = get_bearer_token_provider(
    azure_credential, "https://cognitiveservices.azure.com/.default"
)

llm_client = AzureOpenAIChatCompletionClient(
    model="gpt-4.1-2025-04-14",
    azure_deployment="gpt-4.1",
    api_version="2025-03-01-preview",
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    azure_ad_token_provider=token_provider,
    model_info={
        "vision": True,
        "function_calling": True,
        "json_output": True,
        "family": "gpt-4"
    }
)

class DataRequest(BaseModel):
    table_name: str
    query: Optional[str] = None
    filters: Optional[Dict] = None
    group_by: Optional[List[str]] = None
    sort_by: Optional[str] = None
    limit: Optional[int] = None
    analysis_type: Optional[str] = None
    visualization_type: Optional[str] = None
    columns: Optional[List[str]] = None
    natural_language_query: Optional[str] = None

class AnalysisRequest(BaseModel):
    table_name: str
    analysis_type: str
    parameters: Optional[Dict[str, Any]] = None
    natural_language_insight: Optional[str] = None

class LLMAnalysisRequest(BaseModel):
    table_name: str
    query: str
    context: Optional[Dict[str, Any]] = None

def load_data(table_name: str) -> pd.DataFrame:
    """Load data from CSV file"""
    file_path = os.path.join(DATA_DIR, f"{table_name}.csv")
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"Table {table_name} not found")
    return pd.read_csv(file_path)

def get_table_schema(table_name: str) -> Dict:
    """Get detailed schema information for a table"""
    df = load_data(table_name)
    schema = {
        "columns": list(df.columns),
        "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
        "sample_values": {col: df[col].head(3).tolist() for col in df.columns},
        "missing_values": df.isnull().sum().to_dict(),
        "unique_values": {col: df[col].nunique() for col in df.columns}
    }
    return schema

async def analyze_with_llm(table_name: str, query: str, context: Optional[Dict] = None) -> Dict:
    """Use LLM to analyze data and provide insights"""
    df = load_data(table_name)
    schema = get_table_schema(table_name)
    
    # Prepare context for LLM
    context_str = json.dumps({
        "table_name": table_name,
        "schema": schema,
        "sample_data": df.head(5).to_dict(orient='records'),
        "additional_context": context or {}
    })
    
    # Create prompt for LLM
    prompt = f"""You are a data analyst AI. Analyze the following data and provide insights based on the query.
    
Context:
{context_str}

Query: {query}

Provide your analysis in the following JSON format:
{{
    "insights": [list of key insights],
    "recommendations": [list of recommendations],
    "visualization_suggestions": [list of suggested visualizations],
    "potential_issues": [list of potential data quality issues],
    "summary": "brief summary of findings"
}}

Focus on providing actionable insights and clear explanations."""

    # Get LLM response
    response = await llm_client.create(
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=1000
    )
    
    try:
        analysis = json.loads(response.choices[0].message.content)
        return analysis
    except json.JSONDecodeError:
        # If LLM response is not valid JSON, try to extract JSON from the text
        json_match = re.search(r'\{.*\}', response.choices[0].message.content, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
        raise HTTPException(status_code=500, detail="Failed to parse LLM analysis response")

def generate_visualization(df: pd.DataFrame, viz_type: str, columns: List[str], title: Optional[str] = None) -> str:
    """Generate visualization using plotly with enhanced styling"""
    if viz_type == "bar":
        fig = px.bar(df, x=columns[0], y=columns[1] if len(columns) > 1 else None,
                    title=title or f"{columns[1]} by {columns[0]}" if len(columns) > 1 else f"Count by {columns[0]}")
    elif viz_type == "line":
        fig = px.line(df, x=columns[0], y=columns[1] if len(columns) > 1 else None,
                     title=title or f"{columns[1]} over {columns[0]}" if len(columns) > 1 else f"Trend over {columns[0]}")
    elif viz_type == "scatter":
        fig = px.scatter(df, x=columns[0], y=columns[1] if len(columns) > 1 else None,
                        title=title or f"{columns[1]} vs {columns[0]}" if len(columns) > 1 else f"Scatter plot of {columns[0]}")
    elif viz_type == "pie":
        fig = px.pie(df, names=columns[0], values=columns[1] if len(columns) > 1 else None,
                    title=title or f"Distribution of {columns[0]}")
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported visualization type: {viz_type}")
    
    # Enhance visualization
    fig.update_layout(
        template="plotly_white",
        font=dict(family="Arial", size=12),
        margin=dict(l=50, r=50, t=50, b=50),
        showlegend=True
    )
    
    return fig.to_json()

@app.get("/tables")
async def list_tables():
    """List all available tables with their descriptions and schema"""
    tables = {}
    for f in os.listdir(DATA_DIR):
        if f.endswith('.csv'):
            table_name = f.replace('.csv', '')
            df = load_data(table_name)
            tables[table_name] = {
                "columns": list(df.columns),
                "row_count": len(df),
                "description": get_table_description(table_name),
                "schema": get_table_schema(table_name)
            }
    return {"tables": tables}

def get_table_description(table_name: str) -> str:
    """Get human-readable description of the table"""
    descriptions = {
        "sensor": "Sensor readings and measurements data",
        "maintenance": "Maintenance records and schedules",
        "resolutions": "Issue resolution tracking and status",
        "customer_base": "Customer information and demographics",
        "customer_orders": "Customer order history and details",
        "inventory": "Inventory management and stock levels",
        "bookings": "Booking and reservation records",
        "complaints": "Customer complaint records and resolutions"
    }
    return descriptions.get(table_name, "No description available")

@app.post("/query")
async def query_data(request: DataRequest):
    """Query data with various operations and optional LLM analysis"""
    try:
        df = load_data(request.table_name)
        
        # Apply filters if provided
        if request.filters:
            for column, value in request.filters.items():
                if isinstance(value, list):
                    df = df[df[column].isin(value)]
                else:
                    df = df[df[column] == value]
        
        # Apply grouping if provided
        if request.group_by:
            df = df.groupby(request.group_by).agg({
                col: ['count', 'mean', 'sum'] for col in df.select_dtypes(include=[np.number]).columns
            }).reset_index()
        
        # Apply sorting if provided
        if request.sort_by:
            df = df.sort_values(by=request.sort_by, ascending=False)
        
        # Apply limit if provided
        if request.limit:
            df = df.head(request.limit)

        # Generate visualization if requested
        visualization = None
        if request.visualization_type and request.columns:
            visualization = generate_visualization(df, request.visualization_type, request.columns)
        
        # Perform LLM analysis if natural language query is provided
        llm_analysis = None
        if request.natural_language_query:
            llm_analysis = await analyze_with_llm(
                request.table_name,
                request.natural_language_query,
                context={"filtered_data": df.head(10).to_dict(orient='records')}
            )
        
        return {
            "data": df.to_dict(orient='records'),
            "visualization": visualization,
            "llm_analysis": llm_analysis,
            "summary": {
                "row_count": len(df),
                "columns": list(df.columns),
                "numeric_columns": list(df.select_dtypes(include=[np.number]).columns),
                "categorical_columns": list(df.select_dtypes(include=['object']).columns)
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/analyze")
async def analyze_data(request: AnalysisRequest):
    """Perform advanced analysis on the data with optional LLM insights"""
    try:
        df = load_data(request.table_name)
        analysis_type = request.analysis_type
        parameters = request.parameters or {}

        # Perform standard analysis
        if analysis_type == "trend":
            time_col = parameters.get("time_column")
            value_col = parameters.get("value_column")
            if not time_col or not value_col:
                raise HTTPException(status_code=400, detail="time_column and value_column are required for trend analysis")
            
            df[time_col] = pd.to_datetime(df[time_col])
            trend = df.groupby(df[time_col].dt.date)[value_col].agg(['mean', 'min', 'max']).reset_index()
            analysis_result = {"trend_analysis": trend.to_dict(orient='records')}

        elif analysis_type == "correlation":
            columns = parameters.get("columns", df.select_dtypes(include=[np.number]).columns)
            corr = df[columns].corr()
            analysis_result = {"correlation_matrix": corr.to_dict()}

        elif analysis_type == "distribution":
            column = parameters.get("column")
            if not column:
                raise HTTPException(status_code=400, detail="column is required for distribution analysis")
            
            stats = df[column].describe()
            analysis_result = {"distribution": stats.to_dict()}

        else:
            raise HTTPException(status_code=400, detail=f"Unsupported analysis type: {analysis_type}")

        # Add LLM insights if requested
        if request.natural_language_insight:
            llm_insights = await analyze_with_llm(
                request.table_name,
                request.natural_language_insight,
                context={"analysis_result": analysis_result}
            )
            analysis_result["llm_insights"] = llm_insights

        return analysis_result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/llm_analyze")
async def llm_analyze(request: LLMAnalysisRequest):
    """Perform LLM-powered analysis on the data"""
    try:
        analysis = await analyze_with_llm(request.table_name, request.query, request.context)
        return analysis
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/sse")
async def handle_sse(request: Request):
    """SSE endpoint for MCP server"""
    async with sse.connect_sse(request.scope, request.receive, request._send) as (
        read_stream,
        write_stream,
    ):
        init_options = mcp._mcp_server.create_initialization_options()
        await mcp._mcp_server.run(
            read_stream,
            write_stream,
            init_options,
        )

@mcp.tool()
def data_provider(table_name: str) -> str:
    """A tool that provides data from a specific table.
    
    Args:
        table_name (str): The name of the table to get data from.
        
    Returns:
        str: JSON string containing the table data and metadata.
    """
    try:
        df = load_data(table_name)
        schema = get_table_schema(table_name)
        return json.dumps({
            "data": df.head(10).to_dict(orient='records'),
            "schema": schema,
            "description": get_table_description(table_name),
            "row_count": len(df)
        })
    except Exception as e:
        return json.dumps({"error": str(e)})

@mcp.tool()
def show_tables() -> str:
    """A tool that lists all available tables with their descriptions and schema.
    
    Returns:
        str: JSON string containing table information.
    """
    tables = {}
    for f in os.listdir(DATA_DIR):
        if f.endswith('.csv'):
            table_name = f.replace('.csv', '')
            df = load_data(table_name)
            tables[table_name] = {
                "columns": list(df.columns),
                "row_count": len(df),
                "description": get_table_description(table_name),
                "schema": get_table_schema(table_name)
            }
    return json.dumps({"tables": tables})

@mcp.tool()
def analyze_data(table_name: str, analysis_type: str, parameters: Optional[Dict[str, Any]] = None) -> str:
    """A tool that performs analysis on the specified table.
    
    Args:
        table_name (str): The name of the table to analyze.
        analysis_type (str): The type of analysis to perform.
        parameters (Optional[Dict[str, Any]]): Additional parameters for the analysis.
        
    Returns:
        str: JSON string containing the analysis results.
    """
    try:
        df = load_data(table_name)
        parameters = parameters or {}

        if analysis_type == "trend":
            time_col = parameters.get("time_column")
            value_col = parameters.get("value_column")
            if not time_col or not value_col:
                return json.dumps({"error": "time_column and value_column are required for trend analysis"})
            
            df[time_col] = pd.to_datetime(df[time_col])
            trend = df.groupby(df[time_col].dt.date)[value_col].agg(['mean', 'min', 'max']).reset_index()
            analysis_result = {"trend_analysis": trend.to_dict(orient='records')}

        elif analysis_type == "correlation":
            columns = parameters.get("columns", df.select_dtypes(include=[np.number]).columns)
            corr = df[columns].corr()
            analysis_result = {"correlation_matrix": corr.to_dict()}

        elif analysis_type == "distribution":
            column = parameters.get("column")
            if not column:
                return json.dumps({"error": "column is required for distribution analysis"})
            
            stats = df[column].describe()
            analysis_result = {"distribution": stats.to_dict()}

        else:
            return json.dumps({"error": f"Unsupported analysis type: {analysis_type}"})

        return json.dumps(analysis_result)

    except Exception as e:
        return json.dumps({"error": str(e)})

@mcp.tool()
async def llm_analyze(table_name: str, query: str, context: Optional[Dict[str, Any]] = None) -> str:
    """A tool that performs LLM-powered analysis on the data.
    
    Args:
        table_name (str): The name of the table to analyze.
        query (str): The natural language query for analysis.
        context (Optional[Dict[str, Any]]): Additional context for the analysis.
        
    Returns:
        str: JSON string containing the LLM analysis results.
    """
    try:
        analysis = await analyze_with_llm(table_name, query, context)
        return json.dumps(analysis)
    except Exception as e:
        return json.dumps({"error": str(e)})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8333) 