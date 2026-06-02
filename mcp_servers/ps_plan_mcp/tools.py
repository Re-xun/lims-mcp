"""MCP tools for PsPlanListAction queries."""
from __future__ import annotations

import json
import os
import sys
from typing import Any

import httpx

JAVA_API_BASE = os.environ.get("JAVA_API_BASE", "http://localhost:8080")

SCOPE_TO_ENDPOINT = {
    "default": "/PsPlanListAction/listQuery",
    "dept": "/PsPlanListAction/listQueryDept",
    "mine": "/PsPlanListAction/listQueryMy",
    "my_week": "/PsPlanListAction/listQueryMyWeek",
}

SCOPE_TO_CUSTOMER_TYPE = {
    "default": 1,
    "dept": 2,
    "mine": 3,
    "my_week": 3,
}

SCOPE_TO_DATA_TYPE = {
    "default": "listView",
    "dept": "LIST_SALES_DEP_ID_VIEW",
    "mine": "LIST_CREAT_MY_VIEW",
    "my_week": "LIST_CREAT_MY_VIEW_WEEK",
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
    "contact_obj_name": {
        "backend_field": "contactObjName",
        "template": "like '%{value}%'",
    },
    "customer_obj_name": {
        "backend_field": "customerObjName",
        "template": "like '%{value}%'",
    },
    "description": {
        "backend_field": "description",
        "template": "like '%{value}%'",
    },
    "lookup_name": {
        "backend_field": "lookupName",
        "template": "like '%{value}%'",
    },
    "plan_start_time_start": {
        "backend_field": "planStartTime",
        "template": ">= '{value}'",
    },
    "plan_start_time_end": {
        "backend_field": "planStartTime",
        "template": "<= '{value} 23:59:59'",
    },
    "remark": {
        "backend_field": "remark",
        "template": "like '%{value}%'",
    },
    "sales_dep_obj_name": {
        "backend_field": "salesDepObjName",
        "template": "like '%{value}%'",
    },
    "sales_person_obj_name": {
        "backend_field": "salesPersonObjName",
        "template": "like '%{value}%'",
    },
}

FIELD_LABELS = {
    "planStartTime": {
        "key": "plan_start_time",
        "title": "计划联系日期",
    },    
    "salesPersonObjName": {
        "key": "sales_person_obj_name",
        "title": "销售",
    },
    "lookupName": {
        "key": "lookup_name",
        "title": "联系方式",
    },
    "contactObjName": {
        "key": "contact_obj_name",
        "title": "联系对象",
    },
    "customerObjName": {
        "key": "customer_obj_name",
        "title": "公司名称",
    },
    "description": {
        "key": "description",
        "title": "计划联系内容",
    },
    "bstatus": {
        "key": "bstatus",
        "title": "完成情况",
    },
    "salesDepObjName": {
        "key": "sales_dep_obj_name",
        "title": "销售部门",
    },
    "remark": {
        "key": "remark",
        "title": "备注",
    },
    

}

ENUM_FIELDS = {
    "bstatus": {
        1: "计划中",
        2: "已联系",
        3: "未联系",
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
    contact_obj_name: str | None = None,
    customer_obj_name: str | None = None,
    description: str | None = None,
    lookup_name: str | None = None,
    plan_start_time_start: str | None = None,
    plan_start_time_end: str | None = None,
    remark: str | None = None,
    sales_dep_obj_name: str | None = None,
    sales_person_obj_name: str | None = None,
) -> str | None:
    values = {
        "fast_search": fast_search,
        "bstatus": bstatus,
        "contact_obj_name": contact_obj_name,
        "customer_obj_name": customer_obj_name,
        "description": description,
        "lookup_name": lookup_name,
        "plan_start_time_start": plan_start_time_start,
        "plan_start_time_end": plan_start_time_end,
        "remark": remark,
        "sales_dep_obj_name": sales_dep_obj_name,
        "sales_person_obj_name": sales_person_obj_name,
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
    contact_obj_name: str | None = None,
    customer_obj_name: str | None = None,
    description: str | None = None,
    lookup_name: str | None = None,
    plan_start_time_start: str | None = None,
    plan_start_time_end: str | None = None,
    remark: str | None = None,
    sales_dep_obj_name: str | None = None,
    sales_person_obj_name: str | None = None,
    sVars: dict | None = None,
) -> dict[str, str]:
    merged_svars = {
        "customerType": SCOPE_TO_CUSTOMER_TYPE[scope],
        "dataType": SCOPE_TO_DATA_TYPE[scope],
    }
    if sVars is not None:
        merged_svars.update(sVars)
    svar_str = json.dumps(merged_svars, ensure_ascii=False)
    params = {
        "start": str(0 if start is None else start),
        "limit": str(10 if limit is None else limit),
        "sVars": svar_str,
    }

    filter_sql = build_filter(
        fast_search=fast_search,
        bstatus=bstatus,
        contact_obj_name=contact_obj_name,
        customer_obj_name=customer_obj_name,
        description=description,
        lookup_name=lookup_name,
        plan_start_time_start=plan_start_time_start,
        plan_start_time_end=plan_start_time_end,
        remark=remark,
        sales_dep_obj_name=sales_dep_obj_name,
        sales_person_obj_name=sales_person_obj_name,
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


async def query_contact_plan_list(
    token: str,
    scope: str = "default",
    view: str | None = None,
    start: int = 0,
    limit: int = 10,
    fast_search: str | None = None,
    bstatus: int | None = None,
    contact_obj_name: str | None = None,
    customer_obj_name: str | None = None,
    description: str | None = None,
    lookup_name: str | None = None,
    plan_start_time_start: str | None = None,
    plan_start_time_end: str | None = None,
    remark: str | None = None,
    sales_dep_obj_name: str | None = None,
    sales_person_obj_name: str | None = None,
    sVars: dict | None = None,
    include_raw: bool = False,
) -> dict[str, Any]:
    """查询客户联系计划列表，按 scope 路由到默认、部门、我的、本周视图。"""
    resolved_scope = _resolve_scope(scope=scope, view=view)
    params = build_params(
        scope=resolved_scope,
        start=start,
        limit=limit,
        fast_search=fast_search,
        bstatus=bstatus,
        contact_obj_name=contact_obj_name,
        customer_obj_name=customer_obj_name,
        description=description,
        lookup_name=lookup_name,
        plan_start_time_start=plan_start_time_start,
        plan_start_time_end=plan_start_time_end,
        remark=remark,
        sales_dep_obj_name=sales_dep_obj_name,
        sales_person_obj_name=sales_person_obj_name,
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
    "query_contact_plan_list": query_contact_plan_list,
}

TOOL_SCHEMAS = [
    {
        "name": "query_contact_plan_list",
        "description": (
            "查询客户联系计划列表。通过 scope/view 路由到默认、部门、我的、本周四种视图，"
            "支持 fast_search 以及文档中建议暴露的候选 filter 字段。"
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "scope": {
                    "type": "string",
                    "description": "视图范围：default=默认列表，dept=部门视图，mine=我的视图，my_week=我的本周视图。",
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
                    "description": "视图搜索词，模糊匹配 (fastSearch -> fastSearch)。",
                },
                "bstatus": {
                    "type": "integer",
                    "description": "完成情况，精确匹配 (bstatus -> bstatus): 1=计划中, 2=已联系, 3=未联系。",
                },
                "contact_obj_name": {
                    "type": "string",
                    "description": "联系对象，模糊匹配 (contactObjName -> contactId)。",
                },
                "customer_obj_name": {
                    "type": "string",
                    "description": "公司名称，模糊匹配 (customerObjName -> customerId)。",
                },
                "description": {
                    "type": "string",
                    "description": "计划联系内容，模糊匹配 (description -> description)。",
                },
                "lookup_name": {
                    "type": "string",
                    "description": "联系方式，模糊匹配 (lookupName -> contactType)。",
                },
                "plan_start_time_start": {
                    "type": "string",
                    "description": "计划联系日期开始，格式 YYYY-MM-DD (planStartTime -> planStartTime, >=)。",
                },
                "plan_start_time_end": {
                    "type": "string",
                    "description": "计划联系日期结束，格式 YYYY-MM-DD (planStartTime -> planStartTime, <= 23:59:59)。",
                },
                "remark": {
                    "type": "string",
                    "description": "备注，模糊匹配 (remark -> remark)。",
                },
                "sales_dep_obj_name": {
                    "type": "string",
                    "description": "销售部门，模糊匹配 (salesDepObjName -> salesDepId)。",
                },
                "sales_person_obj_name": {
                    "type": "string",
                    "description": "销售，模糊匹配 (salesPersonObjName -> salesPersonId)。",
                },
                "sVars": {
                    "type": "object",
                    "description": "自定义 sVars 负载，会覆盖默认的 customerType。例如: {\"operationCode\":\"''PSPLANDEPS-NEW','PSPLANDEPS-MODIFY','PSPLANDEPS-VIEW','PSPLANDEPS-DELETE''\",\"customerType\":1}",
                },
                "include_raw": {
                    "type": "boolean",
                    "description": "调试用。默认 false；为 true 时才返回后端原始 raw_resultList/raw_response。",
                },
            },
        },
    },
]
