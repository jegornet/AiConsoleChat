#!/usr/bin/env python3
"""
MCP сервер для выполнения Python кода в Docker контейнере
"""

import asyncio
import logging
import sys
from mcp.server.lowlevel import Server, NotificationOptions
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import (
    Tool,
    TextContent,
    CallToolResult,
)
import docker


class PythonDockerMCPServer:
    def __init__(self):
        self.server = Server("python-docker-executor")
        self.docker_client = None
        self._setup_logging()
        self._setup_docker()
        self._setup_tools()

    def _setup_logging(self):
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

    def _setup_docker(self):
        try:
            self.docker_client = docker.from_env()
            # Проверяем доступность Docker
            self.docker_client.ping()
            self.logger.info("Docker клиент успешно инициализирован")

            # Проверяем наличие образа Python
            try:
                self.docker_client.images.get("python:3")
                self.logger.info("Docker образ 'python:3' найден")
            except docker.errors.ImageNotFound:
                self.logger.info("Загружаем Docker образ 'python:3'...")
                self.docker_client.images.pull("python:3")

        except Exception as e:
            self.logger.error(f"Ошибка инициализации Docker: {e}")
            raise

    def _setup_tools(self):
        @self.server.list_tools()
        async def handle_list_tools() -> list[Tool]:
            return [
                Tool(
                    name="execute_python",
                    description="Выполняет Python код в изолированном Docker контейнере",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "code": {
                                "type": "string",
                                "description": "Python код для выполнения"
                            }
                        },
                        "required": ["code"]
                    }
                )
            ]

        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: dict) -> CallToolResult:
            if name == "execute_python":
                return await self._execute_python(arguments.get("code", ""))
            else:
                raise ValueError(f"Неизвестный инструмент: {name}")

    async def _execute_python(self, code: str) -> CallToolResult:
        """Выполняет Python код в Docker контейнере"""
        try:
            self.logger.info(f"Выполняем Python код: {code[:100]}...")

            # Запускаем контейнер с Python кодом
            result = self.docker_client.containers.run(
                "python:3",
                ["python", "-c", code],
                remove=True,
            )

            output = result.decode('utf-8') if isinstance(result, bytes) else str(result)
            self.logger.info(f"Результат выполнения: {output[:100]}...")

            return CallToolResult(
                content=[TextContent(type="text", text=output)]
            )

        except Exception as e:
            error_msg = f"Ошибка выполнения: {str(e)}"
            self.logger.error(error_msg)
            return CallToolResult(
                content=[TextContent(type="text", text=error_msg)]
            )

    def execute_code_direct(self, code: str) -> str:
        """
        Прямое выполнение кода без MCP протокола (для тестирования)
        """
        try:
            self.logger.info(f"Прямое выполнение кода: {code[:100]}...")

            result = self.docker_client.containers.run(
                "python:3",
                ["python", "-c", code],
                remove=True,
            )

            output = result.decode('utf-8') if isinstance(result, bytes) else str(result)
            self.logger.info(f"Результат: {output}")
            return output

        except Exception as e:
            error_msg = f"Ошибка выполнения: {str(e)}"
            self.logger.error(error_msg)
            return error_msg

    async def run_server(self):
        """Запуск MCP сервера"""
        self.logger.info("Запуск MCP сервера 'python-docker-executor'...")

        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="python-docker-executor",
                    server_version="1.0.0",
                    capabilities=self.server.get_capabilities(
                        notification_options=NotificationOptions(),
                        experimental_capabilities={},
                    ),
                ),
            )


def main():
    # Если передан аргумент --test, выполняем прямое тестирование
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        print("🧪 Режим прямого тестирования...")
        try:
            server = PythonDockerMCPServer()
            print("✅ Сервер инициализирован!")

            # Тестируем выполнение кода
            print("\n📝 Тест 1: Простой вывод")
            result = server.execute_code_direct("print('Python code test ok')")
            print(f"Результат: {result}")

            # Еще один тест
            print("\n📝 Тест 2: Математические вычисления")
            result = server.execute_code_direct("""
import math
result = math.sqrt(16)
print(f"sqrt(16) = {result}")
for i in range(3):
    print(f"Итерация {i}")
            """)
            print(f"Результат: {result}")

            # Тест с библиотеками
            print("\n📝 Тест 3: Работа с библиотеками")
            result = server.execute_code_direct("""
import json
import datetime

data = {
    "timestamp": str(datetime.datetime.now()),
    "message": "Тест успешен!",
    "numbers": [1, 2, 3, 4, 5]
}

print(json.dumps(data, indent=2, ensure_ascii=False))
            """)
            print(f"Результат: {result}")

            print("\n✅ Все тесты завершены успешно!")

        except Exception as e:
            print(f"❌ Ошибка в тестах: {e}")
            import traceback
            traceback.print_exc()

    else:
        # Обычный режим MCP сервера
        print("🚀 Сервер готов к работе!")
        print("💡 Для тестирования запустите: python mcp_server_python.py --test")
        try:
            server = PythonDockerMCPServer()
            asyncio.run(server.run_server())
        except KeyboardInterrupt:
            print("\n👋 Сервер остановлен пользователем")
        except Exception as e:
            print(f"❌ Ошибка сервера: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    main()