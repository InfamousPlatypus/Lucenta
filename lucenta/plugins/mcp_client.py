import asyncio
import logging
import os
from typing import List, Optional, Any, Dict
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

class LucentaMCPClient:
    def __init__(self, command: str, args: List[str]):
        self.server_params = StdioServerParameters(
            command=command,
            args=args,
            env=None
        )
        self.session: Optional[ClientSession] = None
        self._exit_stack = None

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        async with stdio_client(self.server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                logging.info(f"Connected to MCP server: {self.server_params.command}")
                result = await session.call_tool(tool_name, arguments)
                return result

    async def list_tools(self) -> List[Any]:
        async with stdio_client(self.server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.list_tools()
                return result.tools

class DoclingSandboxedClient(LucentaMCPClient):
    def __init__(self, docker_image: str = "mcp/docling", use_podman: bool = None):
        # Support both Docker (default) and Podman
        # Check environment variable if not explicitly set
        if use_podman is None:
            use_podman = os.getenv("USE_PODMAN", "false").lower() == "true"
        
        container_cmd = "podman" if use_podman else "docker"
        
        # Mount current directory to /data for local file access if needed
        super().__init__(
            command=container_cmd,
            args=["run", "-i", "--rm", "-v", f"{os.getcwd()}:/data", docker_image]
        )

    async def convert_pdf(self, pdf_path: str) -> str:
        # Assuming the docling mcp server has a tool named 'convert'
        # and it maps /data internally
        relative_path = os.path.relpath(pdf_path, os.getcwd())
        container_path = f"/data/{relative_path}"

        try:
            result = await self.call_tool("convert", {"path": container_path})
            return result.content[0].text if result.content else ""
        except Exception as e:
            logging.error(f"Docling conversion failed: {e}")
            return f"Error: {e}"
