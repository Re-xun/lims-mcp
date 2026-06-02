"""MCP tools for SdServiceItemListAction service item list queries."""
from __future__ import annotations

import json
import os
import sys
from typing import Any

import httpx

JAVA_API_BASE = os.environ.get("JAVA_API_BASE", "http://localhost:8080")

SCOPE_TO_ENDPOINT = {
    "default": "/SdServiceItemListAction/listQuery",
}

FILTER_CONFIG: dict[str, dict[str, str]] = {
    # ── 核心筛选（第 4 节） ──
    "country": {"backend_field": "country", "template": "like '%{value}%'"},
    "dept": {"backend_field": "ssi.responsible_dept_by", "template": "= '{value}'"},
    "fast_search": {"backend_field": "fastSearch", "template": "like '%{value}%'"},
    "item_category": {"backend_field": "itemCategory", "template": "like '%{value}%'"},
    "item_category2": {"backend_field": "itemCategory2", "template": "like '%{value}%'"},
    "item_name": {"backend_field": "itemName", "template": "like '%{value}%'"},
    "item_no": {"backend_field": "itemNo", "template": "like '%{value}%'"},
    "product_category": {"backend_field": "productCategory", "template": "like '%{value}%'"},
    "product_desc": {"backend_field": "productDesc", "template": "like '%{value}%'"},
    "rstatus": {"backend_field": "ssi.rstatus", "template": "= {value}"},
    "test_standard": {"backend_field": "testStandard", "template": "like '%{value}%'"},
    # ── 候选 filter（第 4.1 节） ──
    "certificate_amt": {"backend_field": "certificateAmt", "template": "like '%{value}%'"},
    "consumable_amt": {"backend_field": "consumableAmt", "template": "like '%{value}%'"},
    "electric_charge_amt": {"backend_field": "electricChargeAmt", "template": "like '%{value}%'"},
    "equipment_depreciation_amt": {"backend_field": "equipmentDepreciationAmt", "template": "like '%{value}%'"},
    "flag_fall_price": {"backend_field": "flagFallPrice", "template": "= {value}"},
    "gross_profit": {"backend_field": "grossProfit", "template": "like '%{value}%'"},
    "information_requirement": {"backend_field": "informationRequirement", "template": "like '%{value}%'"},
    "new_service_duration": {"backend_field": "newServiceDuration", "template": "= {value}"},
    "other_amt": {"backend_field": "otherAmt", "template": "like '%{value}%'"},
    "outsource_amt": {"backend_field": "outsourceAmt", "template": "like '%{value}%'"},
    "remark": {"backend_field": "remark", "template": "like '%{value}%'"},
    "remark1": {"backend_field": "remark1", "template": "like '%{value}%'"},
    "sample_requirement": {"backend_field": "sampleRequirement", "template": "like '%{value}%'"},
    "unit_name": {"backend_field": "unitName", "template": "like '%{value}%'"},
    "unit_price": {"backend_field": "unitPrice", "template": "= {value}"},
    "us_unit_price": {"backend_field": "usUnitPrice", "template": "= {value}"},
}

FIELD_LABELS: dict[str, dict[str, str]] = {
    "itemNo": {"key": "item_no", "title": "编号"},
    "rstatus": {"key": "rstatus", "title": "状态"},
    "itemName": {"key": "item_name", "title": "服务项目名称"},
    "itemCategory": {"key": "item_category", "title": "类别"},
    "responsibleDeptName": {"key": "responsible_dept_name", "title": "负责部门"},
    "productCategory": {"key": "product_category", "title": "产品类别"},
    "itemCategory2": {"key": "item_category2", "title": "领域类别"},
    "country": {"key": "country", "title": "国别"},
    "testStandard": {"key": "test_standard", "title": "依据标准"},
    "usUnitPrice": {"key": "us_unit_price", "title": "美元标准价格"},
    "productDesc": {"key": "product_desc", "title": "产品描述"},
    "unitName": {"key": "unit_name", "title": "计价单位"},
    "newServiceDuration": {"key": "new_service_duration", "title": "服务周期"},
    "unitPrice": {"key": "unit_price", "title": "RMB标准价格"},
    "flagFallPrice": {"key": "flag_fall_price", "title": "最低起步价"},
    "certificateAmt": {"key": "certificate_amt", "title": "规费支出"},
    "outsourceAmt": {"key": "outsource_amt", "title": "外包支出"},
    "consumableAmt": {"key": "consumable_amt", "title": "耗材支出"},
    "electricChargeAmt": {"key": "electric_charge_amt", "title": "电费支出"},
    "equipmentDepreciationAmt": {"key": "equipment_depreciation_amt", "title": "设备折旧"},
    "otherAmt": {"key": "other_amt", "title": "其他支出"},
    "grossProfit": {"key": "gross_profit", "title": "项目毛利"},
    "informationRequirement": {"key": "information_requirement", "title": "资料要求"},
    "sampleRequirement": {"key": "sample_requirement", "title": "样品需求"},
    "remark1": {"key": "remark1", "title": "内部备注"},
    "remark": {"key": "remark", "title": "备注"},
}

ENUM_FIELDS = {
    "rstatus": {
        1: "审核",
        2: "暂存",
        0: "作废",
        3: "等待重新审批",
        4: "提交",
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


async def query_sdserviceitemlistaction(
    token: str,
    scope: str = "default",
    view: str | None = None,
    start: int = 0,
    limit: int = 10,
    # ── 核心筛选（第 4 节） ──
    country: str | None = None,
    dept: str | None = None,
    fast_search: str | None = None,
    item_category: str | None = None,
    item_category2: str | None = None,
    item_name: str | None = None,
    item_no: str | None = None,
    product_category: str | None = None,
    product_desc: str | None = None,
    rstatus: int | None = None,
    test_standard: str | None = None,
    # ── 候选 filter（第 4.1 节） ──
    certificate_amt: str | None = None,
    consumable_amt: str | None = None,
    electric_charge_amt: str | None = None,
    equipment_depreciation_amt: str | None = None,
    flag_fall_price: float | None = None,
    gross_profit: str | None = None,
    information_requirement: str | None = None,
    new_service_duration: float | None = None,
    other_amt: str | None = None,
    outsource_amt: str | None = None,
    remark: str | None = None,
    remark1: str | None = None,
    sample_requirement: str | None = None,
    unit_name: str | None = None,
    unit_price: float | None = None,
    us_unit_price: float | None = None,
    include_raw: bool = False,
) -> dict[str, Any]:
    """查询服务项目列表，default 包含继承的 /SdServiceItemListAction/listQuery。"""
    resolved_scope = _resolve_scope(scope=scope, view=view)
    params = build_params(
        start=start,
        limit=limit,
        country=country,
        dept=dept,
        fast_search=fast_search,
        item_category=item_category,
        item_category2=item_category2,
        item_name=item_name,
        item_no=item_no,
        product_category=product_category,
        product_desc=product_desc,
        rstatus=rstatus,
        test_standard=test_standard,
        certificate_amt=certificate_amt,
        consumable_amt=consumable_amt,
        electric_charge_amt=electric_charge_amt,
        equipment_depreciation_amt=equipment_depreciation_amt,
        flag_fall_price=flag_fall_price,
        gross_profit=gross_profit,
        information_requirement=information_requirement,
        new_service_duration=new_service_duration,
        other_amt=other_amt,
        outsource_amt=outsource_amt,
        remark=remark,
        remark1=remark1,
        sample_requirement=sample_requirement,
        unit_name=unit_name,
        unit_price=unit_price,
        us_unit_price=us_unit_price,
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
    "query_sdserviceitemlistaction": query_sdserviceitemlistaction,
}

_PROPERTIES: dict[str, dict[str, Any]] = {
    "scope": {
        "type": "string",
        "description": (
            "视图范围: default=默认列表查询。"
            "default 包含继承的 /SdServiceItemListAction/listQuery。"
        ),
    },
    "view": {"type": "string", "description": "scope 的别名；如同时传入，以 scope 为准。"},
    "start": {"type": "integer", "description": "分页起始位置，默认 0。"},
    "limit": {"type": "integer", "description": "分页条数，默认 10。"},
    # ── 核心筛选（第 4 节） ──
    "country": {"type": "string", "description": "国别，模糊匹配 (q_country → country)。"},
    "dept": {"type": "string", "description": "负责部门，精确匹配 (q_dept → ssi.responsible_dept_by)。"},
    "fast_search": {"type": "string", "description": "视图，模糊匹配 (fastSearch → fastSearch)。"},
    "item_category": {"type": "string", "description": "q_itemCategory，模糊匹配 (q_itemCategory → itemCategory)。"},
    "item_category2": {"type": "string", "description": "领域类别，模糊匹配 (q_itemCategory2 → itemCategory2)。"},
    "item_name": {"type": "string", "description": "服务项目，模糊匹配 (q_itemName → itemName)。"},
    "item_no": {"type": "string", "description": "编号，模糊匹配 (q_itemNo → itemNo)。"},
    "product_category": {"type": "string", "description": "产品类型，模糊匹配 (q_productCategory → productCategory)。"},
    "product_desc": {"type": "string", "description": "产品描述，模糊匹配 (q_productDesc → productDesc)。"},
    "rstatus": {
        "type": "integer",
        "description": "单据状态 (q_rstatus → ssi.rstatus): 0=作废, 1=审核, 2=暂存, 3=等待重新审批, 4=提交。",
    },
    "test_standard": {"type": "string", "description": "依据标准，模糊匹配 (q_testStandard → testStandard)。"},
    # ── 候选 filter（第 4.1 节） ──
    "certificate_amt": {"type": "string", "description": "规费支出，候选 filter，模糊匹配。"},
    "consumable_amt": {"type": "string", "description": "耗材支出，候选 filter，模糊匹配。"},
    "electric_charge_amt": {"type": "string", "description": "电费支出，候选 filter，模糊匹配。"},
    "equipment_depreciation_amt": {"type": "string", "description": "设备折旧，候选 filter，模糊匹配。"},
    "flag_fall_price": {"type": "number", "description": "最低起步价，候选 filter，精确匹配。"},
    "gross_profit": {"type": "string", "description": "项目毛利，候选 filter，模糊匹配。"},
    "information_requirement": {"type": "string", "description": "资料要求，候选 filter，模糊匹配。"},
    "new_service_duration": {"type": "number", "description": "服务周期，候选 filter，精确匹配。"},
    "other_amt": {"type": "string", "description": "其他支出，候选 filter，模糊匹配。"},
    "outsource_amt": {"type": "string", "description": "外包支出，候选 filter，模糊匹配。"},
    "remark": {"type": "string", "description": "备注，候选 filter，模糊匹配。"},
    "remark1": {"type": "string", "description": "内部备注，候选 filter，模糊匹配。"},
    "sample_requirement": {"type": "string", "description": "样品需求，候选 filter，模糊匹配。"},
    "unit_name": {"type": "string", "description": "计价单位，候选 filter，模糊匹配。"},
    "unit_price": {"type": "number", "description": "RMB标准价格，候选 filter，精确匹配。"},
    "us_unit_price": {"type": "number", "description": "美元标准价格，候选 filter，精确匹配。"},
    "include_raw": {
        "type": "boolean",
        "description": "调试用。默认 false；为 true 时才返回后端原始 raw_resultList/raw_response。",
    },
}

TOOL_SCHEMAS = [
    {
        "name": "query_sdserviceitemlistaction",
        "description": (
            "查询服务项目列表，default 包含继承的 /SdServiceItemListAction/listQuery。"
            "返回 count、columns、data/normalized_data。"
        ),
        "inputSchema": {"type": "object", "properties": _PROPERTIES},
    }
]
