"""MCP tools for PurRequestListAction queries."""
from __future__ import annotations

import json
import os
import sys
from typing import Any, Dict, List, Optional

import httpx

JAVA_API_BASE = os.environ.get("JAVA_API_BASE", "http://localhost:8080")

SCOPE_TO_ENDPOINT = {
    "default": "/PurRequestListAction/listQuery",
    "dept": "/PurRequestListAction/listQuery",
    "home": "/PurRequestListAction/listQueryHome",
    "subcontract": "/PurRequestListAction/listQuerySubcontract",
    "subcontract_report": "/PurRequestListAction/listQuerySubcontractReport",
}

SCOPE_DEFAULT_SVARS = {
    "default": {"show_all": "1"},
    "dept": {"show_dept": "1"},
}

FILTER_CONFIG = {
    "asset_type": {"backend_field": "pr.asset_type", "template": "= '{value}'"},
    "bstatus": {"backend_field": "pr.bstatus", "template": "= '{value}'"},
    "department_id": {"backend_field": "pr.department_id", "template": "= '{value}'"},
    "end_date": {"backend_field": "endDate", "template": "<= '{value} 23:59:59'"},
    "fast_search": {"backend_field": "fastSearch", "template": "like '%{value}%'"},
    "manager_category": {"backend_field": "managerCategory", "template": "= '{value}'"},
    "order_no": {"backend_field": "pr.order_no", "template": "like '%{value}%'"},
    "purchase_category": {"backend_field": "pr.purchase_category", "template": "= '{value}'"},
    "purchase_desc": {"backend_field": "pr.purchase_desc", "template": "like '%{value}%'"},
    "recorder_id": {"backend_field": "ap.person_name", "template": "like '%{value}%'"},
    "source_biz_no": {"backend_field": "pr.TXN_CORE_NO", "template": "like '%{value}%'"},
    "start_date": {"backend_field": "startDate", "template": ">= '{value}'"},
    "statistical_date": {"backend_field": "statisticalDate", "template": "= '{value}'"},
    "subcontract_items": {"backend_field": "pr.purchase_desc", "template": "like '%{value}%'"},
    "supplier_name": {"backend_field": "prs.supplier_name", "template": "like '%{value}%'"},
}

FIELD_LABELS = {
    "orderNo": {"key": "order_no", "title": "申请编号"},
    "choseSupplierName": {"key": "chose_supplier_name", "title": "拟采购供应商"},
    "managerCategory": {"key": "manager_category", "title": "管理类别"},
    "orderDate": {"key": "order_date", "title": "申请日期"},
    "cooperationCount": {"key": "cooperation_count", "title": "合作次数"},
    "purchaseNo": {"key": "purchase_no", "title": "采购记录编号"},
    "rstatus": {"key": "rstatus", "title": "申请状态"},
    "cooperationAmtLocal": {"key": "cooperation_amt_local", "title": "合作金额"},
    "personName": {"key": "person_name", "title": "申请人"},
    "thisYearCooperationAmtLocal": {"key": "this_year_cooperation_amt_local", "title": "本年合作金额"},
    "salerName": {"key": "saler_name", "title": "负责业务"},
    "departmentName": {"key": "department_name", "title": "申请部门"},
    "lastYearCooperationAmtLocal": {"key": "last_year_cooperation_amt_local", "title": "去年合作金额"},
    "purchaseCategory": {"key": "purchase_category", "title": "采购类别"},
    "purchaseDesc": {"key": "purchase_desc", "title": "采购内容"},
    "beforeLastYearCooperationAmtLocal": {"key": "before_last_year_cooperation_amt_local", "title": "前年合作金额"},
    "assetType": {"key": "asset_type", "title": "资产类型"},
    "amtLocal": {"key": "amt_local", "title": "人民币预计分包费用"},
    "txnCoreNo": {"key": "txn_core_no", "title": "来源号"},
    "consignorNameCn": {"key": "consignor_name_cn", "title": "合同方"},
    "choseSupplierAmt": {"key": "chose_supplier_amt", "title": "未税金额"},
    "choseSupplierAmtWithTax": {"key": "chose_supplier_amt_with_tax", "title": "含税金额"},
    "remark": {"key": "remark", "title": "备注"},
}

ENUM_FIELDS = {
    "manager_category": {1: "一类采购", 2: "二类采购"},
    "rstatus": {0: "已作废", 1: "已审核", 2: "暂存", 3: "等待重新审批", 4: "审批中"},
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
    asset_type: Optional[str] = None,
    bstatus: Optional[str] = None,
    department_id: Optional[str] = None,
    end_date: Optional[str] = None,
    fast_search: Optional[str] = None,
    manager_category: Optional[str] = None,
    order_no: Optional[str] = None,
    purchase_category: Optional[str] = None,
    purchase_desc: Optional[str] = None,
    recorder_id: Optional[str] = None,
    source_biz_no: Optional[str] = None,
    start_date: Optional[str] = None,
    statistical_date: Optional[str] = None,
    subcontract_items: Optional[str] = None,
    supplier_name: Optional[str] = None,
) -> Optional[str]:
    values = {
        "asset_type": asset_type,
        "bstatus": bstatus,
        "department_id": department_id,
        "end_date": end_date,
        "fast_search": fast_search,
        "manager_category": manager_category,
        "order_no": order_no,
        "purchase_category": purchase_category,
        "purchase_desc": purchase_desc,
        "recorder_id": recorder_id,
        "source_biz_no": source_biz_no,
        "start_date": start_date,
        "statistical_date": statistical_date,
        "subcontract_items": subcontract_items,
        "supplier_name": supplier_name,
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
    """Merge scope defaults with user-provided sVars (user wins)."""
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
    asset_type: Optional[str] = None,
    bstatus: Optional[str] = None,
    department_id: Optional[str] = None,
    end_date: Optional[str] = None,
    fast_search: Optional[str] = None,
    manager_category: Optional[str] = None,
    order_no: Optional[str] = None,
    purchase_category: Optional[str] = None,
    purchase_desc: Optional[str] = None,
    recorder_id: Optional[str] = None,
    source_biz_no: Optional[str] = None,
    start_date: Optional[str] = None,
    statistical_date: Optional[str] = None,
    subcontract_items: Optional[str] = None,
    supplier_name: Optional[str] = None,
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
        asset_type=asset_type,
        bstatus=bstatus,
        department_id=department_id,
        end_date=end_date,
        fast_search=fast_search,
        manager_category=manager_category,
        order_no=order_no,
        purchase_category=purchase_category,
        purchase_desc=purchase_desc,
        recorder_id=recorder_id,
        source_biz_no=source_biz_no,
        start_date=start_date,
        statistical_date=statistical_date,
        subcontract_items=subcontract_items,
        supplier_name=supplier_name,
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


async def query_purrequestlistaction(
    token: str,
    scope: str = "default",
    view: Optional[str] = None,
    start: int = 0,
    limit: int = 10,
    asset_type: Optional[str] = None,
    bstatus: Optional[str] = None,
    department_id: Optional[str] = None,
    end_date: Optional[str] = None,
    fast_search: Optional[str] = None,
    manager_category: Optional[str] = None,
    order_no: Optional[str] = None,
    purchase_category: Optional[str] = None,
    purchase_desc: Optional[str] = None,
    recorder_id: Optional[str] = None,
    source_biz_no: Optional[str] = None,
    start_date: Optional[str] = None,
    statistical_date: Optional[str] = None,
    subcontract_items: Optional[str] = None,
    supplier_name: Optional[str] = None,
    sVars: Optional[Dict[str, Any]] = None,
    include_raw: bool = False,
) -> Dict[str, Any]:
    """查询采购申请列表，按 scope 路由到文档列出的 listQuery* 视图。"""
    resolved_scope = _resolve_scope(scope=scope, view=view)
    params = build_params(
        scope=resolved_scope,
        start=start,
        limit=limit,
        asset_type=asset_type,
        bstatus=bstatus,
        department_id=department_id,
        end_date=end_date,
        fast_search=fast_search,
        manager_category=manager_category,
        order_no=order_no,
        purchase_category=purchase_category,
        purchase_desc=purchase_desc,
        recorder_id=recorder_id,
        source_biz_no=source_biz_no,
        start_date=start_date,
        statistical_date=statistical_date,
        subcontract_items=subcontract_items,
        supplier_name=supplier_name,
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
    "query_purrequestlistaction": query_purrequestlistaction,
    "query_pur_request_list": query_purrequestlistaction,
}

TOOL_SCHEMAS = [
    {
        "name": "query_purrequestlistaction",
        "description": (
            "查询采购申请列表。通过 scope/view 路由到默认、部门、首页、分包、分包统计报表视图，"
            "默认视图包含继承的 /PurRequestListAction/listQuery。"
            "default 和 dept 视图会自动注入作用域相关 sVars（见 scope 参数说明）。"
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "scope": {
                    "type": "string",
                    "description": (
                        "视图范围：default=默认列表（自动注入 show_all=1），"
                        "dept=本部门视图（自动注入 show_dept=1），"
                        "home=首页视图（只查当前用户），"
                        "subcontract=分包视图，subcontract_report=分包统计报表。"
                    ),
                },
                "view": {"type": "string", "description": "scope 的别名；如同时传入，以 scope 为准。"},
                "start": {"type": "integer", "description": "分页起始位置，默认 0。"},
                "limit": {"type": "integer", "description": "分页条数，默认 10。"},
                "asset_type": {"type": "string", "description": "资产类型，精确匹配 (q_assetType -> pr.asset_type)。"},
                "bstatus": {
                    "type": "string",
                    "description": "申请状态 (q_bstatus -> pr.bstatus): 0=已作废, 1=已审核, 2=暂存, 3=等待重新审批, 4=审批中。",
                },
                "department_id": {"type": "string", "description": "申请部门，精确匹配 (q_departmentId -> pr.department_id)。"},
                "end_date": {"type": "string", "description": "endDate，结束时间 (endDate -> endDate)。"},
                "fast_search": {"type": "string", "description": "视图，模糊匹配 (fastSearch -> fastSearch)。"},
                "manager_category": {
                    "type": "string",
                    "description": "管理类别，精确匹配 (managerCategory -> managerCategory): 1=一类采购, 2=二类采购。",
                },
                "order_no": {"type": "string", "description": "采购编号，模糊匹配 (orderNo -> pr.order_no)。"},
                "purchase_category": {"type": "string", "description": "采购类别，精确匹配 (q_purchaseCategory -> pr.purchase_category)。"},
                "purchase_desc": {"type": "string", "description": "采购内容，模糊匹配 (q_purchaseDesc -> pr.purchase_desc)。"},
                "recorder_id": {"type": "string", "description": "申请人，模糊匹配 (q_recorderId -> ap.person_name)。"},
                "source_biz_no": {"type": "string", "description": "来源号，模糊匹配 (sourceBizNo -> pr.TXN_CORE_NO)。"},
                "start_date": {"type": "string", "description": "startDate，起始时间 (startDate -> startDate)。"},
                "statistical_date": {
                    "type": "string",
                    "description": (
                        "statisticalDate (statisticalDate -> 213): thisYear=本年度, lastYear=上年度, "
                        "thisQuarter=本季度, lastQuarter=上季度, thisMonth=本月, lastMonth=上月, "
                        "thisWeek=本周, lastWeek=上周, free=自定义。"
                    ),
                },
                "subcontract_items": {"type": "string", "description": "申请分包项目，模糊匹配 (subcontractItems -> pr.purchase_desc)。"},
                "supplier_name": {"type": "string", "description": "分包商，模糊匹配 (supplierName -> prs.supplier_name)。"},
                "sVars": {
                    "type": "object",
                    "description": (
                        "自定义 sVars 负载。default scope 自动注入 show_all=1，"
                        "dept scope 自动注入 show_dept=1。"
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
