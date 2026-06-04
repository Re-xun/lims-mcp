"""
Module registry — auto-generates MCP tool schemas from ModuleConfig and
creates callable handlers bound to the QueryEngine.

Usage::

    registry = ModuleRegistry(ALL_MODULES)
    engine = QueryEngine()
    handlers, schemas = registry.build(engine)
    # handlers → {"query_customer_list": <callable>, ...}
    # schemas  → [Tool(name=..., inputSchema=...), ...]
"""

from __future__ import annotations

from typing import Any

from .config import FilterDef, ModuleConfig
from .engine import QueryEngine


def _param_type(f: FilterDef) -> str:
    """Infer JSON Schema type from FilterDef operator and enum presence.

    Integer enum fields → "integer"; date range fields → "string"; and so on.
    """
    if f.enums is not None:
        # enum values are typically int
        return "integer"
    if f.operator in (">=", "<=") or f.is_date_range:
        return "string"
    if f.operator == "like":
        return "string"
    return "string"


def _build_properties(config: ModuleConfig) -> dict[str, dict[str, Any]]:
    """Auto-generate JSON Schema properties from a ModuleConfig.

    This replaces the hand-written ``_PROPS`` / ``_PROPERTIES`` dict in every
    old module.
    """
    props: dict[str, dict[str, Any]] = {
        "scope": {
            "type": "string",
            "description": _build_scope_description(config),
        },
        "view": {"type": "string", "description": "scope 的别名参数"},
        "start": {"type": "integer", "description": "分页起始位置，默认 0"},
        "limit": {"type": "integer", "description": "每页条数，默认 10"},
        "data_type": {
            "type": "string",
            "description": "日期筛选视图（sVars.dataType），不传则按 scope 自动选择默认值",
        },
    }

    for f in config.filters:
        desc = f"filter: {f.backend_field} ({f.label}) [{f.operator}]"
        if f.enums:
            enum_desc = ", ".join(f"{k}={v}" for k, v in sorted(f.enums.items()))
            desc += f"。可选值：{enum_desc}"

        props[f.key] = {
            "type": _param_type(f),
            "description": desc,
        }

    # Always add include_raw as optional debug switch
    props["include_raw"] = {
        "type": "boolean",
        "description": "调试用。默认 false；为 true 时返回后端原始 raw_resultList/raw_response",
    }

    return props


def _build_scope_description(config: ModuleConfig) -> str:
    """Generate human-readable description of available scope values."""
    if not config.scope_endpoints:
        return "无 scope 路由，使用固定端点"

    parts: list[str] = []
    for scope, ep in config.scope_endpoints.items():
        parts.append(f"{scope}={ep}")
    return "查询范围：" + ", ".join(parts)


def _create_handler(config: ModuleConfig, engine: QueryEngine):
    """Create an async handler closure bound to the engine.

    The handler receives ``params`` and ``token`` keyword args and delegates
    to ``engine.execute()``.
    """
    async def handler(**kwargs: Any) -> dict[str, Any]:
        token = kwargs.pop("token")
        return await engine.execute(config, kwargs, token)
    return handler


class ModuleRegistry:
    """Registry that builds MCP tool handlers and schemas from ModuleConfigs."""

    def __init__(self, modules: list[ModuleConfig]) -> None:
        self._modules = modules

    def build(
        self,
        engine: QueryEngine,
    ) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        """Build all tool handlers & schemas.

        Returns:
            (handlers, schemas) where:
            - handlers: dict[name → async callable]
            - schemas: list of dicts with name/description/inputSchema keys
        """
        handlers: dict[str, Any] = {}
        schemas: list[dict[str, Any]] = []

        for config in self._modules:
            handler = _create_handler(config, engine)
            props = _build_properties(config)

            handlers[config.name] = handler

            schemas.append({
                "name": config.name,
                "description": config.description or f"查询{config.display_name}列表",
                "inputSchema": {
                    "type": "object",
                    "properties": props,
                },
            })

        return handlers, schemas
