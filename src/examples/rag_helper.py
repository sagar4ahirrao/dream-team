import os
import asyncio
from typing import List
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
from azure.search.documents.models import VectorizedQuery
from azure.identity import DefaultAzureCredential,get_bearer_token_provider
from openai import AzureOpenAI
from tenacity import retry, wait_random_exponential, stop_after_attempt

from dotenv import load_dotenv
load_dotenv()

def config_search() -> SearchClient:
    service_endpoint = os.getenv("AZURE_SEARCH_SERVICE_ENDPOINT")
    key = os.getenv("AZURE_SEARCH_ADMIN_KEY")
    index_name = "vector-1719475859220"
    credential = AzureKeyCredential(key)
    return SearchClient(endpoint=service_endpoint, index_name=index_name, credential=credential)

@retry(wait=wait_random_exponential(min=1, max=20), stop=stop_after_attempt(6))
def calc_embeddings(text: str) -> List[float]:
    """Generate embeddings using AzureOpenAI."""
    credential = DefaultAzureCredential()
    aclient = AzureOpenAI(
        api_version="2024-06-01",
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        azure_ad_token_provider=get_bearer_token_provider(credential, "https://cognitiveservices.azure.com/.default"),
    )
    return aclient.embeddings.create(
        model="text-embedding-ada-002",
        input=[text]
    ).data[0].embedding

async def do_search(query: str) -> str:
    """Search indexed data using Azure Cognitive Search with vector-based queries."""
    aia_search_client = config_search()
    embedding = calc_embeddings(query)
    fields = "text_vector"
    vector_query = VectorizedQuery(vector=embedding, k_nearest_neighbors=1, fields=fields)
  
    results = aia_search_client.search(  
        search_text=None,  
        vector_queries= [vector_query],
        select=["parent_id", "chunk_id", "chunk"],
        top=1,
    )  

    answer = ''
    for result in results:  
        print(f"parent_id: {result['parent_id']}")  
        print(f"chunk_id: {result['chunk_id']}")  
        print(f"Score: {result['@search.score']}")  
        print(f"Content: {result['chunk']}")
        answer = answer + result['chunk']
    return answer


async def main():
    """Run a sample search as a standalone script."""
    query = "How much taxes elon musk paid?"
    x = await do_search(query)
    print(x)

if __name__ == "__main__":
    asyncio.run(main())

'''
TOOL_AZURE_SEARCH = ToolSchema(
    name="do_search",
    description=" use this tool if you are asked questions about elon musk.",
    parameters=ParametersSchema(
        type="object",
        properties={
            "query": {
                "type": "string",
                "description": "The string to search for on the page. '",
            },
        },
    ),
)
'''