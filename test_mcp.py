"""
Quick test script to verify MCP server integration
"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lucenta.plugins.mcp_manager import MCPServerManager

async def test_mcp_servers():
    print("=" * 50)
    print("MCP Server Integration Test")
    print("=" * 50)
    print()
    
    # Initialize manager
    print("Loading MCP configuration...")
    manager = MCPServerManager()
    
    if not manager.servers:
        print("Error: No servers configured!")
        return
    
    print(f"Found {len(manager.servers)} enabled servers: {', '.join(manager.servers.keys())}")
    print()
    
    # Initialize all servers
    print("Initializing servers...")
    await manager.initialize_all_servers()
    print()
    
    # Show server info
    print("=" * 50)
    print("Available Servers & Tools")
    print("=" * 50)
    
    server_info = manager.get_server_info()
    total_tools = sum(s['tool_count'] for s in server_info)
    
    for info in server_info:
        print(f"\nServer: {info['name']}")
        print(f"   Description: {info['description']}")
        print(f"   Tool Count: {info['tool_count']}")
        if info['tools']:
            print(f"   Tools: {', '.join(info['tools'])}")
        else:
            print(f"   Tools: NONE")
    
    print()
    print("=" * 50)
    print(f"Summary: {len(server_info)} servers, {total_tools} tools")
    print("=" * 50)

    
    # Test a simple tool call
    print()
    print("🧪 Testing a tool call...")
    try:
        # Try to get ISS location (open-notify server)
        if manager.find_tool('get_iss_location'):
            result = await manager.smart_call_tool('get_iss_location', {})
            print("✅ Tool call successful!")
            print(f"Result: {result}")
        else:
            print("⚠️  ISS location tool not available, skipping test")
    except Exception as e:
        print(f"⚠️  Tool call failed: {e}")
    
    print()
    print("✅ MCP Integration Test Complete!")

if __name__ == "__main__":
    asyncio.run(test_mcp_servers())
