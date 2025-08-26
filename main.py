#!/usr/bin/env python3

import asyncio
import json
import os
from typing import Optional
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from anthropic import Anthropic
from dotenv import load_dotenv

from config import MODEL, MAX_TOKENS, IS_MULTILINE, SYSTEM_PROMPT

load_dotenv()  # load environment variables from .env


class MCPClient:
    def __init__(self):
        # Initialize session and client objects
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.anthropic = Anthropic()
        self.max_tokens = MAX_TOKENS  # Current max tokens setting
        self.is_multiline = IS_MULTILINE  # Multiline mode flag

    def load_mcp_config(self, config_path: str = "mcp.json") -> dict:
        """Load MCP configuration from JSON file"""
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"MCP configuration file not found: {config_path}")
        
        with open(config_path, 'r') as f:
            return json.load(f)

    async def connect_to_server(self, server_config: dict):
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

        final_text = []
        max_iterations = 10  # Prevent infinite loops
        iteration = 0

        while iteration < max_iterations:
            iteration += 1
            
            # Claude API call
            response = self.anthropic.messages.create(
                model=MODEL,
                max_tokens=self.max_tokens,
                system=SYSTEM_PROMPT,
                messages=messages,
                tools=available_tools
            )

            # Add assistant message to conversation
            assistant_content = []
            tool_uses = []
            has_tool_calls = False

            for content in response.content:
                if content.type == 'text':
                    final_text.append(content.text)
                    assistant_content.append(content.model_dump())
                elif content.type == 'tool_use':
                    has_tool_calls = True
                    tool_uses.append(content)
                    assistant_content.append(content.model_dump())

            # Add assistant message to conversation history
            if assistant_content:
                messages.append({
                    "role": "assistant", 
                    "content": assistant_content
                })

            # If no tool calls, we're done
            if not has_tool_calls:
                break

            # Execute tool calls and collect results
            tool_results = []
            for tool_use in tool_uses:
                tool_name = tool_use.name
                tool_args = tool_use.input
                tool_id = tool_use.id

                final_text.append(f"[Calling tool {tool_name} with args {tool_args}]")
                
                try:
                    result = await self.session.call_tool(tool_name, tool_args)
                    if result.isError:
                        result_text = f"Error: {result.content[0].text}"
                    else:
                        result_text = result.content[0].text
                    
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tool_id,
                        "content": result_text
                    })
                    final_text.append(f"[Tool result: {result_text}]")
                    
                except Exception as e:
                    error_text = f"Tool execution error: {str(e)}"
                    tool_results.append({
                        "type": "tool_result", 
                        "tool_use_id": tool_id,
                        "content": error_text,
                        "is_error": True
                    })
                    final_text.append(f"[Tool error: {error_text}]")

            # Add tool results to conversation
            if tool_results:
                messages.append({
                    "role": "user",
                    "content": tool_results
                })

        if iteration >= max_iterations:
            final_text.append(f"[Warning: Reached maximum iterations ({max_iterations})]")

        return "\n".join(final_text)

    async def chat_loop(self):
        """Run an interactive chat loop"""
        print("Это чат с ИИ. Команды:")
        print("/quit, /q – выход")
        print(f"/max_tokens [число] – изменить количество токенов (текущее: {self.max_tokens})")
        print("/multiline [on/off] – переключить режим многолинейного ввода")

        line_buffer = []

        while True:
            try:
                # Show appropriate prompt based on buffer state
                if self.is_multiline and line_buffer:
                    prompt = "  "
                else:
                    prompt = "\n> "
                
                line = input(prompt)

                # Check for quit command
                if line.lower() == '/quit' or line.lower() == '/q':
                    break
                
                # Check for max_tokens command
                if line.lower().startswith('/max_tokens'):
                    parts = line.split()
                    if len(parts) == 2:
                        try:
                            new_tokens = int(parts[1])
                            if new_tokens > 0:
                                self.max_tokens = new_tokens
                                print(f"Количество токенов изменено на {self.max_tokens}")
                            else:
                                print("Количество токенов должно быть больше 0")
                        except ValueError:
                            print("Неверный формат числа")
                    else:
                        print(f"Текущее количество токенов: {self.max_tokens}")
                    continue

                # Check for multiline command
                if line.lower().startswith('/multiline'):
                    parts = line.split()
                    if len(parts) == 2 and parts[1].lower() in ['on', 'off']:
                        self.is_multiline = (parts[1].lower() == 'on')
                        print(f"Многолинейный режим {'включен' if self.is_multiline else 'выключен'}")
                    else:
                        print(f"Текущий режим: {'многолинейный' if self.is_multiline else 'однолинейный'}")
                    continue

                if not self.is_multiline:
                    response = await self.process_query(line)
                    print("\n" + response)

                # If line is empty and buffer is not empty, process the message
                if not line and line_buffer:
                    query = "\n".join(line_buffer)
                    line_buffer.clear()
                    
                    response = await self.process_query(query)
                    print("\n" + response)
                
                # If line is not empty, add to buffer
                elif line and self.is_multiline:
                    line_buffer.append(line)

            except Exception as e:
                print(f"\nError: {str(e)}")
                line_buffer.clear()  # Clear buffer on error

    async def cleanup(self):
        """Clean up resources"""
        await self.exit_stack.aclose()


async def main():
    client = MCPClient()
    try:
        # Load MCP configuration
        config = client.load_mcp_config()
        servers = config.get("servers", {})
        
        if not servers:
            raise ValueError("No servers configured in mcp.json")
        
        # Use the first server (you could make this configurable)
        server_name = next(iter(servers))
        server_config = servers[server_name]
        
        print(f"Connecting to server: {server_name}")
        await client.connect_to_server(server_config)
        await client.chat_loop()
    finally:
        await client.cleanup()


if __name__ == "__main__":
    asyncio.run(main())