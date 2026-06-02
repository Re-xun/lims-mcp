"""MCP tools for SdTempTestServiceItemListAction temporary test service item queries."""
from __future__ import annotations

import json
import os
import sys
from typing import Any

import httpx

JAVA_API_BASE = os.environ.get("JAVA_API_BASE", "http://localhost:8080")

SCOPE_TO_ENDPOINT = {
    "default": "/SdTempTestServiceItemListAction/listQuery",
}

FILTER_CONFIG: dict[str, dict[str, str]] = {
    # ── 核心筛选（第 4 节） ──
    "fast_search": {"backend_field": "fastSearch", "template": "like '%{value}%'"},
    "item_name": {"backend_field": "itemName", "template": "like '%{value}%'"},
    "item_no": {"backend_field": "itemNo", "template": "like '%{value}%'"},
    "item_type": {"backend_field": "itemType", "template": "= '{value}'"},
    "modular_type": {"backend_field": "sttsi.modular_type", "template": "= '{value}'"},
    "remark": {"backend_field": "remark", "template": "like '%{value}%'"},
    "test_capability": {"backend_field": "testCapability", "template": "like '%{value}%'"},
    # ── 候选 filter（第 4.1 节） ──
    "cost_assessment": {"backend_field": "costAssessment", "template": "like '%{value}%'"},
    "department_name": {"backend_field": "departmentName", "template": "like '%{value}%'"},
    "rstatus": {"backend_field": "rstatus", "template": "= {value}"},
    "unit_name": {"backend_field": "unitName", "template": "like '%{value}%'"},
    "unit_price": {"backend_field": "unitPrice", "template": "like '%{value}%'"},
}

FIELD_LABELS: dict[str, dict[str, str]] = {
    "itemNo": {"key": "item_no", "title": "价格编号"},
    "departmentName": {"key": "department_name", "title": "部门"},
    "itemName": {"key": "item_name", "title": "试验项目"},
    "unitPrice": {"key": "unit_price", "title": "标准价格（RMB）"},
    "unitName": {"key": "unit_name", "title": "计费单位"},
    "costAssessment": {"key": "cost_assessment", "title": "费用评估"},
    "testCapability": {"key": "test_capability", "title": "试验能力"},
    "itemType": {"key": "item_type", "title": "试验项目类型"},
    "modularType": {"key": "modular_type", "title": "所属模块"},
    "rstatus": {"key": "rstatus", "title": "RSTATUS"},
    "remark": {"key": "remark", "title": "备注"},
}

ENUM_FIELDS = {
    "item_type": {
        "EMI": "EMI",
        "EMS": "EMS",
        "电性能": "电性能",
        "丰田项目": "丰田项目",
        "RF": "RF",
    },
    "modular_type": {
        "general_emc": "普通EMC",
        "rf": "RF",
        "sar": "SAR",
        "emc": "汽车电子EMC",
        "electrical_emc": "汽车电子电性能",
        "reliability": "环境可靠性",
        "pencil": "线束",
        "safety": "安规实验室",
        "energy_efficiency": "能效",
        "sound_pressure": "声压",
        "battery": "电池",
        "material": "材料",
        "software": "软件",
        "information_security": "信息安全",
        "material_pencil": "材料线束",
        "connector": "连接器",
        "chemistry": "化学实验室",
        "other": "其他",
        "optical_property": "光学实验室",
    },
    "rstatus": {
        0: "已作废",
        1: "已审核",
        2: "暂存",
        3: "等待重新审批",
        4: "审批中",
    },
}


def _mask_token(token: str) -> str:
    if token and len(token) > 8:
        return token[:8] + "***"
    return "***"


def _resolve_scope(scope: str | None = None, view: str | None = None) -> str:
    resolved = (scope or view or "default").strip()
    key = resolved.lower()
    if key not in SCOPE_TO_ENDPOINT:
        raise ValueError(
            "Unsupported scope/view: {}. Allowed values: {}".format(
                resolved,
                ", ".join(sorted(SCOPE_TO_ENDPOINT)),
            )
        )
    return key


def build_filter(**values: Any) -> str | None:
    conditions: list[str] = []
    for param_name, value in values.items():
        if value is None or value == "" or param_name not in FILTER_CONFIG:
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
    **filter_values: Any,
) -> dict[str, str]:
    params = {
        "start": str(0 if start is None else start),
        "limit": str(10 if limit is None else limit),
    }

    filter_sql = build_filter(**filter_values)
    if filter_sql:
        params["filter"] = filter_sql

    return params


def _build_columns() -> list[dict[str, str]]:
    return [
        {"field": field, "key": meta["key"], "title": meta["title"]}
        for field, meta in FIELD_LABELS.items()
    ]


def _enum_text(key: str, value: Any) -> str | None:
    enum_map = ENUM_FIELDS.get(key)
    if not isinstance(enum_map, dict):
        return None
    if value in enum_map:
        return enum_map[value]
    if value is None:
        return None
    try:
        return enum_map.get(int(value))
    except (TypeError, ValueError):
        return enum_map.get(str(value))


def _normalize_row(row: dict[str, Any]) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    for field, meta in FIELD_LABELS.items():
        key = meta["key"]
        value = row.get(field)
        normalized[key] = value
        text = _enum_text(key, value)
        if text is not None:
            normalized["{}_text".format(key)] = text
    return normalized


def _extract_result_list(payload: dict[str, Any]) -> list[dict[str, Any]]:
    nested_data = payload.get("data")
    if isinstance(nested_data, dict) and isinstance(nested_data.get("resultList"), list):
        return nested_data["resultList"]
    if isinstance(payload.get("resultList"), list):
        return payload["resultList"]
    return []


def _extract_count(payload: dict[str, Any], fallback_count: int) -> int:
    nested_data = payload.get("data")
    if isinstance(nested_data, dict) and isinstance(nested_data.get("count"), int):
        return nested_data["count"]
    if isinstance(payload.get("count"), int):
        return payload["count"]
    return fallback_count


async def query_sdtemptestserviceitemlistaction(
    token: str,
    scope: str = "default",
    view: str | None = None,
    start: int = 0,
    limit: int = 10,
    # ── 核心筛选（第 4 节） ──
    fast_search: str | None = None,
    item_name: str | None = None,
    item_no: str | None = None,
    item_type: str | None = None,
    modular_type: str | None = None,
    remark: str | None = None,
    test_capability: str | None = None,
    # ── 候选 filter（第 4.1 节） ──
    cost_assessment: str | None = None,
    department_name: str | None = None,
    rstatus: int | None = None,
    unit_name: str | None = None,
    unit_price: str | None = None,
    include_raw: bool = False,
) -> dict[str, Any]:
    """查询临时测试服务项目列表，默认包含继承的 /SdTempTestServiceItemListAction/listQuery。"""
    resolved_scope = _resolve_scope(scope=scope, view=view)
    params = build_params(
        start=start,
        limit=limit,
        fast_search=fast_search,
        item_name=item_name,
        item_no=item_no,
        item_type=item_type,
        modular_type=modular_type,
        remark=remark,
        test_capability=test_capability,
        cost_assessment=cost_assessment,
        department_name=department_name,
        rstatus=rstatus,
        unit_name=unit_name,
        unit_price=unit_price,
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
        payload = response.json()

    raw_result_list = _extract_result_list(payload)
    normalized_data = [_normalize_row(row) for row in raw_result_list]
    result: dict[str, Any] = {
        "success": payload.get("success", True),
        "count": _extract_count(payload, len(raw_result_list)),
        "columns": _build_columns(),
        "data": normalized_data,
        "normalized_data": normalized_data,
        "_api_call": {
            "method": "GET",
            "url": api_url,
            "scope": resolved_scope,
            "params": dict(params),
            "token_masked": _mask_token(token),
        },
        "_filter_config": FILTER_CONFIG,
        "_field_labels": FIELD_LABELS,
        "_enum_fields": ENUM_FIELDS,
    }
    if include_raw:
        result["raw_resultList"] = raw_result_list
        result["raw_response"] = payload
    return result


TOOL_HANDLERS = {
    "query_sdtemptestserviceitemlistaction": query_sdtemptestserviceitemlistaction,
}

_PROPERTIES: dict[str, dict[str, Any]] = {
    "scope": {
        "type": "string",
        "description": (
            "视图范围: default=默认列表查询。"
            "default 包含继承的 /SdTempTestServiceItemListAction/listQuery。"
        ),
    },
    "view": {"type": "string", "description": "scope 的别名；如同时传入，以 scope 为准。"},
    "start": {"type": "integer", "description": "分页起始位置，默认 0。"},
    "limit": {"type": "integer", "description": "分页条数，默认 10。"},
    # ── 核心筛选（第 4 节） ──
    "fast_search": {"type": "string", "description": "视图，模糊匹配 (fastSearch → fastSearch)。"},
    "item_name": {"type": "string", "description": "试验项目，模糊匹配 (q_itemName → itemName)。"},
    "item_no": {"type": "string", "description": "价格编号，模糊匹配 (q_itemNo → itemNo)。"},
    "item_type": {"type": "string", "description": "项目类型，精确匹配 (q_itemType → itemType)。"},
    "modular_type": {
        "type": "string",
        "description": (
            "所属模块 (q_modularType → sttsi.modular_type): "
            "general_emc=普通EMC, rf=RF, sar=SAR, emc=汽车电子EMC, "
            "electrical_emc=汽车电子电性能, reliability=环境可靠性, pencil=线束, "
            "safety=安规实验室, energy_efficiency=能效, sound_pressure=声压, "
            "battery=电池, material=材料, software=软件, information_security=信息安全, "
            "material_pencil=材料线束, connector=连接器, chemistry=化学实验室, "
            "other=其他, optical_property=光学实验室"
        ),
    },
    "remark": {"type": "string", "description": "备注，模糊匹配 (q_remark → remark)。"},
    "test_capability": {"type": "string", "description": "试验能力，模糊匹配 (q_testCapability → testCapability)。"},
    # ── 候选 filter（第 4.1 节） ──
    "cost_assessment": {"type": "string", "description": "费用评估，候选 filter，模糊匹配。"},
    "department_name": {"type": "string", "description": "部门，候选 filter，模糊匹配。"},
    "rstatus": {
        "type": "integer",
        "description": "RSTATUS，候选 filter，精确匹配: 0=已作废, 1=已审核, 2=暂存, 3=等待重新审批, 4=审批中。",
    },
    "unit_name": {"type": "string", "description": "计费单位，候选 filter，模糊匹配。"},
    "unit_price": {"type": "string", "description": "标准价格（RMB），候选 filter，模糊匹配。"},
    "include_raw": {
        "type": "boolean",
        "description": "调试用。默认 false；为 true 时才返回后端原始 raw_resultList/raw_response。",
    },
}

TOOL_SCHEMAS = [
    {
        "name": "query_sdtemptestserviceitemlistaction",
        "description": (
            "查询临时测试服务项目列表，default 包含继承的 /SdTempTestServiceItemListAction/listQuery。"
            "返回 count、columns、data/normalized_data。"
        ),
        "inputSchema": {"type": "object", "properties": _PROPERTIES},
    }
]
