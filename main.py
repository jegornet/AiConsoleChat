#!/usr/bin/env python3
"""
Простой консольный чат с ИИ
"""

import argparse
import anthropic
import os
import sys

from anthropic.types import MessageParam
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
    # Парсинг аргументов командной строки
    parser = argparse.ArgumentParser(description="Консольный чат с ИИ")
    parser.add_argument("--model", choices=models_list, help="Модель для использования")
    parser.add_argument("--max-tokens", type=int, help="Максимальное количество токенов")
    parser.add_argument("--temperature", type=float, help="Температура (0.0-1.0)")
    parser.add_argument("--system-prompt", help="Системный промпт")
    parser.add_argument("--exec-prompt", help="Выполнить промпт и выйти")
    parser.add_argument("--exec-prompt-file", help="Выполнить промпт из файла и выйти")
    args = parser.parse_args()

    # Загрузка переменных из .env файла
    load_dotenv()
    
    # Проверка наличия API ключа
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("Должна быть установлена переменная окружения ANTHROPIC_API_KEY")
        sys.exit(1)
    
    # Валидация аргументов командной строки
    if args.temperature is not None and not (0.0 <= args.temperature <= 1.0):
        print("Температура должна быть от 0.0 до 1.0")
        sys.exit(1)
    
    if args.max_tokens is not None and args.max_tokens <= 0:
        print("Количество токенов должно быть положительным числом")
        sys.exit(1)

    client = anthropic.Anthropic()
    current_model = args.model if args.model else MODEL
    current_temperature = args.temperature if args.temperature is not None else TEMPERATURE
    current_max_tokens = args.max_tokens if args.max_tokens else MAX_TOKENS
    current_system_prompt = args.system_prompt if args.system_prompt else SYSTEM_PROMPT

    # Обработка режима выполнения одного промпта
    exec_prompt_text = None
    if args.exec_prompt:
        exec_prompt_text = args.exec_prompt
    elif args.exec_prompt_file:
        try:
            with open(args.exec_prompt_file, 'r', encoding='utf-8') as f:
                exec_prompt_text = f.read().strip()
        except FileNotFoundError:
            print(f"Файл не найден: {args.exec_prompt_file}")
            sys.exit(1)
        except Exception as e:
            print(f"Ошибка при чтении файла: {e}")
            sys.exit(1)

    if exec_prompt_text:
        try:
            message = client.messages.create(
                model=current_model,
                max_tokens=current_max_tokens,
                temperature=current_temperature,
                system=current_system_prompt,
                messages=[MessageParam(role="user", content=exec_prompt_text)],
            )
            response = message.content[0].text
            print(response)
        except Exception as e:
            print(e)
            sys.exit(1)
        return

    conversation = []
    print("Это чат с ИИ. Доступные команды:")
    print("/models - список моделей")
    print("/model <название> - сменить модель")
    print("/temperature <значение> - установить температуру (0.0-1.0)")
    print("/max_tokens <значение> - установить максимальное количество токенов")
    print("/clear - очистить диалог")
    print("/q - выход")
    while True:
        user_prompt = input("> ")

        if user_prompt == "/q":
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

        if user_prompt.startswith("/temperature "):
            temp_str = user_prompt[13:].strip()
            try:
                temp_value = float(temp_str)
                if 0.0 <= temp_value <= 1.0:
                    current_temperature = temp_value
                    print(f"Температура изменена на: {current_temperature}")
                else:
                    print("Температура должна быть от 0.0 до 1.0")
            except ValueError:
                print("Неверный формат температуры. Используйте число от 0.0 до 1.0")
            continue

        if user_prompt.startswith("/max_tokens "):
            tokens_str = user_prompt[12:].strip()
            try:
                tokens_value = int(tokens_str)
                if tokens_value > 0:
                    current_max_tokens = tokens_value
                    print(f"Максимальное количество токенов изменено на: {current_max_tokens}")
                else:
                    print("Количество токенов должно быть положительным числом")
            except ValueError:
                print("Неверный формат количества токенов. Используйте положительное целое число")
            continue

        if user_prompt == "/clear":
            conversation = []
            print("Диалог очищен")
            continue

        conversation.append(MessageParam(role="user", content=user_prompt))

        if user_prompt:
            try:
                message = client.messages.create(
                    model=current_model,
                    max_tokens=current_max_tokens,
                    temperature=current_temperature,
                    system=current_system_prompt,
                    messages=conversation,
                )
                response = message.content[0].text
                conversation.append(MessageParam(role="assistant", content=response))
                print(response)
            except Exception as e:
                print(e)

if __name__ == "__main__":
    main()
