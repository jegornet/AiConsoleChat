#!/usr/bin/env python3
"""
Простой консольный чат с ИИ
"""

import anthropic
import json
import os
import sys

from anthropic.types import MessageParam
from dotenv import load_dotenv

from config import MODEL, MAX_TOKENS, TEMPERATURE, SYSTEM_PROMPT


def format_as_ascii_table(data):
    """Форматирует список объектов в ASCII таблицу"""
    if not data or not isinstance(data, list):
        return str(data)
    
    if not data[0] or not isinstance(data[0], dict):
        return str(data)
    
    # Получаем заголовки из первого объекта
    headers = list(data[0].keys())
    
    # Вычисляем максимальную ширину для каждой колонки
    col_widths = {}
    for header in headers:
        col_widths[header] = len(str(header))
        for row in data:
            if header in row:
                col_widths[header] = max(col_widths[header], len(str(row[header])))
    
    # Строим таблицу
    result = []
    
    # Верхняя граница
    top_border = "+" + "+".join("-" * (col_widths[h] + 2) for h in headers) + "+"
    result.append(top_border)
    
    # Заголовки
    header_row = "|" + "|".join(f" {h:<{col_widths[h]}} " for h in headers) + "|"
    result.append(header_row)
    
    # Разделитель
    separator = "+" + "+".join("-" * (col_widths[h] + 2) for h in headers) + "+"
    result.append(separator)
    
    # Строки данных
    for row in data:
        data_row = "|" + "|".join(f" {str(row.get(h, '')):<{col_widths[h]}} " for h in headers) + "|"
        result.append(data_row)
    
    # Нижняя граница
    result.append(top_border)
    
    return "\n".join(result)


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
                
                # Пытаемся распарсить JSON и отформатировать как таблицу
                try:
                    json_data = json.loads(response)
                    if isinstance(json_data, list) and len(json_data) > 0 and isinstance(json_data[0], dict):
                        formatted_output = format_as_ascii_table(json_data)
                        print(formatted_output)
                    else:
                        print(response)
                except json.JSONDecodeError:
                    print(response)
            except Exception as e:
                print(e)

if __name__ == "__main__":
    main()
