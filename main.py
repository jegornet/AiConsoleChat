#!/usr/bin/env python3
"""
Простой консольный чат с ИИ
"""

import anthropic
import os
import sys

from anthropic.types import MessageParam, ModelParam
from dotenv import load_dotenv

from config import MODEL, MAX_TOKENS, TEMPERATURE, SYSTEM_PROMPT


models_list = [
    "claude-3-7-sonnet-latest",
    "claude-3-7-sonnet-20250219",
    "claude-3-5-haiku-latest",
    "claude-3-5-haiku-20241022",
    "claude-sonnet-4-20250514",
    "claude-sonnet-4-0",
    "claude-4-sonnet-20250514",
    "claude-3-5-sonnet-latest",
    "claude-3-5-sonnet-20241022",
    "claude-3-5-sonnet-20240620",
    "claude-opus-4-0",
    "claude-opus-4-20250514",
    "claude-4-opus-20250514",
    "claude-opus-4-1-20250805",
    "claude-3-opus-latest",
    "claude-3-opus-20240229",
    "claude-3-haiku-20240307",
]

def main():
    # Загрузка переменных из .env файла
    load_dotenv()
    
    # Проверка наличия API ключа
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("Должна быть установлена переменная окружения ANTHROPIC_API_KEY")
        sys.exit(1)
    
    client = anthropic.Anthropic()
    conversation = []
    current_model = MODEL

    print("Это чат с ИИ. Когда надоест, введи q")
    print("Доступные команды: /models - список моделей, /model <название> - сменить модель")
    while True:
        user_prompt = input("> ")

        if user_prompt == "q":
            break

        if user_prompt == "/models":
            print("Доступные модели:")
            for model in models_list:
                print(f"- {model}")
            continue

        if user_prompt.startswith("/model "):
            model_name = user_prompt[7:].strip()
            if model_name in models_list:
                current_model = model_name
                print(f"Модель изменена на: {current_model}")
            else:
                print("Неизвестная модель. Используйте /models для просмотра доступных моделей.")
            continue

        conversation.append(MessageParam(role="user", content=user_prompt))

        if user_prompt:
            try:
                message = client.messages.create(
                    model=current_model,
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
