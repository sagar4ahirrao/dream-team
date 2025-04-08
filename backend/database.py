import os
from azure.cosmos import CosmosClient, PartitionKey
from azure.identity import DefaultAzureCredential
from typing import Optional, List, Dict

from autogen_agentchat.base import TaskResult
from autogen_agentchat.messages import MultiModalMessage, TextMessage, ToolCallExecutionEvent, ToolCallRequestEvent

from schemas import AutoGenMessage
import uuid
from dotenv import load_dotenv
import time

def load_azd_env():
    load_dotenv("./.env", override=True)

def get_db(container_name: str = "ag_demo"):
    """
    Returns the Cosmos DB container.
    """
    start_time = time.perf_counter()
    # Get Cosmos DB account details from environment variables
    COSMOS_DB_URI = os.getenv("COSMOS_DB_URI", "https://YOURDB.documents.azure.com:443/")
    COSMOS_DB_DATABASE = os.getenv("COSMOS_DB_DATABASE", "ag_demo")
    if container_name is None:
        COSMOS_DB_CONTAINER = os.getenv("COSMOS_DB_CONTAINER", "ag_demo")
    else:
        COSMOS_DB_CONTAINER = container_name
    
    # Use DefaultAzureCredential for AAD token authorization
    credential = DefaultAzureCredential()

    # Initialize the Cosmos client with AAD token authorization
    client = CosmosClient(COSMOS_DB_URI, credential=credential)

    # Create the database if it does not exist
    database = client.create_database_if_not_exists(id=COSMOS_DB_DATABASE)

    # Create the container if it does not exist.
    # Adjust the partition key and throughput as needed.
    container = database.create_container_if_not_exists(
        id=COSMOS_DB_CONTAINER,
        partition_key=PartitionKey(path="/user_id"),
        offer_throughput=400
    ) 
    elapsed_time = time.perf_counter() - start_time
    print(f"get_db executed in {elapsed_time:.4f} seconds")
    
    return container
    # return True
def format_message(_log_entry_json):
    _response = AutoGenMessage(
        time="N/A",
        session_id="session_id",
        session_user="session_user",
        )

    # Check if the message is a TaskResult class
    if isinstance(_log_entry_json, TaskResult):
        _response.type = "TaskResult"
        _response.source = "TaskResult"
        _response.content = _log_entry_json.messages[-1].content
        _response.stop_reason = _log_entry_json.stop_reason
        # store_document(_log_entry_json, _response)

    elif isinstance(_log_entry_json, MultiModalMessage):
        _response.type = _log_entry_json.type
        _response.source = _log_entry_json.source
        _response.content = _log_entry_json.content[0] # text wthout image
        _response.content_image = _log_entry_json.content[1].data_uri # TODO: base64 encoded image -> text / serialize

    elif isinstance(_log_entry_json, TextMessage):
        _response.type = _log_entry_json.type
        _response.source = _log_entry_json.source
        _response.content = _log_entry_json.content

    elif isinstance(_log_entry_json, ToolCallExecutionEvent):
        _response.type = _log_entry_json.type
        _response.source = _log_entry_json.source
        _response.content = _log_entry_json.content[0].content # tool execution

    elif isinstance(_log_entry_json, ToolCallRequestEvent):
        # _models_usage = _log_entry_json.models_usage
        _response.type = _log_entry_json.type
        _response.source = _log_entry_json.source
        _response.content = _log_entry_json.content[0].arguments # tool execution

    else:
        _response.type = "N/A"
        _response.source = "N/A"
        _response.content = "Agents mumbling."
    return _response
def store_conversation(conversation: TaskResult, conveersation_details: AutoGenMessage):
    """
    Stores a conversation document into the Cosmos DB container.
    
    Parameters:
        conversation (dict): The conversation data to store. It must include the partition key field "user_id".
    
    Returns:
        dict: The response from Cosmos DB after the document is created.
    """
    _messsages = []
    for message in conversation.messages:
        _m = format_message(message)
        _messsages.append(_m.to_json())
    conversation_document_item = dict(
        id=str(uuid.uuid4()),
        user_id=conveersation_details.session_user,
        session_id=conveersation_details.session_id,
        messages=_messsages, 
        agents=[], 
        run_mode_locally=False,
        timestamp=conveersation_details.time,
        )

    container = get_db()
    response = container.create_item(body=conversation_document_item)
    return response

def fetch_user_conversatons(user_id: Optional[str] = None) -> List[Dict]:
    """
    Retrieves all documents from the Cosmos DB container. If user_id is provided,
    the results are filtered to match the given user_id. Otherwise, all documents
    are retrieved.
    
    Parameters:
        user_id (Optional[str]): The user ID to filter the documents. When None, no filter is applied.
    
    Returns:
        List[dict]: A list of documents that match the given user_id, or all documents if user_id is None.
    """
    container = get_db()
    
    if user_id is None:
        query = "SELECT c.user_id, c.session_id, c.timestamp FROM c"
        parameters = []
    else:
        query = "SELECT c.user_id, c.session_id, c.timestamp FROM c WHERE c.user_id = @userId"
        parameters = [{"name": "@userId", "value": user_id}]
    
    items = list(container.query_items(
        query=query,
        parameters=parameters,
        enable_cross_partition_query=True
    ))
    return items

def fetch_user_conversation(user_id: str, session_id: str):
    """
    Retrieves a conversation document from the Cosmos DB container identified by its user_id and session_id.
    
    Parameters:
        user_id (str): The user ID of the conversation document.
        session_id (str): The session ID of the conversation document.
    
    Returns:
        dict: The conversation document that matches the given user_id and session_id.
    """
    container = get_db()
    query = "SELECT * FROM c WHERE c.user_id = @userId AND c.session_id = @sessionId"
    parameters = [
        {"name": "@userId", "value": user_id},
        {"name": "@sessionId", "value": session_id},
    ]
    items = list(container.query_items(
        query=query,
        parameters=parameters,
        enable_cross_partition_query=True
    ))
    return items

def delete_user_conversation(user_id: str, session_id: str):
    """
    Deletes a conversation document from the Cosmos DB container identified by its user_id and session_id.
    
    Parameters:
        user_id (str): The user ID of the conversation document.
        session_id (str): The session ID of the conversation document.
    
    Returns:
        dict: The response from Cosmos DB after deleting the document, or an error message if not found.
    """
    container = get_db()
    query = "SELECT * FROM c WHERE c.user_id = @userId AND c.session_id = @sessionId"
    parameters = [
        {"name": "@userId", "value": user_id},
        {"name": "@sessionId", "value": session_id},
    ]
    items = list(container.query_items(
        query=query,
        parameters=parameters,
        enable_cross_partition_query=True
    ))
    
    if not items:
        return {"error": f"No conversation found with user_id {user_id} and session_id {session_id}."}
    
    # Assuming the combination of user_id and session_id uniquely identifies a conversation.
    conversation = items[0]
    response = container.delete_item(item=conversation["id"], partition_key=conversation["user_id"])
    return response

def delete_user_all_conversations(user_id: str):
    """
    Deletes a conversation document from the Cosmos DB container identified by its user_id and session_id.
    
    Parameters:
        user_id (str): The user ID of the conversation document.
    
    Returns:
        dict: The response from Cosmos DB after deleting the document, or an error message if not found.
    """
    container = get_db()
    query = "SELECT * FROM c WHERE c.user_id = @userId"
    parameters = [
        {"name": "@userId", "value": user_id},
    ]
    items = list(container.query_items(
        query=query,
        parameters=parameters,
        enable_cross_partition_query=True
    ))
    
    if not items:
        return {"error": f"No conversation found with user_id {user_id}."}
    
    for item in items:
        container.delete_item(item=item["id"], partition_key=item["user_id"])
    return True

def create_team(team: dict):
    container = get_db(container_name= "agent_teams")
    team_document = {
        "id": team["id"],
        "team_id": team["team_id"],
        "name": team["name"],
        "agents": team["agents"],
        "description": team.get("description"),
        "logo": team["logo"],
        "plan": team["plan"],
        "starting_tasks": team["starting_tasks"],
    }
    response = container.create_item(body=team_document)
    return response

def get_teams():
    container = get_db(container_name= "agent_teams")
    query = "SELECT * FROM c "
    items = list(container.query_items(query=query, enable_cross_partition_query=True))
    return items

def get_team(team_id: str):
    container = get_db(container_name= "agent_teams")
    query = "SELECT * FROM c WHERE c.team_id = @teamId"
    parameters = [{"name": "@teamId", "value": team_id}]
    items = list(container.query_items(query=query, parameters=parameters, enable_cross_partition_query=True))
    return items[0] if items else None

def update_team(team_id: str, team: dict):
    container = get_db(container_name= "agent_teams")
    existing_team = get_team(team_id)
    if not existing_team:
        return {"error": "Team not found"}

    updated_team = {**existing_team, **team}
    response = container.replace_item(item=existing_team["id"], body=updated_team)
    return response

def delete_team(team_id: str):
    container = get_db(container_name= "agent_teams")
    existing_team = get_team(team_id)
    if not existing_team:
        return {"error": "Team not found"}

    response = container.delete_item(item=existing_team["id"], partition_key=existing_team["id"])
    return response

if __name__ == "__main__":
    import json
    import glob
    import os

    load_azd_env()

    # Initialize the database by creating teams from JSON files in ./data/folder
    teams_folder = os.path.join(os.path.dirname(__file__), "./data/teams-definitions")
    json_files = glob.glob(os.path.join(teams_folder, "*.json"))

    # sort the files by name
    json_files.sort()
    

    print(f"Found {len(json_files)} JSON files in {teams_folder}.")
    
    created_items = 0
    for file_path in json_files:
        with open(file_path, "r") as f:
            team = json.load(f)
        # Assuming JSON key "teamId" exists; adjust mapping if necessary.
        response = create_team(team)
        print(f"Created team from {os.path.basename(file_path)}")
        created_items += 1
    print(f"Created {created_items}/{len(json_files)} items in the database.")
    
    # Example usage
    # container = get_db()
    # print(container)
    # fetch_user_conversatons("user_id")
    # fetch_user_conversation("user_id", "session_id")
    # delete_user_conversation("user_id", "session_id")
    pass