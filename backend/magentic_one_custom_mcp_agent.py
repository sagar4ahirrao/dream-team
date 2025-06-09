import os
import json
import logging
from typing import Dict, Any, List, Optional, Union
from autogen_agentchat.agents import AssistantAgent
from autogen_core.models import (
    ChatCompletionClient,
)
from autogen_ext.tools.mcp import SseMcpToolAdapter, StdioServerParams, StdioMcpToolAdapter, SseServerParams
from dotenv import load_dotenv

load_dotenv()

# Configure logging - set to WARNING level to reduce verbosity
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)


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
    def _parse_mcp_config(cls, description: str) -> Optional[Dict[str, Any]]:
        """Parse MCP server configuration from agent description.
        
        Args:
            description: Agent description that may contain MCP configuration JSON
            
        Returns:
            Parsed MCP configuration dict or None if parsing fails
        """
        try:
            # Try to parse the entire description as JSON
            config = json.loads(description)
            if "mcpServers" in config:
                return config["mcpServers"]
        except json.JSONDecodeError:
            pass
        
        # Try to find JSON block within the description
        try:
            start_idx = description.find("{")
            end_idx = description.rfind("}") + 1
            if start_idx >= 0 and end_idx > start_idx:
                json_str = description[start_idx:end_idx]
                config = json.loads(json_str)
                if "mcpServers" in config:
                    return config["mcpServers"]
                else:
                    # If direct mcpServers key not found, assume the JSON is the server config
                    return config
        except (json.JSONDecodeError, ValueError):
            logger.warning("Failed to parse MCP configuration from description")
        
        return None
    
    @classmethod
    async def _create_stdio_adapters(cls, server_name: str, server_config: Dict[str, Any]) -> List:
        adapters = []
        
        try:
            command = server_config.get("command", "npx")
            args = server_config.get("args", [])
            env = server_config.get("env", {})
            tools = server_config.get("tools", [])
            
            full_env = os.environ.copy()
            full_env.update(env)
            
            server_params = StdioServerParams(
                command=command,
                args=args,
                env=full_env,
            )
            
            for tool_name in tools:
                try:
                    adapter = await StdioMcpToolAdapter.from_server_params(server_params, tool_name)
                    adapters.append(adapter)
                except Exception as e:
                    logger.error(f"Failed to create STDIO adapter for tool {tool_name}: {e}")
            
        except Exception as e:
            logger.error(f"Failed to create STDIO adapters for server {server_name}: {e}")
        
        return adapters
    
    @classmethod
    async def _create_sse_adapters(cls, server_name: str, server_config: Dict[str, Any]) -> List:
        adapters = []
        
        try:
            url = server_config.get("url")
            headers = server_config.get("headers", {})
            tools = server_config.get("tools", [])
            
            if not url:
                logger.error(f"No URL specified for SSE server {server_name}")
                return adapters
            
            server_params = SseServerParams(
                url=url,
                headers=headers
            )
            
            for tool_name in tools:
                try:
                    adapter = await SseMcpToolAdapter.from_server_params(server_params, tool_name)
                    adapters.append(adapter)
                except Exception as e:
                    logger.error(f"Failed to create SSE adapter for tool {tool_name}: {e}")
            
        except Exception as e:
            logger.error(f"Failed to create SSE adapters for server {server_name}: {e}")
        
        return adapters
    
    @classmethod
    async def _create_default_adapters(cls) -> List:
        adapters = []
        
        try:
            mcp_server_uri = os.environ.get("MCP_SERVER_URI", "http://localhost:3100")
            if not mcp_server_uri.endswith("/sse"):
                mcp_server_uri += "/sse"
            
            server_params = SseServerParams(
                url=mcp_server_uri,
                headers={"x-api-key": os.environ.get("MCP_SERVER_API_KEY", "")}
            )

            default_tools = ["data_provider", "show_tables", "mailer"]
            
            for tool_name in default_tools:
                try:
                    adapter = await SseMcpToolAdapter.from_server_params(server_params, tool_name)
                    adapters.append(adapter)
                except Exception as e:
                    logger.error(f"Failed to create default adapter for tool {tool_name}: {e}")

        except Exception as e:
            logger.error(f"Failed to create default adapters: {e}")
        
        return adapters
    
    @classmethod
    async def _create_adapters_from_config(cls, mcp_servers_config: Dict[str, Any]) -> List:
        all_adapters = []
        
        for server_name, server_config in mcp_servers_config.items():
            if "url" in server_config:
                adapters = await cls._create_sse_adapters(server_name, server_config)
            elif "command" in server_config:
                adapters = await cls._create_stdio_adapters(server_name, server_config)
            else:
                logger.error(f"Invalid server configuration type for {server_name}")
                continue
            
            all_adapters.extend(adapters)
        
        return all_adapters
    
    @classmethod
    async def create(
        cls,
        name: str,
        model_client: ChatCompletionClient,
        system_message: str,
        description: str,
        user_id: str = None
    ):
        logger.info("Initializing MagenticOneCustomMCPAgent...")
        
        adapters = []
        mcp_config = cls._parse_mcp_config(description)
        
        if mcp_config:
            try:
                adapters = await cls._create_adapters_from_config(mcp_config)
                if not adapters:
                    logger.warning("No adapters created from configuration, using defaults")
            except Exception as e:
                logger.error(f"Failed to configure MCP servers: {e}")
        
        if not adapters:
            adapters = await cls._create_default_adapters()
        
        if not adapters:
            logger.error("Failed to create any MCP tool adapters")
        
        return cls(
            name, 
            model_client, 
            system_message, 
            description, 
            adapters,
            user_id=user_id
        )