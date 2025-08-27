from typing import List

from config import MAX_TOKENS, IS_MULTILINE
from slash_commands import SlashCommandHandler


class ChatInterface:
    """Handles user interface and chat interaction logic"""
    
    def __init__(self, max_tokens: int = MAX_TOKENS, is_multiline: bool = IS_MULTILINE):
        self.max_tokens = max_tokens
        self.is_multiline = is_multiline
        self.command_handler = SlashCommandHandler(max_tokens, is_multiline)
    
    def get_prompt(self, has_buffer: bool = False) -> str:
        """Get input prompt based on current state"""
        if self.is_multiline and has_buffer:
            return "  "
        else:
            return "\n> "
    
    async def run_chat_loop(self, claude_chat, mcp_client) -> None:
        """Run the main chat loop
        
        Args:
            claude_chat: ClaudeChat instance
            mcp_client: MCPConnection instance
        """
        self.command_handler.show_help()
        line_buffer = []

        while True:
            try:
                prompt = self.get_prompt(bool(line_buffer))
                line = input(prompt)

                command_result = self.command_handler.handle_command(line)
                if command_result == 'quit':
                    break
                elif command_result == 'handled':
                    if line.lower().startswith('/max_tokens'):
                        claude_chat.set_max_tokens(self.command_handler.max_tokens)
                        self.max_tokens = self.command_handler.max_tokens
                    elif line.lower().startswith('/multiline'):
                        self.is_multiline = self.command_handler.is_multiline
                    continue

                if not self.is_multiline:
                    available_tools = await mcp_client.get_available_tools()
                    response, token_usage = await claude_chat.process_query(line, available_tools, mcp_client)
                    print("\n" + response)
                    session_usage = claude_chat.get_session_token_usage()
                    print(f"\n[Токены за запрос: {token_usage['input_tokens']} вход + {token_usage['output_tokens']} выход = {token_usage['total_tokens']} всего]")
                    print(f"[Токены за сессию: {session_usage['input_tokens']} вход + {session_usage['output_tokens']} выход = {session_usage['total_tokens']} всего]")
                else:
                    if not line and line_buffer:
                        query = "\n".join(line_buffer)
                        line_buffer.clear()
                        
                        available_tools = await mcp_client.get_available_tools()
                        response, token_usage = await claude_chat.process_query(query, available_tools, mcp_client)
                        print("\n" + response)
                        session_usage = claude_chat.get_session_token_usage()
                        print(f"\n[Токены за запрос: {token_usage['input_tokens']} вход + {token_usage['output_tokens']} выход = {token_usage['total_tokens']} всего]")
                        print(f"[Токены за сессию: {session_usage['input_tokens']} вход + {session_usage['output_tokens']} выход = {session_usage['total_tokens']} всего]")
                    elif line:
                        line_buffer.append(line)

            except Exception as e:
                print(f"\nError: {str(e)}")
                line_buffer.clear()