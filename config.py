"""
Конфигурация для консольного чата с ИИ
"""

# Константы для API
MODEL = "claude-3-5-haiku-latest"
MAX_TOKENS = 4000  # По умолчанию 4000 токенов
IS_MULTILINE = False
SYSTEM_PROMPT = "Ты бот-помощник программиста, использующий MCP-инструменты."
