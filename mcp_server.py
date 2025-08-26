#!/usr/bin/env python3
"""
MCP сервер для работы с файловой системой и получения содержимого URL
"""

import os

from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv

load_dotenv()

mcp = FastMCP("filesystem")

# Рабочая директория - ограничиваем доступ только к ней и её подпапкам
WORK_DIR = os.getcwd()


def is_safe_path(path: str) -> tuple[bool, str]:
    """
    Проверяет, что путь находится внутри рабочей директории
    Возвращает (is_safe, normalized_path)
    """
    try:
        # Нормализуем путь и получаем абсолютный путь
        normalized_path = os.path.abspath(os.path.normpath(path))
        
        # Проверяем, что путь начинается с рабочей директории
        if normalized_path.startswith(WORK_DIR + os.sep) or normalized_path == WORK_DIR:
            return True, normalized_path
        else:
            return False, normalized_path
    except Exception:
        return False, path


@mcp.tool()
async def list_files(directory: str = ".") -> str:
    """
    Возвращает список файлов и директорий в указанной папке.
    По умолчанию показывает содержимое текущей директории.
    """
    # Проверка безопасности пути
    is_safe, normalized_path = is_safe_path(directory)
    if not is_safe:
        return f"Error: Access denied. Path '{directory}' is outside the working directory"
    
    try:
        files = os.listdir(normalized_path)
        result = []
        
        for file in sorted(files):
            file_path = os.path.join(normalized_path, file)
            if os.path.isdir(file_path):
                result.append(f"[DIR]  {file}")
            else:
                result.append(f"[FILE] {file}")
        
        return "\n".join(result)
    except FileNotFoundError:
        return f"Error: Directory '{directory}' not found"
    except PermissionError:
        return f"Error: Permission denied accessing '{directory}'"
    except Exception as e:
        return f"Error listing files: {str(e)}"


@mcp.tool()
async def read_file(file_path: str) -> str:
    """
    Читает содержимое файла и возвращает его как строку.
    """
    # Проверка безопасности пути
    is_safe, normalized_path = is_safe_path(file_path)
    if not is_safe:
        return f"Error: Access denied. Path '{file_path}' is outside the working directory"
    
    try:
        with open(normalized_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return f"Error: File '{file_path}' not found"
    except PermissionError:
        return f"Error: Permission denied reading '{file_path}'"
    except UnicodeDecodeError:
        try:
            with open(normalized_path, 'r', encoding='latin-1') as f:
                return f"Warning: File contains non-UTF-8 characters\n{f.read()}"
        except Exception:
            return f"Error: Cannot decode file '{file_path}' as text"
    except Exception as e:
        return f"Error reading file: {str(e)}"


@mcp.tool()
async def write_file(file_path: str, content: str) -> str:
    """
    Записывает содержимое в файл. Если файл не существует, он будет создан.
    Если файл существует, его содержимое будет перезаписано.
    """
    # Проверка безопасности пути
    is_safe, normalized_path = is_safe_path(file_path)
    if not is_safe:
        return f"Error: Access denied. Path '{file_path}' is outside the working directory"
    
    try:
        # Создаем директории при необходимости
        directory = os.path.dirname(normalized_path)
        if directory and not os.path.exists(directory):
            # Также проверяем безопасность директории
            is_dir_safe, _ = is_safe_path(directory)
            if not is_dir_safe:
                return f"Error: Access denied. Directory path is outside the working directory"
            os.makedirs(directory)
        
        with open(normalized_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return f"File '{file_path}' written successfully ({len(content)} characters)"
    except PermissionError:
        return f"Error: Permission denied writing to '{file_path}'"
    except Exception as e:
        return f"Error writing file: {str(e)}"


@mcp.tool()
async def delete_file(file_path: str) -> str:
    """
    Удаляет указанный файл.
    """
    # Проверка безопасности пути
    is_safe, normalized_path = is_safe_path(file_path)
    if not is_safe:
        return f"Error: Access denied. Path '{file_path}' is outside the working directory"
    
    try:
        if not os.path.exists(normalized_path):
            return f"Error: File '{file_path}' not found"
        
        if os.path.isdir(normalized_path):
            return f"Error: '{file_path}' is a directory, not a file"
        
        os.remove(normalized_path)
        return f"File '{file_path}' deleted successfully"
    except PermissionError:
        return f"Error: Permission denied deleting '{file_path}'"
    except Exception as e:
        return f"Error deleting file: {str(e)}"


if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport='stdio')
