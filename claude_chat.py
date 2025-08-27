import os
from typing import List, Dict, Any, Optional
from anthropic import Anthropic
from dotenv import load_dotenv

from config import MODEL, SYSTEM_PROMPT

load_dotenv()


class ClaudeChat:
    """Handles interaction with Anthropic's Claude API"""
    
    def __init__(self, max_tokens: int = 8192):
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY не найден в .env файле")
        self.anthropic = Anthropic(api_key=api_key)
        self.max_tokens = max_tokens
    
    def set_max_tokens(self, max_tokens: int) -> None:
        """Set the maximum number of tokens for responses"""
        if max_tokens > 0:
            self.max_tokens = max_tokens
        else:
            raise ValueError("Max tokens must be greater than 0")
    
    async def process_query(self, query: str, available_tools: List[Dict[str, Any]], 
                          mcp_client) -> str:
        """Process a query using Claude and available tools
        
        Args:
            query: User query
            available_tools: List of available MCP tools
            mcp_client: MCP client instance for tool calls
            
        Returns:
            Final response text
        """
        messages = [{"role": "user", "content": query}]
        final_text = []
        max_iterations = 10
        iteration = 0

        while iteration < max_iterations:
            iteration += 1
            
            response = self.anthropic.messages.create(
                model=MODEL,
                max_tokens=self.max_tokens,
                system=SYSTEM_PROMPT,
                messages=messages,
                tools=available_tools
            )

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

            if assistant_content:
                messages.append({
                    "role": "assistant", 
                    "content": assistant_content
                })

            if not has_tool_calls:
                break

            tool_results = []
            for tool_use in tool_uses:
                tool_name = tool_use.name
                tool_args = tool_use.input
                tool_id = tool_use.id

                final_text.append(f"[Calling tool {tool_name} with args {tool_args}]")
                
                result = await mcp_client.call_tool(tool_name, tool_args)
                
                if result["success"]:
                    result_text = result["content"]
                else:
                    result_text = f"Error: {result['content']}"
                
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_id,
                    "content": result_text,
                    "is_error": not result["success"]
                })
                final_text.append(f"[Tool result: {result_text}]")

            if tool_results:
                messages.append({
                    "role": "user",
                    "content": tool_results
                })

        if iteration >= max_iterations:
            final_text.append(f"[Warning: Reached maximum iterations ({max_iterations})]")

        return "\n".join(final_text)