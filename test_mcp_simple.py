import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lucenta.plugins.mcp_manager import MCPServerManager

async def test_mcp_servers():
    print("--- MCP Test Start ---")
    manager = MCPServerManager()
    print(f"Loaded config: {len(manager.servers)} servers")
    
    await manager.initialize_all_servers()
    
    server_info = manager.get_server_info()
    total_tools = sum(s['tool_count'] for s in server_info)
    
    for info in server_info:
        print(f"Server: {info['name']} - Tools: {info['tool_count']}")
        if info['tool_count'] > 0:
            print(f"  Tools: {', '.join(info['tools'][:5])}...")
            
    print(f"Summary: {len(server_info)} servers, {total_tools} tools")
    print("--- MCP Test End ---")

if __name__ == "__main__":
    asyncio.run(test_mcp_servers())
