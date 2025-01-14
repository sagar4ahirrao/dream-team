# Autonomously complete a coding task:
import asyncio
import os
from autogen_agentchat.ui import Console
from autogen_agentchat.agents import CodeExecutorAgent, AssistantAgent
from autogen_agentchat.teams import MagenticOneGroupChat
from autogen_ext.agents.file_surfer import FileSurfer
from autogen_ext.agents.magentic_one import MagenticOneCoderAgent
from autogen_ext.agents.web_surfer import MultimodalWebSurfer
from autogen_ext.code_executors.local import LocalCommandLineCodeExecutor
from autogen_ext.models.openai import AzureOpenAIChatCompletionClient
from autogen_core import AgentId, AgentProxy, DefaultTopicId
from autogen_core import SingleThreadedAgentRuntime



from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from dotenv import load_dotenv
from rag_helper import do_search

load_dotenv()
azure_credential = DefaultAzureCredential()
token_provider = get_bearer_token_provider(
    azure_credential, "https://cognitiveservices.azure.com/.default"
)
runtime = SingleThreadedAgentRuntime()



async def main() -> None:
    client = AzureOpenAIChatCompletionClient(
            model="gpt-4o-2024-11-20",
            azure_deployment="gpt-4o",
            api_version="2024-06-01",
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            azure_ad_token_provider=token_provider,
            model_info={
                "vision": True,
                "function_calling": True,
                "json_output": True,
            }
        )
    fs = FileSurfer("FileSurfer", model_client=client)
    ws = MultimodalWebSurfer("WebSurfer", model_client=client)
    coder = MagenticOneCoderAgent("Coder", model_client=client,)
    #coder = AgentProxy(AgentId("Coder", "default"), runtime)

    executor = CodeExecutorAgent("Executor", code_executor=LocalCommandLineCodeExecutor())
   
    team = MagenticOneGroupChat([fs,ws,executor, coder], model_client=client)
    await Console(team.run_stream(task="How much taxes elon musk paid?"))

if __name__ == "__main__":
    asyncio.run(main())


