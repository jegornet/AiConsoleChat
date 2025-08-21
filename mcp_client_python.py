#!/usr/bin/env python3

import asyncio
from typing import Optional
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from anthropic import Anthropic
from dotenv import load_dotenv

from config import MODEL, MAX_TOKENS

load_dotenv()  # load environment variables from .env


class MCPClient:
    def __init__(self):
        # Initialize session and client objects
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.anthropic = Anthropic()

    async def connect_to_server(self, server_script_path: str):
        """Connect to an MCP server

        Args:
            server_script_path: Path to the server script (.py or .js)
        """
        is_python = server_script_path.endswith('.py')
        is_js = server_script_path.endswith('.js')
        if not (is_python or is_js):
            raise ValueError("Server script must be a .py or .js file")

        command = "python3" if is_python else "node"
        server_params = StdioServerParameters(
            command=command,
            args=[server_script_path],
            env=None
        )

        stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
        self.stdio, self.write = stdio_transport
        self.session = await self.exit_stack.enter_async_context(ClientSession(self.stdio, self.write))

        await self.session.initialize()

        # List available tools
        response = await self.session.list_tools()
        tools = response.tools
        print("\nConnected to server with tools:", [tool.name for tool in tools])

    async def process_query(self, query: str) -> str:
        """Process a query using Claude and available tools"""
        messages = [
            {
                "role": "user",
                "content": query
            }
        ]

        response = await self.session.list_tools()
        available_tools = [{
            "name": tool.name,
            "description": tool.description,
            "input_schema": tool.inputSchema
        } for tool in response.tools]

        # Initial Claude API call
        response = self.anthropic.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system="""
Ты генератор автоматических тестов для кода на Python. 
Пользователь пишет функцию на Python, ты в ответ выдаёшь этот же код, за которым следуют тесты для него.
Критически важно выдавать только Python код, никакого дополнительного текста быть не должно. 
            """,
            messages=messages,
            tools=available_tools
        )

        # Process response and handle tool calls
        tool_results = []
        final_text = []

        for content in response.content:
            if content.type == 'text':
                final_text.append(content.text)
            elif content.type == 'tool_use':
                tool_name = content.name
                tool_args = content.input

                # Execute tool call
                final_text.append(f"[Calling tool {tool_name} with args {tool_args}]")
                result = await self.session.call_tool(tool_name, tool_args)
                tool_results.append({"call": tool_name, "result": result})


                # Continue conversation with tool results
                messages.append({
                    "role": "assistant",
                    "content": result.content[0].text
                })
                if hasattr(result.content[0], 'text'):
                    final_text.append(result.content[0].text)

        return "\n".join(final_text)

    async def chat_loop(self):
        """Run an interactive chat loop"""
        print("\nMCP Client Started!")
        print("Type your queries or 'quit' to exit.")
        print("For multi-line input, enter multiple lines and press Enter on empty line to send.")

        line_buffer = []

        while True:
            try:
                # Show appropriate prompt based on buffer state
                if line_buffer:
                    prompt = "  "
                else:
                    prompt = "\n> "
                
                line = input(prompt)

                # Check for quit command
                if line.lower() == 'quit' or line.lower() == 'q':
                    if line_buffer:
                        print("Discarding buffered input. Goodbye!")
                    break

                # If line is empty and buffer is not empty, process the message
                if not line and line_buffer:
                    query = "\n".join(line_buffer)
                    line_buffer.clear()
                    
                    response = await self.process_query(query)
                    print("\n" + response)
                
                # If line is not empty, add to buffer
                elif line:
                    line_buffer.append(line)

            except Exception as e:
                print(f"\nError: {str(e)}")
                line_buffer.clear()  # Clear buffer on error

    async def cleanup(self):
        """Clean up resources"""
        await self.exit_stack.aclose()


async def main():
    server = "mcp_server_python.py"
    client = MCPClient()
    try:
        await client.connect_to_server(server)
        await client.chat_loop()
    finally:
        await client.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
