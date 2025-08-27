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
        self.session_input_tokens = 0
        self.session_output_tokens = 0
    
    def set_max_tokens(self, max_tokens: int) -> None:
        """Set the maximum number of tokens for responses"""
        if max_tokens > 0:
            self.max_tokens = max_tokens
        else:
            raise ValueError("Max tokens must be greater than 0")
    
    def get_session_token_usage(self) -> Dict[str, int]:
        """Get current session token usage"""
        return {
            "input_tokens": self.session_input_tokens,
            "output_tokens": self.session_output_tokens,
            "total_tokens": self.session_input_tokens + self.session_output_tokens
        }
    
    def reset_session_token_usage(self) -> None:
        """Reset session token counters"""
        self.session_input_tokens = 0
        self.session_output_tokens = 0
    
    async def process_query(self, query: str, available_tools: List[Dict[str, Any]], 
                          mcp_client) -> tuple[str, Dict[str, int]]:
        """Process a query using Claude and available tools
        
        Args:
            query: User query
            available_tools: List of available MCP tools
            mcp_client: MCP client instance for tool calls
            
        Returns:
            Tuple of (final response text, token usage for this request)
        """
        messages = [{"role": "user", "content": query}]
        final_text = []
        max_iterations = 10
        iteration = 0
        request_input_tokens = 0
        request_output_tokens = 0

        while iteration < max_iterations:
            iteration += 1
            
            response = self.anthropic.messages.create(
                model=MODEL,
                max_tokens=self.max_tokens,
                system=SYSTEM_PROMPT,
                messages=messages,
                tools=available_tools
            )
            
            # Track token usage
            if hasattr(response, 'usage'):
                request_input_tokens += response.usage.input_tokens
                request_output_tokens += response.usage.output_tokens
                self.session_input_tokens += response.usage.input_tokens
                self.session_output_tokens += response.usage.output_tokens

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

        request_usage = {
            "input_tokens": request_input_tokens,
            "output_tokens": request_output_tokens,
            "total_tokens": request_input_tokens + request_output_tokens
        }

        return "\n".join(final_text), request_usage