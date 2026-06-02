"""MCP tools for FinCasReversingListAction reversing queries."""
from __future__ import annotations

import json
import os
import sys
from typing import Any

import httpx

JAVA_API_BASE = os.environ.get("JAVA_API_BASE", "http://localhost:8080")

SCOPE_TO_ENDPOINT = {
    "default": "/FinCasReversingListAction/listQuery",
    "listQueryForSVar": "/FinCasReversingListAction/listQueryForSVar",
}

SCOPE_DEFAULT_SVARS = {
    "default": {"operation": "operation", "modType": "modType"},
    "listQueryForSVar": {"operationCode": "''FINCASREVERSING-VIEW''", "modType": "SD"},
}

FILTER_CONFIG = {
    "fast_search": {"backend_field": "fastSearch", "template": "like '%{value}%'"},
    "order_date_end": {"backend_field": "orderDate", "template": "<= '{value} 23:59:59'"},
    "order_date_start": {"backend_field": "orderDate", "template": ">= '{value}'"},
    "order_no": {"backend_field": "orderNo", "template": "like '%{value}%'"},
    "receiving_company": {"backend_field": "receivingCompany", "template": "like '%{value}%'"},
    "reversed_invoice_amt": {"backend_field": "reversedInvoiceAmt", "template": "like '%{value}%'"},
    "reversing_date_end": {"backend_field": "reversingDate", "template": "<= '{value} 23:59:59'"},
    "reversing_date_start": {"backend_field": "reversingDate", "template": ">= '{value}'"},
    "reversing_type": {"backend_field": "reversingType", "template": "= '{value}'"},
    "total_reversing_amt": {"backend_field": "totalReversingAmt", "template": "like '%{value}%'"},
    "txn_source_no": {"backend_field": "txnSourceNo", "template": "like '%{value}%'"},
}

FIELD_LABELS = {
    "orderNo": {"key": "order_no", "title": "退款单号"},
    "orderDate": {"key": "order_date", "title": "记录日期"},
    "reversingDate": {"key": "reversing_date", "title": "退款日期"},
    "txnSourceNo": {"key": "txn_source_no", "title": "收款单号"},
    "totalReversingAmt": {"key": "total_reversing_amt", "title": "本次退款金额"},
    "reversedInvoiceAmt": {"key": "reversed_invoice_amt", "title": "本次退票金额"},
    "reversingType": {"key": "reversing_type", "title": "退款方式"},
    "receivingCompany": {"key": "receiving_company", "title": "收款公司"},
}

ENUM_FIELDS = {
    "reversing_type": {
        1: "现金",
        2: "转账",
        3: "支票",
        4: "备用金",
        5: "汇票",
        6: "支出退款",
    },
}


def _mask_token(token: str) -> str:
    if token and len(token) > 8:
        return token[:8] + "***"
    return "***"


def _resolve_scope(scope: str | None = None, view: str | None = None) -> str:
    resolved = (scope or view or "default").strip().lower()
    if resolved == "listqueryforsvar":
        resolved = "listQueryForSVar"
    if resolved not in SCOPE_TO_ENDPOINT:
        raise ValueError(
            "Unsupported scope/view: {}. Allowed values: {}".format(
                resolved, ", ".join(sorted(SCOPE_TO_ENDPOINT))
            )
        )
    return resolved


def build_filter(**values: Any) -> str | None:
    conditions: list[str] = []
    for param_name, value in values.items():
        if param_name not in FILTER_CONFIG or value is None or value == "":
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
    sVars: dict | None = None,
    **filters: Any,
) -> dict[str, str]:
    params = {
        "start": str(0 if start is None else start),
        "limit": str(10 if limit is None else limit),
        "sVars": json.dumps(dict(sVars or {}), ensure_ascii=False),
    }

    filter_sql = build_filter(**filters)
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


async def query_fincasreversinglistaction(
    token: str,
    scope: str = "default",
    view: str | None = None,
    start: int = 0,
    limit: int = 10,
    fast_search: str | None = None,
    order_date_end: str | None = None,
    order_date_start: str | None = None,
    order_no: str | None = None,
    receiving_company: str | None = None,
    reversed_invoice_amt: str | None = None,
    reversing_date_end: str | None = None,
    reversing_date_start: str | None = None,
    reversing_type: int | None = None,
    total_reversing_amt: str | None = None,
    txn_source_no: str | None = None,
    sVars: dict | None = None,
    include_raw: bool = False,
) -> dict[str, Any]:
    """查询退款单列表，default 包含继承的 /FinCasReversingListAction/listQuery。"""
    resolved_scope = _resolve_scope(scope=scope, view=view)

    merged_svars = dict(SCOPE_DEFAULT_SVARS.get(resolved_scope, {}))
    if sVars:
        merged_svars.update(sVars)

    params = build_params(
        start=start,
        limit=limit,
        fast_search=fast_search,
        order_date_end=order_date_end,
        order_date_start=order_date_start,
        order_no=order_no,
        receiving_company=receiving_company,
        reversed_invoice_amt=reversed_invoice_amt,
        reversing_date_end=reversing_date_end,
        reversing_date_start=reversing_date_start,
        reversing_type=reversing_type,
        total_reversing_amt=total_reversing_amt,
        txn_source_no=txn_source_no,
        sVars=merged_svars,
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
    "query_fincasreversinglistaction": query_fincasreversinglistaction,
}

TOOL_SCHEMAS = [
    {
        "name": "query_fincasreversinglistaction",
        "description": (
            "查询退款单列表。default=默认列表，包含继承的 "
            "/FinCasReversingListAction/listQuery（自动注入 operation=operation、modType=modType）。"
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "scope": {
                    "type": "string",
                    "description": (
                        "视图范围：default=默认列表（自动注入 operation=operation, modType=modType），"
                        "listQueryForSVar=退款记录。"
                    ),
                },
                "view": {"type": "string", "description": "scope 的别名；如同时传入，以 scope 为准。"},
                "start": {"type": "integer", "description": "分页起始位置，默认 0。"},
                "limit": {"type": "integer", "description": "分页条数，默认 10。"},
                "fast_search": {"type": "string", "description": "视图，模糊匹配 (fastSearch -> fastSearch)。"},
                "order_date_end": {"type": "string", "description": "记录日期结束，格式 YYYY-MM-DD (orderDate, <= 23:59:59)。"},
                "order_date_start": {"type": "string", "description": "记录日期开始，格式 YYYY-MM-DD (orderDate, >=)。"},
                "order_no": {"type": "string", "description": "退款单号，模糊匹配 (orderNo -> orderNo)。"},
                "receiving_company": {"type": "string", "description": "收款公司，模糊匹配 (receivingCompany -> receivingCompany)。"},
                "reversed_invoice_amt": {"type": "string", "description": "本次退票金额，模糊匹配 (reversedInvoiceAmt -> reversedInvoiceAmt)。"},
                "reversing_date_end": {"type": "string", "description": "退款日期结束，格式 YYYY-MM-DD (reversingDate, <= 23:59:59)。"},
                "reversing_date_start": {"type": "string", "description": "退款日期开始，格式 YYYY-MM-DD (reversingDate, >=)。"},
                "reversing_type": {
                    "type": "integer",
                    "description": "退款方式，精确匹配 (reversingType -> reversingType)：1=现金, 2=转账, 3=支票, 4=备用金, 5=汇票, 6=支出退款。",
                },
                "total_reversing_amt": {"type": "string", "description": "本次退款金额，模糊匹配 (totalReversingAmt -> totalReversingAmt)。"},
                "txn_source_no": {"type": "string", "description": "收款单号，模糊匹配 (txnSourceNo -> txnSourceNo)。"},
                "sVars": {"type": "object", "description": "自定义 sVars 负载。default scope 自动注入 operation=operation、modType=modType；可传入额外键值合并。"},
                "include_raw": {"type": "boolean", "description": "调试用。默认 false；为 true 时才返回后端原始 raw_resultList/raw_response。"},
            },
        },
    },
]
