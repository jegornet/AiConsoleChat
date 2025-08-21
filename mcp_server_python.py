#!/usr/bin/env python3
"""
MCP сервер для выполнения Python кода в Docker контейнере
"""

import docker
from mcp.server.fastmcp import FastMCP


mcp = FastMCP("python-docker")

@mcp.tool()
async def execute_python(code: str) -> str:
    import tempfile
    import base64
    
    client = docker.from_env()
    
    # Encode code in base64 for safe transfer
    encoded_code = base64.b64encode(code.encode('utf-8')).decode('ascii')
    
    # Create and execute Python code using temporary file
    cmd = f'python -c "import tempfile, base64; code=base64.b64decode(\'{encoded_code}\').decode(\'utf-8\'); f=tempfile.NamedTemporaryFile(mode=\'w\', suffix=\'.py\', delete=False); f.write(code); f.close(); exec(open(f.name).read())"'
    
    result = client.containers.run(
        'python:3',
        cmd,
        stderr=True,
        remove=True
    )
    decoded = result.decode('utf-8')
    return decoded


if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport='stdio')
