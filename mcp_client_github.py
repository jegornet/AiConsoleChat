#!/usr/bin/env python3
import asyncio
import os
import json
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def get_my_repos_with_commits(token: str):
    server_params = StdioServerParameters(
        command="docker",
        args=["run", "-i", "--rm", "-e", f"GITHUB_PERSONAL_ACCESS_TOKEN={token}",
              "ghcr.io/github/github-mcp-server"]
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Получаем информацию о текущем пользователе
            user_result = await session.call_tool("get_me", {})
            user_data = json.loads(user_result.content[0].text)
            username = user_data["login"]

            # Получаем репозитории этого пользователя
            repos_result = await session.call_tool(
                "search_repositories",
                {"query": f"user:{username}"}
            )

            repos_data = json.loads(repos_result.content[0].text)
            repos = repos_data.get("items", [])

            repo_commits = []

            for repo in repos:
                repo_name = repo["name"]
                try:
                    # Получаем коммиты для каждого репозитория
                    commits_result = await session.call_tool(
                        "list_commits",
                        {"owner": username, "repo": repo_name}
                    )
                    commits_data = json.loads(commits_result.content[0].text)
                    commit_count = len(commits_data)
                    repo_commits.append((repo_name, commit_count))
                except Exception:
                    # Если не удалось получить коммиты (приватный репо, ошибка и т.д.)
                    repo_commits.append((repo_name, 0))

            return repo_commits
