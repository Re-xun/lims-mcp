"""MCP tools for SdInvoiceRequestListAction queries."""
from __future__ import annotations

import json
import os
import sys
from typing import Any, Dict, List, Optional

import httpx

JAVA_API_BASE = os.environ.get("JAVA_API_BASE", "http://localhost:8080")

SCOPE_TO_ENDPOINT = {
    "default": "/SdInvoiceRequestListAction/listQuery",
    "mine": "/SdInvoiceRequestListAction/listQueryMy",
}

FILTER_CONFIG = {
    "bstatus": {
        "backend_field": "sia.bstatus",
        "template": "= '{value}'",
    },
    "customer_name": {
        "backend_field": "ac.CUSTOMER_NAME_CN",
        "template": "like '%{value}%'",
    },
    "fast_search": {
        "backend_field": "fastSearch",
        "template": "like '%{value}%'",
    },
    "order_no": {
        "backend_field": "orderNo",
        "template": "like '%{value}%'",
    },
    "rstatus": {
        "backend_field": "sia.rstatus",
        "template": "= '{value}'",
    },
    "saler_no": {
        "backend_field": "sso.sales_order_no",
        "template": "like '%{value}%'",
    },
    "order_date_end": {
        "backend_field": "orderDate",
        "template": "<= '{value} 23:59:59'",
    },
    "order_date_start": {
        "backend_field": "orderDate",
        "template": ">= '{value}'",
    },
    "request_amt": {
        "backend_field": "requestAmt",
        "template": "like '%{value}%'",
    },
    "request_desc": {
        "backend_field": "requestDesc",
        "template": "like '%{value}%'",
    },
    "request_invoice_media": {
        "backend_field": "requestInvoiceMedia",
        "template": "= '{value}'",
    },
    "request_invoice_type": {
        "backend_field": "requestInvoiceType",
        "template": "= '{value}'",
    },
    "sales_order_no": {
        "backend_field": "salesOrderNo",
        "template": "like '%{value}%'",
    },
    "source_name": {
        "backend_field": "sourceName",
        "template": "like '%{value}%'",
    },
    "tax_id": {
        "backend_field": "taxId",
        "template": "like '%{value}%'",
    },
    "tax_name": {
        "backend_field": "taxName",
        "template": "like '%{value}%'",
    },
    "tax_remark": {
        "backend_field": "taxRemark",
        "template": "like '%{value}%'",
    },
}

FIELD_LABELS = {
    "rstatus": {
        "key": "rstatus",
        "title": "单据状态",
    },
    "orderDate": {
        "key": "order_date",
        "title": "申请日期",
    },
    "orderNo": {
        "key": "order_no",
        "title": "申请编号",
    },
    "customerName": {
        "key": "customer_name",
        "title": "客户名称",
    },
    "requestInvoiceType": {
        "key": "request_invoice_type",
        "title": "申请开票类型",
    },
    "requestInvoiceMedia": {
        "key": "request_invoice_media",
        "title": "申请发票介质",
    },
    "requestAmt": {
        "key": "request_amt",
        "title": "申请开票金额",
    },
    "taxName": {
        "key": "tax_name",
        "title": "申请开票抬头",
    },
    "taxId": {
        "key": "tax_id",
        "title": "开票抬头编号",
    },
    "taxRemark": {
        "key": "tax_remark",
        "title": "开票抬头备注",
    },
    "sourceName": {
        "key": "source_name",
        "title": "申请人",
    },
    "salesOrderNo": {
        "key": "sales_order_no",
        "title": "合同编号",
    },
    "bstatus": {
        "key": "bstatus",
        "title": "开票状态",
    },
    "requestDesc": {
        "key": "request_desc",
        "title": "申请开票内容",
    },
    "finArInvoiceNo": {
        "key": "fin_ar_invoice_no",
        "title": "开票编号",
    },
}

ENUM_FIELDS = {
    "bstatus": {
        1: "已开",
        2: "未开",
    },
    "request_invoice_media": {
        1: "电子发票",
        2: "纸质发票",
        3: "电子+纸质",
    },
    "request_invoice_type": {
        1: "收据",
        2: "增值税专用发票",
        3: "增值税普通发票",
        4: "形式发票",
    },
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
    bstatus: Optional[str] = None,
    customer_name: Optional[str] = None,
    fast_search: Optional[str] = None,
    order_no: Optional[str] = None,
    rstatus: Optional[int] = None,
    saler_no: Optional[str] = None,
    order_date_end: Optional[str] = None,
    order_date_start: Optional[str] = None,
    request_amt: Optional[str] = None,
    request_desc: Optional[str] = None,
    request_invoice_media: Optional[str] = None,
    request_invoice_type: Optional[str] = None,
    sales_order_no: Optional[str] = None,
    source_name: Optional[str] = None,
    tax_id: Optional[str] = None,
    tax_name: Optional[str] = None,
    tax_remark: Optional[str] = None,
) -> Optional[str]:
    values = {
        "bstatus": bstatus,
        "customer_name": customer_name,
        "fast_search": fast_search,
        "order_no": order_no,
        "rstatus": rstatus,
        "saler_no": saler_no,
        "order_date_end": order_date_end,
        "order_date_start": order_date_start,
        "request_amt": request_amt,
        "request_desc": request_desc,
        "request_invoice_media": request_invoice_media,
        "request_invoice_type": request_invoice_type,
        "sales_order_no": sales_order_no,
        "source_name": source_name,
        "tax_id": tax_id,
        "tax_name": tax_name,
        "tax_remark": tax_remark,
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


def build_params(
    *,
    scope: str,
    start: int = 0,
    limit: int = 10,
    bstatus: Optional[str] = None,
    customer_name: Optional[str] = None,
    fast_search: Optional[str] = None,
    order_no: Optional[str] = None,
    rstatus: Optional[int] = None,
    saler_no: Optional[str] = None,
    order_date_end: Optional[str] = None,
    order_date_start: Optional[str] = None,
    request_amt: Optional[str] = None,
    request_desc: Optional[str] = None,
    request_invoice_media: Optional[str] = None,
    request_invoice_type: Optional[str] = None,
    sales_order_no: Optional[str] = None,
    source_name: Optional[str] = None,
    tax_id: Optional[str] = None,
    tax_name: Optional[str] = None,
    tax_remark: Optional[str] = None,
    sVars: Optional[Dict[str, Any]] = None,
) -> Dict[str, str]:
    params = {
        "start": str(0 if start is None else start),
        "limit": str(10 if limit is None else limit),
    }
    if sVars is not None:
        params["sVars"] = json.dumps(sVars, ensure_ascii=False)

    filter_sql = build_filter(
        bstatus=bstatus,
        customer_name=customer_name,
        fast_search=fast_search,
        order_no=order_no,
        rstatus=rstatus,
        saler_no=saler_no,
        order_date_end=order_date_end,
        order_date_start=order_date_start,
        request_amt=request_amt,
        request_desc=request_desc,
        request_invoice_media=request_invoice_media,
        request_invoice_type=request_invoice_type,
        sales_order_no=sales_order_no,
        source_name=source_name,
        tax_id=tax_id,
        tax_name=tax_name,
        tax_remark=tax_remark,
    )
    if filter_sql:
        params["filter"] = filter_sql

    return params


def _build_columns() -> List[Dict[str, str]]:
    return [
        {
            "field": field,
            "key": meta["key"],
            "title": meta["title"],
        }
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


async def query_sdinvoicerequestlistaction(
    token: str,
    scope: str = "default",
    view: Optional[str] = None,
    start: int = 0,
    limit: int = 10,
    bstatus: Optional[str] = None,
    customer_name: Optional[str] = None,
    fast_search: Optional[str] = None,
    order_no: Optional[str] = None,
    rstatus: Optional[int] = None,
    saler_no: Optional[str] = None,
    order_date_end: Optional[str] = None,
    order_date_start: Optional[str] = None,
    request_amt: Optional[str] = None,
    request_desc: Optional[str] = None,
    request_invoice_media: Optional[str] = None,
    request_invoice_type: Optional[str] = None,
    sales_order_no: Optional[str] = None,
    source_name: Optional[str] = None,
    tax_id: Optional[str] = None,
    tax_name: Optional[str] = None,
    tax_remark: Optional[str] = None,
    sVars: Optional[Dict[str, Any]] = None,
    include_raw: bool = False,
) -> Dict[str, Any]:
    """查询开票申请/发票申请列表，按 scope 路由到默认、我的视图。"""
    resolved_scope = _resolve_scope(scope=scope, view=view)
    params = build_params(
        scope=resolved_scope,
        start=start,
        limit=limit,
        bstatus=bstatus,
        customer_name=customer_name,
        fast_search=fast_search,
        order_no=order_no,
        rstatus=rstatus,
        saler_no=saler_no,
        order_date_end=order_date_end,
        order_date_start=order_date_start,
        request_amt=request_amt,
        request_desc=request_desc,
        request_invoice_media=request_invoice_media,
        request_invoice_type=request_invoice_type,
        sales_order_no=sales_order_no,
        source_name=source_name,
        tax_id=tax_id,
        tax_name=tax_name,
        tax_remark=tax_remark,
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
    "query_sdinvoicerequestlistaction": query_sdinvoicerequestlistaction,
    "query_sd_invoice_request_list": query_sdinvoicerequestlistaction,
}

TOOL_SCHEMAS = [
    {
        "name": "query_sdinvoicerequestlistaction",
        "description": (
            "查询开票申请/发票申请列表。通过 scope/view 路由到默认、我的两个视图，"
            "默认视图包含继承的 /SdInvoiceRequestListAction/listQuery。"
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "scope": {
                    "type": "string",
                    "description": "视图范围：default=默认列表，mine=我的数据视图。",
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
                "bstatus": {
                    "type": "string",
                    "description": "开票状态 (bstatus -> sia.bstatus): 1=已开, 2=未开。",
                },
                "customer_name": {
                    "type": "string",
                    "description": "客户名称，模糊匹配 (q_customerName -> ac.CUSTOMER_NAME_CN)。",
                },
                "fast_search": {
                    "type": "string",
                    "description": "视图，模糊匹配 (fastSearch -> fastSearch)。",
                },
                "order_no": {
                    "type": "string",
                    "description": "申请编号，模糊匹配 (orderNo -> orderNo)。",
                },
                "rstatus": {
                    "type": "integer",
                    "description": "单据状态 (q_rstatus -> sia.rstatus): 1=审核, 2=暂存, 0=作废, 3=等待重新审批, 4=提交。",
                },
                "saler_no": {
                    "type": "string",
                    "description": "合同编号，模糊匹配 (salerNo -> sso.sales_order_no)。",
                },
                "order_date_end": {
                    "type": "string",
                    "description": "申请日期结束候选字段，格式 YYYY-MM-DD (orderDate -> orderDate, <= 23:59:59)。",
                },
                "order_date_start": {
                    "type": "string",
                    "description": "申请日期开始候选字段，格式 YYYY-MM-DD (orderDate -> orderDate, >=)。",
                },
                "request_amt": {
                    "type": "string",
                    "description": "申请开票金额候选字段，模糊匹配 (requestAmt -> requestAmt)。",
                },
                "request_desc": {
                    "type": "string",
                    "description": "申请开票内容候选字段，模糊匹配 (requestDesc -> requestDesc)。",
                },
                "request_invoice_media": {
                    "type": "string",
                    "description": "申请发票介质候选字段 (requestInvoiceMedia -> requestInvoiceMedia): 1=电子发票, 2=纸质发票, 3=电子+纸质。",
                },
                "request_invoice_type": {
                    "type": "string",
                    "description": "申请开票类型候选字段 (requestInvoiceType -> requestInvoiceType): 1=收据, 2=增值税专用发票, 3=增值税普通发票, 4=形式发票。",
                },
                "sales_order_no": {
                    "type": "string",
                    "description": "合同编号候选字段，模糊匹配 (salesOrderNo -> salesOrderNo)。",
                },
                "source_name": {
                    "type": "string",
                    "description": "申请人候选字段，模糊匹配 (sourceName -> sourceName)。",
                },
                "tax_id": {
                    "type": "string",
                    "description": "开票抬头编号候选字段，模糊匹配 (taxId -> taxId)。",
                },
                "tax_name": {
                    "type": "string",
                    "description": "申请开票抬头候选字段，模糊匹配 (taxName -> taxName)。",
                },
                "tax_remark": {
                    "type": "string",
                    "description": "开票抬头备注候选字段，模糊匹配 (taxRemark -> taxRemark)。",
                },
                "sVars": {
                    "type": "object",
                    "description": "自定义 sVars 负载；本工具不会根据未在文档第 7 节出现的 dataType 来源注入默认 dataType。",
                },
                "include_raw": {
                    "type": "boolean",
                    "description": "调试用。默认 false；为 true 时才返回后端原始 raw_resultList/raw_response。",
                },
            },
        },
    },
]
