"""MCP tools for DcProjectListAction DC project list queries."""
from __future__ import annotations

import json
import os
import sys
from typing import Any

import httpx

JAVA_API_BASE = os.environ.get("JAVA_API_BASE", "http://localhost:8080")

SCOPE_TO_ENDPOINT = {
    "default": "/DcProjectListAction/listQueryMyDc",
    "urgent": "/DcProjectListAction/listQueryMyDc",
}

DATA_TYPE_OPTIONS: dict[str, dict[str, str]] = {
    "listView": {
        "title": "我的全部案件",
        "source": "DcMyProjectListV2.xml / SdMyProjectListV2.xml <date_types defaultType>",
    },
    "urgent": {
        "title": "紧急案件",
        "source": "DcMyProjectListV2.xml / SdMyProjectListV2.xml <date_type>",
    },
}

SCOPE_DEFAULT_DATA_TYPE: dict[str, str] = {
    "default": "listView",
    "urgent": "urgent",
}

FILTER_CONFIG: dict[str, dict[str, str]] = {
    # ── 核心筛选（第 4 节） ──
    "apply_certificate_date": {"backend_field": "dp.apply_certificate_date", "template": "= '{value}'"},
    "arrival_date_end": {"backend_field": "dp.arrival_date", "template": "<= '{value} 23:59:59'"},
    "arrival_date_start": {"backend_field": "dp.arrival_date", "template": ">= '{value}'"},
    "assistant_name": {"backend_field": "ap.PERSON_NAME", "template": "like '%{value}%'"},
    "bstatus": {"backend_field": "dp.BSTATUS", "template": "= {value}"},
    "bstatus_project": {"backend_field": "sso.bstatus_project", "template": "= {value}"},
    "closed_date_end": {"backend_field": "dp.closed_date", "template": "<= '{value} 23:59:59'"},
    "closed_date_start": {"backend_field": "dp.closed_date", "template": ">= '{value}'"},
    "delivery_name": {"backend_field": "ap2.PERSON_NAME", "template": "like '%{value}%'"},
    "dept_id": {"backend_field": "dp.dept_id", "template": "= '{value}'"},
    "dm_report_require_report_type": {"backend_field": "drr.report_type", "template": "= '{value}'"},
    "engineer_name": {"backend_field": "ap1.PERSON_NAME", "template": "like '%{value}%'"},
    "fast_search": {"backend_field": "fastSearch", "template": "like '%{value}%'"},
    "finish_date": {"backend_field": "dp.closed_date", "template": "<= '{value} 23:59:59'"},
    "finish_date_end": {"backend_field": "dp.closed_date", "template": "<= '{value} 23:59:59'"},
    "item_category": {"backend_field": "ssod.item_category", "template": "= '{value}'"},
    "organization_name": {"backend_field": "ao.organization_name", "template": "like '%{value}%'"},
    "plan_delivery_date": {"backend_field": "dp.plan_delivery_date", "template": "= '{value}'"},
    "plan_end_date_end": {"backend_field": "dp.plan_end_date", "template": "<= '{value} 23:59:59'"},
    "plan_end_date_start": {"backend_field": "dp.plan_end_date", "template": ">= '{value}'"},
    "product_model": {"backend_field": "sso.sample_model_cn", "template": "like '%{value}%'"},
    "product_name": {"backend_field": "sso.sample_name_cn", "template": "like '%{value}%'"},
    "project_consignor_name": {"backend_field": "ac.CUSTOMER_NAME_CN", "template": "like '%{value}%'"},
    "project_name": {"backend_field": "dp.service_pro_name", "template": "like '%{value}%'"},
    "project_no": {"backend_field": "dp.PROJECT_NO", "template": "like '%{value}%'"},
    "rstatus": {"backend_field": "dp.rstatus", "template": "= {value}"},
    "sales_order_no": {"backend_field": "sso.sales_order_no", "template": "like '%{value}%'"},
    "service_item_desc": {"backend_field": "sso.service_item_desc", "template": "like '%{value}%'"},
    "service_pro_standard": {"backend_field": "dp.service_pro_standard", "template": "like '%{value}%'"},
    "start_up_date": {"backend_field": "dp.CREATE_ON", "template": "<= '{value} 23:59:59'"},
    "start_up_date_end": {"backend_field": "dp.CREATE_ON", "template": "<= '{value} 23:59:59'"},
    "terminal_authorization_customer": {"backend_field": "sso.terminal_authorization_customer_name", "template": "like '%{value}%'"},
    # ── 候选 filter（第 4.1 节） ──
    "actuality_finish_date_end": {"backend_field": "actualityFinishDate", "template": "<= '{value} 23:59:59'"},
    "actuality_finish_date_start": {"backend_field": "actualityFinishDate", "template": ">= '{value}'"},
    "apply_certificate_date_end": {"backend_field": "applyCertificateDate", "template": "<= '{value} 23:59:59'"},
    "apply_certificate_date_start": {"backend_field": "applyCertificateDate", "template": ">= '{value}'"},
    "assignment_date_end": {"backend_field": "assignmentDate", "template": "<= '{value} 23:59:59'"},
    "assignment_date_start": {"backend_field": "assignmentDate", "template": ">= '{value}'"},
    "certificate_amt_local": {"backend_field": "certificateAmtLocal", "template": "like '%{value}%'"},
    "certification_case_type": {"backend_field": "certificationCaseType", "template": "like '%{value}%'"},
    "confirm_standard": {"backend_field": "confirmStandard", "template": "like '%{value}%'"},
    "consumable_amt_local": {"backend_field": "consumableAmtLocal", "template": "like '%{value}%'"},
    "create_on_end": {"backend_field": "createOn", "template": "<= '{value} 23:59:59'"},
    "create_on_start": {"backend_field": "createOn", "template": ">= '{value}'"},
    "customer_level": {"backend_field": "customerLevel", "template": "like '%{value}%'"},
    "day_count": {"backend_field": "dayCount", "template": "like '%{value}%'"},
    "deduction_amt_local": {"backend_field": "deductionAmtLocal", "template": "like '%{value}%'"},
    "delivery_dept_name": {"backend_field": "deliveryDeptName", "template": "like '%{value}%'"},
    "delivery_name2": {"backend_field": "assistantName2", "template": "like '%{value}%'"},
    "department_name": {"backend_field": "departmentName", "template": "like '%{value}%'"},
    "draft_report_date_end": {"backend_field": "draftReportDate", "template": "<= '{value} 23:59:59'"},
    "draft_report_date_start": {"backend_field": "draftReportDate", "template": ">= '{value}'"},
    "end_date_end": {"backend_field": "endDate", "template": "<= '{value} 23:59:59'"},
    "end_date_start": {"backend_field": "endDate", "template": ">= '{value}'"},
    "expiration_reminder": {"backend_field": "expirationReminder", "template": "like '%{value}%'"},
    "external_brand": {"backend_field": "externalBrand", "template": "like '%{value}%'"},
    "external_certificate_agency": {"backend_field": "externalCertificateAgency", "template": "like '%{value}%'"},
    "external_certificate_no": {"backend_field": "externalCertificateNo", "template": "like '%{value}%'"},
    "gross_profit_margin": {"backend_field": "grossProfitMargin", "template": "like '%{value}%'"},
    "manufacturer_name_cn": {"backend_field": "manufacturerNameCn", "template": "like '%{value}%'"},
    "manufacturer_name_en": {"backend_field": "manufacturerNameEn", "template": "like '%{value}%'"},
    "message_notification": {"backend_field": "messageNotification", "template": "like '%{value}%'"},
    "net_price2_local": {"backend_field": "netPrice2Local", "template": "like '%{value}%'"},
    "outsource_amt_local": {"backend_field": "outsourceAmtLocal", "template": "like '%{value}%'"},
    "overdue_days": {"backend_field": "overdueDays", "template": "like '%{value}%'"},
    "plan_delivery_date_end": {"backend_field": "planDeliveryDate", "template": "<= '{value} 23:59:59'"},
    "plan_delivery_date_start": {"backend_field": "planDeliveryDate", "template": ">= '{value}'"},
    "project_progress_history": {"backend_field": "projectProgressHistory", "template": "like '%{value}%'"},
    "report_label": {"backend_field": "actReportType", "template": "like '%{value}%'"},
    "report_nos": {"backend_field": "reportNos", "template": "like '%{value}%'"},
    "sale_amount_with_tax_local": {"backend_field": "saleAmountWithTaxLocal", "template": "like '%{value}%'"},
    "sales_remark": {"backend_field": "salesRemark", "template": "like '%{value}%'"},
    "service_items": {"backend_field": "projectName", "template": "like '%{value}%'"},
    "service_pro_name": {"backend_field": "serviceProName", "template": "like '%{value}%'"},
    "so_distribute_code": {"backend_field": "soDistributeCode", "template": "like '%{value}%'"},
    "start_up_date_start": {"backend_field": "startUpDate", "template": ">= '{value}'"},
    "sum_other_amt_local": {"backend_field": "sumOtherAmtLocal", "template": "like '%{value}%'"},
    "tax_amt_local": {"backend_field": "taxAmtLocal", "template": "like '%{value}%'"},
}

FIELD_LABELS: dict[str, dict[str, str]] = {
    "projectNo": {"key": "project_no", "title": "开案号"},
    "createOn": {"key": "create_on", "title": "创建日期"},
    "organizationName": {"key": "organization_name", "title": "报价公司"},
    "salesOrderNo": {"key": "sales_order_no", "title": "销售合同"},
    "actualityFinishDate": {"key": "actuality_finish_date", "title": "合同结束日期"},
    "departmentName": {"key": "department_name", "title": "负责实验室"},
    "assignmentDate": {"key": "assignment_date", "title": "分配日期"},
    "arrivalDate": {"key": "arrival_date", "title": "开案日期"},
    "engineerName": {"key": "engineer_name", "title": "项目工程师"},
    "projectConsignorName": {"key": "project_consignor_name", "title": "合同方"},
    "expirationReminder": {"key": "expiration_reminder", "title": "到期提醒"},
    "startUpDate": {"key": "start_up_date", "title": "开案日期"},
    "assistantName": {"key": "assistant_name", "title": "销售"},
    "productName": {"key": "product_name", "title": "样品名称"},
    "deliveryName": {"key": "delivery_name", "title": "交付专员"},
    "productModel": {"key": "product_model", "title": "样品型号"},
    "dmReportRequireReportType": {"key": "dm_report_require_report_type", "title": "要求报告标识"},
    "serviceItems": {"key": "service_items", "title": "负责项目"},
    "bstatus": {"key": "bstatus", "title": "案件状态"},
    "terminalAuthorizationCustomer": {"key": "terminal_authorization_customer", "title": "授权终端"},
    "serviceProName": {"key": "service_pro_name", "title": "项目描述"},
    "soDistributeCode": {"key": "so_distribute_code", "title": "项目代码"},
    "itemCategory": {"key": "item_category", "title": "服务类别"},
    "serviceProStandard": {"key": "service_pro_standard", "title": "依据标准库"},
    "reportLabel": {"key": "report_label", "title": "实际报告标识"},
    "projectProgressHistory": {"key": "project_progress_history", "title": "案件进度"},
    "customerLevel": {"key": "customer_level", "title": "客户级别"},
    "messageNotification": {"key": "message_notification", "title": "留言通知"},
    "confirmStandard": {"key": "confirm_standard", "title": "实验室确认标准"},
    "endDate": {"key": "end_date", "title": "实际结案"},
    "planEndDate": {"key": "plan_end_date", "title": "要求结案"},
    "closedDate": {"key": "closed_date", "title": "实际结案"},
    "saleAmountWithTaxLocal": {"key": "sale_amount_with_tax_local", "title": "案件金额"},
    "planDeliveryDate": {"key": "plan_delivery_date", "title": "计划交付日期"},
    "applyCertificateDate": {"key": "apply_certificate_date", "title": "递交申请证书时间"},
    "outsourceAmtLocal": {"key": "outsource_amt_local", "title": "外包费"},
    "salesRemark": {"key": "sales_remark", "title": "内部备注"},
    "overdueDays": {"key": "overdue_days", "title": "逾期天数"},
    "draftReportDate": {"key": "draft_report_date", "title": "草稿报告完成日期"},
    "deliveryName2": {"key": "delivery_name2", "title": "交付专员"},
    "deliveryDeptName": {"key": "delivery_dept_name", "title": "交付部门"},
    "externalCertificateAgency": {"key": "external_certificate_agency", "title": "发证机构"},
    "externalBrand": {"key": "external_brand", "title": "商标"},
    "dayCount": {"key": "day_count", "title": "案件耗时(天)"},
    "externalCertificateNo": {"key": "external_certificate_no", "title": "认证号"},
    "reportNos": {"key": "report_nos", "title": "报告号"},
    "sumOtherAmtLocal": {"key": "sum_other_amt_local", "title": "规费A"},
    "certificationCaseType": {"key": "certification_case_type", "title": "是否认证案件"},
    "manufacturerNameCn": {"key": "manufacturer_name_cn", "title": "制造商(中)"},
    "certificateAmtLocal": {"key": "certificate_amt_local", "title": "规费B"},
    "manufacturerNameEn": {"key": "manufacturer_name_en", "title": "制造商(英)"},
    "consumableAmtLocal": {"key": "consumable_amt_local", "title": "耗材支出"},
    "deductionAmtLocal": {"key": "deduction_amt_local", "title": "税费进项抵扣金额"},
    "taxAmtLocal": {"key": "tax_amt_local", "title": "税费"},
    "netPrice2Local": {"key": "net_price2_local", "title": "净值"},
    "grossProfitMargin": {"key": "gross_profit_margin", "title": "毛利率(%)"},
}

ENUM_FIELDS = {
    "bstatus": {
        2: "未开始",
        3: "进行中",
        1: "试验完成报告未出",
        4: "试验完成报告已出",
        5: "试验暂停中",
        6: "试验终止",
        7: "结案",
        0: "未开案",
        8: "取消",
        9: "未分配",
        10: "实验室退回",
    },
    "bstatus_project": {
        20: "未开案",
        25: "未开始",
        30: "案件进行中",
        40: "试验完成报告未出",
        45: "试验完成报告已出",
        50: "结案",
        55: "异常",
    },
    "dm_report_require_report_type": {
        "not": "无标志",
        "cnas": "CNAS标志",
        "a2la": "A2LA标志",
        "cma": "CMA标志",
        "cnas/a2la": "CNAS+A2LA标志",
        "not/cma": "CNAS+CMA标志",
        "nvlap": "NVLAP标志",
        "cnas/nvlap": "CNAS+NVLAP标志",
        "other": "其它标志",
    },
    "rstatus": {
        0: "已作废",
        1: "已审核",
        2: "暂存",
        3: "等待重新审批",
        4: "审批中",
    },
    "date_enums": {
        "thisYear": "本年度",
        "lastYear": "上年度",
        "thisQuarter": "本季度",
        "lastQuarter": "上季度",
        "thisMonth": "本月",
        "lastMonth": "上月",
        "thisWeek": "本周",
        "lastWeek": "上周",
        "free": "自定义",
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


def _resolve_data_type(scope: str, data_type: str | None = None) -> str | None:
    if data_type:
        return data_type
    return SCOPE_DEFAULT_DATA_TYPE.get(scope)


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
    data_type: str | None = None,
    date_enums: str | None = None,
    finish_date_enums: str | None = None,
    start_up_date_enums: str | None = None,
    **filter_values: Any,
) -> dict[str, str]:
    params = {
        "start": str(0 if start is None else start),
        "limit": str(10 if limit is None else limit),
    }

    s_vars: dict[str, Any] = {}
    resolved_data_type = _resolve_data_type(scope, data_type)
    if resolved_data_type:
        s_vars["dataType"] = resolved_data_type
    if date_enums:
        s_vars["dateEnums"] = date_enums
    if finish_date_enums:
        s_vars["finishDateEnums"] = finish_date_enums
    if start_up_date_enums:
        s_vars["startUpDateEnums"] = start_up_date_enums
    if s_vars:
        params["sVars"] = json.dumps(s_vars, ensure_ascii=False)

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


async def query_dc_project_list(
    token: str,
    scope: str = "default",
    view: str | None = None,
    start: int = 0,
    limit: int = 10,
    # ── 核心筛选（第 4 节） ──
    apply_certificate_date: str | None = None,
    arrival_date_end: str | None = None,
    arrival_date_start: str | None = None,
    assistant_name: str | None = None,
    bstatus: int | None = None,
    bstatus_project: int | None = None,
    closed_date_end: str | None = None,
    closed_date_start: str | None = None,
    date_enums: str | None = None,
    delivery_name: str | None = None,
    dept_id: str | None = None,
    dm_report_require_report_type: str | None = None,
    engineer_name: str | None = None,
    fast_search: str | None = None,
    finish_date: str | None = None,
    finish_date_end: str | None = None,
    finish_date_enums: str | None = None,
    item_category: str | None = None,
    organization_name: str | None = None,
    plan_delivery_date: str | None = None,
    plan_end_date_end: str | None = None,
    plan_end_date_start: str | None = None,
    product_model: str | None = None,
    product_name: str | None = None,
    project_consignor_name: str | None = None,
    project_name: str | None = None,
    project_no: str | None = None,
    rstatus: int | None = None,
    sales_order_no: str | None = None,
    service_item_desc: str | None = None,
    service_pro_standard: str | None = None,
    start_up_date: str | None = None,
    start_up_date_end: str | None = None,
    start_up_date_enums: str | None = None,
    terminal_authorization_customer: str | None = None,
    # ── 候选 filter（第 4.1 节） ──
    actuality_finish_date_end: str | None = None,
    actuality_finish_date_start: str | None = None,
    apply_certificate_date_end: str | None = None,
    apply_certificate_date_start: str | None = None,
    assignment_date_end: str | None = None,
    assignment_date_start: str | None = None,
    certificate_amt_local: str | None = None,
    certification_case_type: str | None = None,
    confirm_standard: str | None = None,
    consumable_amt_local: str | None = None,
    create_on_end: str | None = None,
    create_on_start: str | None = None,
    customer_level: str | None = None,
    day_count: str | None = None,
    deduction_amt_local: str | None = None,
    delivery_dept_name: str | None = None,
    delivery_name2: str | None = None,
    department_name: str | None = None,
    draft_report_date_end: str | None = None,
    draft_report_date_start: str | None = None,
    end_date_end: str | None = None,
    end_date_start: str | None = None,
    expiration_reminder: str | None = None,
    external_brand: str | None = None,
    external_certificate_agency: str | None = None,
    external_certificate_no: str | None = None,
    gross_profit_margin: str | None = None,
    manufacturer_name_cn: str | None = None,
    manufacturer_name_en: str | None = None,
    message_notification: str | None = None,
    net_price2_local: str | None = None,
    outsource_amt_local: str | None = None,
    overdue_days: str | None = None,
    plan_delivery_date_end: str | None = None,
    plan_delivery_date_start: str | None = None,
    project_progress_history: str | None = None,
    report_label: str | None = None,
    report_nos: str | None = None,
    sale_amount_with_tax_local: str | None = None,
    sales_remark: str | None = None,
    service_items: str | None = None,
    service_pro_name: str | None = None,
    so_distribute_code: str | None = None,
    start_up_date_start: str | None = None,
    sum_other_amt_local: str | None = None,
    tax_amt_local: str | None = None,
    data_type: str | None = None,
    include_raw: bool = False,
) -> dict[str, Any]:
    """查询 DC 项目列表，按 scope 路由到默认视图（我的 DC 项目）。"""
    resolved_scope = _resolve_scope(scope=scope, view=view)
    params = build_params(
        scope=resolved_scope,
        start=start,
        limit=limit,
        data_type=data_type,
        date_enums=date_enums,
        finish_date_enums=finish_date_enums,
        start_up_date_enums=start_up_date_enums,
        apply_certificate_date=apply_certificate_date,
        arrival_date_end=arrival_date_end,
        arrival_date_start=arrival_date_start,
        assistant_name=assistant_name,
        bstatus=bstatus,
        bstatus_project=bstatus_project,
        closed_date_end=closed_date_end,
        closed_date_start=closed_date_start,
        delivery_name=delivery_name,
        dept_id=dept_id,
        dm_report_require_report_type=dm_report_require_report_type,
        engineer_name=engineer_name,
        fast_search=fast_search,
        finish_date=finish_date,
        finish_date_end=finish_date_end,
        item_category=item_category,
        organization_name=organization_name,
        plan_delivery_date=plan_delivery_date,
        plan_end_date_end=plan_end_date_end,
        plan_end_date_start=plan_end_date_start,
        product_model=product_model,
        product_name=product_name,
        project_consignor_name=project_consignor_name,
        project_name=project_name,
        project_no=project_no,
        rstatus=rstatus,
        sales_order_no=sales_order_no,
        service_item_desc=service_item_desc,
        service_pro_standard=service_pro_standard,
        start_up_date=start_up_date,
        start_up_date_end=start_up_date_end,
        terminal_authorization_customer=terminal_authorization_customer,
        actuality_finish_date_end=actuality_finish_date_end,
        actuality_finish_date_start=actuality_finish_date_start,
        apply_certificate_date_end=apply_certificate_date_end,
        apply_certificate_date_start=apply_certificate_date_start,
        assignment_date_end=assignment_date_end,
        assignment_date_start=assignment_date_start,
        certificate_amt_local=certificate_amt_local,
        certification_case_type=certification_case_type,
        confirm_standard=confirm_standard,
        consumable_amt_local=consumable_amt_local,
        create_on_end=create_on_end,
        create_on_start=create_on_start,
        customer_level=customer_level,
        day_count=day_count,
        deduction_amt_local=deduction_amt_local,
        delivery_dept_name=delivery_dept_name,
        delivery_name2=delivery_name2,
        department_name=department_name,
        draft_report_date_end=draft_report_date_end,
        draft_report_date_start=draft_report_date_start,
        end_date_end=end_date_end,
        end_date_start=end_date_start,
        expiration_reminder=expiration_reminder,
        external_brand=external_brand,
        external_certificate_agency=external_certificate_agency,
        external_certificate_no=external_certificate_no,
        gross_profit_margin=gross_profit_margin,
        manufacturer_name_cn=manufacturer_name_cn,
        manufacturer_name_en=manufacturer_name_en,
        message_notification=message_notification,
        net_price2_local=net_price2_local,
        outsource_amt_local=outsource_amt_local,
        overdue_days=overdue_days,
        plan_delivery_date_end=plan_delivery_date_end,
        plan_delivery_date_start=plan_delivery_date_start,
        project_progress_history=project_progress_history,
        report_label=report_label,
        report_nos=report_nos,
        sale_amount_with_tax_local=sale_amount_with_tax_local,
        sales_remark=sales_remark,
        service_items=service_items,
        service_pro_name=service_pro_name,
        so_distribute_code=so_distribute_code,
        start_up_date_start=start_up_date_start,
        sum_other_amt_local=sum_other_amt_local,
        tax_amt_local=tax_amt_local,
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
            "data_type": _resolve_data_type(resolved_scope, data_type),
            "params": dict(params),
            "token_masked": _mask_token(token),
        },
        "_filter_config": FILTER_CONFIG,
        "_field_labels": FIELD_LABELS,
        "_enum_fields": ENUM_FIELDS,
        "_data_type_options": DATA_TYPE_OPTIONS,
    }
    if include_raw:
        result["raw_resultList"] = raw_result_list
        result["raw_response"] = payload
    return result


TOOL_HANDLERS = {
    "query_dc_project_list": query_dc_project_list,
}

_PROPERTIES: dict[str, dict[str, Any]] = {
    "scope": {
        "type": "string",
        "description": (
            "视图范围: default=默认列表查询（我的全部案件，dataType=listView），"
            "urgent=紧急案件（dataType=urgent）。"
            "default 包含继承的 /DcProjectListAction/listQueryMyDc。"
        ),
    },
    "view": {"type": "string", "description": "scope 的别名；如同时传入，以 scope 为准。"},
    "start": {"type": "integer", "description": "分页起始位置，默认 0。"},
    "limit": {"type": "integer", "description": "分页条数，默认 10。"},
    # ── 核心筛选（第 4 节） ──
    "apply_certificate_date": {"type": "string", "description": "实际交付日期，精确匹配 (q_applyCertificateDate → dp.apply_certificate_date)。"},
    "arrival_date_end": {"type": "string", "description": "到结束，结束时间 (q_createOnEnd → dp.arrival_date)。"},
    "arrival_date_start": {"type": "string", "description": "从开始，起始时间 (q_createOn → dp.arrival_date)。"},
    "assistant_name": {"type": "string", "description": "销售，模糊匹配 (assistantName → ap.PERSON_NAME)。"},
    "bstatus": {
        "type": "integer",
        "description": (
            "案件状态 (bstatus → dp.BSTATUS): 2=未开始, 3=进行中, "
            "1=试验完成报告未出, 4=试验完成报告已出, 5=试验暂停中, "
            "6=试验终止, 7=结案, 0=未开案, 8=取消, 9=未分配, 10=实验室退回。"
        ),
    },
    "bstatus_project": {
        "type": "integer",
        "description": (
            "合同开案状态 (q_bstatus_project → sso.bstatus_project): "
            "20=未开案, 25=未开始, 30=案件进行中, 40=试验完成报告未出, "
            "45=试验完成报告已出, 50=结案, 55=异常。"
        ),
    },
    "closed_date_end": {"type": "string", "description": "到结束，结束时间 (q_createOnEnd → dp.closed_date)。"},
    "closed_date_start": {"type": "string", "description": "从开始，起始时间 (q_createOn → dp.closed_date)。"},
    "date_enums": {
        "type": "string",
        "description": (
            "日期快捷范围 (dateEnums → dateEnums): "
            "thisYear=本年度, lastYear=上年度, thisQuarter=本季度, "
            "lastQuarter=上季度, thisMonth=本月, lastMonth=上月, "
            "thisWeek=本周, lastWeek=上周, free=自定义。"
        ),
    },
    "delivery_name": {"type": "string", "description": "交付专员，模糊匹配 (deliveryName → ap2.PERSON_NAME)。"},
    "dept_id": {"type": "string", "description": "负责实验室，精确匹配 (deptId → dp.dept_id)。"},
    "dm_report_require_report_type": {
        "type": "string",
        "description": (
            "要求报告标识 (q_dmReportRequireReportType → drr.report_type): "
            "not=无标志, cnas=CNAS标志, a2la=A2LA标志, cma=CMA标志, "
            "cnas/a2la=CNAS+A2LA标志, not/cma=CNAS+CMA标志, "
            "nvlap=NVLAP标志, cnas/nvlap=CNAS+NVLAP标志, other=其它标志。"
        ),
    },
    "engineer_name": {"type": "string", "description": "项目工程师，模糊匹配 (engineerName → ap1.PERSON_NAME)。"},
    "fast_search": {"type": "string", "description": "视图，模糊匹配 (fastSearch → fastSearch)。"},
    "finish_date": {"type": "string", "description": "从，结束时间 (finishDate → dp.closed_date)。"},
    "finish_date_end": {"type": "string", "description": "到结束，结束时间 (finishDateEnd → dp.closed_date)。"},
    "finish_date_enums": {
        "type": "string",
        "description": (
            "结案日期快捷范围 (finishDateEnums → finishDateEnums): "
            "thisYear=本年度, lastYear=上年度, thisQuarter=本季度, "
            "lastQuarter=上季度, thisMonth=本月, lastMonth=上月, "
            "thisWeek=本周, lastWeek=上周, free=自定义。"
        ),
    },
    "item_category": {"type": "string", "description": "服务类别，精确匹配 (q_itemCategory → ssod.item_category)。"},
    "organization_name": {"type": "string", "description": "报价公司，模糊匹配 (q_organizationName → ao.organization_name)。"},
    "plan_delivery_date": {"type": "string", "description": "计划交付日期，精确匹配 (q_planDeliveryDate → dp.plan_delivery_date)。"},
    "plan_end_date_end": {"type": "string", "description": "到结束，结束时间 (q_createOnEnd → dp.plan_end_date)。"},
    "plan_end_date_start": {"type": "string", "description": "从开始，起始时间 (q_createOn → dp.plan_end_date)。"},
    "product_model": {"type": "string", "description": "样品型号，模糊匹配 (productModel → sso.sample_model_cn)。"},
    "product_name": {"type": "string", "description": "样品名称，模糊匹配 (productName → sso.sample_name_cn)。"},
    "project_consignor_name": {"type": "string", "description": "合同方，模糊匹配 (projectConsignorName → ac.CUSTOMER_NAME_CN)。"},
    "project_name": {"type": "string", "description": "负责项目，模糊匹配 (projectName → dp.service_pro_name)。"},
    "project_no": {"type": "string", "description": "开案号，模糊匹配 (projectNo → dp.PROJECT_NO)。"},
    "rstatus": {
        "type": "integer",
        "description": "单据状态 (q_rstatus → dp.rstatus): 0=已作废, 1=已审核, 2=暂存, 3=等待重新审批, 4=审批中。",
    },
    "sales_order_no": {"type": "string", "description": "销售合同，模糊匹配 (salesOrderNo → sso.sales_order_no)。"},
    "service_item_desc": {"type": "string", "description": "服务项目，模糊匹配 (q_serviceItemDesc → sso.service_item_desc)。"},
    "service_pro_standard": {"type": "string", "description": "依据标准库，模糊匹配 (serviceProStandard → dp.service_pro_standard)。"},
    "start_up_date": {"type": "string", "description": "从，结束时间 (startUpDate → dp.CREATE_ON)。"},
    "start_up_date_end": {"type": "string", "description": "到结束，结束时间 (startUpDateEnd → dp.CREATE_ON)。"},
    "start_up_date_enums": {
        "type": "string",
        "description": (
            "开案日期快捷范围 (startUpDateEnums → startUpDateEnums): "
            "thisYear=本年度, lastYear=上年度, thisQuarter=本季度, "
            "lastQuarter=上季度, thisMonth=本月, lastMonth=上月, "
            "thisWeek=本周, lastWeek=上周, free=自定义。"
        ),
    },
    "terminal_authorization_customer": {
        "type": "string",
        "description": "授权终端，模糊匹配 (terminalAuthorizationCustomer → sso.terminal_authorization_customer_name)。",
    },
    # ── 候选 filter（第 4.1 节） ──
    "actuality_finish_date_end": {"type": "string", "description": "合同结束日期结束，候选 filter，结束时间。"},
    "actuality_finish_date_start": {"type": "string", "description": "合同结束日期开始，候选 filter，起始时间。"},
    "apply_certificate_date_end": {"type": "string", "description": "递交申请证书时间结束，候选 filter，结束时间。"},
    "apply_certificate_date_start": {"type": "string", "description": "递交申请证书时间开始，候选 filter，起始时间。"},
    "assignment_date_end": {"type": "string", "description": "分配日期结束，候选 filter，结束时间。"},
    "assignment_date_start": {"type": "string", "description": "分配日期开始，候选 filter，起始时间。"},
    "certificate_amt_local": {"type": "string", "description": "规费B，候选 filter，模糊匹配。"},
    "certification_case_type": {"type": "string", "description": "是否认证案件，候选 filter，模糊匹配。"},
    "confirm_standard": {"type": "string", "description": "实验室确认标准，候选 filter，模糊匹配。"},
    "consumable_amt_local": {"type": "string", "description": "耗材支出，候选 filter，模糊匹配。"},
    "create_on_end": {"type": "string", "description": "创建日期结束，候选 filter，结束时间。"},
    "create_on_start": {"type": "string", "description": "创建日期开始，候选 filter，起始时间。"},
    "customer_level": {"type": "string", "description": "客户级别，候选 filter，模糊匹配。"},
    "day_count": {"type": "string", "description": "案件耗时(天)，候选 filter，模糊匹配。"},
    "deduction_amt_local": {"type": "string", "description": "税费进项抵扣金额，候选 filter，模糊匹配。"},
    "delivery_dept_name": {"type": "string", "description": "交付部门，候选 filter，模糊匹配。"},
    "delivery_name2": {"type": "string", "description": "交付专员，候选 filter，模糊匹配。"},
    "department_name": {"type": "string", "description": "负责实验室，候选 filter，模糊匹配。"},
    "draft_report_date_end": {"type": "string", "description": "草稿报告完成日期结束，候选 filter，结束时间。"},
    "draft_report_date_start": {"type": "string", "description": "草稿报告完成日期开始，候选 filter，起始时间。"},
    "end_date_end": {"type": "string", "description": "实际结案结束，候选 filter，结束时间。"},
    "end_date_start": {"type": "string", "description": "实际结案开始，候选 filter，起始时间。"},
    "expiration_reminder": {"type": "string", "description": "到期提醒，候选 filter，模糊匹配。"},
    "external_brand": {"type": "string", "description": "商标，候选 filter，模糊匹配。"},
    "external_certificate_agency": {"type": "string", "description": "发证机构，候选 filter，模糊匹配。"},
    "external_certificate_no": {"type": "string", "description": "认证号，候选 filter，模糊匹配。"},
    "gross_profit_margin": {"type": "string", "description": "毛利率(%)，候选 filter，模糊匹配。"},
    "manufacturer_name_cn": {"type": "string", "description": "制造商(中)，候选 filter，模糊匹配。"},
    "manufacturer_name_en": {"type": "string", "description": "制造商(英)，候选 filter，模糊匹配。"},
    "message_notification": {"type": "string", "description": "留言通知，候选 filter，模糊匹配。"},
    "net_price2_local": {"type": "string", "description": "净值，候选 filter，模糊匹配。"},
    "outsource_amt_local": {"type": "string", "description": "外包费，候选 filter，模糊匹配。"},
    "overdue_days": {"type": "string", "description": "逾期天数，候选 filter，模糊匹配。"},
    "plan_delivery_date_end": {"type": "string", "description": "计划交付日期结束，候选 filter，结束时间。"},
    "plan_delivery_date_start": {"type": "string", "description": "计划交付日期开始，候选 filter，起始时间。"},
    "project_progress_history": {"type": "string", "description": "案件进度，候选 filter，模糊匹配。"},
    "report_label": {"type": "string", "description": "实际报告标识，候选 filter，模糊匹配。"},
    "report_nos": {"type": "string", "description": "报告号，候选 filter，模糊匹配。"},
    "sale_amount_with_tax_local": {"type": "string", "description": "案件金额，候选 filter，模糊匹配。"},
    "sales_remark": {"type": "string", "description": "内部备注，候选 filter，模糊匹配。"},
    "service_items": {"type": "string", "description": "负责项目，候选 filter，模糊匹配。"},
    "service_pro_name": {"type": "string", "description": "项目描述，候选 filter，模糊匹配。"},
    "so_distribute_code": {"type": "string", "description": "项目代码，候选 filter，模糊匹配。"},
    "start_up_date_start": {"type": "string", "description": "开案日期开始，候选 filter，起始时间。"},
    "sum_other_amt_local": {"type": "string", "description": "规费A，候选 filter，模糊匹配。"},
    "tax_amt_local": {"type": "string", "description": "税费，候选 filter，模糊匹配。"},
    "data_type": {
        "type": "string",
        "description": (
            "可选 sVars.dataType；不传时 default 自动使用 listView。"
            "可选值: listView=我的全部案件, urgent=紧急案件。"
        ),
    },
    "include_raw": {
        "type": "boolean",
        "description": "调试用。默认 false；为 true 时才返回后端原始 raw_resultList/raw_response。",
    },
}

TOOL_SCHEMAS = [
    {
        "name": "query_dc_project_list",
        "description": (
            "查询 DC 项目列表，按 scope 路由到我的全部案件或紧急案件视图。"
            "default 包含继承的 /DcProjectListAction/listQueryMyDc。"
            "返回 count、columns、data/normalized_data。"
        ),
        "inputSchema": {"type": "object", "properties": _PROPERTIES},
    }
]
