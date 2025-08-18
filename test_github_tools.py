#!/usr/bin/env python3
"""
Тест для проверки доступных инструментов в GitHub MCP сервере
"""

import asyncio
import os
from dotenv import load_dotenv
from mcp_client_github import GitHubMCPClient

async def main():
    load_dotenv()
    
    github_token = os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN")
    if not github_token:
        print("Ошибка: не установлена переменная окружения GITHUB_PERSONAL_ACCESS_TOKEN")
        return 1
        
    client = GitHubMCPClient(github_token, debug=True)
    
    try:
        print("Получаем список инструментов из GitHub MCP сервера...")
        tools = await client.get_tools_schema()
        
        print(f"\nДоступно {len(tools)} инструментов:")
        for tool_name, tool_info in tools.items():
            print(f"\n🔧 {tool_name}")
            print(f"   Описание: {tool_info.get('description', 'Нет описания')}")
            if 'inputSchema' in tool_info and 'properties' in tool_info['inputSchema']:
                print(f"   Параметры: {list(tool_info['inputSchema']['properties'].keys())}")
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())