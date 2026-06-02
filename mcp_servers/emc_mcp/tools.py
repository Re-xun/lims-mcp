"""MCP tools for EMC-related queries."""
from __future__ import annotations

import json
import os
import sys
from typing import Any

import httpx

JAVA_API_BASE = os.environ.get("JAVA_API_BASE", "http://localhost:8080")

SCOPE_TO_ENDPOINT = {
    "emc": "/EmcDeviceListAction/listQueryForEmc",
    "gen": "/EmcDeviceListAction/listQueryForGen",
}

FILTER_CONFIG = {
    "device_name": {
        "backend_field": "dd.DEVICE_NAME",
        "operator": "like",
        "template": "like '%{value}%'",
        "is_date_range": False,
        "is_enum": False,
    },
    "device_name_en": {
        "backend_field": "dd.DEVICE_NAME_En",
        "operator": "like",
        "template": "like '%{value}%'",
        "is_date_range": False,
        "is_enum": False,
    },
    "model": {
        "backend_field": "dd.model",
        "operator": "like",
        "template": "like '%{value}%'",
        "is_date_range": False,
        "is_enum": False,
    },
    "serial_number": {
        "backend_field": "dd.serial_number",
        "operator": "like",
        "template": "like '%{value}%'",
        "is_date_range": False,
        "is_enum": False,
    },
}

ENUM_FIELDS: dict[str, Any] = {}


def _mask_token(token: str) -> str:
    if token and len(token) > 8:
        return token[:8] + "***"
    return "***"


def _resolve_scope(scope: str | None = None, view: str | None = None) -> str:
    resolved = (scope or view or "emc").strip().lower()
    if resolved not in SCOPE_TO_ENDPOINT:
        raise ValueError(
            "不支持的 scope/view 值：{}。可选值：{}".format(
                resolved, ", ".join(sorted(SCOPE_TO_ENDPOINT))
            )
        )
    return resolved


def build_filter(
    *,
    device_name: str | None = None,
    device_name_en: str | None = None,
    model: str | None = None,
    serial_number: str | None = None,
) -> str | None:
    """仅基于 EmcDeviceListAction 文档中的查询字段构造 AND 连接的 filter。"""
    values = {
        "device_name": device_name,
        "device_name_en": device_name_en,
        "model": model,
        "serial_number": serial_number,
    }

    conditions: list[str] = []
    for param_name, value in values.items():
        if value is None or value == "":
            continue
        config = FILTER_CONFIG[param_name]
        conditions.append(
            "{} {}".format(
                config["backend_field"],
                config["template"].format(value=value),
            )
        )

    return " and ".join(conditions) if conditions else None


def build_params(
    *,
    start: int = 0,
    limit: int = 10,
    device_name: str | None = None,
    device_name_en: str | None = None,
    model: str | None = None,
    serial_number: str | None = None,
) -> dict[str, str]:
    """为 EmcDeviceListAction 的 listQuery* 接口构造请求参数。"""
    params = {
        "start": str(0 if start is None else start),
        "limit": str(10 if limit is None else limit),
        "sVars": json.dumps({}, ensure_ascii=False),
    }

    filter_sql = build_filter(
        device_name=device_name,
        device_name_en=device_name_en,
        model=model,
        serial_number=serial_number,
    )
    if filter_sql:
        params["filter"] = filter_sql

    return params


async def query_emc_device_list(
    token: str,
    scope: str = "emc",
    view: str | None = None,
    start: int = 0,
    limit: int = 10,
    device_name: str | None = None,
    device_name_en: str | None = None,
    model: str | None = None,
    serial_number: str | None = None,
) -> dict[str, Any]:
    """查询 EmcDeviceListAction 设备列表，支持 EMC 或 GEN 视图。"""
    resolved_scope = _resolve_scope(scope=scope, view=view)
    params = build_params(
        start=start,
        limit=limit,
        device_name=device_name,
        device_name_en=device_name_en,
        model=model,
        serial_number=serial_number,
    )
    api_url = "{}{}".format(JAVA_API_BASE, SCOPE_TO_ENDPOINT[resolved_scope])

    sys.stderr.write("\n[API REQUEST] GET {}\n".format(api_url))
    sys.stderr.write("  scope = {}\n".format(resolved_scope))
    for key, value in params.items():
        sys.stderr.write("  {} = {}\n".format(key, value))
    sys.stderr.write("\n")
    sys.stderr.flush()

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            api_url,
            headers={"x-access-token": token},
            params=params,
        )
        response.raise_for_status()
        data = response.json()
        data["_api_call"] = {
            "method": "GET",
            "url": api_url,
            "scope": resolved_scope,
            "params": dict(params),
            "token_masked": _mask_token(token),
        }
        data["_filter_config"] = FILTER_CONFIG
        data["_enum_fields"] = ENUM_FIELDS
        return data


async def get_emc_test_item_locations(
    token: str,
    id: str,
    modular_type: str | None = None,
) -> dict[str, Any]:
    """根据 EMC 测试项目 ID 查询可用场地位置列表。"""
    params = {"id": id}
    if modular_type:
        params["modularType"] = modular_type

    api_url = "{}/EmcTestItemLibListAction/getItemLocationListById".format(JAVA_API_BASE)
    sys.stderr.write("\n[API REQUEST] GET {}\n".format(api_url))
    for key, value in params.items():
        sys.stderr.write("  {} = {}\n".format(key, value))
    sys.stderr.write("\n")
    sys.stderr.flush()

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            api_url,
            headers={"x-access-token": token},
            params=params,
        )
        response.raise_for_status()
        data = response.json()
        data["_api_call"] = {
            "method": "GET",
            "url": api_url,
            "params": dict(params),
            "token_masked": _mask_token(token),
        }
        return data


async def get_emc_subscribe_items_by_order_id(
    token: str,
    id: str,
) -> dict[str, Any]:
    """根据 EMC 预约单 ID 查询其明细项目列表。"""
    params = {"id": id}
    api_url = "{}/EmcServiceSubscribeDetailAction/getSubscribeItemByOrderId".format(JAVA_API_BASE)
    sys.stderr.write("\n[API REQUEST] GET {}\n".format(api_url))
    for key, value in params.items():
        sys.stderr.write("  {} = {}\n".format(key, value))
    sys.stderr.write("\n")
    sys.stderr.flush()

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            api_url,
            headers={"x-access-token": token},
            params=params,
        )
        response.raise_for_status()
        data = response.json()
        data["_api_call"] = {
            "method": "GET",
            "url": api_url,
            "params": dict(params),
            "token_masked": _mask_token(token),
        }
        return data


TOOL_HANDLERS = {
    "query_emc_device_list": query_emc_device_list,
    "get_emc_test_item_locations": get_emc_test_item_locations,
    "get_emc_subscribe_items_by_order_id": get_emc_subscribe_items_by_order_id,
}

TOOL_SCHEMAS = [
    {
        "name": "query_emc_device_list",
        "description": (
            "查询 EmcDeviceListAction 设备列表。"
            "通过 scope/view 路由到不同接口：emc 对应 listQueryForEmc，gen 对应 listQueryForGen。"
            "筛选字段严格限制为文档“查询字段表”中声明的字段。"
            "当前文档未发现已确认的枚举查询字段。"
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "scope": {
                    "type": "string",
                    "description": "业务视图范围。emc=EMC 视图；gen=GEN/通用视图。",
                },
                "view": {
                    "type": "string",
                    "description": (
                        "scope 的别名参数，也可用于路由选择。"
                        "如果同时传入 scope 和 view，则以 scope 为准。"
                    ),
                },
                "start": {
                    "type": "integer",
                    "description": "分页起始位置，默认 0。",
                },
                "limit": {
                    "type": "integer",
                    "description": "分页每页条数，默认 10。",
                },
                "device_name": {
                    "type": "string",
                    "description": "设备名称，模糊匹配，对应后端字段 dd.DEVICE_NAME。",
                },
                "device_name_en": {
                    "type": "string",
                    "description": "设备英文名称，模糊匹配，对应后端字段 dd.DEVICE_NAME_En。",
                },
                "model": {
                    "type": "string",
                    "description": "型号，模糊匹配，对应后端字段 dd.model。",
                },
                "serial_number": {
                    "type": "string",
                    "description": "序列号，模糊匹配，对应后端字段 dd.serial_number。",
                },
            },
        },
    },
    {
        "name": "get_emc_test_item_locations",
        "description": "根据 EMC 测试项目 ID 查询可用场地位置列表。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "id": {
                    "type": "string",
                    "description": "EMC 测试项目 ID。",
                },
                "modular_type": {
                    "type": "string",
                    "description": "可选模块类型，例如 emc。",
                },
            },
            "required": ["id"],
        },
    },
    {
        "name": "get_emc_subscribe_items_by_order_id",
        "description": "根据 EMC 预约单 ID 查询其明细项目列表。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "id": {
                    "type": "string",
                    "description": "EMC 预约单 ID。",
                },
            },
            "required": ["id"],
        },
    },
]
