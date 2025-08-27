#!/usr/bin/env python3

import asyncio
from dotenv import load_dotenv

from mcp_connection import MCPConnection
from claude_chat import ClaudeChat
from chat_interface import ChatInterface
from mcp_config_loader import McpConfigLoader

load_dotenv()  # load environment variables from .env


async def main():
    """Main application entry point"""
    mcp_client = MCPConnection()
    claude_chat = ClaudeChat()
    chat_interface = ChatInterface()
    
    try:
        # Load MCP configuration
        config = McpConfigLoader.load_mcp_config()
        server_name, server_config = McpConfigLoader.get_first_server_config(config)
        
        print(f"Connecting to server: {server_name}")
        await mcp_client.connect(server_config)
        
        # Show connected tools
        available_tools = await mcp_client.get_available_tools()
        print("Connected to server with tools:", [tool["name"] for tool in available_tools])
        
        # Start chat loop
        await chat_interface.run_chat_loop(claude_chat, mcp_client)
    finally:
        await mcp_client.cleanup()


if __name__ == "__main__":
    asyncio.run(main())