#!/usr/bin/env python3
"""
Простой MCP клиент для общения с mcp_server_python.py
"""

import asyncio
import subprocess
import json
import logging
from typing import Dict, Any, Optional


class PythonDockerMCPClient:
    """Клиент для общения с MCP сервером Python Docker"""
    
    def __init__(self):
        self.process: Optional[subprocess.Popen] = None
        self.server_script = "mcp_server_python.py"
        
    async def start_server(self):
        """Запускает MCP сервер"""
        if self.process is None:
            try:
                self.process = subprocess.Popen(
                    ["python", self.server_script],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    bufsize=0
                )
                # Даем серверу время на запуск
                await asyncio.sleep(0.5)
                
                # Инициализируем сессию
                await self._initialize_session()
            except Exception as e:
                raise Exception(f"Не удалось запустить MCP сервер: {e}")
    
    async def _initialize_session(self):
        """Инициализирует сессию MCP"""
        init_request = {
            "jsonrpc": "2.0",
            "id": 0,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {}
                },
                "clientInfo": {
                    "name": "python-docker-client",
                    "version": "1.0.0"
                }
            }
        }
        
        # Отправляем запрос инициализации
        init_response = await self.send_request(init_request)
        
        if "error" in init_response:
            raise Exception(f"Ошибка инициализации: {init_response['error']}")
        
        # Отправляем initialized notification
        initialized_notification = {
            "jsonrpc": "2.0",
            "method": "notifications/initialized"
        }
        
        request_json = json.dumps(initialized_notification) + "\n"
        self.process.stdin.write(request_json)
        self.process.stdin.flush()
    
    async def send_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Отправляет JSON-RPC запрос серверу"""
        if self.process is None:
            await self.start_server()
        
        try:
            # Отправляем запрос
            request_json = json.dumps(request) + "\n"
            self.process.stdin.write(request_json)
            self.process.stdin.flush()
            
            # Читаем ответ
            response_line = self.process.stdout.readline()
            if not response_line:
                raise Exception("Сервер не ответил")
            
            return json.loads(response_line.strip())
        except Exception as e:
            raise Exception(f"Ошибка общения с сервером: {e}")
    
    async def get_tools_schema(self) -> Dict[str, Any]:
        """Получает схему доступных инструментов"""
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/list",
            "params": {}
        }
        
        response = await self.send_request(request)
        
        if "error" in response:
            raise Exception(f"Ошибка получения инструментов: {response['error']}")
        
        # Преобразуем список инструментов в словарь
        tools_schema = {}
        for tool in response.get("result", {}).get("tools", []):
            tools_schema[tool["name"]] = {
                "description": tool.get("description", ""),
                "inputSchema": tool.get("inputSchema", {"type": "object", "properties": {}})
            }
        
        return tools_schema
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """Вызывает инструмент с заданными аргументами"""
        request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }
        
        response = await self.send_request(request)
        
        if "error" in response:
            raise Exception(f"Ошибка вызова инструмента {tool_name}: {response['error']}")
        
        # Извлекаем результат выполнения
        result = response.get("result", {})
        if "content" in result:
            # Если есть content, извлекаем текст
            content = result["content"]
            if isinstance(content, list) and len(content) > 0:
                return content[0].get("text", str(content))
            return str(content)
        
        return str(result)
    
    def close(self):
        """Закрывает соединение с сервером"""
        if self.process:
            self.process.terminate()
            self.process.wait()
            self.process = None
    
    def __del__(self):
        """Автоматически закрываем соединение при удалении объекта"""
        self.close()