#!/usr/bin/env python3
"""
Консольный чат с ИИ использующий MCP
"""

import anthropic
import os
import sys
import asyncio
import argparse
import json

from anthropic.types import MessageParam
from dotenv import load_dotenv

from config import MODEL, MAX_TOKENS, TEMPERATURE
from mcp_client_github import GitHubMCPClient


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
    args = parser.parse_args()

    load_dotenv()

    if not os.getenv("ANTHROPIC_API_KEY"):
        print("Должна быть установлена переменная окружения ANTHROPIC_API_KEY")
        sys.exit(1)

    if not os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN"):
        print("Должна быть установлена переменная окружения GITHUB_PERSONAL_ACCESS_TOKEN")
        sys.exit(1)

    # Создаём MCP клиент
    mcp_client = GitHubMCPClient(os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN"))

    # Получаем схему инструментов от MCP сервера
    print("Получаем список доступных инструментов...")
    tools_schema = await mcp_client.get_tools_schema()

    # Конвертируем в формат Anthropic Function Calling
    anthropic_tools = convert_mcp_to_anthropic_tools(tools_schema)

    print(f"Обнаружено {len(tools_schema)} инструментов:")
    for tool_name in tools_schema:
        print(f"  - {tool_name}")
    print()

    client = anthropic.Anthropic()
    conversation = []

    system_prompt = """Ты - полезный ассистент с доступом к GitHub через MCP инструменты.

Когда пользователь задает вопросы о GitHub (репозитории, коммиты, пользователи и т.д.), 
используй доступные инструменты для получения актуальной информации.

Анализируй результаты инструментов и давай полезные ответы пользователю."""

    if args.prompt:
        await process_user_prompt(args.prompt, client, mcp_client, conversation, anthropic_tools, system_prompt)
    else:
        print("Это чат с ИИ с Function Calling для MCP. Когда надоест, введи q")
        while True:
            user_prompt = input("> ")

            if user_prompt == "q":
                break

            await process_user_prompt(user_prompt, client, mcp_client, conversation, anthropic_tools, system_prompt)


async def process_user_prompt(user_prompt, client, mcp_client, conversation, tools, system_prompt):
    conversation.append(MessageParam(role="user", content=user_prompt))

    try:
        max_iterations = 5
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

            response_content = message.content[0]

            # Проверяем, хочет ли модель вызвать инструмент
            if message.stop_reason == "tool_use":
                # Модель хочет использовать инструмент
                tool_use = None
                text_content = ""

                for content_block in message.content:
                    if hasattr(content_block, 'type'):
                        if content_block.type == "text":
                            text_content += content_block.text
                        elif content_block.type == "tool_use":
                            tool_use = content_block

                if tool_use:
                    # Добавляем ответ модели в беседу
                    conversation.append(MessageParam(role="assistant", content=message.content))

                    # Вызываем инструмент через MCP
                    try:
                        tool_result = await mcp_client.call_tool(
                            tool_use.name,
                            tool_use.input
                        )

                        # Добавляем результат инструмента в беседу
                        conversation.append(MessageParam(
                            role="user",
                            content=[
                                {
                                    "type": "tool_result",
                                    "tool_use_id": tool_use.id,
                                    "content": tool_result
                                }
                            ]
                        ))

                        iteration += 1
                        continue

                    except Exception as e:
                        print(f"Ошибка выполнения инструмента {tool_use.name}: {e}")
                        break
            else:
                # Модель дала финальный ответ без инструментов
                conversation.append(MessageParam(role="assistant", content=message.content))
                print(response_content.text)
                break

    except Exception as e:
        print(f"Ошибка: {e}")


if __name__ == "__main__":
    asyncio.run(main())
