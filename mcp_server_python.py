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

@mcp.tool()
async def validate_python(code: str) -> bool:
    """
    Проверяет корректность Python кода без выполнения.
    Возвращает True если код синтаксически корректен, False если есть ошибки.
    """
    client = docker.from_env()
    try:
        # Создаем временный файл с кодом и проверяем его
        import tempfile
        import base64
        
        # Кодируем код в base64 для безопасной передачи
        encoded_code = base64.b64encode(code.encode('utf-8')).decode('ascii')
        
        # Команда для декодирования и компиляции
        cmd = f'python -c "import base64; code=base64.b64decode(\'{encoded_code}\').decode(\'utf-8\'); compile(code, \'<string>\', \'exec\')"'
        
        client.containers.run(
            'python:3',
            cmd,
            remove=True
        )
        return True
    except Exception:
        return False

if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport='stdio')
