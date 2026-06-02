"""MCP tools for PsOpportunityListAction queries."""
from __future__ import annotations

import json
import os
import sys
from typing import Any

import httpx

JAVA_API_BASE = os.environ.get("JAVA_API_BASE", "http://localhost:8080")

SCOPE_TO_ENDPOINT = {
    "default": "/PsOpportunityListAction/listQuery",
    "dept": "/PsOpportunityListAction/listQueryDept",
    "mine": "/PsOpportunityListAction/listQueryMy",
}

SCOPE_TO_CUSTOMER_TYPE = {
    "default": 1,
    "dept": 2,
    "mine": 3,
}

FILTER_CONFIG = {
    "fast_search": {
        "backend_field": "fastSearch",
        "template": "like '%{value}%'",
    },
    "bstatus": {
        "backend_field": "bstatus",
        "template": "= {value}",
    },
    "case_intending_amt": {
        "backend_field": "caseIntendingAmt",
        "template": "like '%{value}%'",
    },
    "contact_name": {
        "backend_field": "contactName",
        "template": "like '%{value}%'",
    },
    "content": {
        "backend_field": "content",
        "template": "like '%{value}%'",
    },
    "create_on_start": {
        "backend_field": "createOn",
        "template": ">= '{value}'",
    },
    "create_on_end": {
        "backend_field": "createOn",
        "template": "<= '{value} 23:59:59'",
    },
    "customer_name": {
        "backend_field": "customerName",
        "template": "like '%{value}%'",
    },
    "remarks": {
        "backend_field": "remarks",
        "template": "like '%{value}%'",
    },
    "response_department_name": {
        "backend_field": "responseDepartmentName",
        "template": "like '%{value}%'",
    },
    "response_person_name": {
        "backend_field": "responsePersonName",
        "template": "like '%{value}%'",
    },
    "rstatus": {
        "backend_field": "rstatus",
        "template": "= {value}",
    },
    "sample_type": {
        "backend_field": "sampleType",
        "template": "like '%{value}%'",
    },
}

FIELD_LABELS = { 
    "createOn": {
        "key": "create_on",
        "title": "创建日期",
    },  
    "responsePersonName": {
        "key": "response_person_name",
        "title": "销售",
    },
    "customerName": {
        "key": "customer_name",
        "title": "客户名称",
    },
    "contactName": {
        "key": "contact_name",
        "title": "联系人名称",
    },
    "sampleType": {
        "key": "sample_type",
        "title": "样品名称类型",
    },
    "content": {
        "key": "content",
        "title": "内容",
    },
    "caseIntendingAmt": {
        "key": "case_intending_amt",
        "title": "预计金额",
    },
    "bstatus": {
        "key": "bstatus",
        "title": "进度",
    }, 
    "responseDepartmentName": {
        "key": "response_department_name",
        "title": "销售部门",
    },
    "remarks": {
        "key": "remarks",
        "title": "备注",
    },
    "rstatus": {
        "key": "rstatus",
        "title": "状态",
    },
}

ENUM_FIELDS = {
    "bstatus": {
        1: "成功",
        2: "失败",
        3: "客户咨询中",
        4: "已出报价",
    },
    "rstatus": {
        0: "作废",
        1: "审核",
        2: "暂存",
        3: "等待重新审批",
        4: "提交",
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
            "Unsupported scope/view: {}. Allowed values: {}".format(
                resolved, ", ".join(sorted(SCOPE_TO_ENDPOINT))
            )
        )
    return resolved


def build_filter(
    *,
    fast_search: str | None = None,
    bstatus: int | None = None,
    case_intending_amt: str | None = None,
    contact_name: str | None = None,
    content: str | None = None,
    create_on_start: str | None = None,
    create_on_end: str | None = None,
    customer_name: str | None = None,
    remarks: str | None = None,
    response_department_name: str | None = None,
    response_person_name: str | None = None,
    rstatus: int | None = None,
    sample_type: str | None = None,
) -> str | None:
    values = {
        "fast_search": fast_search,
        "bstatus": bstatus,
        "case_intending_amt": case_intending_amt,
        "contact_name": contact_name,
        "content": content,
        "create_on_start": create_on_start,
        "create_on_end": create_on_end,
        "customer_name": customer_name,
        "remarks": remarks,
        "response_department_name": response_department_name,
        "response_person_name": response_person_name,
        "rstatus": rstatus,
        "sample_type": sample_type,
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
    fast_search: str | None = None,
    bstatus: int | None = None,
    case_intending_amt: str | None = None,
    contact_name: str | None = None,
    content: str | None = None,
    create_on_start: str | None = None,
    create_on_end: str | None = None,
    customer_name: str | None = None,
    remarks: str | None = None,
    response_department_name: str | None = None,
    response_person_name: str | None = None,
    rstatus: int | None = None,
    sample_type: str | None = None,
) -> dict[str, str]:
    params = {
        "start": str(0 if start is None else start),
        "limit": str(10 if limit is None else limit),
        "sVars": json.dumps(
            {"customerType": SCOPE_TO_CUSTOMER_TYPE[scope]},
            ensure_ascii=False,
        ),
    }

    filter_sql = build_filter(
        fast_search=fast_search,
        bstatus=bstatus,
        case_intending_amt=case_intending_amt,
        contact_name=contact_name,
        content=content,
        create_on_start=create_on_start,
        create_on_end=create_on_end,
        customer_name=customer_name,
        remarks=remarks,
        response_department_name=response_department_name,
        response_person_name=response_person_name,
        rstatus=rstatus,
        sample_type=sample_type,
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


async def query_sales_opportunity_list(
    token: str,
    scope: str = "default",
    view: str | None = None,
    start: int = 0,
    limit: int = 10,
    fast_search: str | None = None,
    bstatus: int | None = None,
    case_intending_amt: str | None = None,
    contact_name: str | None = None,
    content: str | None = None,
    create_on_start: str | None = None,
    create_on_end: str | None = None,
    customer_name: str | None = None,
    remarks: str | None = None,
    response_department_name: str | None = None,
    response_person_name: str | None = None,
    rstatus: int | None = None,
    sample_type: str | None = None,
    include_raw: bool = False,
) -> dict[str, Any]:
    """查询销售机会列表，按 scope 路由到全部、部门、我的视图。"""
    resolved_scope = _resolve_scope(scope=scope, view=view)
    params = build_params(
        scope=resolved_scope,
        start=start,
        limit=limit,
        fast_search=fast_search,
        bstatus=bstatus,
        case_intending_amt=case_intending_amt,
        contact_name=contact_name,
        content=content,
        create_on_start=create_on_start,
        create_on_end=create_on_end,
        customer_name=customer_name,
        remarks=remarks,
        response_department_name=response_department_name,
        response_person_name=response_person_name,
        rstatus=rstatus,
        sample_type=sample_type,
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
    "query_sales_opportunity_list": query_sales_opportunity_list,
    "query_psopportunitylistaction": query_sales_opportunity_list,
    "query_ps_opportunity_list": query_sales_opportunity_list,
}

TOOL_SCHEMAS = [
    {
        "name": "query_sales_opportunity_list",
        "description": (
            "查询销售机会列表。通过 scope/view 路由到默认、部门、我的三个视图，"
            "支持 fast_search 与文档 4.1 中列出的候选 filter 字段。"
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "scope": {
                    "type": "string",
                    "description": "视图范围：default=默认列表，dept=部门视图，mine=我的视图。",
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
                "fast_search": {
                    "type": "string",
                    "description": "视图搜索词，模糊匹配 (fastSearch → fastSearch)。",
                },
                "bstatus": {
                    "type": "integer",
                    "description": "进度，精确匹配 (bstatus → bstatus): 1=成功, 2=失败, 3=客户咨询中, 4=已出报价。",
                },
                "case_intending_amt": {
                    "type": "string",
                    "description": "预计金额，模糊匹配 (caseIntendingAmt → caseIntendingAmt)。",
                },
                "contact_name": {
                    "type": "string",
                    "description": "联系人名称，模糊匹配 (contactName → contactName)。",
                },
                "content": {
                    "type": "string",
                    "description": "内容，模糊匹配 (content → content)。",
                },
                "create_on_start": {
                    "type": "string",
                    "description": "创建日期开始，格式 YYYY-MM-DD (createOn → createOn, >=)。",
                },
                "create_on_end": {
                    "type": "string",
                    "description": "创建日期结束，格式 YYYY-MM-DD (createOn → createOn, <= 23:59:59)。",
                },
                "customer_name": {
                    "type": "string",
                    "description": "客户名称，模糊匹配 (customerName → customerName)。",
                },
                "remarks": {
                    "type": "string",
                    "description": "备注，模糊匹配 (remarks → remarks)。",
                },
                "response_department_name": {
                    "type": "string",
                    "description": "销售部门，模糊匹配 (responseDepartmentName → responseDepartmentId)。",
                },
                "response_person_name": {
                    "type": "string",
                    "description": "销售，模糊匹配 (responsePersonName → responsePersonId)。",
                },
                "rstatus": {
                    "type": "integer",
                    "description": "状态，精确匹配 (rstatus → rstatus): 0=作废, 1=审核, 2=暂存, 3=等待重新审批, 4=提交。",
                },
                "sample_type": {
                    "type": "string",
                    "description": "样品名称类型，模糊匹配 (sampleType → sampleType)。",
                },
                "include_raw": {
                    "type": "boolean",
                    "description": "调试用。默认 false；为 true 时才返回后端原始 raw_resultList/raw_response。",
                },
            },
        },
    },
]
