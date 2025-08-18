#!/usr/bin/env python3
"""
Консольный чат с ИИ использующий MCP
"""

import anthropic
import os
import sys
import asyncio
import argparse
import traceback

from anthropic.types import MessageParam
from dotenv import load_dotenv

from config import MODEL, MAX_TOKENS, TEMPERATURE, COST_MTOKENS_IN, COST_MTOKENS_OUT
from mcp_client_stats import StatsMCPClient


def calculate_cost(input_tokens, output_tokens):
    """Вычисляет стоимость запроса на основе количества токенов"""
    input_cost = (input_tokens / 1_000_000) * COST_MTOKENS_IN
    output_cost = (output_tokens / 1_000_000) * COST_MTOKENS_OUT
    
    return input_cost + output_cost


def print_detailed_error(context, error):
    """Выводит подробную информацию об ошибке, включая саб-исключения"""
    print(f"\n❌ {context}:")
    print(f"Тип ошибки: {type(error).__name__}")
    print(f"Сообщение: {error}")

    # Обрабатываем ExceptionGroup (TaskGroup ошибки)
    if isinstance(error, ExceptionGroup):
        print(f"\n📦 ExceptionGroup содержит {len(error.exceptions)} исключений:")
        for i, sub_error in enumerate(error.exceptions, 1):
            print(f"\n  🔸 Исключение {i}:")
            print(f"     Тип: {type(sub_error).__name__}")
            print(f"     Сообщение: {sub_error}")
            print(f"     Traceback:")
            # Выводим traceback для каждого саб-исключения
            sub_traceback = ''.join(traceback.format_exception(type(sub_error), sub_error, sub_error.__traceback__))
            for line in sub_traceback.split('\n'):
                if line.strip():
                    print(f"       {line}")
    else:
        # Обычное исключение
        print(f"\n📋 Полный traceback:")
        error_traceback = ''.join(traceback.format_exception(type(error), error, error.__traceback__))
        for line in error_traceback.split('\n'):
            if line.strip():
                print(f"  {line}")

    print()  # Пустая строка для разделения


def convert_mcp_to_anthropic_tools(tools_schema):
    """Конвертирует MCP схему в формат Function Calling Anthropic"""
    anthropic_tools = []

    for tool_name, tool_info in tools_schema.items():
        anthropic_tool = {
            "name": tool_name,
            "description": tool_info.get('description', f'Инструмент {tool_name}'),
            "input_schema": tool_info.get('inputSchema', {"type": "object", "properties": {}})
        }
        anthropic_tools.append(anthropic_tool)

    return anthropic_tools


async def main():
    parser = argparse.ArgumentParser(description="Консольный чат с ИИ")
    parser.add_argument("-p", "--prompt", type=str, help="Первый промпт для отправки")
    parser.add_argument("-d", "--debug", action="store_true", help="Включить отладочный вывод")
    args = parser.parse_args()

    load_dotenv()

    if not os.getenv("ANTHROPIC_API_KEY"):
        print("Должна быть установлена переменная окружения ANTHROPIC_API_KEY")
        sys.exit(1)

    if not os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN"):
        print("Должна быть установлена переменная окружения GITHUB_PERSONAL_ACCESS_TOKEN")
        sys.exit(1)

    # Создаём StatsMCP клиент с отладкой
    mcp_client = StatsMCPClient(os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN"), debug=args.debug)

    # Получаем схему инструментов от MCP сервера
    if args.debug:
        print("Получаем список доступных инструментов...")
    try:
        tools_schema = await mcp_client.get_tools_schema()

        # Конвертируем в формат Anthropic Function Calling
        anthropic_tools = convert_mcp_to_anthropic_tools(tools_schema)

        if args.debug:
            print(f"Обнаружено {len(tools_schema)} инструментов:")
            for tool_name in tools_schema:
                print(f"  - {tool_name}")
            print()

    except Exception as e:
        print_detailed_error("Не удалось получить список инструментов", e)
        print("\n💡 Возможные причины:")
        print("  - StatsMCP сервер не может запуститься")
        print("  - Неверный GITHUB_PERSONAL_ACCESS_TOKEN")  
        print("  - Проблемы с зависимостями Python")
        print("  - Проблемы с доступом к GitHub MCP серверу")
        sys.exit(1)

    client = anthropic.Anthropic()
    conversation = []

    system_prompt = """Ты ассистент программиста и у тебя есть доступ к GitHub статистике через MCP инструменты.

Когда пользователь задает вопросы о GitHub статистике (репозитории, коммиты и т.д.), 
используй доступный инструмент github_stats для получения подробной статистики.

Анализируй результаты инструментов и давай полезные ответы пользователю с красивым форматированием."""

    if args.prompt:
        await process_user_prompt(args.prompt, client, mcp_client, conversation, anthropic_tools, system_prompt)
    else:
        print("Это чат с ИИ, использующий MCP. Когда надоест, введи q")
        while True:
            user_prompt = input("> ")

            if user_prompt == "q":
                break

            if user_prompt != "":
                await process_user_prompt(user_prompt, client, mcp_client, conversation, anthropic_tools, system_prompt)


async def process_user_prompt(user_prompt, client, mcp_client, conversation, tools, system_prompt):
    conversation.append(MessageParam(role="user", content=user_prompt))

    total_cost = 0.0
    total_input_tokens = 0
    total_output_tokens = 0

    try:
        max_iterations = 10
        iteration = 0

        while iteration < max_iterations:
            # Отправляем сообщение с доступными инструментами
            message = client.messages.create(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                temperature=TEMPERATURE,
                system=system_prompt,
                messages=conversation,
                tools=tools  # Передаём доступные инструменты
            )
            
            # Рассчитываем стоимость запроса
            if hasattr(message, 'usage') and message.usage:
                cost = calculate_cost(
                    message.usage.input_tokens,
                    message.usage.output_tokens,
                )
                total_cost += cost
                total_input_tokens += message.usage.input_tokens
                total_output_tokens += message.usage.output_tokens
            else:
                print("\n⚠️ Информация о токенах недоступна")

            response_content = message.content[0]

            # Проверяем, хочет ли модель вызвать инструмент
            if message.stop_reason == "tool_use":
                # Модель хочет использовать инструменты
                tool_uses = []
                text_content = ""

                for content_block in message.content:
                    if hasattr(content_block, 'type'):
                        if content_block.type == "text":
                            text_content += content_block.text
                        elif content_block.type == "tool_use":
                            tool_uses.append(content_block)

                if tool_uses:
                    # Добавляем ответ модели в беседу
                    conversation.append(MessageParam(role="assistant", content=message.content))

                    # Вызываем все инструменты и собираем результаты
                    tool_results = []
                    
                    for tool_use in tool_uses:
                        try:
                            tool_result = await mcp_client.call_tool(
                                tool_use.name,
                                tool_use.input
                            )

                            tool_results.append({
                                "type": "tool_result",
                                "tool_use_id": tool_use.id,
                                "content": tool_result
                            })

                        except Exception as e:
                            print_detailed_error(f"Ошибка выполнения инструмента {tool_use.name}", e)
                            # Добавляем результат с ошибкой
                            tool_results.append({
                                "type": "tool_result",
                                "tool_use_id": tool_use.id,
                                "content": f"Ошибка: {str(e)}"
                            })

                    # Добавляем все результаты инструментов в одном сообщении
                    conversation.append(MessageParam(
                        role="user",
                        content=tool_results
                    ))

                    iteration += 1
                    continue
            else:
                # Модель дала финальный ответ без инструментов
                conversation.append(MessageParam(role="assistant", content=message.content))
                print(response_content.text)
                break

    except Exception as e:
        print_detailed_error("Общая ошибка при обработке запроса", e)

    print(f"\n💰 С вас ${total_cost:.4f} (вход: {total_input_tokens}, выход: {total_output_tokens} токенов)")


if __name__ == "__main__":
    asyncio.run(main())