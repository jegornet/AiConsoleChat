#!/usr/bin/env python3
"""
MCP сервер для выполнения Python кода в Docker контейнере
"""

from typing import Any
import ast
import re

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

@mcp.tool()
async def generate_tests(code: str) -> str:
    """
    Генерирует тесты для Python кода.
    Принимает на вход Python код и возвращает код с тестами для входного кода.
    """
    try:
        # Парсим AST для анализа кода
        tree = ast.parse(code)
        
        functions = []
        classes = []
        
        # Извлекаем функции и классы из кода
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Пропускаем приватные функции и методы
                if not node.name.startswith('_'):
                    # Извлекаем аргументы с их типами
                    args_info = []
                    for arg in node.args.args:
                        arg_info = {'name': arg.arg}
                        if arg.annotation:
                            # Получаем строковое представление типа
                            if isinstance(arg.annotation, ast.Name):
                                arg_info['type'] = arg.annotation.id
                            elif isinstance(arg.annotation, ast.Constant):
                                arg_info['type'] = str(arg.annotation.value)
                            else:
                                arg_info['type'] = ast.unparse(arg.annotation) if hasattr(ast, 'unparse') else 'Any'
                        else:
                            arg_info['type'] = None
                        args_info.append(arg_info)
                    
                    functions.append({
                        'name': node.name,
                        'args': args_info,
                        'returns': node.returns is not None
                    })
            elif isinstance(node, ast.ClassDef):
                # Извлекаем методы класса
                methods = []
                for class_node in node.body:
                    if isinstance(class_node, ast.FunctionDef) and not class_node.name.startswith('_'):
                        methods.append(class_node.name)
                
                classes.append({
                    'name': node.name,
                    'methods': methods
                })
        
        # Генерируем тесты
        test_code = "import unittest\n"
        
        # Если есть оригинальный код, добавляем его в начало
        if code.strip():
            test_code += f"\n# Original code\n{code}\n\n"
        
        # Генерируем тесты для функций
        if functions:
            test_code += "class TestFunctions(unittest.TestCase):\n"
            for func in functions:
                test_code += f"    def test_{func['name']}(self):\n"
                test_code += f"        # Test {func['name']} function\n"
                
                # Генерируем простые тестовые случаи в зависимости от аргументов
                if not func['args']:
                    test_code += f"        result = {func['name']}()\n"
                    test_code += f"        self.assertIsNotNone(result)\n"
                else:
                    # Генерируем тестовые значения на основе типов аргументов
                    test_values = []
                    for arg_info in func['args']:
                        arg_type = arg_info.get('type')
                        arg_name = arg_info['name']
                        
                        if arg_type == 'int':
                            test_values.append('1')
                        elif arg_type == 'float':
                            test_values.append('1.0')
                        elif arg_type == 'str':
                            test_values.append('"test"')
                        elif arg_type == 'bool':
                            test_values.append('True')
                        elif arg_type == 'list':
                            test_values.append('[1, 2, 3]')
                        elif arg_type == 'dict':
                            test_values.append('{"key": "value"}')
                        elif arg_type == 'tuple':
                            test_values.append('(1, 2)')
                        elif arg_type == 'set':
                            test_values.append('{1, 2, 3}')
                        elif arg_type is None:
                            # Если тип не указан, угадываем по имени аргумента
                            if 'str' in arg_name.lower() or 'text' in arg_name.lower() or 'name' in arg_name.lower():
                                test_values.append('"test"')
                            elif 'int' in arg_name.lower() or 'num' in arg_name.lower() or 'count' in arg_name.lower():
                                test_values.append('1')
                            elif 'float' in arg_name.lower():
                                test_values.append('1.0')
                            elif 'list' in arg_name.lower() or 'arr' in arg_name.lower():
                                test_values.append('[1, 2, 3]')
                            elif 'dict' in arg_name.lower():
                                test_values.append('{"key": "value"}')
                            elif 'bool' in arg_name.lower():
                                test_values.append('True')
                            else:
                                test_values.append('None')
                        else:
                            # Для других типов используем None как безопасное значение
                            test_values.append('None')
                    
                    args_str = ', '.join(test_values)
                    test_code += f"        result = {func['name']}({args_str})\n"
                    test_code += f"        self.assertIsNotNone(result)\n"
                
                test_code += "\n"
        
        # Генерируем тесты для классов
        if classes:
            for cls in classes:
                test_code += f"class Test{cls['name']}(unittest.TestCase):\n"
                test_code += f"    def setUp(self):\n"
                test_code += f"        self.obj = {cls['name']}()\n\n"
                
                if cls['methods']:
                    for method in cls['methods']:
                        test_code += f"    def test_{method}(self):\n"
                        test_code += f"        # Test {method} method\n"
                        test_code += f"        result = self.obj.{method}()\n"
                        test_code += f"        self.assertIsNotNone(result)\n\n"
                else:
                    test_code += f"    def test_instance_creation(self):\n"
                    test_code += f"        # Test {cls['name']} instance creation\n"
                    test_code += f"        self.assertIsInstance(self.obj, {cls['name']})\n\n"
        
        # Если нет функций и классов, создаем базовый тест
        if not functions and not classes:
            test_code += "class TestCode(unittest.TestCase):\n"
            test_code += "    def test_code_execution(self):\n"
            test_code += "        # Test that code executes without errors\n"
            test_code += "        try:\n"
            for line in code.split('\n'):
                if line.strip() and not line.strip().startswith('#'):
                    test_code += f"            {line}\n"
            test_code += "            self.assertTrue(True)\n"
            test_code += "        except Exception as e:\n"
            test_code += "            self.fail(f'Code execution failed: {e}')\n\n"
        
        # Добавляем main блок для запуска тестов
        test_code += "if __name__ == '__main__':\n"
        test_code += "    unittest.main()\n"
        
        return test_code
        
    except SyntaxError as e:
        return f"# Error: Invalid Python syntax\n# {str(e)}\n\n# Unable to generate tests for invalid code"
    except Exception as e:
        return f"# Error generating tests: {str(e)}\n\n# Basic test template:\nimport unittest\n\nclass TestCode(unittest.TestCase):\n    def test_placeholder(self):\n        self.assertTrue(True)\n\nif __name__ == '__main__':\n    unittest.main()\n"

if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport='stdio')
