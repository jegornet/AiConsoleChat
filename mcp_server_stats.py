#!/usr/bin/env python3
"""
StatsMCP - MCP сервер для получения статистики GitHub через GitHubMCPClient
"""

import json
import asyncio
import traceback
from typing import Dict, Any
from mcp import Tool
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import JSONRPCError, TextContent, ServerCapabilities
from mcp.server.lowlevel.server import InitializationOptions

from mcp_client_github import GitHubMCPClient


class StatsMCPServer:
    def __init__(self, github_token: str, debug: bool = False):
        self.github_client = GitHubMCPClient(github_token, debug=debug)
        self.debug = debug
        self.app = Server("stats-mcp")
        self._setup_tools()

    def _log(self, message):
        """Логирование для отладки"""
        if self.debug:
            print(f"📊 StatsMCP: {message}")

    def _setup_tools(self):
        """Настройка инструментов MCP сервера"""
        
        @self.app.list_tools()
        async def list_tools() -> list[Tool]:
            return [
                Tool(
                    name="github_stats",
                    description="Получить статистику по коммитам для всех репозиториев текущего пользователя GitHub",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                )
            ]

        @self.app.call_tool()
        async def call_tool(name: str, arguments: Dict[str, Any] | None = None) -> list[dict]:
            if name == "github_stats":
                return await self._get_github_stats()
            else:
                raise JSONRPCError(f"Неизвестный инструмент: {name}")

    async def _get_github_stats(self) -> list[dict]:
        """Основная логика получения статистики GitHub"""
        try:
            self._log("Начинаем сбор статистики GitHub...")

            # 1. Найти имя текущего пользователя на GitHub
            self._log("Получаем информацию о текущем пользователе...")
            user_info = await self.github_client.call_tool("get_me")
            user_data = json.loads(user_info)
            username = user_data['login']
            self._log(f"Пользователь: {username}")

            # 2. Получить список репозиториев текущего пользователя
            self._log("Получаем список репозиториев...")
            repos_info = await self.github_client.call_tool("search_repositories", {"query": f"user:{username}"})
            repos_data = json.loads(repos_info)
            # search_repositories возвращает структуру {"items": [...], "total_count": ...}
            repos_list = repos_data.get("items", [])
            self._log(f"Найдено {len(repos_list)} репозиториев")

            stats = {
                "username": username,
                "repositories": [],
                "total_commits": 0,
                "total_repositories": len(repos_list)
            }

            # 3-5. Для каждого репозитория получить ветки и посчитать коммиты
            for repo in repos_list:
                repo_name = repo['name']
                repo_full_name = repo['full_name']
                self._log(f"Обрабатываем репозиторий: {repo_name}")

                try:
                    # Получить список веток для репозитория
                    branches_info = await self.github_client.call_tool("list_branches", {
                        "owner": username,
                        "repo": repo_name
                    })
                    branches_data = json.loads(branches_info)
                    self._log(f"  Найдено {len(branches_data)} веток")

                    repo_stats = {
                        "name": repo_name,
                        "full_name": repo_full_name,
                        "branches": [],
                        "total_commits": 0
                    }

                    # Для каждой ветки посчитать количество коммитов
                    for branch in branches_data:
                        branch_name = branch['name']
                        self._log(f"    Обрабатываем ветку: {branch_name}")

                        try:
                            # Получить коммиты в ветке
                            commits_info = await self.github_client.call_tool("list_commits", {
                                "owner": username,
                                "repo": repo_name,
                                "sha": branch_name
                            })
                            commits_data = json.loads(commits_info)
                            commits_count = len(commits_data)
                            
                            branch_stats = {
                                "name": branch_name,
                                "commits_count": commits_count
                            }
                            
                            repo_stats["branches"].append(branch_stats)
                            repo_stats["total_commits"] += commits_count
                            self._log(f"      Коммитов в ветке {branch_name}: {commits_count}")

                        except Exception as e:
                            self._log(f"      ❌ Ошибка при получении коммитов для ветки {branch_name}: {e}")
                            # Добавляем ветку с ошибкой
                            repo_stats["branches"].append({
                                "name": branch_name,
                                "commits_count": 0,
                                "error": str(e)
                            })

                    stats["repositories"].append(repo_stats)
                    stats["total_commits"] += repo_stats["total_commits"]
                    self._log(f"  Всего коммитов в {repo_name}: {repo_stats['total_commits']}")

                except Exception as e:
                    self._log(f"  ❌ Ошибка при обработке репозитория {repo_name}: {e}")
                    # Добавляем репозиторий с ошибкой
                    stats["repositories"].append({
                        "name": repo_name,
                        "full_name": repo_full_name,
                        "error": str(e),
                        "branches": [],
                        "total_commits": 0
                    })

            self._log(f"Сбор статистики завершен. Всего коммитов: {stats['total_commits']}")

            # Возвращаем результат в формате MCP
            return [TextContent(type="text", text=json.dumps(stats, indent=2, ensure_ascii=False))]

        except Exception as e:
            error_msg = f"Ошибка при сборе статистики: {str(e)}"
            self._log(f"❌ {error_msg}")
            traceback.print_exc()
            return [TextContent(type="text", text=json.dumps({"error": error_msg}, ensure_ascii=False))]

    async def run(self):
        """Запуск MCP сервера"""
        self._log("Запуск StatsMCP сервера...")
        async with stdio_server() as streams:
            init_options = InitializationOptions(
                server_name="stats-mcp",
                server_version="1.0.0", 
                capabilities=ServerCapabilities(tools={})
            )
            await self.app.run(*streams, init_options)


async def main():
    """Точка входа для запуска сервера"""
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    github_token = os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN")
    if not github_token:
        print("Ошибка: не установлена переменная окружения GITHUB_PERSONAL_ACCESS_TOKEN")
        return 1
        
    debug = os.getenv("DEBUG", "").lower() in ("true", "1", "yes")
    
    server = StatsMCPServer(github_token, debug=debug)
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())