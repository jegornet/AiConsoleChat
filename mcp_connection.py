import asyncio
from typing import Optional, Dict, Any, List
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


class MCPConnection:
    """Handles connection and interaction with MCP servers"""
    
    def __init__(self):
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self._stdio = None
        self._write = None
    
    async def connect(self, server_config: Dict[str, Any]) -> None:
        """Connect to an MCP server
        
        Args:
            server_config: Server configuration dictionary with 'command' and 'args'
        """
        command = server_config.get('command', 'python3')
        args = server_config.get('args', [])
        env = server_config.get('env', None)
        
        server_params = StdioServerParameters(
            command=command,
            args=args,
            env=env
        )

        stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
        self._stdio, self._write = stdio_transport
        self.session = await self.exit_stack.enter_async_context(ClientSession(self._stdio, self._write))

        await self.session.initialize()
    
    async def get_available_tools(self) -> List[Dict[str, Any]]:
        """Get list of available tools from the MCP server"""
        if not self.session:
            raise RuntimeError("Not connected to MCP server")
        
        response = await self.session.list_tools()
        return [{
            "name": tool.name,
            "description": tool.description,
            "input_schema": tool.inputSchema
        } for tool in response.tools]
    
    async def call_tool(self, tool_name: str, tool_args: Dict[str, Any]) -> Dict[str, Any]:
        """Call a tool on the MCP server
        
        Args:
            tool_name: Name of the tool to call
            tool_args: Arguments to pass to the tool
            
        Returns:
            Dictionary with 'success', 'content', and optionally 'error' keys
        """
        if not self.session:
            raise RuntimeError("Not connected to MCP server")
        
        try:
            result = await self.session.call_tool(tool_name, tool_args)
            if result.isError:
                return {
                    "success": False,
                    "content": result.content[0].text,
                    "error": "Tool returned error"
                }
            else:
                return {
                    "success": True,
                    "content": result.content[0].text
                }
        except Exception as e:
            return {
                "success": False,
                "content": f"Tool execution error: {str(e)}",
                "error": str(e)
            }
    
    async def cleanup(self) -> None:
        """Clean up resources"""
        await self.exit_stack.aclose()