"""MCP Client Adapter - Load tools from MCP servers.

POC mode (default): imports generated tool modules directly, injects token via ContextVar.
This avoids subprocess overhead during development.

Upgrade path: switch to MultiServerMCPClient with stdio transport for process isolation.
"""
from __future__ import annotations

import importlib
import json
from contextvars import ContextVar
from typing import Any

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field, create_model

from .router import DomainConfig

# Context variable for per-request token injection
# Set by the FastAPI endpoint before each agent invocation
current_token: ContextVar[str | None] = ContextVar("current_token", default=None)


def _build_pydantic_model(tool_name: str, input_schema: dict) -> type[BaseModel]:
    """Dynamically create a Pydantic model from JSON Schema for StructuredTool."""
    fields: dict[str, Any] = {}
    props = input_schema.get("properties", {})
    required = input_schema.get("required", [])

    for param_name, param_schema in props.items():
        param_type = param_schema.get("type", "string")
        python_type: type = str
        if param_type == "integer":
            python_type = int
        elif param_type == "number":
            python_type = float
        elif param_type == "boolean":
            python_type = bool

        desc = param_schema.get("description", "")
        if param_name in required:
            fields[param_name] = (python_type, Field(description=desc))
        else:
            fields[param_name] = (python_type | None, Field(default=None, description=desc))

    model_name = f"{tool_name}_args".replace("-", "_")
    return create_model(model_name, **fields) if fields else create_model(model_name)


def _make_tool_callable(tool_func, tool_name: str):
    """Wrap a generated async tool function to inject token from ContextVar."""
    async def _call(**kwargs):
        token = current_token.get()
        if not token:
            raise RuntimeError("No token in context. User must be logged in.")
        return await tool_func(token=token, **kwargs)

    _call.__name__ = tool_name
    return _call


async def load_tools_for_domains(domains: list[DomainConfig]) -> list[StructuredTool]:
    """Load LangChain tools from the given MCP domains (inline mode).

    For each domain, import its tools.py module, read TOOL_SCHEMAS and TOOL_HANDLERS,
    and wrap each tool as a LangChain StructuredTool.
    """
    tools: list[StructuredTool] = []

    for domain in domains:
        try:
            module = importlib.import_module(f"mcp_servers.{domain.name}.tools")
        except ModuleNotFoundError:
            print(f"[mcp_client] MCP server '{domain.name}' not found. Run generator first.")
            continue

        handlers: dict = getattr(module, "TOOL_HANDLERS", {})
        schemas: list[dict] = getattr(module, "TOOL_SCHEMAS", [])

        for schema in schemas:
            name = schema["name"]
            desc = schema.get("description", "")
            input_schema = schema.get("inputSchema", {})

            handler = handlers.get(name)
            if not handler:
                continue

            args_model = _build_pydantic_model(name, input_schema)
            callable_fn = _make_tool_callable(handler, name)

            tool = StructuredTool(
                name=name,
                description=desc,
                args_schema=args_model,
                coroutine=callable_fn,
            )
            tools.append(tool)

    return tools


async def load_all_tools() -> list[StructuredTool]:
    """Load tools from all registered MCP domains."""
    from .router import get_all_domains
    return await load_tools_for_domains(get_all_domains())
