#!/usr/bin/env python3
"""
Простой консольный чат с ИИ
"""

import anthropic
import os
import sys

from anthropic.types import MessageParam
from dotenv import load_dotenv

from config import MODEL, MAX_TOKENS, TEMPERATURE, SYSTEM_PROMPT


def main():
    # Загрузка переменных из .env файла
    load_dotenv()
    
    # Проверка наличия API ключа
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("Должна быть установлена переменная окружения ANTHROPIC_API_KEY")
        sys.exit(1)
    
    client = anthropic.Anthropic()
    conversation = []

    print("Введи список городов через запятую или q для выхода")
    while True:
        user_prompt = input("> ")

        if user_prompt == "q":
            break

        conversation.append(MessageParam(role="user", content=user_prompt))

        if user_prompt:
            try:
                message = client.messages.create(
                    model=MODEL,
                    max_tokens=MAX_TOKENS,
                    temperature=TEMPERATURE,
                    system=SYSTEM_PROMPT,
                    messages=conversation,
                )
                response = message.content[0].text
                conversation.append(MessageParam(role="assistant", content=response))
                print(response)
            except Exception as e:
                print(e)

if __name__ == "__main__":
    main()
