import asyncio
import logging
import json
import os
import sys
from typing import Dict, List, Any, Optional
from pathlib import Path
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

class MCPServerManager:
    """Manages multiple MCP servers for Lucenta"""
    
    def __init__(self, config_path: str = "mcp-config.json"):
        self.config_path = config_path
        self.servers: Dict[str, Dict[str, Any]] = {}
        self.active_sessions: Dict[str, ClientSession] = {}
        self.available_tools: Dict[str, List[Any]] = {}
        self.load_config()
    
    def load_config(self):
        """Load MCP server configuration from JSON file"""
        try:
            with open(self.config_path, 'r') as f:
                config = json.load(f)
                self.servers = {
                    name: server_config 
                    for name, server_config in config.get('mcpServers', {}).items()
                    if server_config.get('enabled', False)
                }
            logging.info(f"Loaded {len(self.servers)} enabled MCP servers")
        except FileNotFoundError:
            logging.warning(f"MCP config file not found: {self.config_path}")
            self.servers = {}
        except Exception as e:
            logging.error(f"Error loading MCP config: {e}")
            self.servers = {}
    
    async def initialize_server(self, server_name: str) -> bool:
        """Initialize a single MCP server and cache its tools"""
        if server_name not in self.servers:
            logging.error(f"Server {server_name} not found in config")
            return False
        
        server_config = self.servers[server_name]
        try:
            # Get tools list from server
            tools = await self._list_server_tools(server_name)
            self.available_tools[server_name] = tools
            logging.info(f"Initialized {server_name}: {len(tools)} tools available")
            return True
        except Exception as e:
            logging.error(f"Failed to initialize {server_name}: {e}")
            return False
    
    async def initialize_all_servers(self):
        """Initialize all enabled MCP servers"""
        tasks = [self.initialize_server(name) for name in self.servers.keys()]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        successful = sum(1 for r in results if r is True)
        logging.info(f"Initialized {successful}/{len(self.servers)} MCP servers")

    
    async def _list_server_tools(self, server_name: str) -> List[Any]:
        """List tools available from a specific server"""
        server_config = self.servers[server_name]
        
        # Merge server-specific env with current process env
        env = os.environ.copy()
        if 'env' in server_config and server_config['env']:
            env.update(server_config['env'])
            
            
        server_params = StdioServerParameters(
            command=server_config['command'],
            args=server_config['args'],
            env=env
        )
        
        try:
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    result = await session.list_tools()
                    return result.tools
        except Exception as e:
            logging.error(f"Error listing tools for {server_name}: {e}")
            raise


    
    async def call_tool(self, server_name: str, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Call a tool on a specific MCP server"""
        if server_name not in self.servers:
            raise ValueError(f"Server {server_name} not found")
        
        server_config = self.servers[server_name]
        server_params = StdioServerParameters(
            command=server_config['command'],
            args=server_config['args'],
            env=server_config.get('env')
        )
        
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                logging.info(f"Calling {server_name}.{tool_name}")
                result = await session.call_tool(tool_name, arguments)
                return result
    
    def get_all_tools(self) -> Dict[str, List[str]]:
        """Get a summary of all available tools grouped by server"""
        return {
            server: [tool.name for tool in tools]
            for server, tools in self.available_tools.items()
        }
    
    def find_tool(self, tool_name: str) -> Optional[str]:
        """Find which server provides a specific tool"""
        for server_name, tools in self.available_tools.items():
            for tool in tools:
                if tool.name == tool_name:
                    return server_name
        return None
    
    async def smart_call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """
        Automatically find the server that provides the tool and call it.
        Return a string representation of the result for the LLM.
        """
        server_name = self.find_tool(tool_name)
        if not server_name:
            # Check if it was prefixed with server name
            if '-' in tool_name:
                parts = tool_name.split('-', 1)
                server_name = parts[0]
                tool_name = parts[1]
            else:
                raise ValueError(f"Tool {tool_name} not found in any server")
        
        result = await self.call_tool(server_name, tool_name, arguments)
        
        # Extract content from CallToolResult
        if hasattr(result, 'content'):
            return "\n".join([c.text for c in result.content if hasattr(c, 'text')])
        return str(result)

    
    def get_server_info(self) -> List[Dict[str, Any]]:
        """Get information about all enabled servers"""
        info = []
        for name, config in self.servers.items():
            tool_count = len(self.available_tools.get(name, []))
            info.append({
                'name': name,
                'description': config.get('description', 'No description'),
                'tool_count': tool_count,
                'tools': [t.name for t in self.available_tools.get(name, [])],
                'tool_details': [
                    {'name': t.name, 'description': t.description} 
                    for t in self.available_tools.get(name, [])
                ]
            })
        return info

    def get_tools_system_prompt(self) -> str:
        """Create a summary of capabilities for the LLM system prompt"""
        if not self.available_tools:
            return "No external tools are currently available."

        prompt = "You have access to the following Model Context Protocol (MCP) tools:\n"
        for server, tools in self.available_tools.items():
            prompt += f"\n### {server}\n"
            for tool in tools:
                prompt += f"- {tool.name}: {tool.description}\n"
        
        prompt += "\nYou can ask me to use these tools to fetch real-time data."
        return prompt

