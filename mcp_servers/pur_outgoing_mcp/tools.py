"""MCP tools for PurOutgoingRequestFormListAction queries."""
from __future__ import annotations

import json
import os
import sys
from typing import Any, Dict, List, Optional

import httpx

JAVA_API_BASE = os.environ.get("JAVA_API_BASE", "http://localhost:8080")

SCOPE_TO_ENDPOINT = {
    "default": "/PurOutgoingRequestFormListAction/listQuery",
    "mine": "/PurOutgoingRequestFormListAction/listQuery",
}

SCOPE_DEFAULT_SVARS = {
    "default": {"operation": "operation"},
    "mine": {"operation": "My"},
}

FILTER_CONFIG = {
    "fast_search": {"backend_field": "fastSearch", "template": "like '%{value}%'"},
    "applt_person_name": {"backend_field": "appltPersonName", "template": "like '%{value}%'"},
    "bstatus": {"backend_field": "bstatus", "template": "= '{value}'"},
    "consignor_name_cn": {"backend_field": "consignorNameCn", "template": "like '%{value}%'"},
    "order_date_end": {"backend_field": "orderDate", "template": "<= '{value} 23:59:59'"},
    "order_date_start": {"backend_field": "orderDate", "template": ">= '{value}'"},
    "order_no": {"backend_field": "orderNo", "template": "like '%{value}%'"},
    "purchase_desc": {"backend_field": "subcontractItems", "template": "like '%{value}%'"},
    "rstatus": {"backend_field": "rstatus", "template": "= '{value}'"},
    "saler_name": {"backend_field": "salerName", "template": "like '%{value}%'"},
    "txn_core_no": {"backend_field": "sourceBizNo", "template": "like '%{value}%'"},
}

FIELD_LABELS = {
    "rstatus": {
        "key": "rstatus",
        "title": "审核状态",
    },
    "bstatus": {
        "key": "bstatus",
        "title": "是否已转分包申请",
    },
    "orderNo": {
        "key": "order_no",
        "title": "申请单编号",
    },
    "orderDate": {
        "key": "order_date",
        "title": "申请日期",
    },
    "salerName": {
        "key": "saler_name",
        "title": "负责业务员",
    },
    "appltPersonName": {
        "key": "applt_person_name",
        "title": "申请人",
    },
    "purchaseDesc": {
        "key": "purchase_desc",
        "title": "申请分包项目",
    },
    "txnCoreNo": {
        "key": "txn_core_no",
        "title": "单源号",
    },
    "consignorNameCn": {
        "key": "consignor_name_cn",
        "title": "合同方",
    },
}

ENUM_FIELDS = {
    "bstatus": {
        1: "已转",
        2: "未转",
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


def _resolve_scope(scope: Optional[str] = None, view: Optional[str] = None) -> str:
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
    fast_search: Optional[str] = None,
    applt_person_name: Optional[str] = None,
    bstatus: Optional[str] = None,
    consignor_name_cn: Optional[str] = None,
    order_date_end: Optional[str] = None,
    order_date_start: Optional[str] = None,
    order_no: Optional[str] = None,
    purchase_desc: Optional[str] = None,
    rstatus: Optional[str] = None,
    saler_name: Optional[str] = None,
    txn_core_no: Optional[str] = None,
) -> Optional[str]:
    values = {
        "fast_search": fast_search,
        "applt_person_name": applt_person_name,
        "bstatus": bstatus,
        "consignor_name_cn": consignor_name_cn,
        "order_date_end": order_date_end,
        "order_date_start": order_date_start,
        "order_no": order_no,
        "purchase_desc": purchase_desc,
        "rstatus": rstatus,
        "saler_name": saler_name,
        "txn_core_no": txn_core_no,
    }

    conditions = []
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


def _resolve_svars(scope: str, user_svars: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    defaults = SCOPE_DEFAULT_SVARS.get(scope, {})
    if not defaults and not user_svars:
        return None
    merged = dict(defaults)
    if user_svars:
        merged.update(user_svars)
    return merged


def build_params(
    *,
    scope: str,
    start: int = 0,
    limit: int = 10,
    fast_search: Optional[str] = None,
    applt_person_name: Optional[str] = None,
    bstatus: Optional[str] = None,
    consignor_name_cn: Optional[str] = None,
    order_date_end: Optional[str] = None,
    order_date_start: Optional[str] = None,
    order_no: Optional[str] = None,
    purchase_desc: Optional[str] = None,
    rstatus: Optional[str] = None,
    saler_name: Optional[str] = None,
    txn_core_no: Optional[str] = None,
    sVars: Optional[Dict[str, Any]] = None,
) -> Dict[str, str]:
    params = {
        "start": str(0 if start is None else start),
        "limit": str(10 if limit is None else limit),
    }

    resolved_sVars = _resolve_svars(scope, sVars)
    if resolved_sVars is not None:
        params["sVars"] = json.dumps(resolved_sVars, ensure_ascii=False)

    filter_sql = build_filter(
        fast_search=fast_search,
        applt_person_name=applt_person_name,
        bstatus=bstatus,
        consignor_name_cn=consignor_name_cn,
        order_date_end=order_date_end,
        order_date_start=order_date_start,
        order_no=order_no,
        purchase_desc=purchase_desc,
        rstatus=rstatus,
        saler_name=saler_name,
        txn_core_no=txn_core_no,
    )
    if filter_sql:
        params["filter"] = filter_sql

    return params


def _build_columns() -> List[Dict[str, str]]:
    return [
        {"field": field, "key": meta["key"], "title": meta["title"]}
        for field, meta in FIELD_LABELS.items()
    ]


def _enum_text(key: str, value: Any) -> Optional[str]:
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


def _normalize_row(row: Dict[str, Any]) -> Dict[str, Any]:
    normalized = {}
    for field, meta in FIELD_LABELS.items():
        key = meta["key"]
        value = row.get(field)
        normalized[key] = value
        text = _enum_text(key, value)
        if text is not None:
            normalized["{}_text".format(key)] = text
    return normalized


def _extract_result_list(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    nested_data = payload.get("data")
    if isinstance(nested_data, dict):
        nested_result_list = nested_data.get("resultList")
        if isinstance(nested_result_list, list):
            return nested_result_list

    top_level_result_list = payload.get("resultList")
    if isinstance(top_level_result_list, list):
        return top_level_result_list

    return []


def _extract_count(payload: Dict[str, Any], fallback_count: int) -> int:
    nested_data = payload.get("data")
    if isinstance(nested_data, dict) and isinstance(nested_data.get("count"), int):
        return nested_data["count"]
    if isinstance(payload.get("count"), int):
        return payload["count"]
    return fallback_count


async def query_puroutgoingrequestformlistaction(
    token: str,
    scope: str = "default",
    view: Optional[str] = None,
    start: int = 0,
    limit: int = 10,
    fast_search: Optional[str] = None,
    applt_person_name: Optional[str] = None,
    bstatus: Optional[str] = None,
    consignor_name_cn: Optional[str] = None,
    order_date_end: Optional[str] = None,
    order_date_start: Optional[str] = None,
    order_no: Optional[str] = None,
    purchase_desc: Optional[str] = None,
    rstatus: Optional[str] = None,
    saler_name: Optional[str] = None,
    txn_core_no: Optional[str] = None,
    sVars: Optional[Dict[str, Any]] = None,
    include_raw: bool = False,
) -> Dict[str, Any]:
    """查询外发/分包申请单列表，通过 scope 路由到 PurOutgoingRequestFormListAction/listQuery。"""
    resolved_scope = _resolve_scope(scope=scope, view=view)
    params = build_params(
        scope=resolved_scope,
        start=start,
        limit=limit,
        fast_search=fast_search,
        applt_person_name=applt_person_name,
        bstatus=bstatus,
        consignor_name_cn=consignor_name_cn,
        order_date_end=order_date_end,
        order_date_start=order_date_start,
        order_no=order_no,
        purchase_desc=purchase_desc,
        rstatus=rstatus,
        saler_name=saler_name,
        txn_core_no=txn_core_no,
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
        result = {
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
    "query_puroutgoingrequestformlistaction": query_puroutgoingrequestformlistaction,
}

TOOL_SCHEMAS = [
    {
        "name": "query_puroutgoingrequestformlistaction",
            "description": (
                "查询外发/分包申请单列表。通过 scope 路由到默认列表（继承自 ListBaseAction 的"
                " /PurOutgoingRequestFormListAction/listQuery）。"
                "default 视图自动注入 operation=operation 的 sVar；"
                "mine 视图自动注入 operation=My 的 sVar。"
                "本工具不会根据未在文档第 7 节出现的 dataType 来源注入默认 dataType。"
            ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "scope": {
                    "type": "string",
                    "description": (
                        "视图范围：default=默认列表（继承自 ListBaseAction，自动注入 operation=operation），"
                        "mine=我的外发申请单（自动注入 operation=My）。"
                    ),
                },
                "view": {"type": "string", "description": "scope 的别名；如同时传入，以 scope 为准。"},
                "start": {"type": "integer", "description": "分页起始位置，默认 0。"},
                "limit": {"type": "integer", "description": "分页条数，默认 10。"},
                "fast_search": {"type": "string", "description": "fastSearch，模糊匹配 (fastSearch → fastSearch)。"},
                "applt_person_name": {"type": "string", "description": "申请人，模糊匹配（filter 候选字段）(appltPersonName → appltPersonName)。"},
                "bstatus": {
                    "type": "integer",
                    "description": "是否已转分包申请 (bstatus → bstatus): 1=已转, 2=未转。",
                },
                "consignor_name_cn": {"type": "string", "description": "合同方，模糊匹配（filter 候选字段）(consignorNameCn → consignorNameCn)。"},
                "order_date_end": {"type": "string", "description": "申请日期结束（filter 候选字段）(orderDate <= value)。"},
                "order_date_start": {"type": "string", "description": "申请日期开始（filter 候选字段）(orderDate >= value)。"},
                "order_no": {"type": "string", "description": "申请单编号，模糊匹配（filter 候选字段）(orderNo → orderNo)。"},
                "purchase_desc": {"type": "string", "description": "申请分包项目，模糊匹配（filter 候选字段）(purchaseDesc → subcontractItems)。"},
                "rstatus": {
                    "type": "integer",
                    "description": "审核状态 (rstatus → rstatus): 0=已作废, 1=已审核, 2=暂存, 3=等待重新审批, 4=审批中。",
                },
                "saler_name": {"type": "string", "description": "负责业务员，模糊匹配（filter 候选字段）(salerName → salerName)。"},
                "txn_core_no": {"type": "string", "description": "单源号，模糊匹配（filter 候选字段）(txnCoreNo → sourceBizNo)。"},
                "sVars": {
                    "type": "object",
                    "description": (
                        "自定义 sVars 负载。default scope 自动注入 operation=operation。"
                        "用户传入的 sVars 会覆盖 scope 默认值。"
                        "本工具不会根据未在文档第 7 节出现的 dataType 来源注入默认 dataType。"
                    ),
                },
                "include_raw": {
                    "type": "boolean",
                    "description": "调试用。默认 false；为 true 时才返回后端原始 raw_resultList/raw_response。",
                },
            },
        },
    },
]
