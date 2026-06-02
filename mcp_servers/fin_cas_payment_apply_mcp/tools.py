"""MCP tools for FinCasPaymentApplyListAction payment apply queries."""
from __future__ import annotations

import json
import os
import sys
from typing import Any, Dict, List, Optional

import httpx

JAVA_API_BASE = os.environ.get("JAVA_API_BASE", "http://localhost:8080")

SCOPE_TO_ENDPOINT = {
    "default": "/FinCasPaymentApplyListAction/listQuery",
    "emc": "/FinCasPaymentApplyListAction/listQueryEmc",
    "expense": "/FinCasPaymentApplyListAction/listQueryExpense",
    "home": "/FinCasPaymentApplyListAction/listQueryFinCasPaymentApplyHome",
    "home2": "/FinCasPaymentApplyListAction/listQueryFinCasPaymentApplyHome2",
    "home3": "/FinCasPaymentApplyListAction/listQueryFinCasPaymentApplyHome3",
    "home4": "/FinCasPaymentApplyListAction/listQueryFinCasPaymentApplyHome4",
    "gen": "/FinCasPaymentApplyListAction/listQueryGeneralEmc",
    "dept": "/FinCasPaymentApplyListAction/listQueryMyDept",
    "mine": "/FinCasPaymentApplyListAction/listQueryMyPerson",
    "reliability": "/FinCasPaymentApplyListAction/listQueryReliability",
    "rf": "/FinCasPaymentApplyListAction/listQueryRf",
    "safety": "/FinCasPaymentApplyListAction/listQuerySafety",
}

FILTER_CONFIG = {
    "advance_no": {"backend_field": "order_no2", "template": "like '%{value}%'"},
    "amt": {"backend_field": "sum_amt", "template": "= '{value}'"},
    "applicant_name": {"backend_field": "applicantName", "template": "like '%{value}%'"},
    "apply_status": {"backend_field": "rstatus", "template": "= '{value}'"},
    "apply_type": {"backend_field": "apply_type", "template": "= '{value}'"},
    "approve_date_end": {"backend_field": "approve_date", "template": "<= '{value} 23:59:59'"},
    "bstatus": {"backend_field": "bstatus", "template": "= '{value}'"},
    "contract_no": {"backend_field": "sales_order_no", "template": "like '%{value}%'"},
    "customer_name_cn": {"backend_field": "customer_name_cn", "template": "like '%{value}%'"},
    "department_id": {"backend_field": "department_id", "template": "= '{value}'"},
    "description_of_expenditure_content": {"backend_field": "fcpad.description_of_expenditure_content", "template": "like '%{value}%'"},
    "end_time": {"backend_field": "create_on", "template": "<= '{value} 23:59:59'"},
    "expense_course": {"backend_field": "expenseAccount", "template": "like '%{value}%'"},
    "expense_type": {"backend_field": "expenditureCategory", "template": "like '%{value}%'"},
    "fast_search": {"backend_field": "fastSearch", "template": "like '%{value}%'"},
    "offset_rstatus": {"backend_field": "offset_rstatus", "template": "= {value}"},
    "order_no": {"backend_field": "order_no", "template": "like '%{value}%'"},
    "pay_account_name": {"backend_field": "account_name", "template": "like '%{value}%'"},
    "payment_status": {"backend_field": "payment_status", "template": "= '{value}'"},
    "receiver_name": {"backend_field": "receiverName", "template": "like '%{value}%'"},
    "recorder_id": {"backend_field": "personName", "template": "like '%{value}%'"},
    "remark": {"backend_field": "remark", "template": "like '%{value}%'"},
    "start_approve_date": {"backend_field": "approve_date", "template": ">= '{value}'"},
    "start_time": {"backend_field": "create_on", "template": ">= '{value}'"},
    "supplier_name": {"backend_field": "supplier_name", "template": "like '%{value}%'"},
    "amt_local": {"backend_field": "amtLocal", "template": "like '%{value}%'"},
    "approve_date_start": {"backend_field": "approveDate", "template": ">= '{value}'"},
    "create_on_end": {"backend_field": "createOn", "template": "<= '{value} 23:59:59'"},
    "create_on_start": {"backend_field": "createOn", "template": ">= '{value}'"},
    "expenditure_category": {"backend_field": "expenditureCategory", "template": "like '%{value}%'"},
    "expense_account": {"backend_field": "expenseAccount", "template": "like '%{value}%'"},
    "expense_item_type": {"backend_field": "expenseItemType", "template": "= '{value}'"},
    "item_name": {"backend_field": "itemName", "template": "like '%{value}%'"},
    "order_no2": {"backend_field": "orderNo2", "template": "like '%{value}%'"},
    "payment_amt_local": {"backend_field": "paymentAmtLocal", "template": "like '%{value}%'"},
    "person_name": {"backend_field": "personName", "template": "like '%{value}%'"},
    "project_no": {"backend_field": "projectNo", "template": "like '%{value}%'"},
    "receive_acctnumber": {"backend_field": "receiveAcctnumber", "template": "like '%{value}%'"},
    "receive_bank_name": {"backend_field": "receiveBankName", "template": "like '%{value}%'"},
    "rstatus": {"backend_field": "rstatus", "template": "= '{value}'"},
    "sales_order_no": {"backend_field": "salesOrderNo", "template": "like '%{value}%'"},
    "sales_order_rstatus": {"backend_field": "salesOrderRstatus", "template": "= '{value}'"},
    "unpayment_amt_local": {"backend_field": "unpaymentAmtLocal", "template": "like '%{value}%'"},
}

FIELD_LABELS = {
    "orderNo": {"key": "order_no", "title": "申请编号"},
    "createOn": {"key": "create_on", "title": "申请日期"},
    "rstatus": {"key": "rstatus", "title": "审核状态"},
    "salesOrderRstatus": {"key": "sales_order_rstatus", "title": "合同审核状态"},
    "approveDate": {"key": "approve_date", "title": "审核日期"},
    "personName": {"key": "person_name", "title": "制单人"},
    "salesOrderNo": {"key": "sales_order_no", "title": "合同编号"},
    "applicantName": {"key": "applicant_name", "title": "费用申请人"},
    "departmentName": {"key": "department_name", "title": "申请部门"},
    "orderNo2": {"key": "order_no2", "title": "预支编号"},
    "applyType": {"key": "apply_type", "title": "申请类别"},
    "customerNameCn": {"key": "customer_name_cn", "title": "客户名称"},
    "projectNo": {"key": "project_no", "title": "案件号"},
    "descriptionOfExpenditureContent": {"key": "description_of_expenditure_content", "title": "预支内容"},
    "amt": {"key": "amt", "title": "申请金额"},
    "supplierName": {"key": "supplier_name", "title": "供应商/收款方"},
    "expenditureCategory": {"key": "expenditure_category", "title": "支出类别"},
    "paymentStatus": {"key": "payment_status", "title": "付款状态"},
    "itemName": {"key": "item_name", "title": "服务项目"},
    "amtLocal": {"key": "amt_local", "title": "人民币申请金额"},
    "expenseAccount": {"key": "expense_account", "title": "支出科目"},
    "receiverName": {"key": "receiver_name", "title": "收款方"},
    "receiveAcctnumber": {"key": "receive_acctnumber", "title": "收款方账号"},
    "bstatus": {"key": "bstatus", "title": "报销状态"},
    "paymentAmtLocal": {"key": "payment_amt_local", "title": "人民币已付款金额"},
    "receiveBankName": {"key": "receive_bank_name", "title": "收款方开户行"},
    "remark": {"key": "remark", "title": "备注"},
    "offsetRstatus": {"key": "offset_rstatus", "title": "还款/冲账状态"},
    "expenseItemType": {"key": "expense_item_type", "title": "支出类别"},
    "unpaymentAmtLocal": {"key": "unpayment_amt_local", "title": "人民币待付款金额"},
}

ENUM_FIELDS = {
    "apply_type": {
        10: "有发票报销付款",
        20: "无发票报销付款",
        30: "借款付款",
    },
    "bstatus": {
        1: "未报销",
        2: "已报销",
    },
    "expense_item_type": {
        "sd-certificate-a": "规费B/发证费",
        "sd-outsource": "外包",
        "sd-consumable": "其它耗材",
        "sd-other": "规费A",
    },
    "offset_rstatus": {
        2: "已部分还款/冲账",
        1: "已还款/冲账",
        0: "未还款/未冲账",
        -1: "N/A",
    },
    "payment_status": {
        10: "未付款",
        20: "部分付款",
        30: "已付款",
    },
    "rstatus": {
        0: "已作废",
        1: "已审核",
        2: "暂存",
        3: "等待重新审批",
        4: "审批中",
    },
    "sales_order_rstatus": {
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
    advance_no: Optional[str] = None,
    amt: Optional[str] = None,
    applicant_name: Optional[str] = None,
    apply_status: Optional[int] = None,
    apply_type: Optional[int] = None,
    approve_date_end: Optional[str] = None,
    bstatus: Optional[str] = None,
    contract_no: Optional[str] = None,
    customer_name_cn: Optional[str] = None,
    department_id: Optional[str] = None,
    description_of_expenditure_content: Optional[str] = None,
    end_time: Optional[str] = None,
    expense_course: Optional[str] = None,
    expense_type: Optional[str] = None,
    fast_search: Optional[str] = None,
    offset_rstatus: Optional[int] = None,
    order_no: Optional[str] = None,
    pay_account_name: Optional[str] = None,
    payment_status: Optional[str] = None,
    receiver_name: Optional[str] = None,
    recorder_id: Optional[str] = None,
    remark: Optional[str] = None,
    start_approve_date: Optional[str] = None,
    start_time: Optional[str] = None,
    supplier_name: Optional[str] = None,
    amt_local: Optional[str] = None,
    approve_date_start: Optional[str] = None,
    create_on_end: Optional[str] = None,
    create_on_start: Optional[str] = None,
    expenditure_category: Optional[str] = None,
    expense_account: Optional[str] = None,
    expense_item_type: Optional[str] = None,
    item_name: Optional[str] = None,
    order_no2: Optional[str] = None,
    payment_amt_local: Optional[str] = None,
    person_name: Optional[str] = None,
    project_no: Optional[str] = None,
    receive_acctnumber: Optional[str] = None,
    receive_bank_name: Optional[str] = None,
    rstatus: Optional[int] = None,
    sales_order_no: Optional[str] = None,
    sales_order_rstatus: Optional[int] = None,
    unpayment_amt_local: Optional[str] = None,
) -> Optional[str]:
    values = {
        "advance_no": advance_no,
        "amt": amt,
        "applicant_name": applicant_name,
        "apply_status": apply_status,
        "apply_type": apply_type,
        "approve_date_end": approve_date_end,
        "bstatus": bstatus,
        "contract_no": contract_no,
        "customer_name_cn": customer_name_cn,
        "department_id": department_id,
        "description_of_expenditure_content": description_of_expenditure_content,
        "end_time": end_time,
        "expense_course": expense_course,
        "expense_type": expense_type,
        "fast_search": fast_search,
        "offset_rstatus": offset_rstatus,
        "order_no": order_no,
        "pay_account_name": pay_account_name,
        "payment_status": payment_status,
        "receiver_name": receiver_name,
        "recorder_id": recorder_id,
        "remark": remark,
        "start_approve_date": start_approve_date,
        "start_time": start_time,
        "supplier_name": supplier_name,
        "amt_local": amt_local,
        "approve_date_start": approve_date_start,
        "create_on_end": create_on_end,
        "create_on_start": create_on_start,
        "expenditure_category": expenditure_category,
        "expense_account": expense_account,
        "expense_item_type": expense_item_type,
        "item_name": item_name,
        "order_no2": order_no2,
        "payment_amt_local": payment_amt_local,
        "person_name": person_name,
        "project_no": project_no,
        "receive_acctnumber": receive_acctnumber,
        "receive_bank_name": receive_bank_name,
        "rstatus": rstatus,
        "sales_order_no": sales_order_no,
        "sales_order_rstatus": sales_order_rstatus,
        "unpayment_amt_local": unpayment_amt_local,
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


def _resolve_svars(user_svars: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    if not user_svars:
        return None
    return dict(user_svars)


def build_params(
    *,
    scope: str,
    start: int = 0,
    limit: int = 10,
    advance_no: Optional[str] = None,
    amt: Optional[str] = None,
    applicant_name: Optional[str] = None,
    apply_status: Optional[int] = None,
    apply_type: Optional[int] = None,
    approve_date_end: Optional[str] = None,
    bstatus: Optional[str] = None,
    contract_no: Optional[str] = None,
    customer_name_cn: Optional[str] = None,
    department_id: Optional[str] = None,
    description_of_expenditure_content: Optional[str] = None,
    end_time: Optional[str] = None,
    expense_course: Optional[str] = None,
    expense_type: Optional[str] = None,
    fast_search: Optional[str] = None,
    offset_rstatus: Optional[int] = None,
    order_no: Optional[str] = None,
    pay_account_name: Optional[str] = None,
    payment_status: Optional[str] = None,
    receiver_name: Optional[str] = None,
    recorder_id: Optional[str] = None,
    remark: Optional[str] = None,
    start_approve_date: Optional[str] = None,
    start_time: Optional[str] = None,
    supplier_name: Optional[str] = None,
    amt_local: Optional[str] = None,
    approve_date_start: Optional[str] = None,
    create_on_end: Optional[str] = None,
    create_on_start: Optional[str] = None,
    expenditure_category: Optional[str] = None,
    expense_account: Optional[str] = None,
    expense_item_type: Optional[str] = None,
    item_name: Optional[str] = None,
    order_no2: Optional[str] = None,
    payment_amt_local: Optional[str] = None,
    person_name: Optional[str] = None,
    project_no: Optional[str] = None,
    receive_acctnumber: Optional[str] = None,
    receive_bank_name: Optional[str] = None,
    rstatus: Optional[int] = None,
    sales_order_no: Optional[str] = None,
    sales_order_rstatus: Optional[int] = None,
    unpayment_amt_local: Optional[str] = None,
    sVars: Optional[Dict[str, Any]] = None,
) -> Dict[str, str]:
    params = {
        "start": str(0 if start is None else start),
        "limit": str(10 if limit is None else limit),
    }
    resolved_sVars = _resolve_svars(sVars)
    if resolved_sVars is not None:
        params["sVars"] = json.dumps(resolved_sVars, ensure_ascii=False)

    filter_sql = build_filter(
        advance_no=advance_no,
        amt=amt,
        applicant_name=applicant_name,
        apply_status=apply_status,
        apply_type=apply_type,
        approve_date_end=approve_date_end,
        bstatus=bstatus,
        contract_no=contract_no,
        customer_name_cn=customer_name_cn,
        department_id=department_id,
        description_of_expenditure_content=description_of_expenditure_content,
        end_time=end_time,
        expense_course=expense_course,
        expense_type=expense_type,
        fast_search=fast_search,
        offset_rstatus=offset_rstatus,
        order_no=order_no,
        pay_account_name=pay_account_name,
        payment_status=payment_status,
        receiver_name=receiver_name,
        recorder_id=recorder_id,
        remark=remark,
        start_approve_date=start_approve_date,
        start_time=start_time,
        supplier_name=supplier_name,
        amt_local=amt_local,
        approve_date_start=approve_date_start,
        create_on_end=create_on_end,
        create_on_start=create_on_start,
        expenditure_category=expenditure_category,
        expense_account=expense_account,
        expense_item_type=expense_item_type,
        item_name=item_name,
        order_no2=order_no2,
        payment_amt_local=payment_amt_local,
        person_name=person_name,
        project_no=project_no,
        receive_acctnumber=receive_acctnumber,
        receive_bank_name=receive_bank_name,
        rstatus=rstatus,
        sales_order_no=sales_order_no,
        sales_order_rstatus=sales_order_rstatus,
        unpayment_amt_local=unpayment_amt_local,
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


async def query_fincaspaymentapplylistaction(
    token: str,
    scope: str = "default",
    view: Optional[str] = None,
    start: int = 0,
    limit: int = 10,
    advance_no: Optional[str] = None,
    amt: Optional[str] = None,
    applicant_name: Optional[str] = None,
    apply_status: Optional[int] = None,
    apply_type: Optional[int] = None,
    approve_date_end: Optional[str] = None,
    approve_date_enums: Optional[str] = None,
    bstatus: Optional[str] = None,
    contract_no: Optional[str] = None,
    customer_name_cn: Optional[str] = None,
    department_id: Optional[str] = None,
    description_of_expenditure_content: Optional[str] = None,
    end_time: Optional[str] = None,
    expense_course: Optional[str] = None,
    expense_type: Optional[str] = None,
    fast_search: Optional[str] = None,
    offset_rstatus: Optional[int] = None,
    order_no: Optional[str] = None,
    pay_account_name: Optional[str] = None,
    payment_status: Optional[str] = None,
    receiver_name: Optional[str] = None,
    recorder_id: Optional[str] = None,
    remark: Optional[str] = None,
    start_approve_date: Optional[str] = None,
    start_time: Optional[str] = None,
    supplier_name: Optional[str] = None,
    amt_local: Optional[str] = None,
    approve_date_start: Optional[str] = None,
    create_on_end: Optional[str] = None,
    create_on_start: Optional[str] = None,
    expenditure_category: Optional[str] = None,
    expense_account: Optional[str] = None,
    expense_item_type: Optional[str] = None,
    item_name: Optional[str] = None,
    order_no2: Optional[str] = None,
    payment_amt_local: Optional[str] = None,
    person_name: Optional[str] = None,
    project_no: Optional[str] = None,
    receive_acctnumber: Optional[str] = None,
    receive_bank_name: Optional[str] = None,
    rstatus: Optional[int] = None,
    sales_order_no: Optional[str] = None,
    sales_order_rstatus: Optional[int] = None,
    unpayment_amt_local: Optional[str] = None,
    sVars: Optional[Dict[str, Any]] = None,
    include_raw: bool = False,
) -> Dict[str, Any]:
    """查询付款申请列表，按 scope 路由到文档列出的 listQuery* 视图。"""
    resolved_scope = _resolve_scope(scope=scope, view=view)
    params = build_params(
        scope=resolved_scope,
        start=start,
        limit=limit,
        advance_no=advance_no,
        amt=amt,
        applicant_name=applicant_name,
        apply_status=apply_status,
        apply_type=apply_type,
        approve_date_end=approve_date_end,
        bstatus=bstatus,
        contract_no=contract_no,
        customer_name_cn=customer_name_cn,
        department_id=department_id,
        description_of_expenditure_content=description_of_expenditure_content,
        end_time=end_time,
        expense_course=expense_course,
        expense_type=expense_type,
        fast_search=fast_search,
        offset_rstatus=offset_rstatus,
        order_no=order_no,
        pay_account_name=pay_account_name,
        payment_status=payment_status,
        receiver_name=receiver_name,
        recorder_id=recorder_id,
        remark=remark,
        start_approve_date=start_approve_date,
        start_time=start_time,
        supplier_name=supplier_name,
        amt_local=amt_local,
        approve_date_start=approve_date_start,
        create_on_end=create_on_end,
        create_on_start=create_on_start,
        expenditure_category=expenditure_category,
        expense_account=expense_account,
        expense_item_type=expense_item_type,
        item_name=item_name,
        order_no2=order_no2,
        payment_amt_local=payment_amt_local,
        person_name=person_name,
        project_no=project_no,
        receive_acctnumber=receive_acctnumber,
        receive_bank_name=receive_bank_name,
        rstatus=rstatus,
        sales_order_no=sales_order_no,
        sales_order_rstatus=sales_order_rstatus,
        unpayment_amt_local=unpayment_amt_local,
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
    "query_fincaspaymentapplylistaction": query_fincaspaymentapplylistaction,
    "query_fin_cas_payment_apply_list": query_fincaspaymentapplylistaction,
}

TOOL_SCHEMAS = [
    {
        "name": "query_fincaspaymentapplylistaction",
        "description": (
            "查询付款申请列表。通过 scope/view 路由到默认、EMC、费用、首页、GEN、部门、我的、可靠性、RF、安全等 13 个视图，"
            "默认视图包含继承自 ListBaseAction 的 /FinCasPaymentApplyListAction/listQuery。"
            "default scope 自动注入 operation=operation 的 sVar。"
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "scope": {
                    "type": "string",
                    "description": (
                        "视图范围：default=默认列表（listQuery），"
                        "emc=EMC 业务视图（listQueryEmc），"
                        "expense=费用视图（listQueryExpense），"
                        "home=首页视图（listQueryFinCasPaymentApplyHome），"
                        "home2=首页视图2（listQueryFinCasPaymentApplyHome2），"
                        "home3=首页视图3（listQueryFinCasPaymentApplyHome3），"
                        "home4=首页视图4（listQueryFinCasPaymentApplyHome4），"
                        "gen=通用 EMC 视图（listQueryGeneralEmc），"
                        "dept=部门范围视图（listQueryMyDept），"
                        "mine=我的数据视图（listQueryMyPerson），"
                        "reliability=可靠性视图（listQueryReliability），"
                        "rf=RF 业务视图（listQueryRf），"
                        "safety=安全业务视图（listQuerySafety）。"
                    ),
                },
                "view": {"type": "string", "description": "scope 的别名；如同时传入，以 scope 为准。"},
                "start": {"type": "integer", "description": "分页起始位置，默认 0。"},
                "limit": {"type": "integer", "description": "分页条数，默认 10。"},
                "advance_no": {"type": "string", "description": "预支编号，模糊匹配 (q_advanceNo -> order_no2)。"},
                "amt": {"type": "string", "description": "原币总计申请金额，精确匹配 (amt -> sum_amt)。"},
                "applicant_name": {"type": "string", "description": "费用申请人，模糊匹配 (q_applicantName -> applicantName)。"},
                "apply_status": {
                    "type": "integer",
                    "description": "申请状态，精确匹配 (q_applyStatus -> rstatus)：0=已作废, 1=已审核, 2=暂存, 3=等待重新审批, 4=审批中。",
                },
                "apply_type": {
                    "type": "integer",
                    "description": "申请类别，精确匹配 (q_applyType -> apply_type)：10=有发票报销付款, 20=无发票报销付款, 30=借款付款。",
                },
                "approve_date_end": {"type": "string", "description": "审核日期结束，格式 YYYY-MM-DD (approveDateEnd -> approve_date, <= 23:59:59)。"},
                "approve_date_enums": {
                    "type": "string",
                    "description": "审核日期快捷筛选 (approveDateEnums -> approveDateEnums)：thisYear=本年度, lastYear=上年度, thisQuarter=本季度, lastQuarter=上季度, thisMonth=本月, lastMonth=上月, thisWeek=本周, lastWeek=上周, free=自定义。",
                },
                "bstatus": {
                    "type": "string",
                    "description": "报销状态，精确匹配 (q_bstatus -> bstatus)：1=未报销, 2=已报销。",
                },
                "contract_no": {"type": "string", "description": "合同/项目编号，模糊匹配 (q_contractNo -> sales_order_no)。"},
                "customer_name_cn": {"type": "string", "description": "客户名称，模糊匹配 (customerNameCn -> customer_name_cn)。"},
                "department_id": {"type": "string", "description": "申请部门，精确匹配 (q_departmentId -> department_id)。"},
                "description_of_expenditure_content": {"type": "string", "description": "预支内容，模糊匹配 (descriptionOfExpenditureContent -> fcpad.description_of_expenditure_content)。"},
                "end_time": {"type": "string", "description": "申请日期结束，格式 YYYY-MM-DD (endTime -> create_on, <= 23:59:59)。"},
                "expense_course": {"type": "string", "description": "支出科目，模糊匹配 (q_expenseCourse -> expenseAccount)。"},
                "expense_type": {"type": "string", "description": "父级科目，模糊匹配 (q_expenseType -> expenditureCategory)。"},
                "fast_search": {"type": "string", "description": "快速搜索词，模糊匹配 (fastSearch -> fastSearch)。"},
                "offset_rstatus": {
                    "type": "integer",
                    "description": "还款/冲账状态，精确匹配 (q_offsetRstatus -> offset_rstatus)：2=已部分还款/冲账, 1=已还款/冲账, 0=未还款/未冲账, -1=N/A。",
                },
                "order_no": {"type": "string", "description": "申请编号，模糊匹配 (q_orderNo -> order_no)。"},
                "pay_account_name": {"type": "string", "description": "账户名称，模糊匹配 (q_payAccountName -> account_name)。"},
                "payment_status": {
                    "type": "string",
                    "description": "付款状态，精确匹配 (q_paymentStatus -> payment_status)：10=未付款, 20=部分付款, 30=已付款。",
                },
                "receiver_name": {"type": "string", "description": "收款方，模糊匹配 (q_receiverName -> receiverName)。"},
                "recorder_id": {"type": "string", "description": "申请人，模糊匹配 (q_recorderId -> personName)。"},
                "remark": {"type": "string", "description": "备注，模糊匹配 (remark -> remark)。"},
                "start_approve_date": {"type": "string", "description": "审核日期开始，格式 YYYY-MM-DD (startApproveDate -> approve_date, >=)。"},
                "start_time": {"type": "string", "description": "申请日期开始，格式 YYYY-MM-DD (startTime -> create_on, >=)。"},
                "supplier_name": {"type": "string", "description": "供应商/收款方，模糊匹配 (supplierName -> supplier_name)。"},
                "amt_local": {"type": "string", "description": "人民币申请金额候选字段，模糊匹配 (amtLocal -> amtLocal)。"},
                "approve_date_start": {"type": "string", "description": "审核日期开始候选字段，格式 YYYY-MM-DD (approveDate -> approveDate, >=)。"},
                "create_on_end": {"type": "string", "description": "申请日期结束候选字段，格式 YYYY-MM-DD (createOn -> createOn, <= 23:59:59)。"},
                "create_on_start": {"type": "string", "description": "申请日期开始候选字段，格式 YYYY-MM-DD (createOn -> createOn, >=)。"},
                "expenditure_category": {"type": "string", "description": "支出类别候选字段，模糊匹配 (expenditureCategory -> expenditureCategory)。"},
                "expense_account": {"type": "string", "description": "支出科目候选字段，模糊匹配 (expenseAccount -> expenseAccount)。"},
                "expense_item_type": {
                    "type": "string",
                    "description": "支出类别候选字段，精确匹配 (expenseItemType -> expenseItemType)：sd-certificate-a=规费B/发证费, sd-outsource=外包, sd-consumable=其它耗材, sd-other=规费A。",
                },
                "item_name": {"type": "string", "description": "服务项目候选字段，模糊匹配 (itemName -> itemName)。"},
                "order_no2": {"type": "string", "description": "预支编号候选字段，模糊匹配 (orderNo2 -> orderNo2)。"},
                "payment_amt_local": {"type": "string", "description": "人民币已付款金额候选字段，模糊匹配 (paymentAmtLocal -> paymentAmtLocal)。"},
                "person_name": {"type": "string", "description": "制单人候选字段，模糊匹配 (personName -> personName)。"},
                "project_no": {"type": "string", "description": "案件号候选字段，模糊匹配 (projectNo -> projectNo)。"},
                "receive_acctnumber": {"type": "string", "description": "收款方账号候选字段，模糊匹配 (receiveAcctnumber -> receiveAcctnumber)。"},
                "receive_bank_name": {"type": "string", "description": "收款方开户行候选字段，模糊匹配 (receiveBankName -> receiveBankName)。"},
                "rstatus": {
                    "type": "integer",
                    "description": "审核状态候选字段，精确匹配 (rstatus -> rstatus)：0=已作废, 1=已审核, 2=暂存, 3=等待重新审批, 4=审批中。",
                },
                "sales_order_no": {"type": "string", "description": "合同编号候选字段，模糊匹配 (salesOrderNo -> salesOrderNo)。"},
                "sales_order_rstatus": {
                    "type": "integer",
                    "description": "合同审核状态候选字段，精确匹配 (salesOrderRstatus -> salesOrderRstatus)：0=已作废, 1=已审核, 2=暂存, 3=等待重新审批, 4=审批中。",
                },
                "unpayment_amt_local": {"type": "string", "description": "人民币待付款金额候选字段，模糊匹配 (unpaymentAmtLocal -> unpaymentAmtLocal)。"},
                "sVars": {
                    "type": "object",
                    "description": (
                        "自定义 sVars 负载。文档第 7 节未发现默认 sVars/dataType 注入值，"
                        "因此不自动注入任何默认值。用户传入的 sVars 会原样发送到后端。"
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
