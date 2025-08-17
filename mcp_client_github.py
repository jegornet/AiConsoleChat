#!/usr/bin/env python3
"""
MCP клиент с автоматическим обнаружением инструментов
"""

import json
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


class GitHubMCPClient:
    def __init__(self, token: str):
        self.token = token
        self.server_params = StdioServerParameters(
            command="sh",
            args=["-c",
                  f"docker run -i --rm -e GITHUB_PERSONAL_ACCESS_TOKEN={token} ghcr.io/github/github-mcp-server 2>/dev/null"]
        )
        self._tools_cache = None

    async def get_tools_schema(self):
        """
        АВТОМАТИЧЕСКИ получает схему всех доступных инструментов от MCP сервера
        Это ключевая функция - она спрашивает у сервера "что ты умеешь?"
        """
        if self._tools_cache is not None:
            return self._tools_cache

        async with stdio_client(self.server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()

                # Получаем список всех доступных инструментов
                # Это стандартный MCP метод - list_tools
                tools_response = await session.list_tools()

                tools_schema = {}
                for tool in tools_response.tools:
                    tools_schema[tool.name] = {
                        'description': tool.description,
                        'inputSchema': tool.inputSchema
                    }

                self._tools_cache = tools_schema
                return tools_schema

    async def call_tool(self, tool_name: str, parameters: dict = None):
        """
        Универсальный метод для вызова любого инструмента
        Работает с любыми инструментами, которые поддерживает MCP сервер
        """
        if parameters is None:
            parameters = {}

        async with stdio_client(self.server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()

                # Вызываем инструмент с переданными параметрами
                result = await session.call_tool(tool_name, parameters)
                return result.content[0].text

    # Для обратной совместимости оставляем специфические методы
    async def get_me(self):
        return await self.call_tool("get_me")

    async def search_repositories(self, query: str):
        return await self.call_tool("search_repositories", {"query": query})

    async def list_branches(self, owner: str, repo: str):
        return await self.call_tool("list_branches", {"owner": owner, "repo": repo})

    async def list_commits(self, owner: str, repo: str, sha: str = None):
        parameters = {"owner": owner, "repo": repo}
        if sha:
            parameters["sha"] = sha
        return await self.call_tool("list_commits", parameters)