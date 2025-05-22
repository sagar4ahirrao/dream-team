
from autogen_agentchat.agents import AssistantAgent
from autogen_core.models import (
    ChatCompletionClient,
)
from autogen_ext.tools.mcp import SseMcpToolAdapter, StdioServerParams, StdioMcpToolAdapter

# TODO add checks to ususer inputs to make sure it is a valid definition of custom agent
class MagenticOneCustomMCPAgent(AssistantAgent):
    """An agent used by MagenticOne that provides coding assistance using an LLM model client.
    
    The prompts and description are sealed to replicate the original MagenticOne configuration.
    See AssistantAgent if you wish to modify these values.
    """
    
    def __init__(
        self,
        name: str,
        model_client: ChatCompletionClient,
        system_message: str,
        description: str,
        adapter,  # adapter is now provided by the async factory method
        user_id: str = None
    ):
        super().__init__(
            name,
            model_client,
            description=description,
            system_message=system_message,
            tools=adapter
        )
        self.user_id = user_id
    
    @classmethod
    async def create(
        cls,
        name: str,
        model_client: ChatCompletionClient,
        system_message: str,
        description: str,
        user_id: str = None
    ):
        server_params = StdioServerParams(
            command="python",
            args=["mcp_math_server.py"],
        )
        # Get the addition tool from the server asynchronously
        adapter_addition = await StdioMcpToolAdapter.from_server_params(server_params, "add")
        adapter_multiplication = await StdioMcpToolAdapter.from_server_params(server_params, "multiply")
        adapter_data_provider = await SseMcpToolAdapter.from_server_params(server_params, "data_provider")
        adapter_mailer = await SseMcpToolAdapter.from_server_params(server_params, "mailer")
        return cls(name, 
                   model_client, 
                   system_message, 
                   description, 
                   [adapter_addition, adapter_multiplication, adapter_data_provider, adapter_mailer],
                   user_id=user_id)