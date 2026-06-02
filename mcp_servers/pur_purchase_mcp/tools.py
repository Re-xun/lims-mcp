"""MCP tools for PurPurchaseListAction queries."""
from __future__ import annotations

import json
import os
import sys
from typing import Any, Dict, List, Optional

import httpx

JAVA_API_BASE = os.environ.get("JAVA_API_BASE", "http://localhost:8080")

SCOPE_TO_ENDPOINT = {
    "default": "/PurPurchaseListAction/listQuery",
    "listquerybysupplierid": "/PurPurchaseListAction/listQueryBySupplierId",
    "listquerymaterial": "/PurPurchaseListAction/listQueryMaterial",
    "listquerysubcontract": "/PurPurchaseListAction/listQuerySubcontract",
}

SCOPE_DEFAULT_SVARS = {
    "default": {"show_all": "1", "modularType": "modular_type", "operation": "operation"},
}

FILTER_CONFIG = {
    "accept_status": {"backend_field": "pp.accept_status", "template": "= '{value}'"},
    "arrive_status": {"backend_field": "pp.arrive_status", "template": "= '{value}'"},
    "assess_status": {"backend_field": "pp.assess_status", "template": "= '{value}'"},
    "bstatus": {"backend_field": "pp.bstatus", "template": "= '{value}'"},
    "bstatus_payment": {"backend_field": "pp.bstatus_payment", "template": "= '{value}'"},
    "consignor_name_cn": {"backend_field": "consignorNameCn", "template": "like '%{value}%'"},
    "department_id": {"backend_field": "ad.id", "template": "= '{value}'"},
    "fast_search": {"backend_field": "fastSearch", "template": "like '%{value}%'"},
    "invoice_status": {"backend_field": "pp.invoice_status", "template": "= '{value}'"},
    "manager_category": {"backend_field": "pp.manager_category", "template": "= '{value}'"},
    "order_no": {"backend_field": "orderNo", "template": "like '%{value}%'"},
    "purchase_desc": {"backend_field": "purchaseDesc", "template": "like '%{value}%'"},
    "source_biz_no": {"backend_field": "txnCoreNo", "template": "like '%{value}%'"},
    "store_status": {"backend_field": "pp.store_status", "template": "= '{value}'"},
    "supplier": {"backend_field": "pp.supplier_name", "template": "like '%{value}%'"},
    "supplier_name": {"backend_field": "pp.supplier_name", "template": "like '%{value}%'"},
    "actuality_settlement_date_end": {"backend_field": "actualitySettlementDate", "template": "<= '{value} 23:59:59'"},
    "actuality_settlement_date_start": {"backend_field": "actualitySettlementDate", "template": ">= '{value}'"},
    "amt_with_tax": {"backend_field": "amtWithTax", "template": "like '%{value}%'"},
    "complete_invoice_date_end": {"backend_field": "completeInvoiceDate", "template": "<= '{value} 23:59:59'"},
    "complete_invoice_date_start": {"backend_field": "completeInvoiceDate", "template": ">= '{value}'"},
    "invoiced_amt": {"backend_field": "invoicedAmt", "template": "like '%{value}%'"},
    "latest_invoice_date_end": {"backend_field": "latestInvoiceDate", "template": "<= '{value} 23:59:59'"},
    "latest_invoice_date_start": {"backend_field": "latestInvoiceDate", "template": ">= '{value}'"},
    "latest_payment_date_end": {"backend_field": "latestPaymentDate", "template": "<= '{value} 23:59:59'"},
    "latest_payment_date_start": {"backend_field": "latestPaymentDate", "template": ">= '{value}'"},
    "order_date_end": {"backend_field": "orderDate", "template": "<= '{value} 23:59:59'"},
    "order_date_start": {"backend_field": "orderDate", "template": ">= '{value}'"},
    "paid_amt": {"backend_field": "paidAmt", "template": "like '%{value}%'"},
    "person_name": {"backend_field": "personName", "template": "like '%{value}%'"},
    "purchase_contract_no": {"backend_field": "purchaseContractNo", "template": "like '%{value}%'"},
    "saler_name": {"backend_field": "salerName", "template": "like '%{value}%'"},
    "uninvoiced_amt": {"backend_field": "uninvoicedAmt", "template": "like '%{value}%'"},
    "unpaid_amt": {"backend_field": "unpaidAmt", "template": "like '%{value}%'"},
}

FIELD_LABELS = {
    "orderNo": {"key": "order_no", "title": "采购编号"},
    "managerCategory": {"key": "manager_category", "title": "管理类别"},
    "orderDate": {"key": "order_date", "title": "采购日期"},
    "txnCoreNo": {"key": "txn_core_no", "title": "开案号"},
    "personName": {"key": "person_name", "title": "申请人"},
    "salerName": {"key": "saler_name", "title": "负责业务"},
    "purchaseContractNo": {"key": "purchase_contract_no", "title": "采购合同编号"},
    "consignorNameCn": {"key": "consignor_name_cn", "title": "合同方"},
    "supplierName": {"key": "supplier_name", "title": "供应商名称"},
    "departmentName": {"key": "department_name", "title": "负责实验室/部门"},
    "purchaseDesc": {"key": "purchase_desc", "title": "采购内容描述"},
    "amtWithTax": {"key": "amt_with_tax", "title": "总计金额"},
    "bstatusPayment": {"key": "bstatus_payment", "title": "付款状态"},
    "paidAmt": {"key": "paid_amt", "title": "已经付款金额"},
    "unpaidAmt": {"key": "unpaid_amt", "title": "剩余应付款金额"},
    "invoicedAmt": {"key": "invoiced_amt", "title": "已经开票金额"},
    "uninvoicedAmt": {"key": "uninvoiced_amt", "title": "剩余应开票金额"},
    "bstatus": {"key": "bstatus", "title": "采购状态"},
    "invoiceStatus": {"key": "invoice_status", "title": "开票状态"},
    "latestPaymentDate": {"key": "latest_payment_date", "title": "最新付款日期"},
    "actualitySettlementDate": {"key": "actuality_settlement_date", "title": "实际结款日期"},
    "latestInvoiceDate": {"key": "latest_invoice_date", "title": "最新收票日期"},
    "completeInvoiceDate": {"key": "complete_invoice_date", "title": "收齐票日期"},
    "arriveStatus": {"key": "arrive_status", "title": "服务/到货状态"},
    "acceptStatus": {"key": "accept_status", "title": "验收状态"},
    "storeStatus": {"key": "store_status", "title": "资产入库"},
    "assessStatus": {"key": "assess_status", "title": "采购评价"},
}

ENUM_FIELDS = {
    "accept_status": {
        0: "未验收",
        1: "已验收",
    },
    "arrive_status": {
        0: "未到货",
        2: "部分到货",
        1: "全部到货",
        3: "未开始服务",
        4: "服务中",
        5: "服务完成",
    },
    "assess_status": {
        0: "待评价",
        1: "已评价",
    },
    "bstatus": {
        1: "完成",
        2: "进行中",
        0: "作废",
    },
    "bstatus_payment": {
        20: "未付款",
        30: "部分付款",
        50: "全部付款",
    },
    "invoice_status": {
        20: "未收票",
        30: "部分已收",
        50: "收齐票",
    },
    "manager_category": {
        1: "一类采购",
        2: "二类采购",
    },
    "store_status": {
        0: "未入库",
        2: "部分入库",
        1: "已入库",
        3: "N/A",
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
    accept_status: Optional[str] = None,
    arrive_status: Optional[str] = None,
    assess_status: Optional[str] = None,
    bstatus: Optional[str] = None,
    bstatus_payment: Optional[str] = None,
    consignor_name_cn: Optional[str] = None,
    department_id: Optional[str] = None,
    fast_search: Optional[str] = None,
    invoice_status: Optional[str] = None,
    manager_category: Optional[str] = None,
    order_no: Optional[str] = None,
    purchase_desc: Optional[str] = None,
    source_biz_no: Optional[str] = None,
    store_status: Optional[str] = None,
    supplier: Optional[str] = None,
    supplier_name: Optional[str] = None,
    actuality_settlement_date_end: Optional[str] = None,
    actuality_settlement_date_start: Optional[str] = None,
    amt_with_tax: Optional[str] = None,
    complete_invoice_date_end: Optional[str] = None,
    complete_invoice_date_start: Optional[str] = None,
    invoiced_amt: Optional[str] = None,
    latest_invoice_date_end: Optional[str] = None,
    latest_invoice_date_start: Optional[str] = None,
    latest_payment_date_end: Optional[str] = None,
    latest_payment_date_start: Optional[str] = None,
    order_date_end: Optional[str] = None,
    order_date_start: Optional[str] = None,
    paid_amt: Optional[str] = None,
    person_name: Optional[str] = None,
    purchase_contract_no: Optional[str] = None,
    saler_name: Optional[str] = None,
    uninvoiced_amt: Optional[str] = None,
    unpaid_amt: Optional[str] = None,
) -> Optional[str]:
    values = {
        "accept_status": accept_status,
        "arrive_status": arrive_status,
        "assess_status": assess_status,
        "bstatus": bstatus,
        "bstatus_payment": bstatus_payment,
        "consignor_name_cn": consignor_name_cn,
        "department_id": department_id,
        "fast_search": fast_search,
        "invoice_status": invoice_status,
        "manager_category": manager_category,
        "order_no": order_no,
        "purchase_desc": purchase_desc,
        "source_biz_no": source_biz_no,
        "store_status": store_status,
        "supplier": supplier,
        "supplier_name": supplier_name,
        "actuality_settlement_date_end": actuality_settlement_date_end,
        "actuality_settlement_date_start": actuality_settlement_date_start,
        "amt_with_tax": amt_with_tax,
        "complete_invoice_date_end": complete_invoice_date_end,
        "complete_invoice_date_start": complete_invoice_date_start,
        "invoiced_amt": invoiced_amt,
        "latest_invoice_date_end": latest_invoice_date_end,
        "latest_invoice_date_start": latest_invoice_date_start,
        "latest_payment_date_end": latest_payment_date_end,
        "latest_payment_date_start": latest_payment_date_start,
        "order_date_end": order_date_end,
        "order_date_start": order_date_start,
        "paid_amt": paid_amt,
        "person_name": person_name,
        "purchase_contract_no": purchase_contract_no,
        "saler_name": saler_name,
        "uninvoiced_amt": uninvoiced_amt,
        "unpaid_amt": unpaid_amt,
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
    data_id: Optional[str] = None,
    accept_status: Optional[str] = None,
    arrive_status: Optional[str] = None,
    assess_status: Optional[str] = None,
    bstatus: Optional[str] = None,
    bstatus_payment: Optional[str] = None,
    consignor_name_cn: Optional[str] = None,
    department_id: Optional[str] = None,
    fast_search: Optional[str] = None,
    invoice_status: Optional[str] = None,
    manager_category: Optional[str] = None,
    order_no: Optional[str] = None,
    purchase_desc: Optional[str] = None,
    source_biz_no: Optional[str] = None,
    store_status: Optional[str] = None,
    supplier: Optional[str] = None,
    supplier_name: Optional[str] = None,
    actuality_settlement_date_end: Optional[str] = None,
    actuality_settlement_date_start: Optional[str] = None,
    amt_with_tax: Optional[str] = None,
    complete_invoice_date_end: Optional[str] = None,
    complete_invoice_date_start: Optional[str] = None,
    invoiced_amt: Optional[str] = None,
    latest_invoice_date_end: Optional[str] = None,
    latest_invoice_date_start: Optional[str] = None,
    latest_payment_date_end: Optional[str] = None,
    latest_payment_date_start: Optional[str] = None,
    order_date_end: Optional[str] = None,
    order_date_start: Optional[str] = None,
    paid_amt: Optional[str] = None,
    person_name: Optional[str] = None,
    purchase_contract_no: Optional[str] = None,
    saler_name: Optional[str] = None,
    uninvoiced_amt: Optional[str] = None,
    unpaid_amt: Optional[str] = None,
    sVars: Optional[Dict[str, Any]] = None,
) -> Dict[str, str]:
    params = {
        "start": str(0 if start is None else start),
        "limit": str(10 if limit is None else limit),
    }
    if data_id is not None and data_id != "":
        params["dataId"] = str(data_id)

    resolved_sVars = _resolve_svars(scope, sVars)
    if resolved_sVars is not None:
        params["sVars"] = json.dumps(resolved_sVars, ensure_ascii=False)

    filter_sql = build_filter(
        accept_status=accept_status,
        arrive_status=arrive_status,
        assess_status=assess_status,
        bstatus=bstatus,
        bstatus_payment=bstatus_payment,
        consignor_name_cn=consignor_name_cn,
        department_id=department_id,
        fast_search=fast_search,
        invoice_status=invoice_status,
        manager_category=manager_category,
        order_no=order_no,
        purchase_desc=purchase_desc,
        source_biz_no=source_biz_no,
        store_status=store_status,
        supplier=supplier,
        supplier_name=supplier_name,
        actuality_settlement_date_end=actuality_settlement_date_end,
        actuality_settlement_date_start=actuality_settlement_date_start,
        amt_with_tax=amt_with_tax,
        complete_invoice_date_end=complete_invoice_date_end,
        complete_invoice_date_start=complete_invoice_date_start,
        invoiced_amt=invoiced_amt,
        latest_invoice_date_end=latest_invoice_date_end,
        latest_invoice_date_start=latest_invoice_date_start,
        latest_payment_date_end=latest_payment_date_end,
        latest_payment_date_start=latest_payment_date_start,
        order_date_end=order_date_end,
        order_date_start=order_date_start,
        paid_amt=paid_amt,
        person_name=person_name,
        purchase_contract_no=purchase_contract_no,
        saler_name=saler_name,
        uninvoiced_amt=uninvoiced_amt,
        unpaid_amt=unpaid_amt,
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


async def query_purpurchaselistaction(
    token: str,
    scope: str = "default",
    view: Optional[str] = None,
    start: int = 0,
    limit: int = 10,
    data_id: Optional[str] = None,
    accept_status: Optional[str] = None,
    arrive_status: Optional[str] = None,
    assess_status: Optional[str] = None,
    bstatus: Optional[str] = None,
    bstatus_payment: Optional[str] = None,
    consignor_name_cn: Optional[str] = None,
    department_id: Optional[str] = None,
    fast_search: Optional[str] = None,
    invoice_status: Optional[str] = None,
    manager_category: Optional[str] = None,
    order_no: Optional[str] = None,
    purchase_desc: Optional[str] = None,
    source_biz_no: Optional[str] = None,
    store_status: Optional[str] = None,
    supplier: Optional[str] = None,
    supplier_name: Optional[str] = None,
    actuality_settlement_date_end: Optional[str] = None,
    actuality_settlement_date_start: Optional[str] = None,
    amt_with_tax: Optional[str] = None,
    complete_invoice_date_end: Optional[str] = None,
    complete_invoice_date_start: Optional[str] = None,
    invoiced_amt: Optional[str] = None,
    latest_invoice_date_end: Optional[str] = None,
    latest_invoice_date_start: Optional[str] = None,
    latest_payment_date_end: Optional[str] = None,
    latest_payment_date_start: Optional[str] = None,
    order_date_end: Optional[str] = None,
    order_date_start: Optional[str] = None,
    paid_amt: Optional[str] = None,
    person_name: Optional[str] = None,
    purchase_contract_no: Optional[str] = None,
    saler_name: Optional[str] = None,
    uninvoiced_amt: Optional[str] = None,
    unpaid_amt: Optional[str] = None,
    sVars: Optional[Dict[str, Any]] = None,
    include_raw: bool = False,
) -> Dict[str, Any]:
    """查询采购单列表，按 scope 路由到文档列出的 listQuery* 视图。"""
    resolved_scope = _resolve_scope(scope=scope, view=view)
    params = build_params(
        scope=resolved_scope,
        start=start,
        limit=limit,
        data_id=data_id,
        accept_status=accept_status,
        arrive_status=arrive_status,
        assess_status=assess_status,
        bstatus=bstatus,
        bstatus_payment=bstatus_payment,
        consignor_name_cn=consignor_name_cn,
        department_id=department_id,
        fast_search=fast_search,
        invoice_status=invoice_status,
        manager_category=manager_category,
        order_no=order_no,
        purchase_desc=purchase_desc,
        source_biz_no=source_biz_no,
        store_status=store_status,
        supplier=supplier,
        supplier_name=supplier_name,
        actuality_settlement_date_end=actuality_settlement_date_end,
        actuality_settlement_date_start=actuality_settlement_date_start,
        amt_with_tax=amt_with_tax,
        complete_invoice_date_end=complete_invoice_date_end,
        complete_invoice_date_start=complete_invoice_date_start,
        invoiced_amt=invoiced_amt,
        latest_invoice_date_end=latest_invoice_date_end,
        latest_invoice_date_start=latest_invoice_date_start,
        latest_payment_date_end=latest_payment_date_end,
        latest_payment_date_start=latest_payment_date_start,
        order_date_end=order_date_end,
        order_date_start=order_date_start,
        paid_amt=paid_amt,
        person_name=person_name,
        purchase_contract_no=purchase_contract_no,
        saler_name=saler_name,
        uninvoiced_amt=uninvoiced_amt,
        unpaid_amt=unpaid_amt,
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
    "query_purpurchaselistaction": query_purpurchaselistaction,
}

TOOL_SCHEMAS = [
    {
        "name": "query_purpurchaselistaction",
        "description": (
            "查询采购单列表。通过 scope 路由到默认列表（继承自 ListBaseAction 的 /PurPurchaseListAction/listQuery）、"
            "按供应商查询、物资查询、分包外发查询视图。"
            "default 视图自动注入 show_all=1、modularType=modular_type、operation=operation 等 sVars。"
            "本工具不会根据未在文档第 7 节出现的 dataType 来源注入默认 dataType。"
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "scope": {
                    "type": "string",
                    "description": (
                        "视图范围：default=默认列表（自动注入 show_all=1, modularType=modular_type, operation=operation），"
                        "listQueryBySupplierId=按供应商查询（需传 data_id），"
                        "listQueryMaterial=物资查询，"
                        "listQuerySubcontract=分包外发查询。"
                    ),
                },
                "view": {"type": "string", "description": "scope 的别名；如同时传入，以 scope 为准。"},
                "start": {"type": "integer", "description": "分页起始位置，默认 0。"},
                "limit": {"type": "integer", "description": "分页条数，默认 10。"},
                "data_id": {"type": "string", "description": "供应商 ID，用于 listQueryBySupplierId 视图。"},
                "accept_status": {
                    "type": "integer",
                    "description": "验收状态 (q_acceptStatus → pp.accept_status): 0=未验收, 1=已验收。",
                },
                "arrive_status": {
                    "type": "integer",
                    "description": "服务/到货状态 (q_arriveStatus → pp.arrive_status): 0=未到货, 2=部分到货, 1=全部到货, 3=未开始服务, 4=服务中, 5=服务完成。",
                },
                "assess_status": {
                    "type": "string",
                    "description": "采购评价 (q_assessStatus → pp.assess_status): 0=待评价, 1=已评价。",
                },
                "bstatus": {
                    "type": "string",
                    "description": "采购状态 (q_bstatus → pp.bstatus): 1=完成, 2=进行中, 0=作废。",
                },
                "bstatus_payment": {
                    "type": "integer",
                    "description": "付款状态 (q_bstatusPayment → pp.bstatus_payment): 20=未付款, 30=部分付款, 50=全部付款。",
                },
                "consignor_name_cn": {"type": "string", "description": "合同方，模糊匹配 (consignorNameCn → consignorNameCn)。"},
                "department_id": {"type": "string", "description": "负责实验室，精确匹配 (departmentId → ad.id)。"},
                "fast_search": {"type": "string", "description": "视图，模糊匹配 (fastSearch → fastSearch)。"},
                "invoice_status": {
                    "type": "integer",
                    "description": "开票状态 (q_invoiceStatus → pp.invoice_status): 20=未收票, 30=部分已收, 50=收齐票。",
                },
                "manager_category": {
                    "type": "string",
                    "description": "管理类型 (q_managerCategory → pp.manager_category): 1=一类采购, 2=二类采购。",
                },
                "order_no": {"type": "string", "description": "采购编号，模糊匹配 (orderNo → orderNo)。"},
                "purchase_desc": {"type": "string", "description": "采购内容，模糊匹配 (q_purchaseDesc → purchaseDesc)。"},
                "source_biz_no": {"type": "string", "description": "开案号，模糊匹配 (sourceBizNo → txnCoreNo)。"},
                "store_status": {
                    "type": "integer",
                    "description": "资产入库 (q_storeStatus → pp.store_status): 0=未入库, 2=部分入库, 1=已入库, 3=N/A。",
                },
                "supplier": {"type": "string", "description": "分包实验室，模糊匹配 (supplier → pp.supplier_name)。"},
                "supplier_name": {"type": "string", "description": "供应商名称，模糊匹配 (q_supplierName → pp.supplier_name)。"},
                "actuality_settlement_date_end": {"type": "string", "description": "实际结款日期结束 (actualitySettlementDate <= value)。"},
                "actuality_settlement_date_start": {"type": "string", "description": "实际结款日期开始 (actualitySettlementDate >= value)。"},
                "amt_with_tax": {"type": "string", "description": "总计金额，模糊匹配 (amtWithTax → amtWithTax)。"},
                "complete_invoice_date_end": {"type": "string", "description": "收齐票日期结束 (completeInvoiceDate <= value)。"},
                "complete_invoice_date_start": {"type": "string", "description": "收齐票日期开始 (completeInvoiceDate >= value)。"},
                "invoiced_amt": {"type": "string", "description": "已经开票金额，模糊匹配 (invoicedAmt → invoicedAmt)。"},
                "latest_invoice_date_end": {"type": "string", "description": "最新收票日期结束 (latestInvoiceDate <= value)。"},
                "latest_invoice_date_start": {"type": "string", "description": "最新收票日期开始 (latestInvoiceDate >= value)。"},
                "latest_payment_date_end": {"type": "string", "description": "最新付款日期结束 (latestPaymentDate <= value)。"},
                "latest_payment_date_start": {"type": "string", "description": "最新付款日期开始 (latestPaymentDate >= value)。"},
                "order_date_end": {"type": "string", "description": "采购日期结束 (orderDate <= value)。"},
                "order_date_start": {"type": "string", "description": "采购日期开始 (orderDate >= value)。"},
                "paid_amt": {"type": "string", "description": "已经付款金额，模糊匹配 (paidAmt → paidAmt)。"},
                "person_name": {"type": "string", "description": "申请人，模糊匹配 (personName → personName)。"},
                "purchase_contract_no": {"type": "string", "description": "采购合同编号，模糊匹配 (purchaseContractNo → purchaseContractNo)。"},
                "saler_name": {"type": "string", "description": "负责业务，模糊匹配 (salerName → salerName)。"},
                "uninvoiced_amt": {"type": "string", "description": "剩余应开票金额，模糊匹配 (uninvoicedAmt → uninvoicedAmt)。"},
                "unpaid_amt": {"type": "string", "description": "剩余应付款金额，模糊匹配 (unpaidAmt → unpaidAmt)。"},
                "sVars": {
                    "type": "object",
                    "description": (
                        "自定义 sVars 负载。default scope 自动注入 show_all=1、"
                        "modularType=modular_type、operation=operation。"
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
