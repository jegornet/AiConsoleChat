from typing import Optional


class SlashCommandHandler:
    """Handles all slash commands for the chat interface"""
    
    def __init__(self, max_tokens: int, is_multiline: bool):
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
    
    def handle_command(self, line: str) -> Optional[str]:
        """Handle any slash command
        
        Args:
            line: Input line containing the command
            
        Returns:
            'quit' if quit command, 'handled' if other command was handled, None if not a command
        """
        if self.is_quit_command(line):
            return 'quit'
        
        if self.handle_max_tokens_command(line):
            return 'handled'
        
        if self.handle_multiline_command(line):
            return 'handled'
        
        return None