#!/usr/bin/env python3
"""
Простой консольный чат с ИИ
"""

import anthropic
import os
import sys
import asyncio

from anthropic.types import MessageParam
from dotenv import load_dotenv

from config import MODEL, MAX_TOKENS, TEMPERATURE, SYSTEM_PROMPT
from mcp_client_github import get_my_repos_with_commits


def main():
    # Загрузка переменных из .env файла
    load_dotenv()

    # Проверка наличия API ключа
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("Должна быть установлена переменная окружения ANTHROPIC_API_KEY")
        sys.exit(1)

    if not os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN"):
        print("Должна быть установлена переменная окружения GITHUB_PERSONAL_ACCESS_TOKEN")
        sys.exit(1)

    client = anthropic.Anthropic()
    conversation = []

    print("Это чат с ИИ. Когда надоест, введи q")
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
                print(response)
                if "---STATS" in response:
                    show_github_stats()
            except Exception as e:
                print(e)


def show_github_stats():
    token = os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN")
    repo_commits = asyncio.run(get_my_repos_with_commits(token))
    total_repos = 0
    total_commits = 0
    for repo_name, commit_count in repo_commits:
        total_repos += 1
        total_commits += commit_count
        print(f"{repo_name}: {commit_count} commit(s)")
    print(f"{total_commits} in {total_repos} repo(s)")

if __name__ == "__main__":
    main()
