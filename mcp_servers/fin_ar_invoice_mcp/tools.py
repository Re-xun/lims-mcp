"""MCP tools for FinArInvoiceListAction invoice record queries."""
from __future__ import annotations

import json
import os
import sys
from typing import Any

import httpx

JAVA_API_BASE = os.environ.get("JAVA_API_BASE", "http://localhost:8080")

SCOPE_TO_ENDPOINT = {
    "default": "/FinArInvoiceListAction/listQuery",
    "item": "/FinArInvoiceListAction/listQueryItem",
    "mine": "/FinArInvoiceListAction/listQueryMyItem",
}

FILTER_CONFIG = {
    "bstatus": {"backend_field": "fai.bstatus", "template": "= '{value}'"},
    "company_invoice_name": {"backend_field": "acii.company_name", "template": "like '%{value}%'"},
    "customer_name": {"backend_field": "ac.CUSTOMER_NAME_CN", "template": "like '%{value}%'"},
    "fast_search": {"backend_field": "fastSearch", "template": "like '%{value}%'"},
    "invoice_no": {"backend_field": "faii.invoice_no", "template": "like '%{value}%'"},
    "order_no": {"backend_field": "fai.order_no", "template": "like '%{value}%'"},
    "rstatus": {"backend_field": "fai.rstatus", "template": "= '{value}'"},
    "saler_no": {"backend_field": "sso.sales_order_no", "template": "like '%{value}%'"},
    "sales_name": {"backend_field": "ap3.person_Name", "template": "like '%{value}%'"},
}

FIELD_LABELS = {
    "orderDate": {"key": "order_date", "title": "开票日期"},
    "orderNo": {"key": "order_no", "title": "开票编号"},
    "salesOrderNo": {"key": "sales_order_no", "title": "合同号"},
    "customerNameCn": {"key": "customer_name_cn", "title": "客户名称"},
    "requestInvoiceType": {"key": "request_invoice_type", "title": "票据类型"},
    "requestInvoiceMedia": {"key": "request_invoice_media", "title": "发票介质"},
    "requestAmt": {"key": "request_amt", "title": "发票金额"},
    "invoiceNo": {"key": "invoice_no", "title": "发票号码"},
    "bstatus": {"key": "bstatus", "title": "收款状态"},
    "shippingNo": {"key": "shipping_no", "title": "快递单号"},
    "contactName": {"key": "contact_name", "title": "接收人"},
    "salesName": {"key": "sales_name", "title": "业务"},
    "mobileTelephone": {"key": "mobile_telephone", "title": "接收人电话"},
    "applicantName": {"key": "applicant_name", "title": "申请人"},
    "detailBstatus": {"key": "detail_bstatus", "title": "接收状态"},
    "personName": {"key": "person_name", "title": "记录人"},
    "rstatus": {"key": "rstatus", "title": "状态"},
    "companyInvoiceName": {"key": "company_invoice_name", "title": "发票抬头"},
}

ENUM_FIELDS = {
    "bstatus": {
        1: "已收",
        2: "部分已收",
        3: "未收",
    },
    "detail_bstatus": {
        1: "electron",
        2: "已收",
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


def _resolve_scope(scope: str | None = None, view: str | None = None) -> str:
    resolved = (scope or view or "default").strip().lower()
    if resolved == "listqueryitem":
        resolved = "item"
    elif resolved == "listquerymyitem":
        resolved = "mine"
    if resolved not in SCOPE_TO_ENDPOINT:
        raise ValueError(
            "Unsupported scope/view: {}. Allowed values: {}".format(
                resolved, ", ".join(sorted(SCOPE_TO_ENDPOINT))
            )
        )
    return resolved


def build_filter(
    *,
    bstatus: int | None = None,
    company_invoice_name: str | None = None,
    customer_name: str | None = None,
    fast_search: str | None = None,
    invoice_no: str | None = None,
    order_no: str | None = None,
    rstatus: int | None = None,
    saler_no: str | None = None,
    sales_name: str | None = None,
) -> str | None:
    values = {
        "bstatus": bstatus,
        "company_invoice_name": company_invoice_name,
        "customer_name": customer_name,
        "fast_search": fast_search,
        "invoice_no": invoice_no,
        "order_no": order_no,
        "rstatus": rstatus,
        "saler_no": saler_no,
        "sales_name": sales_name,
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
    bstatus: int | None = None,
    company_invoice_name: str | None = None,
    customer_name: str | None = None,
    fast_search: str | None = None,
    invoice_no: str | None = None,
    order_no: str | None = None,
    rstatus: int | None = None,
    saler_no: str | None = None,
    sales_name: str | None = None,
    sVars: dict | None = None,
) -> dict[str, str]:
    params = {
        "start": str(0 if start is None else start),
        "limit": str(10 if limit is None else limit),
        "sVars": json.dumps(dict(sVars or {}), ensure_ascii=False),
    }

    filter_sql = build_filter(
        bstatus=bstatus,
        company_invoice_name=company_invoice_name,
        customer_name=customer_name,
        fast_search=fast_search,
        invoice_no=invoice_no,
        order_no=order_no,
        rstatus=rstatus,
        saler_no=saler_no,
        sales_name=sales_name,
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


async def query_finarinvoicelistaction(
    token: str,
    scope: str = "default",
    view: str | None = None,
    start: int = 0,
    limit: int = 10,
    bstatus: int | None = None,
    company_invoice_name: str | None = None,
    customer_name: str | None = None,
    fast_search: str | None = None,
    invoice_no: str | None = None,
    order_no: str | None = None,
    rstatus: int | None = None,
    saler_no: str | None = None,
    sales_name: str | None = None,
    sVars: dict | None = None,
    include_raw: bool = False,
) -> dict[str, Any]:
    """查询开票记录列表，按 scope 路由到默认、明细、我的明细视图。"""
    resolved_scope = _resolve_scope(scope=scope, view=view)
    params = build_params(
        start=start,
        limit=limit,
        bstatus=bstatus,
        company_invoice_name=company_invoice_name,
        customer_name=customer_name,
        fast_search=fast_search,
        invoice_no=invoice_no,
        order_no=order_no,
        rstatus=rstatus,
        saler_no=saler_no,
        sales_name=sales_name,
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
    "query_finarinvoicelistaction": query_finarinvoicelistaction,
    "query_fin_ar_invoice_list": query_finarinvoicelistaction,
}

TOOL_SCHEMAS = [
    {
        "name": "query_finarinvoicelistaction",
        "description": (
            "查询开票记录列表（含收款状态，可用于生成收款通知单）。通过 scope/view 路由到 default、item、mine；"
            "default 包含继承的 /FinArInvoiceListAction/listQuery。"
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "scope": {
                    "type": "string",
                    "description": "视图范围：default=默认列表，item=listQueryItem，mine=listQueryMyItem。",
                },
                "view": {
                    "type": "string",
                    "description": "scope 的别名；如同时传入，以 scope 为准。兼容 listQueryItem/listQueryMyItem。",
                },
                "start": {"type": "integer", "description": "分页起始位置，默认 0。"},
                "limit": {"type": "integer", "description": "分页条数，默认 10。"},
                "bstatus": {
                    "type": "integer",
                    "description": "收款状态，精确匹配 (q_bstatus -> fai.bstatus)：1=已收, 2=部分已收, 3=未收。",
                },
                "company_invoice_name": {
                    "type": "string",
                    "description": "发票抬头，模糊匹配 (companyInvoiceName -> acii.company_name)。",
                },
                "customer_name": {
                    "type": "string",
                    "description": "客户名称，模糊匹配 (q_customerName -> ac.CUSTOMER_NAME_CN)。",
                },
                "fast_search": {
                    "type": "string",
                    "description": "视图，模糊匹配 (fastSearch -> fastSearch)。",
                },
                "invoice_no": {
                    "type": "string",
                    "description": "发票号码，模糊匹配 (q_invoiceNo -> faii.invoice_no)。",
                },
                "order_no": {
                    "type": "string",
                    "description": "开票编号，模糊匹配 (queryOrderNo -> fai.order_no)。",
                },
                "rstatus": {
                    "type": "integer",
                    "description": "单据状态，精确匹配 (q_rstatus -> fai.rstatus)：1=审核, 2=暂存, 0=作废, 3=等待重新审批, 4=提交。",
                },
                "saler_no": {
                    "type": "string",
                    "description": "合同编号，模糊匹配 (salerNo -> sso.sales_order_no)。",
                },
                "sales_name": {
                    "type": "string",
                    "description": "业务，模糊匹配 (q_salesName -> ap3.person_Name)。",
                },
                "sVars": {
                    "type": "object",
                    "description": "高级兼容参数。默认不注入第 7 节未确认来源的字段。",
                },
                "include_raw": {
                    "type": "boolean",
                    "description": "调试用。默认 false；为 true 时才返回后端原始 raw_resultList/raw_response。",
                },
            },
        },
    },
]
