"""MCP tools for MyFinCasReceivingListAction receiving queries."""
from __future__ import annotations

import json
import os
import sys
from typing import Any

import httpx

JAVA_API_BASE = os.environ.get("JAVA_API_BASE", "http://localhost:8080")

SCOPE_TO_ENDPOINT = {
    "default": "/MyFinCasReceivingListAction/listQuery",
}

FILTER_CONFIG = {
    "bstatus": {"backend_field": "sso.bstatus", "template": "= '{value}'"},
    "contract_no": {"backend_field": "sso.sales_order_no", "template": "like '%{value}%'"},
    "customer_name": {"backend_field": "ac.CUSTOMER_NAME_CN", "template": "like '%{value}%'"},
    "fast_search": {"backend_field": "fastSearch", "template": "like '%{value}%'"},
    "order_no": {"backend_field": "orderNo", "template": "like '%{value}%'"},
    "payment_company": {"backend_field": "fcr.payment_company", "template": "like '%{value}%'"},
    "person_name": {"backend_field": "ap.PERSON_NAME", "template": "like '%{value}%'"},
    "received_date_end": {"backend_field": "fcr.received_date", "template": "<= '{value} 23:59:59'"},
    "received_date_start": {"backend_field": "fcr.received_date", "template": ">= '{value}'"},
    "receiving_date_enums": {"backend_field": "receivingDateEnums", "template": "= '{value}'"},
    "rstatus": {"backend_field": "fcr.rstatus", "template": "= '{value}'"},
    "bank_name": {"backend_field": "bankName", "template": "like '%{value}%'"},
    "bill_type_id": {"backend_field": "billTypeId", "template": "= '{value}'"},
    "customer_name_cn": {"backend_field": "customerNameCn", "template": "like '%{value}%'"},
    "receiving_phase": {"backend_field": "receivingPhase", "template": "= '{value}'"},
    "sales_order_bstatus": {"backend_field": "salesOrderBstatus", "template": "= '{value}'"},
    "sales_order_invoiced_amt": {"backend_field": "salesOrderInvoicedAmt", "template": "like '%{value}%'"},
    "sales_order_no": {"backend_field": "salesOrderNo", "template": "like '%{value}%'"},
    "sales_order_uninvoiced_amt": {"backend_field": "salesOrderUninvoicedAmt", "template": "like '%{value}%'"},
    "sso_amt_with_tax_local": {"backend_field": "ssoAmtWithTaxLocal", "template": "like '%{value}%'"},
    "sso_receivable_amt_local": {"backend_field": "ssoReceivableAmtLocal", "template": "like '%{value}%'"},
    "sso_received_amt_local": {"backend_field": "ssoReceivedAmtLocal", "template": "like '%{value}%'"},
}

FIELD_LABELS = {
    "orderNo": {"key": "order_no", "title": "收款记录编号"},
    "receivedDate": {"key": "received_date", "title": "收款日期"},
    "receivingPhase": {"key": "receiving_phase", "title": "期次"},
    "salesOrderNo": {"key": "sales_order_no", "title": "合同编号"},
    "customerNameCn": {"key": "customer_name_cn", "title": "客户名称"},
    "paymentCompany": {"key": "payment_company", "title": "付款公司"},
    "salesOrderBstatus": {"key": "sales_order_bstatus", "title": "合同状态"},
    "billTypeId": {"key": "bill_type_id", "title": "收款类型"},
    "personName": {"key": "person_name", "title": "负责销售"},
    "ssoAmtWithTaxLocal": {"key": "sso_amt_with_tax_local", "title": "合同金额"},
    "ssoReceivedAmtLocal": {"key": "sso_received_amt_local", "title": "已收金额"},
    "ssoReceivableAmtLocal": {"key": "sso_receivable_amt_local", "title": "剩余应收金额"},
    "salesOrderInvoicedAmt": {"key": "sales_order_invoiced_amt", "title": "已开票金额"},
    "salesOrderUninvoicedAmt": {"key": "sales_order_uninvoiced_amt", "title": "剩余应开票金额"},
    "bankName": {"key": "bank_name", "title": "收款银行"},
    "rstatus": {"key": "rstatus", "title": "状态"},
}

ENUM_FIELDS = {
    "bill_type_id": {
        "FCR01-01": "有合同收款",
        "FCR02-01": "认领收款",
        "FCR02-02": "无合同收款",
    },
    "receiving_phase": {
        1: "预付款",
        2: "尾款",
    },
    "rstatus": {
        0: "已作废",
        1: "已审核",
        2: "暂存",
        3: "等待重新审批",
        4: "审批中",
    },
    "sales_order_bstatus": {
        20: "未开案",
        30: "案件进行中",
        40: "结案收款中",
        45: "结案已收款",
        50: "结束",
        60: "取消",
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


async def query_myfincasreceivinglistaction(
    token: str,
    scope: str = "default",
    view: str | None = None,
    start: int = 0,
    limit: int = 10,
    bstatus: int | None = None,
    contract_no: str | None = None,
    customer_name: str | None = None,
    fast_search: str | None = None,
    order_no: str | None = None,
    payment_company: str | None = None,
    person_name: str | None = None,
    received_date_end: str | None = None,
    received_date_start: str | None = None,
    receiving_date_enums: str | None = None,
    rstatus: int | None = None,
    bank_name: str | None = None,
    bill_type_id: str | None = None,
    customer_name_cn: str | None = None,
    receiving_phase: int | None = None,
    sales_order_bstatus: int | None = None,
    sales_order_invoiced_amt: str | None = None,
    sales_order_no: str | None = None,
    sales_order_uninvoiced_amt: str | None = None,
    sso_amt_with_tax_local: str | None = None,
    sso_receivable_amt_local: str | None = None,
    sso_received_amt_local: str | None = None,
    sVars: dict | None = None,
    include_raw: bool = False,
) -> dict[str, Any]:
    """查询我的收款单列表，default 包含继承的 /MyFinCasReceivingListAction/listQuery。"""
    resolved_scope = _resolve_scope(scope=scope, view=view)
    params = build_params(
        start=start,
        limit=limit,
        bstatus=bstatus,
        contract_no=contract_no,
        customer_name=customer_name,
        fast_search=fast_search,
        order_no=order_no,
        payment_company=payment_company,
        person_name=person_name,
        received_date_end=received_date_end,
        received_date_start=received_date_start,
        receiving_date_enums=receiving_date_enums,
        rstatus=rstatus,
        bank_name=bank_name,
        bill_type_id=bill_type_id,
        customer_name_cn=customer_name_cn,
        receiving_phase=receiving_phase,
        sales_order_bstatus=sales_order_bstatus,
        sales_order_invoiced_amt=sales_order_invoiced_amt,
        sales_order_no=sales_order_no,
        sales_order_uninvoiced_amt=sales_order_uninvoiced_amt,
        sso_amt_with_tax_local=sso_amt_with_tax_local,
        sso_receivable_amt_local=sso_receivable_amt_local,
        sso_received_amt_local=sso_received_amt_local,
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
    "query_myfincasreceivinglistaction": query_myfincasreceivinglistaction,
    "query_my_fin_cas_receiving_list": query_myfincasreceivinglistaction,
}

TOOL_SCHEMAS = [
    {
        "name": "query_myfincasreceivinglistaction",
        "description": (
            "查询我的收款单列表。default=默认列表，包含继承的 "
            "/MyFinCasReceivingListAction/listQuery。"
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "scope": {"type": "string", "description": "视图范围：default=默认列表。"},
                "view": {"type": "string", "description": "scope 的别名；如同时传入，以 scope 为准。"},
                "start": {"type": "integer", "description": "分页起始位置，默认 0。"},
                "limit": {"type": "integer", "description": "分页条数，默认 10。"},
                "bstatus": {"type": "integer", "description": "合同状态，精确匹配 (queryBstatus -> sso.bstatus)：20=未开案, 30=案件进行中, 40=结案收款中, 45=结案已收款, 50=结束, 60=取消。"},
                "contract_no": {"type": "string", "description": "合同编号，模糊匹配 (queryContractNo -> sso.sales_order_no)。"},
                "customer_name": {"type": "string", "description": "客户名称，模糊匹配 (queryCustomerName -> ac.CUSTOMER_NAME_CN)。"},
                "fast_search": {"type": "string", "description": "视图，模糊匹配 (fastSearch -> fastSearch)。"},
                "order_no": {"type": "string", "description": "收款记录编号，模糊匹配 (queryOrderNo -> orderNo)。"},
                "payment_company": {"type": "string", "description": "付款公司，模糊匹配 (queryPaymentCompany -> fcr.payment_company)。"},
                "person_name": {"type": "string", "description": "负责销售，模糊匹配 (queryPersonName -> ap.PERSON_NAME)。"},
                "received_date_end": {"type": "string", "description": "到结束，结束时间 (q_receivingEndDate -> fcr.received_date)。"},
                "received_date_start": {"type": "string", "description": "从开始，起始时间 (q_receivingStrDate -> fcr.received_date)。"},
                "receiving_date_enums": {"type": "string", "description": "收款日期，精确匹配 (receivingDateEnums -> receivingDateEnums)：thisYear=本年度, lastYear=上年度, thisQuarter=本季度, lastQuarter=上季度, thisMonth=本月, lastMonth=上月, thisWeek=本周, lastWeek=上周, free=自定义。"},
                "rstatus": {"type": "integer", "description": "单据状态，精确匹配 (q_rstatus -> fcr.rstatus)：1=审核, 2=暂存, 0=作废, 3=等待重新审批, 4=提交。"},
                "bank_name": {"type": "string", "description": "收款银行候选字段，模糊匹配 (bankName -> bankName)。"},
                "bill_type_id": {"type": "string", "description": "收款类型候选字段，精确匹配 (billTypeId -> billTypeId)：FCR01-01=有合同收款, FCR02-01=认领收款, FCR02-02=无合同收款。"},
                "customer_name_cn": {"type": "string", "description": "客户名称候选字段，模糊匹配 (customerNameCn -> customerNameCn)。"},
                "receiving_phase": {"type": "integer", "description": "期次候选字段，精确匹配 (receivingPhase -> receivingPhase)：1=预付款, 2=尾款。"},
                "sales_order_bstatus": {"type": "integer", "description": "合同状态候选字段，精确匹配 (salesOrderBstatus -> salesOrderBstatus)：20=未开案, 30=案件进行中, 40=结案收款中, 45=结案已收款, 50=结束, 60=取消。"},
                "sales_order_invoiced_amt": {"type": "string", "description": "已开票金额候选字段，模糊匹配 (salesOrderInvoicedAmt -> salesOrderInvoicedAmt)。"},
                "sales_order_no": {"type": "string", "description": "合同编号候选字段，模糊匹配 (salesOrderNo -> salesOrderNo)。"},
                "sales_order_uninvoiced_amt": {"type": "string", "description": "剩余应开票金额候选字段，模糊匹配 (salesOrderUninvoicedAmt -> salesOrderUninvoicedAmt)。"},
                "sso_amt_with_tax_local": {"type": "string", "description": "合同金额候选字段，模糊匹配 (ssoAmtWithTaxLocal -> ssoAmtWithTaxLocal)。"},
                "sso_receivable_amt_local": {"type": "string", "description": "剩余应收金额候选字段，模糊匹配 (ssoReceivableAmtLocal -> ssoReceivableAmtLocal)。"},
                "sso_received_amt_local": {"type": "string", "description": "已收金额候选字段，模糊匹配 (ssoReceivedAmtLocal -> ssoReceivedAmtLocal)。"},
                "sVars": {"type": "object", "description": "高级兼容参数。默认不注入第 7 节未确认来源的字段。"},
                "include_raw": {"type": "boolean", "description": "调试用。默认 false；为 true 时才返回后端原始 raw_resultList/raw_response。"},
            },
        },
    },
]
