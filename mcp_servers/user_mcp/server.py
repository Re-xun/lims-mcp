"""user_mcp MCP Server - Auto-generated from OpenAPI spec.

DO NOT EDIT MANUALLY. Run `python -m mcp_servers.generator.generate` to regenerate.
"""
import sys
import json
import logging

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from .tools import TOOL_HANDLERS, TOOL_SCHEMAS

logger = logging.getLogger(__name__)
server = Server("user_mcp-mcp")

# Token injected via CLI arg: python server.py --token <value>
TOKEN: str | None = None
for i, arg in enumerate(sys.argv):
    if arg == "--token" and i + 1 < len(sys.argv):
        TOKEN = sys.argv[i + 1]
        break


@server.list_tools()
async def list_tools() -> list[Tool]:
    return [Tool(**schema) for schema in TOOL_SCHEMAS]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    if name not in TOOL_HANDLERS:
        raise ValueError(f"Unknown tool: {name}")
    if TOKEN is None:
        raise RuntimeError("Token not provided. Start server with --token <value>")
    try:
        result = await TOOL_HANDLERS[name](token=TOKEN, **arguments)
        return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False))]
    except Exception as e:
        logger.error(f"Tool {name} failed: {e}")
        return [TextContent(type="text", text=json.dumps({"error": str(e)}, ensure_ascii=False))]


def main():
    import asyncio
    asyncio.run(_run())


async def _run():
    async with stdio_server() as (read, write):
        await server.run(read, write)


if __name__ == "__main__":
    main()