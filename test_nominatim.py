import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lucenta.plugins.mcp_manager import MCPServerManager

async def test_one():
    manager = MCPServerManager()
    server_name = "nominatim"
    print(f"Testing {server_name}...")
    try:
        success = await manager.initialize_server(server_name)
        print(f"Success: {success}")
        if success:
            print(f"Tools: {manager.get_all_tools().get(server_name)}")
    except Exception as e:
        print(f"FAILED with exception: {e}")

if __name__ == "__main__":
    asyncio.run(test_one())
