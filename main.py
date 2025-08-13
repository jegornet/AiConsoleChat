#!/usr/bin/env python3
"""
Простой TUI чат с ИИ на базе curses
"""

import anthropic
import curses
import os
import sys

from dotenv import load_dotenv
from chat_tui import ChatTUI
from config import MODEL, MAX_TOKENS, TEMPERATURE, SYSTEM_PROMPT_AGENT


def main():
    # Загрузка переменных из .env файла
    load_dotenv()
    
    # Проверка наличия API ключа
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("Должна быть установлена переменная окружения ANTHROPIC_API_KEY")
        sys.exit(1)
    
    client = anthropic.Anthropic()
    chat = ChatTUI(client, MODEL, MAX_TOKENS, TEMPERATURE, SYSTEM_PROMPT_AGENT)
    
    try:
        curses.wrapper(chat.run)
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    main()
