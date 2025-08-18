#!/usr/bin/env python3
"""
MCP клиент для работы с StatsMCP сервером
"""

import json
import traceback
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
import sys
import os


class StatsMCPClient:
    def __init__(self, github_token: str, debug=True):
        self.github_token = github_token
        self.debug = debug
        self.server_params = StdioServerParameters(
            command="python3",
            args=["-c", f"""
import sys
import os
sys.path.insert(0, '{os.getcwd()}')
os.environ['GITHUB_PERSONAL_ACCESS_TOKEN'] = '{github_token}'
if {debug}:
    os.environ['DEBUG'] = 'true'
from mcp_server_stats import main
import asyncio
asyncio.run(main())
"""]
        )
        self._tools_cache = None

    def _log(self, message):
        """Логирование для отладки"""
        if self.debug:
            print(f"📊 StatsMCP Client: {message}")

    async def get_tools_schema(self):
        """
        Получает схему всех доступных инструментов от StatsMCP сервера
        """
        if self._tools_cache is not None:
            return self._tools_cache

        try:
            self._log("Подключаемся к StatsMCP серверу...")

            async with stdio_client(self.server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    self._log("Инициализируем сессию...")
                    await session.initialize()

                    self._log("Запрашиваем список инструментов...")
                    tools_response = await session.list_tools()

                    tools_schema = {}
                    for tool in tools_response.tools:
                        tools_schema[tool.name] = {
                            'description': tool.description,
                            'inputSchema': tool.inputSchema
                        }
                        self._log(f"Найден инструмент: {tool.name}")

                    self._tools_cache = tools_schema
                    self._log(f"Загружено {len(tools_schema)} инструментов")
                    return tools_schema

        except Exception as e:
            self._log(f"❌ Ошибка при получении схемы инструментов: {e}")
            traceback.print_exc()
            raise

    async def call_tool(self, tool_name: str, parameters: dict = None):
        """
        Универсальный метод для вызова любого инструмента StatsMCP
        """
        if parameters is None:
            parameters = {}

        try:
            self._log(f"Вызываем инструмент: {tool_name}")
            self._log(f"Параметры: {json.dumps(parameters, indent=2, ensure_ascii=False)}")

            async with stdio_client(self.server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()

                    self._log("Отправляем запрос к StatsMCP серверу...")
                    result = await session.call_tool(tool_name, parameters)

                    self._log("Получен ответ от StatsMCP сервера")
                    self._log(f"Тип ответа: {type(result)}")
                    response_text = result.content[0].text
                    preview = response_text[:200] + "..." if len(response_text) > 200 else response_text
                    self._log(f"Содержимое: {preview}")

                    return response_text

        except Exception as e:
            self._log(f"❌ Ошибка при вызове инструмента {tool_name}: {e}")
            self._log(f"Тип ошибки: {type(e).__name__}")

            # Подробный вывод для ExceptionGroup
            if hasattr(e, 'exceptions'):  # ExceptionGroup
                self._log(f"Это ExceptionGroup с {len(e.exceptions)} исключениями:")
                for i, sub_e in enumerate(e.exceptions):
                    self._log(f"  Исключение {i + 1}: {type(sub_e).__name__}: {sub_e}")

            traceback.print_exc()
            raise