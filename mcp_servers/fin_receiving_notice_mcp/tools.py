"""MCP tools for FinReceivingNoticeListAction queries."""
from __future__ import annotations

import json
import os
import sys
from typing import Any

import httpx

JAVA_API_BASE = os.environ.get("JAVA_API_BASE", "http://localhost:8080")

SCOPE_TO_ENDPOINT = {
    "default": "/FinReceivingNoticeListAction/listQuery",
    "dept": "/FinReceivingNoticeListAction/listQueryDept",
    "mine": "/FinReceivingNoticeListAction/listQueryMy",
}

SCOPE_TO_CUSTOMER_TYPE = {
    "default": "1",
    "dept": "1",
    "mine": "1",
}

SCOPE_TO_DATA_TYPE = {
    "dept": "listView",
    "mine": "listView",
}

FILTER_CONFIG = {
    "create_on": {
        "backend_field": "frn.create_on",
        "template": "= '{value}'",
    },
    "currency_id": {
        "backend_field": "ac.CUSTOMER_NAME_CN",
        "template": "like '%{value}%'",
    },
    "fast_search": {
        "backend_field": "fastSearch",
        "template": "like '%{value}%'",
    },
    "order_no": {
        "backend_field": "frn.order_no",
        "template": "like '%{value}%'",
    },
    "bank_name": {
        "backend_field": "bankName",
        "template": "like '%{value}%'",
    },
    "create_on_end": {
        "backend_field": "createOn",
        "template": "<= '{value} 23:59:59'",
    },
    "create_on_start": {
        "backend_field": "createOn",
        "template": ">= '{value}'",
    },
    "currency_name": {
        "backend_field": "currencyName",
        "template": "like '%{value}%'",
    },
    "customer_name": {
        "backend_field": "customerName",
        "template": "like '%{value}%'",
    },
    "receiving_notice_date_format": {
        "backend_field": "receivingNoticeDateFormat",
        "template": "like '%{value}%'",
    },
    "remark": {
        "backend_field": "remark",
        "template": "like '%{value}%'",
    },
    "sum_order_amt": {
        "backend_field": "sumOrderAmt",
        "template": "like '%{value}%'",
    },
    "sum_receivable_amt": {
        "backend_field": "sumReceivableAmt",
        "template": "like '%{value}%'",
    },
    "sum_received_amt": {
        "backend_field": "sumReceivedAmt",
        "template": "like '%{value}%'",
    },
    "total_amt": {
        "backend_field": "totalAmt",
        "template": "like '%{value}%'",
    },
    "user_name": {
        "backend_field": "userName",
        "template": "like '%{value}%'",
    },
}

FIELD_LABELS = {
    "createOn": {
        "key": "create_on",
        "title": "创建日期",
    },
    "orderNo": {
        "key": "order_no",
        "title": "收款通知单编号",
    },
    "customerName": {
        "key": "customer_name",
        "title": "客户名称",
    },
    "receivingNoticeDateFormat": {
        "key": "receiving_notice_date_format",
        "title": "收款月度",
    },
    "totalAmt": {
        "key": "total_amt",
        "title": "总计收款金额",
    },
    "sumOrderAmt": {
        "key": "sum_order_amt",
        "title": "总计合同金额",
    },
    "currencyName": {
        "key": "currency_name",
        "title": "币别",
    },
    "sumReceivedAmt": {
        "key": "sum_received_amt",
        "title": "总计已收金额",
    },
    "sumReceivableAmt": {
        "key": "sum_receivable_amt",
        "title": "总计剩余应收金额",
    },
    "bankName": {
        "key": "bank_name",
        "title": "收款银行",
    },
    "userName": {
        "key": "user_name",
        "title": "创建人",
    },
    "remark": {
        "key": "remark",
        "title": "备注",
    },
}

ENUM_FIELDS: dict[str, dict[Any, Any]] = {}


def _mask_token(token: str) -> str:
    if token and len(token) > 8:
        return token[:8] + "***"
    return "***"


def _resolve_scope(scope: str | None = None, view: str | None = None) -> str:
    resolved = (scope or view or "default").strip().lower()
    if resolved not in SCOPE_TO_ENDPOINT:
        raise ValueError(
            "Unsupported scope/view: {}. Allowed values: {}".format(
                resolved, ", ".join(sorted(SCOPE_TO_ENDPOINT))
            )
        )
    return resolved


def build_filter(
    *,
    create_on: str | None = None,
    currency_id: str | None = None,
    fast_search: str | None = None,
    order_no: str | None = None,
    bank_name: str | None = None,
    create_on_end: str | None = None,
    create_on_start: str | None = None,
    currency_name: str | None = None,
    customer_name: str | None = None,
    receiving_notice_date_format: str | None = None,
    remark: str | None = None,
    sum_order_amt: str | None = None,
    sum_receivable_amt: str | None = None,
    sum_received_amt: str | None = None,
    total_amt: str | None = None,
    user_name: str | None = None,
) -> str | None:
    values = {
        "create_on": create_on,
        "currency_id": currency_id,
        "fast_search": fast_search,
        "order_no": order_no,
        "bank_name": bank_name,
        "create_on_end": create_on_end,
        "create_on_start": create_on_start,
        "currency_name": currency_name,
        "customer_name": customer_name,
        "receiving_notice_date_format": receiving_notice_date_format,
        "remark": remark,
        "sum_order_amt": sum_order_amt,
        "sum_receivable_amt": sum_receivable_amt,
        "sum_received_amt": sum_received_amt,
        "total_amt": total_amt,
        "user_name": user_name,
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
    scope: str,
    start: int = 0,
    limit: int = 10,
    create_on: str | None = None,
    currency_id: str | None = None,
    fast_search: str | None = None,
    order_no: str | None = None,
    bank_name: str | None = None,
    create_on_end: str | None = None,
    create_on_start: str | None = None,
    currency_name: str | None = None,
    customer_name: str | None = None,
    receiving_notice_date_format: str | None = None,
    remark: str | None = None,
    sum_order_amt: str | None = None,
    sum_receivable_amt: str | None = None,
    sum_received_amt: str | None = None,
    total_amt: str | None = None,
    user_name: str | None = None,
    sVars: dict | None = None,
) -> dict[str, str]:
    merged_svars = {
        "customerType": SCOPE_TO_CUSTOMER_TYPE[scope],
    }
    data_type = SCOPE_TO_DATA_TYPE.get(scope)
    if data_type is not None:
        merged_svars["dataType"] = data_type
    if sVars is not None:
        merged_svars.update(sVars)

    params = {
        "start": str(0 if start is None else start),
        "limit": str(10 if limit is None else limit),
        "sVars": json.dumps(merged_svars, ensure_ascii=False),
    }

    filter_sql = build_filter(
        create_on=create_on,
        currency_id=currency_id,
        fast_search=fast_search,
        order_no=order_no,
        bank_name=bank_name,
        create_on_end=create_on_end,
        create_on_start=create_on_start,
        currency_name=currency_name,
        customer_name=customer_name,
        receiving_notice_date_format=receiving_notice_date_format,
        remark=remark,
        sum_order_amt=sum_order_amt,
        sum_receivable_amt=sum_receivable_amt,
        sum_received_amt=sum_received_amt,
        total_amt=total_amt,
        user_name=user_name,
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


def _normalize_row(row: dict[str, Any]) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    for field, meta in FIELD_LABELS.items():
        normalized[meta["key"]] = row.get(field)
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


async def query_finreceivingnoticelistaction(
    token: str,
    scope: str = "default",
    view: str | None = None,
    start: int = 0,
    limit: int = 10,
    create_on: str | None = None,
    currency_id: str | None = None,
    fast_search: str | None = None,
    order_no: str | None = None,
    bank_name: str | None = None,
    create_on_end: str | None = None,
    create_on_start: str | None = None,
    currency_name: str | None = None,
    customer_name: str | None = None,
    receiving_notice_date_format: str | None = None,
    remark: str | None = None,
    sum_order_amt: str | None = None,
    sum_receivable_amt: str | None = None,
    sum_received_amt: str | None = None,
    total_amt: str | None = None,
    user_name: str | None = None,
    sVars: dict | None = None,
    include_raw: bool = False,
) -> dict[str, Any]:
    """查询收款通知单列表，按 scope 路由到默认、部门、我的视图。"""
    resolved_scope = _resolve_scope(scope=scope, view=view)
    params = build_params(
        scope=resolved_scope,
        start=start,
        limit=limit,
        create_on=create_on,
        currency_id=currency_id,
        fast_search=fast_search,
        order_no=order_no,
        bank_name=bank_name,
        create_on_end=create_on_end,
        create_on_start=create_on_start,
        currency_name=currency_name,
        customer_name=customer_name,
        receiving_notice_date_format=receiving_notice_date_format,
        remark=remark,
        sum_order_amt=sum_order_amt,
        sum_receivable_amt=sum_receivable_amt,
        sum_received_amt=sum_received_amt,
        total_amt=total_amt,
        user_name=user_name,
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
    "query_finreceivingnoticelistaction": query_finreceivingnoticelistaction,
    "query_fin_receiving_notice_list": query_finreceivingnoticelistaction,
}

TOOL_SCHEMAS = [
    {
        "name": "query_finreceivingnoticelistaction",
        "description": (
            "查询收款通知单列表。通过 scope/view 路由到默认、部门、我的三个视图，"
            "默认视图包含继承的 /FinReceivingNoticeListAction/listQuery。"
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "scope": {
                    "type": "string",
                    "description": "视图范围：default=默认列表，dept=部门范围视图，mine=我的数据视图。",
                },
                "view": {
                    "type": "string",
                    "description": "scope 的别名；如同时传入，以 scope 为准。",
                },
                "start": {
                    "type": "integer",
                    "description": "分页起始位置，默认 0。",
                },
                "limit": {
                    "type": "integer",
                    "description": "分页条数，默认 10。",
                },
                "create_on": {
                    "type": "string",
                    "description": "创建日期，精确匹配 (q_createOn -> frn.create_on)。",
                },
                "currency_id": {
                    "type": "string",
                    "description": "客户名称，模糊匹配 (q_currencyId -> ac.CUSTOMER_NAME_CN)。",
                },
                "fast_search": {
                    "type": "string",
                    "description": "视图，模糊匹配 (fastSearch -> fastSearch)。",
                },
                "order_no": {
                    "type": "string",
                    "description": "收款通知单编号，模糊匹配 (q_orderNo -> frn.order_no)。",
                },
                "bank_name": {
                    "type": "string",
                    "description": "收款银行候选字段，模糊匹配 (bankName -> bankName)。",
                },
                "create_on_end": {
                    "type": "string",
                    "description": "创建日期结束，格式 YYYY-MM-DD (createOn -> createOn, <= 23:59:59)。",
                },
                "create_on_start": {
                    "type": "string",
                    "description": "创建日期开始，格式 YYYY-MM-DD (createOn -> createOn, >=)。",
                },
                "currency_name": {
                    "type": "string",
                    "description": "币别候选字段，模糊匹配 (currencyName -> currencyName)。",
                },
                "customer_name": {
                    "type": "string",
                    "description": "客户名称候选字段，模糊匹配 (customerName -> customerName)。",
                },
                "receiving_notice_date_format": {
                    "type": "string",
                    "description": "收款月度候选字段，模糊匹配 (receivingNoticeDateFormat -> receivingNoticeDateFormat)。",
                },
                "remark": {
                    "type": "string",
                    "description": "备注候选字段，模糊匹配 (remark -> remark)。",
                },
                "sum_order_amt": {
                    "type": "string",
                    "description": "总计合同金额候选字段，模糊匹配 (sumOrderAmt -> sumOrderAmt)。",
                },
                "sum_receivable_amt": {
                    "type": "string",
                    "description": "总计剩余应收金额候选字段，模糊匹配 (sumReceivableAmt -> sumReceivableAmt)。",
                },
                "sum_received_amt": {
                    "type": "string",
                    "description": "总计已收金额候选字段，模糊匹配 (sumReceivedAmt -> sumReceivedAmt)。",
                },
                "total_amt": {
                    "type": "string",
                    "description": "总计收款金额候选字段，模糊匹配 (totalAmt -> totalAmt)。",
                },
                "user_name": {
                    "type": "string",
                    "description": "创建人候选字段，模糊匹配 (userName -> userName)。",
                },
                "sVars": {
                    "type": "object",
                    "description": "自定义 sVars 负载，会覆盖默认 customerType/dataType；dataType 仅按文档第 7 节出现的 listView/Week 传入。",
                },
                "include_raw": {
                    "type": "boolean",
                    "description": "调试用。默认 false；为 true 时才返回后端原始 raw_resultList/raw_response。",
                },
            },
        },
    },
]
