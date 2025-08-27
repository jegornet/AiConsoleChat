from typing import List

from config import MAX_TOKENS, IS_MULTILINE


class ChatInterface:
    """Handles user interface and chat interaction logic"""
    
    def __init__(self, max_tokens: int = MAX_TOKENS, is_multiline: bool = IS_MULTILINE):
        self.max_tokens = max_tokens
        self.is_multiline = is_multiline
    
    def show_help(self) -> None:
        """Display help information"""
        print("Это чат с ИИ. Команды:")
        print("/quit, /q – выход")
        print(f"/max_tokens [число] – изменить количество токенов (текущее: {self.max_tokens})")
        print("/multiline [on/off] – переключить режим многолинейного ввода")
    
    def handle_max_tokens_command(self, line: str) -> bool:
        """Handle max_tokens command
        
        Args:
            line: Input line containing the command
            
        Returns:
            True if command was handled, False otherwise
        """
        if not line.lower().startswith('/max_tokens'):
            return False
        
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
        
        return True
    
    def handle_multiline_command(self, line: str) -> bool:
        """Handle multiline command
        
        Args:
            line: Input line containing the command
            
        Returns:
            True if command was handled, False otherwise
        """
        if not line.lower().startswith('/multiline'):
            return False
        
        parts = line.split()
        if len(parts) == 2 and parts[1].lower() in ['on', 'off']:
            self.is_multiline = (parts[1].lower() == 'on')
            print(f"Многолинейный режим {'включен' if self.is_multiline else 'выключен'}")
        else:
            print(f"Текущий режим: {'многолинейный' if self.is_multiline else 'однолинейный'}")
        
        return True
    
    def is_quit_command(self, line: str) -> bool:
        """Check if line is a quit command"""
        return line.lower() in ['/quit', '/q']
    
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
        self.show_help()
        line_buffer = []

        while True:
            try:
                prompt = self.get_prompt(bool(line_buffer))
                line = input(prompt)

                if self.is_quit_command(line):
                    break
                
                if self.handle_max_tokens_command(line):
                    claude_chat.set_max_tokens(self.max_tokens)
                    continue
                
                if self.handle_multiline_command(line):
                    continue

                if not self.is_multiline:
                    available_tools = await mcp_client.get_available_tools()
                    response = await claude_chat.process_query(line, available_tools, mcp_client)
                    print("\n" + response)
                else:
                    if not line and line_buffer:
                        query = "\n".join(line_buffer)
                        line_buffer.clear()
                        
                        available_tools = await mcp_client.get_available_tools()
                        response = await claude_chat.process_query(query, available_tools, mcp_client)
                        print("\n" + response)
                    elif line:
                        line_buffer.append(line)

            except Exception as e:
                print(f"\nError: {str(e)}")
                line_buffer.clear()