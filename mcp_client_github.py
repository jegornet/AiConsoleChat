#!/usr/bin/env python3
"""
MCP клиент с автоматическим обнаружением инструментов и подробным логированием
"""

import json
import traceback
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


class GitHubMCPClient:
    def __init__(self, token: str, debug=True):
        self.token = token
        self.debug = debug
        self.server_params = StdioServerParameters(
            command="sh",
            args=["-c",
                  f"docker run -i --rm -e GITHUB_PERSONAL_ACCESS_TOKEN={token} ghcr.io/github/github-mcp-server 2>/dev/null"]
        )
        self._tools_cache = None

    def _log(self, message):
        """Логирование для отладки"""
        if self.debug:
            print(f"🔧 MCP: {message}")

    async def get_tools_schema(self):
        """
        АВТОМАТИЧЕСКИ получает схему всех доступных инструментов от MCP сервера
        """
        if self._tools_cache is not None:
            return self._tools_cache

        try:
            self._log("Подключаемся к MCP серверу...")

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
            # Выводим подробный traceback
            traceback.print_exc()
            raise

    async def call_tool(self, tool_name: str, parameters: dict = None):
        """
        Универсальный метод для вызова любого инструмента с подробным логированием
        """
        if parameters is None:
            parameters = {}

        try:
            self._log(f"Вызываем инструмент: {tool_name}")
            self._log(f"Параметры: {json.dumps(parameters, indent=2, ensure_ascii=False)}")

            async with stdio_client(self.server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()

                    self._log("Отправляем запрос к MCP серверу...")
                    result = await session.call_tool(tool_name, parameters)

                    self._log("Получен ответ от MCP сервера")
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

            # Выводим полный traceback
            traceback.print_exc()
            raise
