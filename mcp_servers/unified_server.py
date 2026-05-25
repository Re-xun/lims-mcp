"""
Unified MCP server — exposes all LIMS query tools from 4 domains via stdio.

Usage:
  lims-mcp                        # after pip install
  python -m mcp_servers.unified_server   # from source

Auth:
  Set LIMS_USERNAME + LIMS_PASSWORD env vars for auto-login,
  or call the `login` tool manually.  Token is cached in-memory.

Domains & tools:
  customer_mcp      → query_customer_list
  sales_order_mcp   → query_sales_order_list, query_sales_order_by_id
  dm_project_mcp    → query_project_list, query_project_by_id, query_project_my_all,
                       query_project_unassigned, query_project_for_app
  user_mcp          → get_user_by_id, search_users, list_departments
  (built-in)        → login
"""
from __future__ import annotations

import asyncio
import inspect
import json
import os
import sys

# ── path setup (only needed when running from source) ─────────────────
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

# ── load .env from cwd or project root ────────────────────────────────
def _load_dotenv() -> None:
    """Try loading .env from common locations. Not fatal if missing."""
    try:
        from dotenv import load_dotenv as _ld
    except ImportError:
        return
    for candidate in (os.path.join(os.getcwd(), ".env"),
                      os.path.join(_project_root, ".env")):
        try:
            if os.path.isfile(candidate):
                _ld(candidate)
                return
        except Exception:
            pass

_load_dotenv()

import httpx
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from mcp_servers.customer_mcp.tools import TOOL_HANDLERS as C_H, TOOL_SCHEMAS as C_S
from mcp_servers.sales_order_mcp.tools import TOOL_HANDLERS as S_H, TOOL_SCHEMAS as S_S
from mcp_servers.dm_project_mcp.tools import TOOL_HANDLERS as P_H, TOOL_SCHEMAS as P_S
from mcp_servers.is_workbench_mcp.tools import TOOL_HANDLERS as I_H, TOOL_SCHEMAS as I_S
from mcp_servers.user_mcp.tools import TOOL_HANDLERS as U_H, TOOL_SCHEMAS as U_S

TOKEN_ENV = "LIMS_TOKEN"
JAVA_API_BASE = os.environ.get("JAVA_API_BASE", "http://localhost:3011")

app = Server("lims-unified")

# ── token management ──────────────────────────────────────────────────────

_cached_token: str | None = None
_cached_username: str | None = None
_login_lock = asyncio.Lock()


def _get_token() -> str:
    """Returns cached token synchronously. Raises if not logged in."""
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
    """Returns token, auto-logging in if credentials are available in env."""
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


# ── helpers ──────────────────────────────────────────────────────────────

def _camel_to_snake(name: str) -> str:
    """userId → user_id"""
    return "".join("_" + c.lower() if c.isupper() else c for c in name).lstrip("_")


def _map_arguments(arguments: dict, handler) -> dict:
    """Map MCP tool arguments to handler parameter names."""
    params = inspect.signature(handler).parameters
    mapped: dict[str, object] = {}

    for key, value in arguments.items():
        if key in params and key != "token":
            mapped[key] = value

    for key, value in arguments.items():
        snake = _camel_to_snake(key)
        if snake != key and snake in params and snake not in mapped:
            mapped[snake] = value

    return mapped


# ── login tool ────────────────────────────────────────────────────────────

async def _login(username: str, password: str) -> dict:
    """Authenticate against the LIMS Java API and cache the token."""
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


# ── registry ─────────────────────────────────────────────────────────────

_registry: dict[str, object] = {
    "login": _login,
}
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

for schemas, handlers in [(C_S, C_H), (S_S, S_H), (P_S, P_H), (I_S, I_H), (U_S, U_H)]:
    for s in schemas:
        name = s["name"]
        _registry[name] = handlers[name]
        _raw_schemas[name] = s["inputSchema"]


# ── MCP interface ────────────────────────────────────────────────────────

@app.list_tools()
async def list_tools() -> list[Tool]:
    tools: list[Tool] = []
    for name, handler in _registry.items():
        raw = _raw_schemas[name]
        if name in _tool_descriptions:
            desc = _tool_descriptions[name]
        else:
            doc = inspect.getdoc(handler)
            desc = doc.split("\n")[0] if doc else name

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
            call_kwargs = _map_arguments(arguments, handler)
            call_kwargs["token"] = token
            result = await handler(**call_kwargs)

        return [TextContent(
            type="text",
            text=json.dumps(result, ensure_ascii=False, indent=2, default=str),
        )]
    except Exception as exc:
        return [TextContent(type="text", text=f"Error: {exc}")]


# ── entrypoint ───────────────────────────────────────────────────────────

async def _run() -> None:
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


def main() -> None:
    asyncio.run(_run())


if __name__ == "__main__":
    main()
