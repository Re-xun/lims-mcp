"""MCP tools for PsActivityListAction queries."""
from __future__ import annotations

import json
import os
import sys
from typing import Any

import httpx

JAVA_API_BASE = os.environ.get("JAVA_API_BASE", "http://localhost:8080")

SCOPE_TO_ENDPOINT = {
    "default": "/PsActivityListAction/listQuery",
    "dept": "/PsActivityListAction/listQueryDept",
    "mine": "/PsActivityListAction/listQueryMy",
}

SCOPE_TO_CUSTOMER_TYPE = {
    "default": 1,
    "dept": 2,
    "mine": 3,
}

FILTER_CONFIG = {
    "abd_customer_name": {
        "backend_field": "q_abdCustomerName",
        "template": "like '%{value}%'",
    },
    "contact_name": {
        "backend_field": "q_contactName",
        "template": "like '%{value}%'",
    },
    "fast_search": {
        "backend_field": "fastSearch",
        "template": "like '%{value}%'",
    },
    "sale_person": {
        "backend_field": "q_salePerson",
        "template": "like '%{value}%'",
    },
    "abd_person_name": {
        "backend_field": "abdPersonName",
        "template": "like '%{value}%'",
    },
    "act_start_time_start": {
        "backend_field": "actStartTime",
        "template": ">= '{value}'",
    },
    "act_start_time_end": {
        "backend_field": "actStartTime",
        "template": "<= '{value} 23:59:59'",
    },
    "create_on_start": {
        "backend_field": "createOn",
        "template": ">= '{value}'",
    },
    "create_on_end": {
        "backend_field": "createOn",
        "template": "<= '{value} 23:59:59'",
    },
    "description": {
        "backend_field": "description",
        "template": "like '%{value}%'",
    },
    "fee_amt": {
        "backend_field": "feeAmt",
        "template": "like '%{value}%'",
    },
    "lookup_name": {
        "backend_field": "lookupName",
        "template": "like '%{value}%'",
    },
    "next_action_date_start": {
        "backend_field": "nextActionDate",
        "template": ">= '{value}'",
    },
    "next_action_date_end": {
        "backend_field": "nextActionDate",
        "template": "<= '{value} 23:59:59'",
    },
}

FIELD_LABELS = {
    "abdCustomerName": {
        "key": "abd_customer_name",
        "title": "客户名称",
    },
    "actStartTime": {
        "key": "act_start_time",
        "title": "联系日期",
    },
    "lookupName": {
        "key": "lookup_name",
        "title": "联系方式",
    },
    "abdPersonName": {
        "key": "abd_person_name",
        "title": "负责销售",
    },
    "contactName": {
        "key": "contact_name",
        "title": "联系对象",
    },
    "createOn": {
        "key": "create_on",
        "title": "创建日期",
    },
    "description": {
        "key": "description",
        "title": "联系内容",
    },
    "feeAmt": {
        "key": "fee_amt",
        "title": "费用支出",
    },
    "nextActionDate": {
        "key": "next_action_date",
        "title": "预计下次联系日期",
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
    abd_customer_name: str | None = None,
    contact_name: str | None = None,
    fast_search: str | None = None,
    sale_person: str | None = None,
    abd_person_name: str | None = None,
    act_start_time_start: str | None = None,
    act_start_time_end: str | None = None,
    create_on_start: str | None = None,
    create_on_end: str | None = None,
    description: str | None = None,
    fee_amt: str | None = None,
    lookup_name: str | None = None,
    next_action_date_start: str | None = None,
    next_action_date_end: str | None = None,
) -> str | None:
    values = {
        "abd_customer_name": abd_customer_name,
        "contact_name": contact_name,
        "fast_search": fast_search,
        "sale_person": sale_person,
        "abd_person_name": abd_person_name,
        "act_start_time_start": act_start_time_start,
        "act_start_time_end": act_start_time_end,
        "create_on_start": create_on_start,
        "create_on_end": create_on_end,
        "description": description,
        "fee_amt": fee_amt,
        "lookup_name": lookup_name,
        "next_action_date_start": next_action_date_start,
        "next_action_date_end": next_action_date_end,
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
    abd_customer_name: str | None = None,
    contact_name: str | None = None,
    fast_search: str | None = None,
    sale_person: str | None = None,
    abd_person_name: str | None = None,
    act_start_time_start: str | None = None,
    act_start_time_end: str | None = None,
    create_on_start: str | None = None,
    create_on_end: str | None = None,
    description: str | None = None,
    fee_amt: str | None = None,
    lookup_name: str | None = None,
    next_action_date_start: str | None = None,
    next_action_date_end: str | None = None,
    sVars: dict | None = None,
) -> dict[str, str]:
    merged_svars = {
        "customerType": SCOPE_TO_CUSTOMER_TYPE[scope],
    }
    if sVars is not None:
        merged_svars.update(sVars)

    params = {
        "start": str(0 if start is None else start),
        "limit": str(10 if limit is None else limit),
        "sVars": json.dumps(merged_svars, ensure_ascii=False),
    }

    filter_sql = build_filter(
        abd_customer_name=abd_customer_name,
        contact_name=contact_name,
        fast_search=fast_search,
        sale_person=sale_person,
        abd_person_name=abd_person_name,
        act_start_time_start=act_start_time_start,
        act_start_time_end=act_start_time_end,
        create_on_start=create_on_start,
        create_on_end=create_on_end,
        description=description,
        fee_amt=fee_amt,
        lookup_name=lookup_name,
        next_action_date_start=next_action_date_start,
        next_action_date_end=next_action_date_end,
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


async def query_psactivitylistaction(
    token: str,
    scope: str = "default",
    view: str | None = None,
    start: int = 0,
    limit: int = 10,
    abd_customer_name: str | None = None,
    contact_name: str | None = None,
    fast_search: str | None = None,
    sale_person: str | None = None,
    abd_person_name: str | None = None,
    act_start_time_start: str | None = None,
    act_start_time_end: str | None = None,
    create_on_start: str | None = None,
    create_on_end: str | None = None,
    description: str | None = None,
    fee_amt: str | None = None,
    lookup_name: str | None = None,
    next_action_date_start: str | None = None,
    next_action_date_end: str | None = None,
    sVars: dict | None = None,
    include_raw: bool = False,
) -> dict[str, Any]:
    """查询客户联系记录列表，按 scope 路由到默认、部门、我的视图。"""
    resolved_scope = _resolve_scope(scope=scope, view=view)
    params = build_params(
        scope=resolved_scope,
        start=start,
        limit=limit,
        abd_customer_name=abd_customer_name,
        contact_name=contact_name,
        fast_search=fast_search,
        sale_person=sale_person,
        abd_person_name=abd_person_name,
        act_start_time_start=act_start_time_start,
        act_start_time_end=act_start_time_end,
        create_on_start=create_on_start,
        create_on_end=create_on_end,
        description=description,
        fee_amt=fee_amt,
        lookup_name=lookup_name,
        next_action_date_start=next_action_date_start,
        next_action_date_end=next_action_date_end,
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
    "query_psactivitylistaction": query_psactivitylistaction,
    "query_ps_activity_list": query_psactivitylistaction,
}

TOOL_SCHEMAS = [
    {
        "name": "query_psactivitylistaction",
        "description": (
            "查询客户联系记录列表。通过 scope/view 路由到默认、部门、我的三个视图，"
            "支持核心筛选字段、候选 filter 字段以及 sVars 覆盖入口。"
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "scope": {
                    "type": "string",
                    "description": "视图范围：default=默认列表，dept=部门视图，mine=我的数据视图。",
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
                "abd_customer_name": {
                    "type": "string",
                    "description": "客户名称，模糊匹配 (q_abdCustomerName → ac.CUSTOMER_NAME_CN)。",
                },
                "contact_name": {
                    "type": "string",
                    "description": "联系对象，模糊匹配 (q_contactName → acc.CONTACT_NAME)。",
                },
                "fast_search": {
                    "type": "string",
                    "description": "视图搜索词，模糊匹配 (fastSearch → fastSearch)。",
                },
                "sale_person": {
                    "type": "string",
                    "description": "负责销售，模糊匹配 (q_salePerson → ap.PERSON_NAME)。",
                },
                "abd_person_name": {
                    "type": "string",
                    "description": "负责销售候选字段，模糊匹配 (abdPersonName → responsiblePersonId)。",
                },
                "act_start_time_start": {
                    "type": "string",
                    "description": "联系日期开始，格式 YYYY-MM-DD (actStartTime → actStartTime, >=)。",
                },
                "act_start_time_end": {
                    "type": "string",
                    "description": "联系日期结束，格式 YYYY-MM-DD (actStartTime → actStartTime, <= 23:59:59)。",
                },
                "create_on_start": {
                    "type": "string",
                    "description": "创建日期开始，格式 YYYY-MM-DD (createOn → createOn, >=)。",
                },
                "create_on_end": {
                    "type": "string",
                    "description": "创建日期结束，格式 YYYY-MM-DD (createOn → createOn, <= 23:59:59)。",
                },
                "description": {
                    "type": "string",
                    "description": "联系内容，模糊匹配 (description → description)。",
                },
                "fee_amt": {
                    "type": "string",
                    "description": "费用支出，模糊匹配 (feeAmt → feeAmt)。",
                },
                "lookup_name": {
                    "type": "string",
                    "description": "联系方式，模糊匹配 (lookupName → lookupName)。",
                },
                "next_action_date_start": {
                    "type": "string",
                    "description": "预计下次联系日期开始，格式 YYYY-MM-DD (nextActionDate → nextActionDate, >=)。",
                },
                "next_action_date_end": {
                    "type": "string",
                    "description": "预计下次联系日期结束，格式 YYYY-MM-DD (nextActionDate → nextActionDate, <= 23:59:59)。",
                },
                "sVars": {
                    "type": "object",
                    "description": "自定义 sVars 负载，会覆盖默认 customerType 或追加其他后端变量。",
                },
                "include_raw": {
                    "type": "boolean",
                    "description": "调试用。默认 false；为 true 时才返回后端原始 raw_resultList/raw_response。",
                },
            },
        },
    },
]
