#!/usr/bin/env python3
import json
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def get_my_repos_with_commits(token: str):
    server_params = StdioServerParameters(
        command="sh",
        args=["-c",
              f"docker run -i --rm -e GITHUB_PERSONAL_ACCESS_TOKEN={token} ghcr.io/github/github-mcp-server 2>/dev/null"]
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
                repo_description = repo.get("description", "")
                try:
                    # Получаем список всех веток
                    branches_result = await session.call_tool(
                        "list_branches",
                        {"owner": username, "repo": repo_name}
                    )
                    branches_data = json.loads(branches_result.content[0].text)
                    
                    unique_commits = set()
                    
                    # Подсчитываем коммиты по всем веткам
                    for branch in branches_data:
                        branch_name = branch["name"]
                        try:
                            commits_result = await session.call_tool(
                                "list_commits",
                                {"owner": username, "repo": repo_name, "sha": branch_name}
                            )
                            commits_data = json.loads(commits_result.content[0].text)
                            # Добавляем SHA коммитов в множество для исключения дубликатов
                            for commit in commits_data:
                                unique_commits.add(commit["sha"])
                        except Exception:
                            # Пропускаем ветку если не удалось получить коммиты
                            continue
                    
                    total_commits = len(unique_commits)
                    repo_commits.append((repo_name, total_commits, repo_description))
                except Exception:
                    # Если не удалось получить ветки или коммиты (приватный репо, ошибка и т.д.)
                    repo_commits.append((repo_name, 0, repo_description))

            return repo_commits
