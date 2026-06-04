"""
New unified MCP server — thin orchestration layer over the QueryEngine.

Enabled by setting ``USE_NEW_MCP=1`` in the environment.
When disabled, falls back to the old ``mcp_servers.unified_server``.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys

import httpx
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from new_mcp_servers.configs import ALL_MODULES
from new_mcp_servers.core.engine import JAVA_API_BASE, QueryEngine
from new_mcp_servers.core.registry import ModuleRegistry

# ── env gating ──────────────────────────────────────────────────────────
_should_run = os.environ.get("USE_NEW_MCP", "0") == "1"

if not _should_run:
    # When not enabled, this module is a no-op (the old server handles everything).
    # This module should not be imported as the main entry point.
    pass

TOKEN_ENV = "LIMS_TOKEN"

app = Server("lims-unified")

# ── token management ────────────────────────────────────────────────────

_cached_token: str | None = None
_cached_username: str | None = None
_login_lock = asyncio.Lock()


def _get_token() -> str:
    if _cached_token:
        return _cached_token
    t = os.environ.get(TOKEN_ENV)
    if t:
        return t
    raise RuntimeError(
        "未登录，请先调用 login 工具登录。\n"
        "示例: login(username='你的工号', password='你的密码')"
    )


async def _ensure_token() -> str:
    global _cached_token, _cached_username

    try:
        return _get_token()
    except RuntimeError:
        pass

    username = os.environ.get("LIMS_USERNAME")
    password = os.environ.get("LIMS_PASSWORD")
    if not username or not password:
        raise RuntimeError(
            "未登录且未配置 LIMS_USERNAME / LIMS_PASSWORD 环境变量。\n"
            "请在 .env 中配置，或手动调用 login 工具登录。"
        )

    async with _login_lock:
        result = await _login(username, password)
        if not result.get("success"):
            raise RuntimeError(f"自动登录失败: {result.get('error')}")
        return _cached_token


# ── login tool ──────────────────────────────────────────────────────────

async def _login(username: str, password: str) -> dict:
    global _cached_token, _cached_username
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{JAVA_API_BASE}/LoginAction2/login",
                data={"userNo": username, "password": password, "loginType": "1"},
            )
            if resp.status_code != 200:
                return {"success": False, "error": f"登录失败 (HTTP {resp.status_code})"}
            data = resp.json()
            if data.get("code") != 1:
                return {"success": False, "error": data.get("msg", "登录失败")}
            token = data.get("token")
            if not token:
                return {"success": False, "error": "登录响应中没有 token"}
            _cached_token = token
            _cached_username = data.get("userInfo", {}).get("userName", username)
            return {
                "success": True,
                "username": _cached_username,
                "message": f"登录成功，欢迎 {_cached_username}。token 已缓存，后续查询无需重复登录。",
            }
    except httpx.RequestError as e:
        return {"success": False, "error": f"无法连接 Java API: {e}"}


# ── registry & engine ───────────────────────────────────────────────────

_registry: dict[str, object] = {"login": _login}
_raw_schemas: dict[str, dict] = {
    "login": {
        "type": "object",
        "properties": {
            "username": {"type": "string", "description": "LIMS 用户名/工号"},
            "password": {"type": "string", "description": "LIMS 密码"},
        },
        "required": ["username", "password"],
    },
}
_tool_descriptions: dict[str, str] = {
    "login": "登录 LIMS 系统，获取认证 token。没有 token 时必须先调用此工具。token 会缓存到内存中，后续查询自动使用。",
}

# Build registrations from ModuleConfigs
_module_registry = ModuleRegistry(ALL_MODULES)
_engine = QueryEngine()
_handlers, _schemas = _module_registry.build(_engine)

for s in _schemas:
    name = s["name"]
    _registry[name] = _handlers[name]
    _raw_schemas[name] = s["inputSchema"]

if _tool_descriptions.get("login"):
    pass  # login description already set


# ── MCP interface ──────────────────────────────────────────────────────

@app.list_tools()
async def list_tools() -> list[Tool]:
    tools: list[Tool] = []
    for name, handler in _registry.items():
        raw = _raw_schemas[name]
        desc = _tool_descriptions.get(name, "")

        tools.append(Tool(
            name=name,
            description=desc,
            inputSchema={
                "type": "object",
                "properties": raw.get("properties", {}),
                "required": raw.get("required", []),
            },
        ))
    return tools


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    handler = _registry.get(name)
    if handler is None:
        return [TextContent(type="text", text=f"Unknown tool: {name}")]

    try:
        if name == "login":
            result = await handler(**arguments)
        else:
            token = await _ensure_token()
            result = await handler(**arguments, token=token)

        return [TextContent(
            type="text",
            text=json.dumps(result, ensure_ascii=False, indent=2, default=str),
        )]
    except Exception as exc:
        return [TextContent(type="text", text=f"Error: {exc}")]


# ── lifecycle ───────────────────────────────────────────────────────────

async def _run() -> None:
    try:
        async with stdio_server() as (read_stream, write_stream):
            await app.run(read_stream, write_stream, app.create_initialization_options())
    finally:
        await _engine.close()


def main() -> None:
    if not _should_run:
        print(
            "USE_NEW_MCP 未启用。请设置 USE_NEW_MCP=1 环境变量来启用新架构。",
            file=sys.stderr,
        )
        sys.exit(0)
    asyncio.run(_run())


if __name__ == "__main__":
    main()
