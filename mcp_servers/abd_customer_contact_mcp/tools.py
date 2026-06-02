"""MCP tools for AbdCustomerContactListAction customer contact list queries."""
from __future__ import annotations

import json
import os
import sys
from typing import Any

import httpx

JAVA_API_BASE = os.environ.get("JAVA_API_BASE", "http://localhost:8080")

SCOPE_TO_ENDPOINT = {
    "default": "/AbdCustomerContactListAction/listQuery",
    "dept": "/AbdCustomerContactListAction/listQueryDept",
    "mine": "/AbdCustomerContactListAction/listQueryMy",
}

SCOPE_DEFAULT_SVARS: dict[str, dict[str, str]] = {
    "default": {"customerType": "1"},
}

FILTER_CONFIG: dict[str, dict[str, str]] = {
    # ── 核心筛选（第 4 节） ──
    "contact_name": {"backend_field": "acc.CONTACT_NAME", "template": "like '%{value}%'"},
    "customer_name": {"backend_field": "ac.CUSTOMER_NAME_CN", "template": "like '%{value}%'"},
    "fast_search": {"backend_field": "fastSearch", "template": "like '%{value}%'"},
    "rstatus": {"backend_field": "acc.RSTATUS", "template": "= {value}"},
    # ── 候选 filter（第 4.1 节） ──
    "adress1": {"backend_field": "adress1", "template": "like '%{value}%'"},
    "adress2": {"backend_field": "adress2", "template": "like '%{value}%'"},
    "contact_name_en": {"backend_field": "contactNameEn", "template": "like '%{value}%'"},
    "customer_name_cn": {"backend_field": "customerNameCn", "template": "like '%{value}%'"},
    "email": {"backend_field": "email", "template": "like '%{value}%'"},
    "home_telephone": {"backend_field": "homeTelephone", "template": "like '%{value}%'"},
    "mobile_telephone": {"backend_field": "mobileTelephone", "template": "like '%{value}%'"},
    "title": {"backend_field": "title", "template": "like '%{value}%'"},
    "work_telephone": {"backend_field": "workTelephone", "template": "like '%{value}%'"},
}

FIELD_LABELS: dict[str, dict[str, str]] = {
    "rstatus": {"key": "rstatus", "title": "状态"},
    "customerNameCn": {"key": "customer_name_cn", "title": "客户"},
    "contactName": {"key": "contact_name", "title": "名称（中）"},
    "contactNameEn": {"key": "contact_name_en", "title": "名称（英）"},
    "title": {"key": "title", "title": "职位"},
    "email": {"key": "email", "title": "电子邮箱"},
    "mobileTelephone": {"key": "mobile_telephone", "title": "移动电话"},
    "workTelephone": {"key": "work_telephone", "title": "办公电话"},
    "homeTelephone": {"key": "home_telephone", "title": "家庭电话"},
    "adress1": {"key": "adress1", "title": "地址1"},
    "adress2": {"key": "adress2", "title": "地址2"},
    "mainContact": {"key": "main_contact", "title": "主要联系人"},
}

ENUM_FIELDS = {
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


def _resolve_svars(scope: str, sVars: dict[str, Any] | None = None) -> dict[str, Any] | None:
    defaults = SCOPE_DEFAULT_SVARS.get(scope, {})
    if not defaults and not sVars:
        return None
    merged = dict(defaults)
    if sVars:
        merged.update(sVars)
    return merged


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
    scope: str,
    start: int = 0,
    limit: int = 10,
    sVars: dict[str, Any] | None = None,
    **filter_values: Any,
) -> dict[str, str]:
    params = {
        "start": str(0 if start is None else start),
        "limit": str(10 if limit is None else limit),
    }

    resolved_svars = _resolve_svars(scope, sVars)
    if resolved_svars is not None:
        params["sVars"] = json.dumps(resolved_svars, ensure_ascii=False)

    filter_sql = build_filter(
        contact_name=filter_values.get("contact_name"),
        customer_name=filter_values.get("customer_name"),
        fast_search=filter_values.get("fast_search"),
        rstatus=filter_values.get("rstatus"),
        adress1=filter_values.get("adress1"),
        adress2=filter_values.get("adress2"),
        contact_name_en=filter_values.get("contact_name_en"),
        customer_name_cn=filter_values.get("customer_name_cn"),
        email=filter_values.get("email"),
        home_telephone=filter_values.get("home_telephone"),
        mobile_telephone=filter_values.get("mobile_telephone"),
        title=filter_values.get("title"),
        work_telephone=filter_values.get("work_telephone"),
    )
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


async def query_customer_contact_list(
    token: str,
    scope: str = "default",
    view: str | None = None,
    start: int = 0,
    limit: int = 10,
    # ── 核心筛选（第 4 节） ──
    contact_name: str | None = None,
    customer_name: str | None = None,
    fast_search: str | None = None,
    rstatus: int | None = None,
    # ── 候选 filter（第 4.1 节） ──
    adress1: str | None = None,
    adress2: str | None = None,
    contact_name_en: str | None = None,
    customer_name_cn: str | None = None,
    email: str | None = None,
    home_telephone: str | None = None,
    mobile_telephone: str | None = None,
    title: str | None = None,
    work_telephone: str | None = None,
    sVars: dict[str, Any] | None = None,
    include_raw: bool = False,
) -> dict[str, Any]:
    """查询客户联系人列表，按 scope 路由到默认、部门、我的视图。"""
    resolved_scope = _resolve_scope(scope=scope, view=view)
    params = build_params(
        scope=resolved_scope,
        start=start,
        limit=limit,
        contact_name=contact_name,
        customer_name=customer_name,
        fast_search=fast_search,
        rstatus=rstatus,
        adress1=adress1,
        adress2=adress2,
        contact_name_en=contact_name_en,
        customer_name_cn=customer_name_cn,
        email=email,
        home_telephone=home_telephone,
        mobile_telephone=mobile_telephone,
        title=title,
        work_telephone=work_telephone,
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
    "query_customer_contact_list": query_customer_contact_list,
}

_PROPERTIES: dict[str, dict[str, Any]] = {
    "scope": {
        "type": "string",
        "description": (
            "视图范围: default=默认列表（自动注入 customerType=1），"
            "dept=部门视图，mine=我的数据视图。"
            "default 包含继承的 /AbdCustomerContactListAction/listQuery。"
        ),
    },
    "view": {"type": "string", "description": "scope 的别名；如同时传入，以 scope 为准。"},
    "start": {"type": "integer", "description": "分页起始位置，默认 0。"},
    "limit": {"type": "integer", "description": "分页条数，默认 10。"},
    # ── 核心筛选（第 4 节） ──
    "contact_name": {"type": "string", "description": "联系人名称，模糊匹配 (q_contactName → acc.CONTACT_NAME)。"},
    "customer_name": {"type": "string", "description": "客户名称，模糊匹配 (q_customerName → ac.CUSTOMER_NAME_CN)。"},
    "fast_search": {"type": "string", "description": "视图，模糊匹配 (fastSearch → fastSearch)。"},
    "rstatus": {
        "type": "integer",
        "description": "状态 (q_rstatus → acc.RSTATUS): 0=已作废, 1=已审核, 2=暂存, 3=等待重新审批, 4=审批中。",
    },
    # ── 候选 filter（第 4.1 节） ──
    "adress1": {"type": "string", "description": "地址1，候选 filter，模糊匹配。"},
    "adress2": {"type": "string", "description": "地址2，候选 filter，模糊匹配。"},
    "contact_name_en": {"type": "string", "description": "名称（英），候选 filter，模糊匹配。"},
    "customer_name_cn": {"type": "string", "description": "客户，候选 filter，模糊匹配。"},
    "email": {"type": "string", "description": "电子邮箱，候选 filter，模糊匹配。"},
    "home_telephone": {"type": "string", "description": "家庭电话，候选 filter，模糊匹配。"},
    "mobile_telephone": {"type": "string", "description": "移动电话，候选 filter，模糊匹配。"},
    "title": {"type": "string", "description": "职位，候选 filter，模糊匹配。"},
    "work_telephone": {"type": "string", "description": "办公电话，候选 filter，模糊匹配。"},
    "sVars": {
        "type": "object",
        "description": (
            "自定义 sVars 负载。default scope 自动注入 customerType=1。"
            "用户传入的 sVars 会覆盖 scope 默认值。"
        ),
    },
    "include_raw": {
        "type": "boolean",
        "description": "调试用。默认 false；为 true 时才返回后端原始 raw_resultList/raw_response。",
    },
}

TOOL_SCHEMAS = [
    {
        "name": "query_customer_contact_list",
        "description": (
            "查询客户联系人列表，按 scope 路由到默认、部门、我的视图。"
            "default 包含继承的 /AbdCustomerContactListAction/listQuery。"
            "返回 count、columns、data/normalized_data。"
        ),
        "inputSchema": {"type": "object", "properties": _PROPERTIES},
    }
]
