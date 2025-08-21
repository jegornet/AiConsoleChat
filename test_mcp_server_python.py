#!/usr/bin/env python3
"""
Тесты для mcp_server_python.py
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import asyncio
import docker.errors

from mcp_server_python import execute_python, validate_python, mcp


class TestExecutePython(unittest.TestCase):
    """Тесты для функции execute_python"""
    
    @patch('mcp_server_python.docker')
    def test_execute_python_simple_code(self, mock_docker):
        """Тест выполнения простого Python кода"""
        # Настройка моков
        mock_client = Mock()
        mock_container = Mock()
        mock_container.run.return_value = b'Hello, World!\n'
        mock_client.containers = mock_container
        mock_docker.from_env.return_value = mock_client
        
        # Выполнение теста
        result = asyncio.run(execute_python('print("Hello, World!")'))
        
        # Проверки
        assert result == 'Hello, World!\n'
        mock_docker.from_env.assert_called_once()
        mock_container.run.assert_called_once_with(
            'python:3',
            'python -c "print("Hello, World!")"',
            remove=True
        )
    
    @patch('mcp_server_python.docker')
    def test_execute_python_math_calculation(self, mock_docker):
        """Тест выполнения математических вычислений"""
        mock_client = Mock()
        mock_container = Mock()
        mock_container.run.return_value = b'42\n'
        mock_client.containers = mock_container
        mock_docker.from_env.return_value = mock_client
        
        result = asyncio.run(execute_python('print(6 * 7)'))
        
        assert result == '42\n'
    
    @patch('mcp_server_python.docker')
    def test_execute_python_multiline_code(self, mock_docker):
        """Тест выполнения многострочного кода"""
        mock_client = Mock()
        mock_container = Mock()
        mock_container.run.return_value = b'1\n2\n3\n'
        mock_client.containers = mock_container
        mock_docker.from_env.return_value = mock_client
        
        code = """
for i in range(1, 4):
    print(i)
"""
        result = asyncio.run(execute_python(code))
        
        assert result == '1\n2\n3\n'
    
    @patch('mcp_server_python.docker')
    def test_execute_python_error_handling(self, mock_docker):
        """Тест обработки ошибок при выполнении кода"""
        mock_client = Mock()
        mock_container = Mock()
        mock_container.run.side_effect = Exception("Docker error")
        mock_client.containers = mock_container
        mock_docker.from_env.return_value = mock_client
        
        with self.assertRaises(Exception):
            asyncio.run(execute_python('invalid python code'))
    
    @patch('mcp_server_python.docker')
    def test_execute_python_empty_code(self, mock_docker):
        """Тест выполнения пустого кода"""
        mock_client = Mock()
        mock_container = Mock()
        mock_container.run.return_value = b''
        mock_client.containers = mock_container
        mock_docker.from_env.return_value = mock_client
        
        result = asyncio.run(execute_python(''))
        
        assert result == ''


class TestMCPServer(unittest.TestCase):
    """Тесты для MCP сервера"""
    
    def test_mcp_server_initialization(self):
        """Тест инициализации MCP сервера"""
        assert mcp.name == "python-docker"
    
    def test_execute_python_tool_registered(self):
        """Тест что инструмент execute_python зарегистрирован"""
        # Проверяем что функция зарегистрирована как инструмент
        tools = asyncio.run(mcp.list_tools())
        tool_names = [tool.name for tool in tools]
        self.assertIn('execute_python', tool_names)
    
    @patch('mcp_server_python.docker')
    def test_mcp_tool_call(self, mock_docker):
        """Тест вызова инструмента через MCP"""
        mock_client = Mock()
        mock_container = Mock()
        mock_container.run.return_value = b'Test output\n'
        mock_client.containers = mock_container
        mock_docker.from_env.return_value = mock_client
        
        # Получаем инструмент execute_python
        tools = asyncio.run(mcp.list_tools())
        execute_tool = None
        for tool in tools:
            if tool.name == 'execute_python':
                execute_tool = tool
                break
        
        self.assertIsNotNone(execute_tool)
        
        # Вызываем инструмент
        result = asyncio.run(mcp.call_tool('execute_python', {'code': 'print("Test")'}))
        
        # Результат содержит tuple с content и metadata
        content, metadata = result
        self.assertEqual(metadata['result'], 'Test output\n')


if __name__ == "__main__":
    unittest.main()