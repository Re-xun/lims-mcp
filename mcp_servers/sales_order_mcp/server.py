"""MCP Server entry point for sales_order_mcp."""
from mcp.server import Server
from mcp.server.stdio import stdio_server

app = Server("sales_order_mcp")

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
