"""MCP tools for SdSalesOrderListAction sales order list queries.

Source: SdSalesOrderListAction.java
  com.yiuser.lims.sd.sdsalesorder.SdSalesOrderListAction
"""
from __future__ import annotations

import json
import os
import sys
from typing import Any

import httpx

JAVA_API_BASE = os.environ.get("JAVA_API_BASE", "http://localhost:8080")

BASE_PATH = "/SdSalesOrderListAction"

SCOPE_TO_ENDPOINT: dict[str, str] = {
    "default": BASE_PATH + "/listQuery",
    "gen": BASE_PATH + "/listQuery",
    "approved_uninvoiced": BASE_PATH + "/listQueryApprovedUninvoiced",
    "cancel": BASE_PATH + "/listQueryCancel",
    "dept": BASE_PATH + "/listQueryDept",
    "fin": BASE_PATH + "/listQueryFin",
    "final": BASE_PATH + "/listQueryFinal",
    "fin_my": BASE_PATH + "/listQueryFinMY",
    "offsite_trial": BASE_PATH + "/listQueryForOffsiteTrial",
    "invoice": BASE_PATH + "/listQueryInvoice",
    "my": BASE_PATH + "/listQueryMy",
    "my_unreceive": BASE_PATH + "/listQueryMyUnReceive",
    "top10": BASE_PATH + "/listQueryTop10SaleAmt",
    "underway": BASE_PATH + "/listQueryUnderway",
    "unpaid": BASE_PATH + "/listQueryUnpaid",
}

SCOPE_SVARS: dict[str, dict[str, Any]] = {
    "default": {"customerType": 1, "operation": "operation"},
    "gen": {"bstatusProject": 20, "dcProjectEmergencyList": True},
    "my": {"customerType": 3},
    "offsite_trial": {"customerType": 1, "modularType": "modularType"},
}

SCOPE_DATATYPE_DEFAULTS: dict[str, str] = {
    "default": "Last30days",
    "gen": "pendingCaseView",
    "approved_uninvoiced": "Last30days",
    "dept": "Last30days",
    "offsite_trial": "Last30days",
    "my": "Last30days",
}

FILTER_CONFIG: dict[str, dict[str, str]] = {
    "actuality_end_date_end": {"backend_field": "sso.actuality_end_date", "template": "<= '{value} 23:59:59'"},
    "actuality_end_date_start": {"backend_field": "sso.actuality_end_date", "template": ">= '{value}'"},
    "actuality_finish_date_end": {"backend_field": "sso.actuality_finish_date", "template": "<= '{value} 23:59:59'"},
    "actuality_finish_date_start": {"backend_field": "sso.actuality_finish_date", "template": ">= '{value}'"},
    "amt": {"backend_field": "sso.amt_with_tax_local", "template": "= '{value}'"},
    "approve_date_end": {"backend_field": "sso.approve_date", "template": "<= '{value} 23:59:59'"},
    "approve_date_start": {"backend_field": "sso.approve_date", "template": ">= '{value}'"},
    "bstatus": {"backend_field": "sso.bstatus", "template": "= {value}"},
    "bstatus_attachment": {"backend_field": "sso.bstatus_attachment", "template": "= {value}"},
    "bstatus_project": {"backend_field": "sso.bstatus_project", "template": "= {value}"},
    "bstatus_receive": {"backend_field": "sso.bstatus_receive", "template": "= {value}"},
    "cancel_create_on": {"backend_field": "ssorh.approve_on", "template": ">= '{value}'"},
    "cancel_create_on_end": {"backend_field": "ssorh.approve_on", "template": "<= '{value} 23:59:59'"},
    "contract_amount": {"backend_field": "sso.amt_with_tax_local", "template": "= '{value}'"},
    "contract_status": {"backend_field": "sso.bstatus", "template": "= {value}"},
    "create_on": {"backend_field": "createOn", "template": "= '{value}'"},
    "create_on_end": {"backend_field": "sso.create_on", "template": "<= '{value} 23:59:59'"},
    "create_on_start": {"backend_field": "sso.create_on", "template": ">= '{value}'"},
    "customer_name": {"backend_field": "ac.CUSTOMER_NAME_CN", "template": "like '%{value}%'"},
    "customer_name_cn": {"backend_field": "ac.CUSTOMER_NAME_CN", "template": "like '%{value}%'"},
    "customer_short_name": {"backend_field": "ac.CUSTOMER_NAME_CN", "template": "like '%{value}%'"},
    "delivery_specialist": {"backend_field": "ap2.PERSON_NAME", "template": "like '%{value}%'"},
    "department_id": {"backend_field": "ad.department_name", "template": "like '%{value}%'"},
    "dept": {"backend_field": "ad.department_name", "template": "like '%{value}%'"},
    "engineer_name": {"backend_field": "engineerName", "template": "like '%{value}%'"},
    "expense_latest_create_on": {"backend_field": "sso.latest_expense_date", "template": ">= '{value}'"},
    "expense_latest_create_on_end": {"backend_field": "sso.latest_expense_date", "template": "<= '{value} 23:59:59'"},
    "fast_search": {"backend_field": "fastSearch", "template": "like '%{value}%'"},
    "invoice_status": {"backend_field": "sso.invoice_status", "template": "= {value}"},
    "invoiced_amt": {"backend_field": "sso.invoiced_amt", "template": "like '%{value}%'"},
    "kpi_grant_date_end": {"backend_field": "sso.kpi_grant_date", "template": "<= '{value} 23:59:59'"},
    "kpi_grant_date_start": {"backend_field": "sso.kpi_grant_date", "template": ">= '{value}'"},
    "net_profits_ratio_end": {"backend_field": "sso.net_profits_ratio", "template": "<= '{value}'"},
    "order_date_end": {"backend_field": "fai.order_date", "template": "<= '{value} 23:59:59'"},
    "order_date_start": {"backend_field": "fai.order_date", "template": ">= '{value}'"},
    "organization_name": {"backend_field": "ao.organization_name", "template": "like '%{value}%'"},
    "person_id": {"backend_field": "ap.person_name", "template": "like '%{value}%'"},
    "receive_create_on": {"backend_field": "sso.actuality_settlement_date", "template": ">= '{value}'"},
    "receive_create_on_end": {"backend_field": "sso.actuality_settlement_date", "template": "<= '{value} 23:59:59'"},
    "receive_latest_create_on": {"backend_field": "sso.latest_payment_date", "template": ">= '{value}'"},
    "receive_latest_create_on_end": {"backend_field": "sso.latest_payment_date", "template": "<= '{value} 23:59:59'"},
    "rstatus": {"backend_field": "sso.rstatus", "template": "= {value}"},
    "sale_dept": {"backend_field": "ad.department_name", "template": "like '%{value}%'"},
    "sale_person": {"backend_field": "ap.PERSON_NAME", "template": "like '%{value}%'"},
    "sales_date_end": {"backend_field": "sso.sales_date", "template": "<= '{value} 23:59:59'"},
    "sales_date_start": {"backend_field": "sso.sales_date", "template": ">= '{value}'"},
    "sales_dept_name": {"backend_field": "ad.department_name", "template": "like '%{value}%'"},
    "sales_name": {"backend_field": "ap.PERSON_NAME", "template": "like '%{value}%'"},
    "sales_order_no": {"backend_field": "sso.sales_order_no", "template": "like '%{value}%'"},
    "sales_order_type": {"backend_field": "sso.bill_type_id", "template": "= '{value}'"},
    "sales_person": {"backend_field": "ap.person_name", "template": "like '%{value}%'"},
    "sample_model_cn": {"backend_field": "sso.sample_model_cn", "template": "like '%{value}%'"},
    "sample_name_cn": {"backend_field": "sso.sample_name_cn", "template": "like '%{value}%'"},
    "service_item": {"backend_field": "sso.service_item_desc", "template": "like '%{value}%'"},
    "start_date_end": {"backend_field": "sso.start_date", "template": "<= '{value} 23:59:59'"},
    "start_date_start": {"backend_field": "sso.start_date", "template": ">= '{value}'"},
    "terminal_authorization_customer": {"backend_field": "sso.terminal_authorization_customer_name", "template": "like '%{value}%'"},
    "abd_customer_customer_name_cn": {"backend_field": "abdCustomer.customerNameCn", "template": "like '%{value}%'"},
    "actuality_settlement_date_end": {"backend_field": "actualitySettlementDate", "template": "<= '{value} 23:59:59'"},
    "actuality_settlement_date_start": {"backend_field": "actualitySettlementDate", "template": ">= '{value}'"},
    "actually_expenditure_amt": {"backend_field": "actuallyExpenditureAmt", "template": "like '%{value}%'"},
    "actually_expenditure_amt_local": {"backend_field": "actuallyExpenditureAmtLocal", "template": "like '%{value}%'"},
    "actually_net_price_local": {"backend_field": "actuallyNetPriceLocal", "template": "like '%{value}%'"},
    "amt_with_tax": {"backend_field": "amtWithTax", "template": "like '%{value}%'"},
    "amt_with_tax_local": {"backend_field": "amtWithTaxLocal", "template": "like '%{value}%'"},
    "bill_type_id": {"backend_field": "billTypeId", "template": "= '{value}'"},
    "bstatus_kpi": {"backend_field": "bstatusKpi", "template": "= {value}"},
    "cancel_date_end": {"backend_field": "cancelDate", "template": "<= '{value} 23:59:59'"},
    "cancel_date_start": {"backend_field": "cancelDate", "template": ">= '{value}'"},
    "cancel_person_name": {"backend_field": "cancelPersonName", "template": "like '%{value}%'"},
    "complete_invoice_date_end": {"backend_field": "completeInvoiceDate", "template": "<= '{value} 23:59:59'"},
    "complete_invoice_date_start": {"backend_field": "completeInvoiceDate", "template": ">= '{value}'"},
    "create_person_name": {"backend_field": "createPersonName", "template": "like '%{value}%'"},
    "currency_name": {"backend_field": "currencyName", "template": "like '%{value}%'"},
    "deduction_amt_local": {"backend_field": "deductionAmtLocal", "template": "like '%{value}%'"},
    "expect_expenditure_amt_local": {"backend_field": "expectExpenditureAmtLocal", "template": "like '%{value}%'"},
    "invoice_no": {"backend_field": "invoiceNo", "template": "like '%{value}%'"},
    "invoiced_amt_local": {"backend_field": "invoicedAmtLocal", "template": "like '%{value}%'"},
    "latest_expense_date_end": {"backend_field": "latestExpenseDate", "template": "<= '{value} 23:59:59'"},
    "latest_expense_date_start": {"backend_field": "latestExpenseDate", "template": ">= '{value}'"},
    "latest_invoice_date_end": {"backend_field": "latestInvoiceDate", "template": "<= '{value} 23:59:59'"},
    "latest_invoice_date_start": {"backend_field": "latestInvoiceDate", "template": ">= '{value}'"},
    "latest_payment_date_end": {"backend_field": "latestPaymentDate", "template": "<= '{value} 23:59:59'"},
    "latest_payment_date_start": {"backend_field": "latestPaymentDate", "template": ">= '{value}'"},
    "net_profits_ratio": {"backend_field": "netProfitsRatio", "template": "like '%{value}%'"},
    "net_profits_ratio_local": {"backend_field": "netProfitsRatioLocal", "template": "like '%{value}%'"},
    "overdue_settlement": {"backend_field": "overdueSettlement", "template": "like '%{value}%'"},
    "person_name": {"backend_field": "personName", "template": "like '%{value}%'"},
    "receivable_amt": {"backend_field": "receivableAmt", "template": "like '%{value}%'"},
    "receivable_amt_local": {"backend_field": "receivableAmtLocal", "template": "like '%{value}%'"},
    "received_amt": {"backend_field": "receivedAmt", "template": "like '%{value}%'"},
    "received_amt_local": {"backend_field": "receivedAmtLocal", "template": "like '%{value}%'"},
    "remark": {"backend_field": "remark", "template": "like '%{value}%'"},
    "request_invoice_type": {"backend_field": "requestInvoiceType", "template": "= '{value}'"},
    "request_invoiced_amt": {"backend_field": "requestInvoicedAmt", "template": "like '%{value}%'"},
    "revise_desc": {"backend_field": "reviseDesc", "template": "like '%{value}%'"},
    "sale_amt": {"backend_field": "saleAmt", "template": "like '%{value}%'"},
    "service_item_desc": {"backend_field": "serviceItemDesc", "template": "like '%{value}%'"},
    "sum_certificate_amt_local": {"backend_field": "sumCertificateAmtLocal", "template": "like '%{value}%'"},
    "sum_consumable_amt_local": {"backend_field": "sumConsumableAmtLocal", "template": "like '%{value}%'"},
    "sum_net_price2_local": {"backend_field": "sumNetPrice2Local", "template": "like '%{value}%'"},
    "sum_other_amt_local": {"backend_field": "sumOtherAmtLocal", "template": "like '%{value}%'"},
    "sum_outsource_amt_local": {"backend_field": "sumOutsourceAmtLocal", "template": "like '%{value}%'"},
    "tax_amt_local": {"backend_field": "taxAmtLocal", "template": "like '%{value}%'"},
    "terminal_authorization_customer_name": {"backend_field": "terminalAuthorizationCustomerName", "template": "like '%{value}%'"},
    "uninvoiced_amt_local": {"backend_field": "uninvoicedAmtLocal", "template": "like '%{value}%'"},
}

FIELD_LABELS: dict[str, dict[str, str]] = {
    "salesOrderNo": {"key": "sales_order_no", "title": "销售合同号"},
    "rstatus": {"key": "rstatus", "title": "审核状态"},
    "bstatus": {"key": "bstatus", "title": "业务状态"},
    "invoiceStatus": {"key": "invoice_status", "title": "开票状态"},
    "bstatusReceive": {"key": "bstatus_receive", "title": "收款状态"},
    "createOn": {"key": "create_on", "title": "合同日期"},
    "salesDate": {"key": "sales_date", "title": "报价/开单日期"},
    "startDate": {"key": "start_date", "title": "开案日期"},
    "actualityFinishDate": {"key": "actuality_finish_date", "title": "结束日期"},
    "customerNameCn": {"key": "customer_name_cn", "title": "客户名称"},
    "terminalAuthorizationCustomerName": {"key": "terminal_authorization_customer_name", "title": "授权方/终端客"},
    "serviceItemDesc": {"key": "service_item_desc", "title": "合同描述"},
    "sampleNameCn": {"key": "sample_name_cn", "title": "样品名称"},
    "sampleModelCn": {"key": "sample_model_cn", "title": "样品型号"},
    "amtWithTaxLocal": {"key": "amt_with_tax_local", "title": "人民币合同金额"},
    "personName": {"key": "person_name", "title": "销售"},
    "deliverySpecialist": {"key": "delivery_specialist", "title": "交付专员"},
    "departmentName": {"key": "department_name", "title": "部门"},
    "remark": {"key": "remark", "title": "内部备注"},
    "receivedAmtLocal": {"key": "received_amt_local", "title": "人民币已收"},
    "receivableAmtLocal": {"key": "receivable_amt_local", "title": "人民币剩余应收"},
    "requestInvoicedAmt": {"key": "request_invoiced_amt", "title": "已申请金额"},
    "invoicedAmt": {"key": "invoiced_amt", "title": "已开票"},
    "actualityEndDate": {"key": "actuality_end_date", "title": "结案时间"},
    "sumCertificateAmtLocal": {"key": "sum_certificate_amt_local", "title": "规费/发证费总计"},
    "sumOutsourceAmtLocal": {"key": "sum_outsource_amt_local", "title": "外包费总计"},
    "sumConsumableAmtLocal": {"key": "sum_consumable_amt_local", "title": "耗材总计"},
    "sumOtherAmtLocal": {"key": "sum_other_amt_local", "title": "其它支出总计"},
    "taxAmtLocal": {"key": "tax_amt_local", "title": "税费"},
    "sumNetPrice2Local": {"key": "sum_net_price2_local", "title": "净价2总计"},
    "netProfitsRatio": {"key": "net_profits_ratio", "title": "净利润率"},
    "expectExpenditureAmtLocal": {"key": "expect_expenditure_amt_local", "title": "预计支出"},
    "actuallyExpenditureAmtLocal": {"key": "actually_expenditure_amt_local", "title": "实际支出"},
    "latestInvoiceDate": {"key": "latest_invoice_date", "title": "最新开票日期"},
    "latestPaymentDate": {"key": "latest_payment_date", "title": "最新收款日期"},
    "latestExpenseDate": {"key": "latest_expense_date", "title": "最新付款日期"},
}

ENUM_FIELDS: dict[str, dict[Any, str]] = {
    "bstatus": {
        20: "未开案",
        30: "案件进行中",
        40: "结案收款中",
        45: "结案已收款",
        50: "结束",
        60: "取消",
    },
    "bstatus_receive": {
        20: "未收款",
        30: "已收部分款",
        50: "结清",
    },
    "invoice_status": {
        20: "未开票",
        30: "已部分开票",
        50: "开齐票",
        40: "不开票",
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


def _resolve_scope(scope: str | None = None, view: str | None = None) -> str:
    resolved = (scope or view or "default").strip().lower()
    if resolved not in SCOPE_TO_ENDPOINT:
        raise ValueError(
            "不支持的 scope/view 值：{}。可选值：{}".format(
                resolved, ", ".join(sorted(SCOPE_TO_ENDPOINT))
            )
        )
    return resolved


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
    *, scope: str, start: int = 0, limit: int = 10,
    data_type: str | None = None, **filter_values: Any,
) -> dict[str, str]:
    params: dict[str, str] = {
        "start": str(0 if start is None else start),
        "limit": str(10 if limit is None else limit),
    }
    svar_data: dict[str, Any] = {}
    scope_svars = SCOPE_SVARS.get(scope)
    if scope_svars:
        svar_data.update(scope_svars)
    if scope in SCOPE_DATATYPE_DEFAULTS:
        resolved_data_type = data_type or SCOPE_DATATYPE_DEFAULTS[scope]
        svar_data["dataType"] = resolved_data_type
    if svar_data:
        params["sVars"] = json.dumps(svar_data, ensure_ascii=False)
    filter_sql = build_filter(**filter_values)
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


async def query_sales_order_list(
    token: str,
    scope: str = "default",
    view: str | None = None,
    start: int = 0,
    limit: int = 10,
    data_type: str | None = None,
    actuality_end_date_end: str | None = None,
    actuality_end_date_start: str | None = None,
    actuality_finish_date_end: str | None = None,
    actuality_finish_date_start: str | None = None,
    amt: str | None = None,
    approve_date_end: str | None = None,
    approve_date_start: str | None = None,
    bstatus: int | None = None,
    bstatus_attachment: int | None = None,
    bstatus_project: int | None = None,
    bstatus_receive: int | None = None,
    cancel_create_on: str | None = None,
    cancel_create_on_end: str | None = None,
    contract_amount: str | None = None,
    contract_status: int | None = None,
    create_on: str | None = None,
    create_on_end: str | None = None,
    create_on_start: str | None = None,
    customer_name: str | None = None,
    customer_name_cn: str | None = None,
    customer_short_name: str | None = None,
    delivery_specialist: str | None = None,
    department_id: str | None = None,
    dept: str | None = None,
    engineer_name: str | None = None,
    expense_latest_create_on: str | None = None,
    expense_latest_create_on_end: str | None = None,
    fast_search: str | None = None,
    invoice_status: int | None = None,
    invoiced_amt: str | None = None,
    kpi_grant_date_end: str | None = None,
    kpi_grant_date_start: str | None = None,
    net_profits_ratio_end: str | None = None,
    order_date_end: str | None = None,
    order_date_start: str | None = None,
    organization_name: str | None = None,
    person_id: str | None = None,
    receive_create_on: str | None = None,
    receive_create_on_end: str | None = None,
    receive_latest_create_on: str | None = None,
    receive_latest_create_on_end: str | None = None,
    rstatus: int | None = None,
    sale_dept: str | None = None,
    sale_person: str | None = None,
    sales_date_end: str | None = None,
    sales_date_start: str | None = None,
    sales_dept_name: str | None = None,
    sales_name: str | None = None,
    sales_order_no: str | None = None,
    sales_order_type: str | None = None,
    sales_person: str | None = None,
    sample_model_cn: str | None = None,
    sample_name_cn: str | None = None,
    service_item: str | None = None,
    start_date_end: str | None = None,
    start_date_start: str | None = None,
    terminal_authorization_customer: str | None = None,
    abd_customer_customer_name_cn: str | None = None,
    actuality_settlement_date_end: str | None = None,
    actuality_settlement_date_start: str | None = None,
    actually_expenditure_amt: str | None = None,
    actually_expenditure_amt_local: str | None = None,
    actually_net_price_local: str | None = None,
    amt_with_tax: str | None = None,
    amt_with_tax_local: str | None = None,
    bill_type_id: str | None = None,
    bstatus_kpi: int | None = None,
    cancel_date_end: str | None = None,
    cancel_date_start: str | None = None,
    cancel_person_name: str | None = None,
    complete_invoice_date_end: str | None = None,
    complete_invoice_date_start: str | None = None,
    create_person_name: str | None = None,
    currency_name: str | None = None,
    deduction_amt_local: str | None = None,
    expect_expenditure_amt_local: str | None = None,
    invoice_no: str | None = None,
    invoiced_amt_local: str | None = None,
    latest_expense_date_end: str | None = None,
    latest_expense_date_start: str | None = None,
    latest_invoice_date_end: str | None = None,
    latest_invoice_date_start: str | None = None,
    latest_payment_date_end: str | None = None,
    latest_payment_date_start: str | None = None,
    net_profits_ratio: str | None = None,
    net_profits_ratio_local: str | None = None,
    overdue_settlement: str | None = None,
    person_name: str | None = None,
    receivable_amt: str | None = None,
    receivable_amt_local: str | None = None,
    received_amt: str | None = None,
    received_amt_local: str | None = None,
    remark: str | None = None,
    request_invoice_type: str | None = None,
    request_invoiced_amt: str | None = None,
    revise_desc: str | None = None,
    sale_amt: str | None = None,
    service_item_desc: str | None = None,
    sum_certificate_amt_local: str | None = None,
    sum_consumable_amt_local: str | None = None,
    sum_net_price2_local: str | None = None,
    sum_other_amt_local: str | None = None,
    sum_outsource_amt_local: str | None = None,
    tax_amt_local: str | None = None,
    terminal_authorization_customer_name: str | None = None,
    uninvoiced_amt_local: str | None = None,
    include_raw: bool = False,
) -> dict[str, Any]:
    """查询销售合同/销售订单列表。通过 scope/view 路由到 14 个后端列表接口。

    继承自 ListBaseAction，default 包含 /SdSalesOrderListAction/listQuery。
    源码：com.yiuser.lims.sd.sdsalesorder.SdSalesOrderListAction。
    """
    resolved_scope = _resolve_scope(scope=scope, view=view)
    params = build_params(
        scope=resolved_scope, start=start, limit=limit, data_type=data_type,
        actuality_end_date_end=actuality_end_date_end,
        actuality_end_date_start=actuality_end_date_start,
        actuality_finish_date_end=actuality_finish_date_end,
        actuality_finish_date_start=actuality_finish_date_start,
        amt=amt,
        approve_date_end=approve_date_end,
        approve_date_start=approve_date_start,
        bstatus=bstatus,
        bstatus_attachment=bstatus_attachment,
        bstatus_project=bstatus_project,
        bstatus_receive=bstatus_receive,
        cancel_create_on=cancel_create_on,
        cancel_create_on_end=cancel_create_on_end,
        contract_amount=contract_amount,
        contract_status=contract_status,
        create_on=create_on,
        create_on_end=create_on_end,
        create_on_start=create_on_start,
        customer_name=customer_name,
        customer_name_cn=customer_name_cn,
        customer_short_name=customer_short_name,
        delivery_specialist=delivery_specialist,
        department_id=department_id,
        dept=dept,
        engineer_name=engineer_name,
        expense_latest_create_on=expense_latest_create_on,
        expense_latest_create_on_end=expense_latest_create_on_end,
        fast_search=fast_search,
        invoice_status=invoice_status,
        invoiced_amt=invoiced_amt,
        kpi_grant_date_end=kpi_grant_date_end,
        kpi_grant_date_start=kpi_grant_date_start,
        net_profits_ratio_end=net_profits_ratio_end,
        order_date_end=order_date_end,
        order_date_start=order_date_start,
        organization_name=organization_name,
        person_id=person_id,
        receive_create_on=receive_create_on,
        receive_create_on_end=receive_create_on_end,
        receive_latest_create_on=receive_latest_create_on,
        receive_latest_create_on_end=receive_latest_create_on_end,
        rstatus=rstatus,
        sale_dept=sale_dept,
        sale_person=sale_person,
        sales_date_end=sales_date_end,
        sales_date_start=sales_date_start,
        sales_dept_name=sales_dept_name,
        sales_name=sales_name,
        sales_order_no=sales_order_no,
        sales_order_type=sales_order_type,
        sales_person=sales_person,
        sample_model_cn=sample_model_cn,
        sample_name_cn=sample_name_cn,
        service_item=service_item,
        start_date_end=start_date_end,
        start_date_start=start_date_start,
        terminal_authorization_customer=terminal_authorization_customer,
        abd_customer_customer_name_cn=abd_customer_customer_name_cn,
        actuality_settlement_date_end=actuality_settlement_date_end,
        actuality_settlement_date_start=actuality_settlement_date_start,
        actually_expenditure_amt=actually_expenditure_amt,
        actually_expenditure_amt_local=actually_expenditure_amt_local,
        actually_net_price_local=actually_net_price_local,
        amt_with_tax=amt_with_tax,
        amt_with_tax_local=amt_with_tax_local,
        bill_type_id=bill_type_id,
        bstatus_kpi=bstatus_kpi,
        cancel_date_end=cancel_date_end,
        cancel_date_start=cancel_date_start,
        cancel_person_name=cancel_person_name,
        complete_invoice_date_end=complete_invoice_date_end,
        complete_invoice_date_start=complete_invoice_date_start,
        create_person_name=create_person_name,
        currency_name=currency_name,
        deduction_amt_local=deduction_amt_local,
        expect_expenditure_amt_local=expect_expenditure_amt_local,
        invoice_no=invoice_no,
        invoiced_amt_local=invoiced_amt_local,
        latest_expense_date_end=latest_expense_date_end,
        latest_expense_date_start=latest_expense_date_start,
        latest_invoice_date_end=latest_invoice_date_end,
        latest_invoice_date_start=latest_invoice_date_start,
        latest_payment_date_end=latest_payment_date_end,
        latest_payment_date_start=latest_payment_date_start,
        net_profits_ratio=net_profits_ratio,
        net_profits_ratio_local=net_profits_ratio_local,
        overdue_settlement=overdue_settlement,
        person_name=person_name,
        receivable_amt=receivable_amt,
        receivable_amt_local=receivable_amt_local,
        received_amt=received_amt,
        received_amt_local=received_amt_local,
        remark=remark,
        request_invoice_type=request_invoice_type,
        request_invoiced_amt=request_invoiced_amt,
        revise_desc=revise_desc,
        sale_amt=sale_amt,
        service_item_desc=service_item_desc,
        sum_certificate_amt_local=sum_certificate_amt_local,
        sum_consumable_amt_local=sum_consumable_amt_local,
        sum_net_price2_local=sum_net_price2_local,
        sum_other_amt_local=sum_other_amt_local,
        sum_outsource_amt_local=sum_outsource_amt_local,
        tax_amt_local=tax_amt_local,
        terminal_authorization_customer_name=terminal_authorization_customer_name,
        uninvoiced_amt_local=uninvoiced_amt_local,
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
            api_url, headers={"x-access-token": token}, params=params,
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
    "query_sales_order_list": query_sales_order_list,
}

_PROPS: dict[str, dict[str, Any]] = {
    "scope": {
        "type": "string",
        "description": (
            "查询范围：default=全部销售合同 (listQuery/SdSalesOrderListV2.xml), "
            "gen=全部案件 (listQuery/DcProjectEmergencyListV2.xml), "
            "my=我的销售合同 (listQueryMy/SdSalesOrderMyListV2.xml), "
            "dept=部门销售合同 (listQueryDept/SdSalesOrderDeptListV2.xml), "
            "fin=财务销售合同 (listQueryFin/FinSalesOrderListV2.xml), "
            "fin_my=财务我的合同 (listQueryFinMY), "
            "approved_uninvoiced=已审未开票合同 (listQueryApprovedUninvoiced), "
            "cancel=已取消合同 (listQueryCancel), "
            "final=结案合同 (listQueryFinal), "
            "invoice=发票列表 (listQueryInvoice), "
            "offsite_trial=租场试验合同 (listQueryForOffsiteTrial), "
            "my_unreceive=我的未收款合同 (listQueryMyUnReceive), "
            "top10=销售额Top10 (listQueryTop10SaleAmt), "
            "underway=进行中合同 (listQueryUnderway), "
            "unpaid=未付款合同 (listQueryUnpaid)。"
            "default 包含继承的 /SdSalesOrderListAction/listQuery。"
        ),
    },
    "view": {"type": "string", "description": "scope 的别名参数；如同时传入以 scope 为准。"},
    "start": {"type": "integer", "description": "分页起始位置，默认 0。"},
    "limit": {"type": "integer", "description": "每页条数，默认 10。"},
    "data_type": {
        "type": "string",
        "description": (
            "日期筛选视图（sVars.dataType），按 scope 不同。"
            "default=Last30days(最近30天)/listView(全部销售合同)；"
            "gen=pendingCaseView(全部案件)；"
            "my=Last30days(最近30天)/listView(我的销售合同)。"
        ),
    },
}

# Dynamically add all filter properties to avoid repetition
for param, config in FILTER_CONFIG.items():
    _PROPS[param] = {
        "type": "string",
        "description": "filter 字段: {} -> {}。".format(
            param, config["backend_field"]
        ),
    }

# Override key enum field descriptions with detailed enum values
_PROPS["bstatus"] = {
    "type": "integer",
    "description": "业务状态 (bstatus -> sso.bstatus): 20=未开案, 30=案件进行中, 40=结案收款中, 45=结案已收款, 50=结束, 60=取消。枚举 ref_id: com.yiuser.lims.sd.SdSalesOrder.bstatus。",
}
_PROPS["bstatus_attachment"] = {
    "type": "integer",
    "description": "附件状态 (q_bstatusAttachment -> sso.bstatus_attachment): 20=未上传, 30=已上传, 40=已确认。枚举 ref_id: com.yiuser.lims.sd.sdsalesorder.bstatusAttachment。",
}
_PROPS["bstatus_project"] = {
    "type": "integer",
    "description": "开案状态 (bstatusProject -> sso.bstatus_project): 20=未开案, 25=未开始, 30=案件进行中, 40=试验完成报告未出, 45=试验完成报告已出, 50=结案, 55=异常。枚举 ref_id: com.yiuser.lims.sd.sdquotation.bstatusProject。",
}
_PROPS["bstatus_receive"] = {
    "type": "integer",
    "description": "收款状态 (bstatusReceive -> sso.bstatus_receive): 20=未收款, 30=已收部分款, 50=结清。枚举 ref_id: com.yiuser.lims.sd.sdquotation.bstatusReceive。",
}
_PROPS["invoice_status"] = {
    "type": "integer",
    "description": "开票状态 (q_invoiceStatus -> sso.invoice_status): 20=未开票, 30=已部分开票, 50=开齐票, 40=不开票。枚举 ref_id: com.yiuser.lims.sd.sdsalesorder.invoiceStatus。",
}
_PROPS["rstatus"] = {
    "type": "integer",
    "description": "审核状态 (q_rstatus -> sso.rstatus): 0=已作废, 1=已审核, 2=暂存, 3=等待重新审批, 4=审批中。枚举 ref_id: com.yiuser.base.ab.rstatus。",
}
_PROPS["sales_order_type"] = {
    "type": "string",
    "description": "合同类别 (salesOrderType -> sso.bill_type_id): SO-01=服务合同, SO-02=租场试验。枚举 ref_id: com.yiuser.lims.sd.sdquotation.salesOrderType。",
}
_PROPS["contract_status"] = {
    "type": "integer",
    "description": "合同状态 (q_contractStatus -> sso.bstatus): 20=未开案, 30=案件进行中, 40=结案收款中, 45=结案已收款, 50=结束, 60=取消。",
}
_PROPS["bill_type_id"] = {
    "type": "string",
    "description": "合同类别，候选 filter，精确匹配 (billTypeId -> billTypeId): SO-01=服务合同, SO-02=租场试验，置信度：中。",
}
_PROPS["bstatus_kpi"] = {
    "type": "integer",
    "description": "绩效状态，候选 filter (bstatusKpi -> bstatusKpi): 20=未发, 50=已发，置信度：中。",
}

_PROPS["include_raw"] = {
    "type": "boolean",
    "description": "调试用。默认 false；为 true 时才返回后端原始 raw_resultList/raw_response。",
}

TOOL_SCHEMAS = [
    {
        "name": "query_sales_order_list",
        "description": (
            "查询销售合同/销售订单列表。通过 scope/view 路由到 14 个后端列表接口，"
            "继承自 ListBaseAction，default 包含 /SdSalesOrderListAction/listQuery。"
            "暴露第 4 节核心 filter 与第 4.1 节候选 filter，返回 count、columns、data/normalized_data。"
            "源码：com.yiuser.lims.sd.sdsalesorder.SdSalesOrderListAction。"
        ),
        "inputSchema": {"type": "object", "properties": _PROPS},
    },
]
