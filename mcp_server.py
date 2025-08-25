#!/usr/bin/env python3
"""
MCP сервер для выполнения удалённых команд и получения содержимого URL
"""

import os
import urllib.request
import urllib.error
import paramiko
import ssl

from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv

load_dotenv()

mcp = FastMCP("hosting")


@mcp.tool()
async def execute_remote_command(command: str) -> str:
    """
    Выполняет команду на удалённом сервере через SSH.
    Использует SSH_CREDENTIALS из переменной окружения в формате user@hostname.
    Возвращает вывод команды с удалённого сервера.
    """
    ssh_credentials = os.getenv('SSH_CREDENTIALS')
    if not ssh_credentials:
        return "Error: SSH_CREDENTIALS environment variable is not set"

    ssh_key = os.getenv('SSH_KEY')
    if not ssh_key:
        return "Error: SSH_KEY environment variable is not set"

    try:
        # Парсим учетные данные
        if '@' not in ssh_credentials:
            return "Error: SSH_CREDENTIALS must be in format user@hostname"
        
        username, hostname = ssh_credentials.split('@', 1)
        
        # Создаем SSH клиент
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        ssh_client.connect(
            hostname=hostname,
            username=username,
            key_filename=ssh_key,
            allow_agent=True,
            timeout=30,
        )

        # Выполняем команду
        stdin, stdout, stderr = ssh_client.exec_command(command, timeout=30)
        
        # Читаем результат
        stdout_data = stdout.read().decode('utf-8')
        stderr_data = stderr.read().decode('utf-8')
        exit_code = stdout.channel.recv_exit_status()
        
        ssh_client.close()
        
        if exit_code == 0:
            return stdout_data if stdout_data else "Command executed successfully (no output)"
        else:
            return f"Error (exit code {exit_code}): {stderr_data}"
            
    except Exception as e:
        return f"Error executing remote command: {str(e)}"


@mcp.tool()
async def fetch_url(url: str) -> str:
    """
    Получает содержимое URL и возвращает его в виде строки.
    Поддерживает HTTP и HTTPS протоколы.
    """
    try:
        # Создаем запрос с User-Agent для совместимости
        req = urllib.request.Request(
            url, 
            headers={'User-Agent': 'MCP-Server/1.0'}
        )
        
        # Создаем SSL контекст с менее строгой проверкой сертификатов
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        # Выполняем запрос с таймаутом и SSL контекстом
        with urllib.request.urlopen(req, timeout=30, context=ssl_context) as response:
            # Читаем содержимое
            content = response.read()
            
            # Пытаемся декодировать как текст
            try:
                # Определяем кодировку из заголовков
                charset = 'utf-8'
                content_type = response.headers.get('content-type', '')
                if 'charset=' in content_type:
                    charset = content_type.split('charset=')[1].split(';')[0].strip()
                
                return content.decode(charset)
            except UnicodeDecodeError:
                # Если не удается декодировать как текст, возвращаем информацию о файле
                return f"Binary content ({len(content)} bytes), Content-Type: {response.headers.get('content-type', 'unknown')}"
                
    except urllib.error.HTTPError as e:
        return f"HTTP Error {e.code}: {e.reason}"
    except urllib.error.URLError as e:
        return f"URL Error: {str(e.reason)}"
    except Exception as e:
        return f"Error fetching URL: {str(e)}"


if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport='stdio')
