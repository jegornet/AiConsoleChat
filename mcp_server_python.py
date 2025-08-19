#!/usr/bin/env python3
"""
MCP сервер для выполнения Python кода в Docker контейнере
"""

from typing import Any

import docker
from mcp.server.fastmcp import FastMCP


mcp = FastMCP("python-docker")

@mcp.tool()
async def execute_python(code: str) -> str:
    client = docker.from_env()
    result = client.containers.run(
        'python:3',
        f'python -c "{code}"',
        remove=True
    )
    return result.decode('utf-8')

if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport='stdio')
