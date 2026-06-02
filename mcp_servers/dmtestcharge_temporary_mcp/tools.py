"""MCP tools for DmTestChargeTemporaryListAction charge order list queries."""
from __future__ import annotations

import json
import os
import sys
from typing import Any

import httpx

JAVA_API_BASE = os.environ.get("JAVA_API_BASE", "http://localhost:8080")

SCOPE_TO_ENDPOINT = {
    "default": "/DmTestChargeTemporaryListAction/listQuery",
    "dm": "/DmTestChargeTemporaryListAction/listQueryDm",
    "gen": "/DmTestChargeTemporaryListAction/listQueryGen",
    "op": "/DmTestChargeTemporaryListAction/listQueryOp",
    "rf": "/DmTestChargeTemporaryListAction/listQueryRf",
    "safety": "/DmTestChargeTemporaryListAction/listQuerySFY",
}

FILTER_CONFIG = {
    "bstatus": {"backend_field": "bstatus", "template": "= '{value}'"},
    "charge_no": {"backend_field": "chargeNo", "template": "like '%{value}%'"},
    "customer_contact": {"backend_field": "customerContact", "template": "like '%{value}%'"},
    "customer_name": {"backend_field": "customerName", "template": "like '%{value}%'"},
    "locations": {"backend_field": "locations", "template": "like '%{value}%'"},
    "order_date_end": {"backend_field": "orderDate", "template": "<= '{value} 23:59:59'"},
    "order_date_start": {"backend_field": "orderDate", "template": ">= '{value}'"},
    "order_name": {"backend_field": "orderName", "template": "like '%{value}%'"},
    "saler_name": {"backend_field": "salerName", "template": "like '%{value}%'"},
    "sample_model": {"backend_field": "sampleModel", "template": "like '%{value}%'"},
    "sample_name": {"backend_field": "sampleName", "template": "like '%{value}%'"},
    "sign_status": {"backend_field": "signStatus", "template": "= '{value}'"},
    "test_date": {"backend_field": "testDate", "template": "like '%{value}%'"},
    "test_engineer_name": {"backend_field": "testEngineerName", "template": "like '%{value}%'"},
    "test_item": {"backend_field": "testItem", "template": "like '%{value}%'"},
    "test_time": {"backend_field": "testTime", "template": "like '%{value}%'"},
    "total_hours": {"backend_field": "totalHours", "template": "like '%{value}%'"},
}

FIELD_LABELS = {
    "chargeNo": {"key": "charge_no", "title": "收费单编号"},
    "orderDate": {"key": "order_date", "title": "收费单日期"},
    "totalHours": {"key": "total_hours", "title": "收费单时长(H)"},
    "orderName": {"key": "order_name", "title": "开单人"},
    "signStatus": {"key": "sign_status", "title": "签字状态"},
    "bstatus": {"key": "bstatus", "title": "收费单状态"},
    "customerName": {"key": "customer_name", "title": "客户名称"},
    "customerContact": {"key": "customer_contact", "title": "客户联系人"},
    "sampleName": {"key": "sample_name", "title": "样品名称"},
    "sampleModel": {"key": "sample_model", "title": "样品型号"},
    "locations": {"key": "locations", "title": "试验场地"},
    "testItem": {"key": "test_item", "title": "试验项目"},
    "testDate": {"key": "test_date", "title": "试验日期"},
    "testEngineerName": {"key": "test_engineer_name", "title": "试验人员"},
    "testTime": {"key": "test_time", "title": "试验时长"},
    "salerName": {"key": "saler_name", "title": "负责销售"},
}

ENUM_FIELDS = {
    "bstatus": {
        1: "未转销售合同",
        4: "已转销售合同",
        5: "已收款",
        0: "已作废",
    },
    "sign_status": {
        0: "未签字",
        1: "已签字",
    },
}


def _mask_token(token: str) -> str:
    if token and len(token) > 8:
        return token[:8] + "***"
    return "***"


def _resolve_scope(scope: str | None = None, view: str | None = None) -> str:
    resolved = (scope or view or "default").strip().lower()
    if resolved not in SCOPE_TO_ENDPOINT:
        raise ValueError(
            "不支持的 scope/view 值：{}。可选值：{}".format(
                resolved, ", ".join(sorted(SCOPE_TO_ENDPOINT))
            )
        )
    return resolved


def build_filter(
    *,
    bstatus: str | None = None,
    charge_no: str | None = None,
    customer_contact: str | None = None,
    customer_name: str | None = None,
    locations: str | None = None,
    order_date_end: str | None = None,
    order_date_start: str | None = None,
    order_name: str | None = None,
    saler_name: str | None = None,
    sample_model: str | None = None,
    sample_name: str | None = None,
    sign_status: str | None = None,
    test_date: str | None = None,
    test_engineer_name: str | None = None,
    test_item: str | None = None,
    test_time: str | None = None,
    total_hours: str | None = None,
) -> str | None:
    values = {
        "bstatus": bstatus,
        "charge_no": charge_no,
        "customer_contact": customer_contact,
        "customer_name": customer_name,
        "locations": locations,
        "order_date_end": order_date_end,
        "order_date_start": order_date_start,
        "order_name": order_name,
        "saler_name": saler_name,
        "sample_model": sample_model,
        "sample_name": sample_name,
        "sign_status": sign_status,
        "test_date": test_date,
        "test_engineer_name": test_engineer_name,
        "test_item": test_item,
        "test_time": test_time,
        "total_hours": total_hours,
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
    bstatus: str | None = None,
    charge_no: str | None = None,
    customer_contact: str | None = None,
    customer_name: str | None = None,
    locations: str | None = None,
    order_date_end: str | None = None,
    order_date_start: str | None = None,
    order_name: str | None = None,
    saler_name: str | None = None,
    sample_model: str | None = None,
    sample_name: str | None = None,
    sign_status: str | None = None,
    test_date: str | None = None,
    test_engineer_name: str | None = None,
    test_item: str | None = None,
    test_time: str | None = None,
    total_hours: str | None = None,
    sVars: dict | None = None,
) -> dict[str, str]:
    merged_svars = dict(sVars or {})
    params = {
        "start": str(0 if start is None else start),
        "limit": str(10 if limit is None else limit),
        "sVars": json.dumps(merged_svars, ensure_ascii=False),
    }

    filter_sql = build_filter(
        bstatus=bstatus,
        charge_no=charge_no,
        customer_contact=customer_contact,
        customer_name=customer_name,
        locations=locations,
        order_date_end=order_date_end,
        order_date_start=order_date_start,
        order_name=order_name,
        saler_name=saler_name,
        sample_model=sample_model,
        sample_name=sample_name,
        sign_status=sign_status,
        test_date=test_date,
        test_engineer_name=test_engineer_name,
        test_item=test_item,
        test_time=test_time,
        total_hours=total_hours,
    )
    if filter_sql:
        params["filter"] = filter_sql

    return params


def _build_columns() -> list[dict[str, str]]:
    return [
        {
            "field": field,
            "key": meta["key"],
            "title": meta["title"],
        }
        for field, meta in FIELD_LABELS.items()
    ]


def _enum_text(key: str, value: Any) -> str | None:
    enum_map = ENUM_FIELDS.get(key)
    if not enum_map:
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
            normalized[f"{key}_text"] = text
    return normalized


def _extract_result_list(payload: dict[str, Any]) -> list[dict[str, Any]]:
    nested_data = payload.get("data")
    if isinstance(nested_data, dict):
        nested_result_list = nested_data.get("resultList")
        if isinstance(nested_result_list, list):
            return nested_result_list

    top_level_result_list = payload.get("resultList")
    if isinstance(top_level_result_list, list):
        return top_level_result_list

    return []


def _extract_count(payload: dict[str, Any], fallback_count: int) -> int:
    nested_data = payload.get("data")
    if isinstance(nested_data, dict) and isinstance(nested_data.get("count"), int):
        return nested_data["count"]
    if isinstance(payload.get("count"), int):
        return payload["count"]
    return fallback_count


async def query_dmtestchargetemporarylistaction(
    token: str,
    scope: str = "default",
    view: str | None = None,
    start: int = 0,
    limit: int = 10,
    bstatus: str | None = None,
    charge_no: str | None = None,
    customer_contact: str | None = None,
    customer_name: str | None = None,
    locations: str | None = None,
    order_date_end: str | None = None,
    order_date_start: str | None = None,
    order_name: str | None = None,
    saler_name: str | None = None,
    sample_model: str | None = None,
    sample_name: str | None = None,
    sign_status: str | None = None,
    test_date: str | None = None,
    test_engineer_name: str | None = None,
    test_item: str | None = None,
    test_time: str | None = None,
    total_hours: str | None = None,
    sVars: dict | None = None,
    include_raw: bool = False,
) -> dict[str, Any]:
    """查询 DmTestChargeTemporaryListAction 收费单列表，按 scope 路由不同视图。"""
    resolved_scope = _resolve_scope(scope=scope, view=view)
    params = build_params(
        start=start,
        limit=limit,
        bstatus=bstatus,
        charge_no=charge_no,
        customer_contact=customer_contact,
        customer_name=customer_name,
        locations=locations,
        order_date_end=order_date_end,
        order_date_start=order_date_start,
        order_name=order_name,
        saler_name=saler_name,
        sample_model=sample_model,
        sample_name=sample_name,
        sign_status=sign_status,
        test_date=test_date,
        test_engineer_name=test_engineer_name,
        test_item=test_item,
        test_time=test_time,
        total_hours=total_hours,
        sVars=sVars,
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
    "query_dmtestchargetemporarylistaction": query_dmtestchargetemporarylistaction,
}

TOOL_SCHEMAS = [
    {
        "name": "query_dmtestchargetemporarylistaction",
        "description": (
            "查询 DmTestChargeTemporaryListAction 收费单列表。"
            "默认查询全部收费单；通过 scope 切换不同业务视图（DM/GEN/OP/RF/安全）。"
            "返回 count、columns、data/normalized_data。"
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "scope": {
                    "type": "string",
                    "description": (
                        "视图范围：default=默认列表查询，dm=DM 业务视图，"
                        "gen=GEN 业务视图，op=OP 业务视图，rf=RF 业务视图，"
                        "safety=安全业务视图。"
                    ),
                },
                "view": {
                    "type": "string",
                    "description": "scope 的别名；如同时传入，以 scope 为准。",
                },
                "start": {"type": "integer", "description": "分页起始位置，默认 0。"},
                "limit": {"type": "integer", "description": "分页条数，默认 10。"},
                "bstatus": {
                    "type": "string",
                    "description": "收费单状态，精确匹配 (bstatus)：1=未转销售合同, 4=已转销售合同, 5=已收款, 0=已作废。",
                },
                "charge_no": {"type": "string", "description": "收费单编号，模糊匹配 (chargeNo)。"},
                "customer_contact": {"type": "string", "description": "客户联系人，模糊匹配 (customerContact)。"},
                "customer_name": {"type": "string", "description": "客户名称，模糊匹配 (customerName)。"},
                "locations": {"type": "string", "description": "试验场地，模糊匹配 (locations)。"},
                "order_date_end": {
                    "type": "string",
                    "description": "收费单日期结束 (<= 23:59:59)，格式 YYYY-MM-DD (orderDate)。",
                },
                "order_date_start": {
                    "type": "string",
                    "description": "收费单日期开始 (>=)，格式 YYYY-MM-DD (orderDate)。",
                },
                "order_name": {"type": "string", "description": "开单人，模糊匹配 (orderName)。"},
                "saler_name": {"type": "string", "description": "负责销售，模糊匹配 (salerName)。"},
                "sample_model": {"type": "string", "description": "样品型号，模糊匹配 (sampleModel)。"},
                "sample_name": {"type": "string", "description": "样品名称，模糊匹配 (sampleName)。"},
                "sign_status": {
                    "type": "string",
                    "description": "签字状态，精确匹配 (signStatus)：0=未签字, 1=已签字。",
                },
                "test_date": {"type": "string", "description": "试验日期，模糊匹配 (testDate)。"},
                "test_engineer_name": {"type": "string", "description": "试验人员，模糊匹配 (testEngineerName)。"},
                "test_item": {"type": "string", "description": "试验项目，模糊匹配 (testItem)。"},
                "test_time": {"type": "string", "description": "试验时长，模糊匹配 (testTime)。"},
                "total_hours": {"type": "string", "description": "收费单时长(H)，模糊匹配 (totalHours)。"},
                "sVars": {
                    "type": "object",
                    "description": "高级兼容参数。当前未发现 XML 定义的 dataType；只有明确需要时才传自定义 sVars。",
                },
                "include_raw": {
                    "type": "boolean",
                    "description": "调试用。默认 false；为 true 时才返回后端原始 raw_resultList/raw_response。",
                },
            },
        },
    },
]
