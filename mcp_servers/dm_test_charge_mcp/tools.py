"""MCP tools for DmTestChargeListAction charge list queries."""
from __future__ import annotations

import json
import os
import sys
from typing import Any, Dict, Optional

import httpx

JAVA_API_BASE = os.environ.get("JAVA_API_BASE", "http://localhost:8080")

SCOPE_TO_ENDPOINT = {
    "default": "/DmTestChargeListAction/listQuery",
    "all": "/DmTestChargeListAction/listQueryAll",
    "gen": "/DmTestChargeListAction/listQueryGen",
    "project": "/DmTestChargeListAction/listQueryProject",
    "rf": "/DmTestChargeListAction/listQueryRf",
    "sso": "/DmTestChargeListAction/listQuerySSO",
    "temp": "/DmTestChargeListAction/listQueryTemp",
    "temp_rf": "/DmTestChargeListAction/listQueryTempRf",
}

SCOPE_DEFAULT_SVARS: Dict[str, Dict[str, str]] = {
    "default": {"operation": "operation", "showAmount": "showAmount"},
}

# ── dataType: 仅按文档第 7 节来源处理 ─────────────────────────────────
SCOPE_DEFAULT_DATA_TYPE: Dict[str, str] = {
    "default": "mainView",
    "all": "weekView",
    "rf": "mainView",
}

_DATA_TYPE_RESOURCES: Dict[str, Dict[str, str]] = {
    "default": {
        "allView": "所有收费单记录",
        "dayView": "当日收费单记录",
        "weekView": "本周收费单记录",
    },
    "all": {
        "allView": "所有收费单",
        "lastWeekView": "上周收费单",
        "monthView": "本月收费单",
        "lastMonthView": "上月收费单",
        "weekView": "本周收费单",
    },
    "rf": {
        "allView": "所有收费单记录",
        "dayView": "当日收费单记录",
        "weekView": "本周收费单记录",
    },
}

# ── filter field mapping (第 4 节 + 第 4.1 节) ──────────────────────
FILTER_CONFIG: Dict[str, Dict[str, str]] = {
    # ── 第 4 节：查询字段（q_condition 来源） ──
    "bstatus": {"backend_field": "dtc.bstatus", "template": "= '{value}'"},
    "charge_no": {"backend_field": "charge_no", "template": "like '%{value}%'"},
    "contract_no": {"backend_field": "sso.sales_order_no", "template": "like '%{value}%'"},
    "customer_name": {"backend_field": "tcp.consignor_name_cn", "template": "like '%{value}%'"},
    "entrusted_project_no": {"backend_field": "dp.project_no", "template": "like '%{value}%'"},
    "fast_search": {"backend_field": "fastSearch", "template": "like '%{value}%'"},
    "item_no": {"backend_field": "tcp.project_no", "template": "like '%{value}%'"},
    "modular_type": {"backend_field": "dtc.modular_type", "template": "= '{value}'"},
    "order_date": {"backend_field": "order_date", "template": "= '{value}'"},
    "order_date2": {"backend_field": "order_date", "template": "= '{value}'"},
    "order_date_start": {"backend_field": "order_date", "template": ">='{value}'"},
    "order_name": {"backend_field": "ap.person_name", "template": "like '%{value}%'"},
    "plan_pay_type": {"backend_field": "dtc.plan_pay_type", "template": "= {value}"},
    "saler_name": {"backend_field": "ap1.person_name", "template": "like '%{value}%'"},
    "sample_model": {"backend_field": "dtce.emcTemporarySampleModel", "template": "like '%{value}%'"},
    "sample_name": {"backend_field": "dtce.emcTemporarySampleName", "template": "like '%{value}%'"},
    "sign_status": {"backend_field": "dtc.sign_status", "template": "= '{value}'"},
    "test_requirement": {"backend_field": "tcp.test_requirement", "template": "= '{value}'"},
    # ── 第 4.1 节：Filter 候选字段表（从返回列反推） ──
    "bill_biz_typ_e_id": {"backend_field": "billBizTypeId", "template": "= '{value}'"},
    "bill_biz_type_id": {"backend_field": "billBizTypeId", "template": "= '{value}'"},
    "customer_contact": {"backend_field": "customerContact", "template": "like '%{value}%'"},
    "docket_name": {"backend_field": "docketName", "template": "like '%{value}%'"},
    "emc_temporary_sample_model": {"backend_field": "emcTemporarySampleModel", "template": "like '%{value}%'"},
    "emc_temporary_sample_name": {"backend_field": "emcTemporarySampleName", "template": "like '%{value}%'"},
    "locale_customer_engineer": {"backend_field": "localeCustomerEngineer", "template": "like '%{value}%'"},
    "locations": {"backend_field": "locations", "template": "like '%{value}%'"},
    "order_date_end": {"backend_field": "orderDate", "template": "<= '{value} 23:59:59'"},
    "send_email_status": {"backend_field": "sendEmailStatus", "template": "like '%{value}%'"},
    "test_date": {"backend_field": "testDate", "template": "like '%{value}%'"},
    "test_engineer_name": {"backend_field": "testEngineerName", "template": "like '%{value}%'"},
    "test_item": {"backend_field": "testItem", "template": "like '%{value}%'"},
    "test_time": {"backend_field": "testTime", "template": "like '%{value}%'"},
    "total_amt": {"backend_field": "totalAmt", "template": "like '%{value}%'"},
    "total_chargeable_duration": {"backend_field": "totalChargeableDuration", "template": "like '%{value}%'"},
    "total_free_duration": {"backend_field": "totalFreeDuration", "template": "like '%{value}%'"},
    "total_hours": {"backend_field": "totalHours", "template": "like '%{value}%'"},
}

# ── FIELD_LABELS（第 6 节：按前端展示顺序） ─────────────────────────
FIELD_LABELS: Dict[str, Dict[str, str]] = {
    "billBizTypeId": {
        "key": "bill_biz_type_id",
        "title": "所属模块",
    },
    "chargeNo": {
        "key": "charge_no",
        "title": "收费单编号",
    },
    "contractNo": {
        "key": "contract_no",
        "title": "合同编号",
    },
    "orderDate": {
        "key": "order_date",
        "title": "开单日期",
    },
    "docketName": {
        "key": "docket_name",
        "title": "打单人",
    },
    "signStatus": {
        "key": "sign_status",
        "title": "签字状态",
    },
    "customerName": {
        "key": "customer_name",
        "title": "客户",
    },
    "bstatus": {
        "key": "bstatus",
        "title": "收费单状态",
    },
    "customerContact": {
        "key": "customer_contact",
        "title": "客户联系人",
    },
    "testRequirement": {
        "key": "test_requirement",
        "title": "试验类型",
    },
    "itemNo": {
        "key": "item_no",
        "title": "项目名/现场试验号",
    },
    "entrustedProjectNo": {
        "key": "entrusted_project_no",
        "title": "案件编号",
    },
    "sampleName": {
        "key": "sample_name",
        "title": "样品名称",
    },
    "sendEmailStatus": {
        "key": "send_email_status",
        "title": "发送情况",
    },
    "localeCustomerEngineer": {
        "key": "locale_customer_engineer",
        "title": "现场客户测试工程师",
    },
    "sampleModel": {
        "key": "sample_model",
        "title": "样品型号",
    },
    "locations": {
        "key": "locations",
        "title": "试验场地",
    },
    "hasAttachment": {
        "key": "has_attachment",
        "title": "是否有附件",
    },
    "testItem": {
        "key": "test_item",
        "title": "试验项目",
    },
    "planPayType": {
        "key": "plan_pay_type",
        "title": "计划付款方式",
    },
    "testDate": {
        "key": "test_date",
        "title": "试验日期",
    },
    "testEngineerName": {
        "key": "test_engineer_name",
        "title": "试验人员",
    },
    "emcTemporarySampleName": {
        "key": "emc_temporary_sample_name",
        "title": "试验样品名称",
    },
    "testTime": {
        "key": "test_time",
        "title": "试验时长(H)",
    },
    "emcTemporarySampleModel": {
        "key": "emc_temporary_sample_model",
        "title": "试验样品型号",
    },
    "salerName": {
        "key": "saler_name",
        "title": "负责销售",
    },
    "totalFreeDuration": {
        "key": "total_free_duration",
        "title": "免单时长(H)",
    },
    "totalChargeableDuration": {
        "key": "total_chargeable_duration",
        "title": "应收费时长(H)",
    },
    "totalHours": {
        "key": "total_hours",
        "title": "收费单时长(H)",
    },
    "totalAmt": {
        "key": "total_amt",
        "title": "总计",
    },
    "billBizTyp   eId": {
        "key": "bill_biz_typ_e_id",
        "title": "所属模块",
    },
}

# ── ENUM_FIELDS（第 5 节 + 第 8 节：仅文档明确给出的 ref_id/enum） ──
ENUM_FIELDS: Dict[str, Any] = {
    "bill_biz_typ_e_id": {
        "lab06_01": "案件项目",
        "lab06_02": "现场收费单",
        "lab07_01": "案件项目",
        "lab07_02": "现场收费单",
    },
    "bill_biz_type_id": {
        "lab06_01": "案件项目",
        "lab06_02": "现场收费单",
        "lab07_01": "案件项目",
        "lab07_02": "现场收费单",
    },
    "bstatus": {
        1: "未转销售合同",
        4: "已转销售合同",
        5: "已收款",
        0: "已作废",
    },
    "plan_pay_type": {
        1: "现金",
        2: "转账",
        3: "月结",
        4: "微信支付",
        5: "支付宝支付",
        6: "其它",
    },
    "sign_status": {
        0: "未签字",
        1: "已签字",
    },
    "test_requirement": {
        "scene": "现场测试",
        "rectification": "案件整改/重测",
        "caseTest": "案件测试",
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


def _resolve_data_type(scope: str, data_type: Optional[str] = None) -> Optional[str]:
    if data_type:
        return data_type
    return SCOPE_DEFAULT_DATA_TYPE.get(scope)


def build_filter(
    *,
    bstatus: Optional[str] = None,
    charge_no: Optional[str] = None,
    contract_no: Optional[str] = None,
    customer_name: Optional[str] = None,
    entrusted_project_no: Optional[str] = None,
    fast_search: Optional[str] = None,
    item_no: Optional[str] = None,
    modular_type: Optional[str] = None,
    order_date: Optional[str] = None,
    order_date2: Optional[str] = None,
    order_date_start: Optional[str] = None,
    order_name: Optional[str] = None,
    plan_pay_type: Optional[str] = None,
    saler_name: Optional[str] = None,
    sample_model: Optional[str] = None,
    sample_name: Optional[str] = None,
    sign_status: Optional[str] = None,
    test_requirement: Optional[str] = None,
    # ── 候选 filter 参数（第 4.1 节） ──
    bill_biz_typ_e_id: Optional[str] = None,
    bill_biz_type_id: Optional[str] = None,
    customer_contact: Optional[str] = None,
    docket_name: Optional[str] = None,
    emc_temporary_sample_model: Optional[str] = None,
    emc_temporary_sample_name: Optional[str] = None,
    locale_customer_engineer: Optional[str] = None,
    locations_param: Optional[str] = None,
    order_date_end: Optional[str] = None,
    send_email_status: Optional[str] = None,
    test_date: Optional[str] = None,
    test_engineer_name: Optional[str] = None,
    test_item: Optional[str] = None,
    test_time: Optional[str] = None,
    total_amt: Optional[str] = None,
    total_chargeable_duration: Optional[str] = None,
    total_free_duration: Optional[str] = None,
    total_hours: Optional[str] = None,
) -> Optional[str]:
    values = {
        "bstatus": bstatus,
        "charge_no": charge_no,
        "contract_no": contract_no,
        "customer_name": customer_name,
        "entrusted_project_no": entrusted_project_no,
        "fast_search": fast_search,
        "item_no": item_no,
        "modular_type": modular_type,
        "order_date": order_date,
        "order_date2": order_date2,
        "order_date_start": order_date_start,
        "order_name": order_name,
        "plan_pay_type": plan_pay_type,
        "saler_name": saler_name,
        "sample_model": sample_model,
        "sample_name": sample_name,
        "sign_status": sign_status,
        "test_requirement": test_requirement,
        "bill_biz_typ_e_id": bill_biz_typ_e_id,
        "bill_biz_type_id": bill_biz_type_id,
        "customer_contact": customer_contact,
        "docket_name": docket_name,
        "emc_temporary_sample_model": emc_temporary_sample_model,
        "emc_temporary_sample_name": emc_temporary_sample_name,
        "locale_customer_engineer": locale_customer_engineer,
        "locations": locations_param,
        "order_date_end": order_date_end,
        "send_email_status": send_email_status,
        "test_date": test_date,
        "test_engineer_name": test_engineer_name,
        "test_item": test_item,
        "test_time": test_time,
        "total_amt": total_amt,
        "total_chargeable_duration": total_chargeable_duration,
        "total_free_duration": total_free_duration,
        "total_hours": total_hours,
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
    data_type: Optional[str] = None,
    bstatus: Optional[str] = None,
    charge_no: Optional[str] = None,
    contract_no: Optional[str] = None,
    customer_name: Optional[str] = None,
    entrusted_project_no: Optional[str] = None,
    fast_search: Optional[str] = None,
    item_no: Optional[str] = None,
    modular_type: Optional[str] = None,
    order_date: Optional[str] = None,
    order_date2: Optional[str] = None,
    order_date_start: Optional[str] = None,
    order_name: Optional[str] = None,
    plan_pay_type: Optional[str] = None,
    saler_name: Optional[str] = None,
    sample_model: Optional[str] = None,
    sample_name: Optional[str] = None,
    sign_status: Optional[str] = None,
    test_requirement: Optional[str] = None,
    bill_biz_typ_e_id: Optional[str] = None,
    bill_biz_type_id: Optional[str] = None,
    customer_contact: Optional[str] = None,
    docket_name: Optional[str] = None,
    emc_temporary_sample_model: Optional[str] = None,
    emc_temporary_sample_name: Optional[str] = None,
    locale_customer_engineer: Optional[str] = None,
    locations: Optional[str] = None,
    order_date_end: Optional[str] = None,
    send_email_status: Optional[str] = None,
    test_date: Optional[str] = None,
    test_engineer_name: Optional[str] = None,
    test_item: Optional[str] = None,
    test_time: Optional[str] = None,
    total_amt: Optional[str] = None,
    total_chargeable_duration: Optional[str] = None,
    total_free_duration: Optional[str] = None,
    total_hours: Optional[str] = None,
    sVars: Optional[Dict[str, Any]] = None,
) -> Dict[str, str]:
    params: Dict[str, str] = {
        "start": str(0 if start is None else start),
        "limit": str(10 if limit is None else limit),
    }

    resolved_svars = _resolve_svars(scope, sVars)
    resolved_data_type = _resolve_data_type(scope, data_type)
    if resolved_data_type:
        if resolved_svars is None:
            resolved_svars = {}
        resolved_svars["dataType"] = resolved_data_type
    if resolved_svars is not None:
        params["sVars"] = json.dumps(resolved_svars, ensure_ascii=False)

    filter_sql = build_filter(
        bstatus=bstatus,
        charge_no=charge_no,
        contract_no=contract_no,
        customer_name=customer_name,
        entrusted_project_no=entrusted_project_no,
        fast_search=fast_search,
        item_no=item_no,
        modular_type=modular_type,
        order_date=order_date,
        order_date2=order_date2,
        order_date_start=order_date_start,
        order_name=order_name,
        plan_pay_type=plan_pay_type,
        saler_name=saler_name,
        sample_model=sample_model,
        sample_name=sample_name,
        sign_status=sign_status,
        test_requirement=test_requirement,
        bill_biz_typ_e_id=bill_biz_typ_e_id,
        bill_biz_type_id=bill_biz_type_id,
        customer_contact=customer_contact,
        docket_name=docket_name,
        emc_temporary_sample_model=emc_temporary_sample_model,
        emc_temporary_sample_name=emc_temporary_sample_name,
        locale_customer_engineer=locale_customer_engineer,
        locations_param=locations,
        order_date_end=order_date_end,
        send_email_status=send_email_status,
        test_date=test_date,
        test_engineer_name=test_engineer_name,
        test_item=test_item,
        test_time=test_time,
        total_amt=total_amt,
        total_chargeable_duration=total_chargeable_duration,
        total_free_duration=total_free_duration,
        total_hours=total_hours,
    )
    if filter_sql:
        params["filter"] = filter_sql

    return params


def _build_columns() -> list:
    return [
        {"field": field, "key": meta["key"], "title": meta["title"]}
        for field, meta in FIELD_LABELS.items()
    ]


def _enum_text(key: str, value: Any) -> Optional[str]:
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


def _normalize_row(row: Dict[str, Any]) -> Dict[str, Any]:
    normalized: Dict[str, Any] = {}
    for field, meta in FIELD_LABELS.items():
        key = meta["key"]
        value = row.get(field)
        normalized[key] = value
        text = _enum_text(key, value)
        if text is not None:
            normalized["{}_text".format(key)] = text
    return normalized


def _extract_result_list(payload: Dict[str, Any]) -> list:
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


async def query_dmtestchargelistaction(
    token: str,
    scope: str = "default",
    view: Optional[str] = None,
    start: int = 0,
    limit: int = 10,
    data_type: Optional[str] = None,
    # ── 第 4 节查询字段 ──
    bstatus: Optional[str] = None,
    charge_no: Optional[str] = None,
    contract_no: Optional[str] = None,
    customer_name: Optional[str] = None,
    entrusted_project_no: Optional[str] = None,
    fast_search: Optional[str] = None,
    item_no: Optional[str] = None,
    modular_type: Optional[str] = None,
    order_date: Optional[str] = None,
    order_date2: Optional[str] = None,
    order_date_start: Optional[str] = None,
    order_name: Optional[str] = None,
    plan_pay_type: Optional[str] = None,
    saler_name: Optional[str] = None,
    sample_model: Optional[str] = None,
    sample_name: Optional[str] = None,
    sign_status: Optional[str] = None,
    test_requirement: Optional[str] = None,
    # ── 第 4.1 节候选 filter ──
    bill_biz_typ_e_id: Optional[str] = None,
    bill_biz_type_id: Optional[str] = None,
    customer_contact: Optional[str] = None,
    docket_name: Optional[str] = None,
    emc_temporary_sample_model: Optional[str] = None,
    emc_temporary_sample_name: Optional[str] = None,
    locale_customer_engineer: Optional[str] = None,
    locations: Optional[str] = None,
    order_date_end: Optional[str] = None,
    send_email_status: Optional[str] = None,
    test_date: Optional[str] = None,
    test_engineer_name: Optional[str] = None,
    test_item: Optional[str] = None,
    test_time: Optional[str] = None,
    total_amt: Optional[str] = None,
    total_chargeable_duration: Optional[str] = None,
    total_free_duration: Optional[str] = None,
    total_hours: Optional[str] = None,
    sVars: Optional[Dict[str, Any]] = None,
    include_raw: bool = False,
) -> Dict[str, Any]:
    """查询收费单列表，按 scope 路由到 DmTestChargeListAction 各 listQuery* 视图。

    默认 default scope 自动注入 operation=operation、showAmount=showAmount 两个 sVars。
    dataType 仅按文档第 7 节来源处理：default=mainView、all=weekView、rf=mainView。
    gen/project/sso/temp/temp_rf 不注入默认 dataType。
    """
    resolved_scope = _resolve_scope(scope=scope, view=view)
    params = build_params(
        scope=resolved_scope,
        start=start,
        limit=limit,
        data_type=data_type,
        bstatus=bstatus,
        charge_no=charge_no,
        contract_no=contract_no,
        customer_name=customer_name,
        entrusted_project_no=entrusted_project_no,
        fast_search=fast_search,
        item_no=item_no,
        modular_type=modular_type,
        order_date=order_date,
        order_date2=order_date2,
        order_date_start=order_date_start,
        order_name=order_name,
        plan_pay_type=plan_pay_type,
        saler_name=saler_name,
        sample_model=sample_model,
        sample_name=sample_name,
        sign_status=sign_status,
        test_requirement=test_requirement,
        bill_biz_typ_e_id=bill_biz_typ_e_id,
        bill_biz_type_id=bill_biz_type_id,
        customer_contact=customer_contact,
        docket_name=docket_name,
        emc_temporary_sample_model=emc_temporary_sample_model,
        emc_temporary_sample_name=emc_temporary_sample_name,
        locale_customer_engineer=locale_customer_engineer,
        locations=locations,
        order_date_end=order_date_end,
        send_email_status=send_email_status,
        test_date=test_date,
        test_engineer_name=test_engineer_name,
        test_item=test_item,
        test_time=test_time,
        total_amt=total_amt,
        total_chargeable_duration=total_chargeable_duration,
        total_free_duration=total_free_duration,
        total_hours=total_hours,
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
        result: Dict[str, Any] = {
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
    "query_dmtestchargelistaction": query_dmtestchargelistaction,
}

TOOL_SCHEMAS = [
    {
        "name": "query_dmtestchargelistaction",
        "description": (
            "查询收费单项目列表。通过 scope 路由到 DmTestChargeListAction 各 listQuery* 视图。"
            "default scope 自动注入 operation=operation、showAmount=showAmount 两个 sVars。"
            "dataType 仅按文档第 7 节来源处理：default/mainView、all/weekView、rf/mainView。"
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "scope": {
                    "type": "string",
                    "description": (
                        "视图范围：default=默认列表（自动注入 operation=operation, showAmount=showAmount），"
                        "all=全部数据视图，gen=GEN 业务视图，project=按项目查询，rf=RF 业务视图，"
                        "sso=SSO 视图，temp=临时视图，temp_rf=临时 RF 视图。"
                    ),
                },
                "view": {"type": "string", "description": "scope 的别名；如同时传入，以 scope 为准。"},
                "start": {"type": "integer", "description": "分页起始位置，默认 0。"},
                "limit": {"type": "integer", "description": "分页条数，默认 10。"},
                "data_type": {
                    "type": "string",
                    "description": (
                        "可选 sVars.dataType。不传时按 scope 自动注入："
                        "default=mainView, all=weekView, rf=mainView；"
                        "gen/project/sso/temp/temp_rf 不注入默认 dataType。"
                        "可用值见 scope 对应 dataType 选项表。"
                    ),
                },
                # ── 第 4 节：查询字段 ──
                "bstatus": {
                    "type": "string",
                    "description": "收费单状态 (q_bstatus → dtc.bstatus): 1=未转销售合同, 4=已转销售合同, 5=已收款, 0=已作废。",
                },
                "charge_no": {
                    "type": "string",
                    "description": "收费单编号，模糊匹配 (q_chargeNo → charge_no)。",
                },
                "contract_no": {
                    "type": "string",
                    "description": "合同编号，模糊匹配 (q_contractNo → sso.sales_order_no)。",
                },
                "customer_name": {
                    "type": "string",
                    "description": "客户，模糊匹配 (q_customerName → tcp.consignor_name_cn)。",
                },
                "entrusted_project_no": {
                    "type": "string",
                    "description": "案件编号，模糊匹配 (q_entrustedProjectNo → dp.project_no)。",
                },
                "fast_search": {
                    "type": "string",
                    "description": "视图，模糊匹配 (fastSearch → fastSearch)。",
                },
                "item_no": {
                    "type": "string",
                    "description": "项目名/现场试验号，模糊匹配 (q_itemNo → tcp.project_no)。",
                },
                "modular_type": {
                    "type": "string",
                    "description": (
                        "负责实验室 (q_modularType → dtc.modular_type): "
                        "reliability=可靠性, emc=汽车电子, general_emc=普通EMC, rf=射频RF, safety=安规试验室。"
                    ),
                },
                "order_date": {
                    "type": "string",
                    "description": "开单日期，精确匹配 (q_orderDate → order_date)。",
                },
                "order_date2": {
                    "type": "string",
                    "description": "开单日期至，精确匹配 (q_orderDate2 → order_date)。",
                },
                "order_date_start": {
                    "type": "string",
                    "description": "开单日期起开始，起始时间 (q_orderDate1 → order_date)。",
                },
                "order_name": {
                    "type": "string",
                    "description": "收费单人，模糊匹配 (q_orderName → ap.person_name)。",
                },
                "plan_pay_type": {
                    "type": "integer",
                    "description": "付款方式 (q_planPayType → dtc.plan_pay_type): 1=现金, 2=转账, 3=月结, 4=微信支付, 5=支付宝支付, 6=其它。",
                },
                "saler_name": {
                    "type": "string",
                    "description": "负责销售，模糊匹配 (q_salerName → ap1.person_name)。",
                },
                "sample_model": {
                    "type": "string",
                    "description": "样品型号，模糊匹配 (q_sampleModel → dtce.emcTemporarySampleModel)。",
                },
                "sample_name": {
                    "type": "string",
                    "description": "样品名称，模糊匹配 (q_sampleName → dtce.emcTemporarySampleName)。",
                },
                "sign_status": {
                    "type": "string",
                    "description": "签字状态 (q_signStatus → dtc.sign_status): 0=未签字, 1=已签字。",
                },
                "test_requirement": {
                    "type": "string",
                    "description": "试验类型 (q_testRequirement → tcp.test_requirement): scene=现场测试, rectification=案件整改/重测, caseTest=案件测试。",
                },
                # ── 第 4.1 节：Filter 候选字段 ──
                "bill_biz_typ_e_id": {
                    "type": "string",
                    "description": "所属模块（候选filter），精确匹配 (billBizTypeId)。枚举同 bill_biz_type_id。",
                },
                "bill_biz_type_id": {
                    "type": "string",
                    "description": (
                        "所属模块（候选filter），精确匹配 (billBizTypeId): "
                        "lab06_01=案件项目, lab06_02=现场收费单, lab07_01=案件项目, lab07_02=现场收费单。"
                    ),
                },
                "customer_contact": {
                    "type": "string",
                    "description": "客户联系人（候选filter），模糊匹配 (customerContact)。",
                },
                "docket_name": {
                    "type": "string",
                    "description": "打单人（候选filter），模糊匹配 (docketName)。",
                },
                "emc_temporary_sample_model": {
                    "type": "string",
                    "description": "试验样品型号（候选filter），模糊匹配 (emcTemporarySampleModel)。",
                },
                "emc_temporary_sample_name": {
                    "type": "string",
                    "description": "试验样品名称（候选filter），模糊匹配 (emcTemporarySampleName)。",
                },
                "locale_customer_engineer": {
                    "type": "string",
                    "description": "现场客户测试工程师（候选filter），模糊匹配 (localeCustomerEngineer)。",
                },
                "locations": {
                    "type": "string",
                    "description": "试验场地（候选filter），模糊匹配 (locations)。",
                },
                "order_date_end": {
                    "type": "string",
                    "description": "开单日期结束（候选filter），结束时间 (orderDate <= value)。",
                },
                "send_email_status": {
                    "type": "string",
                    "description": "发送情况（候选filter），模糊匹配 (sendEmailStatus)。",
                },
                "test_date": {
                    "type": "string",
                    "description": "试验日期（候选filter），模糊匹配 (testDate)。",
                },
                "test_engineer_name": {
                    "type": "string",
                    "description": "试验人员（候选filter），模糊匹配 (testEngineerName)。",
                },
                "test_item": {
                    "type": "string",
                    "description": "试验项目（候选filter），模糊匹配 (testItem)。",
                },
                "test_time": {
                    "type": "string",
                    "description": "试验时长(H)（候选filter），模糊匹配 (testTime)。",
                },
                "total_amt": {
                    "type": "string",
                    "description": "总计（候选filter），模糊匹配 (totalAmt)。",
                },
                "total_chargeable_duration": {
                    "type": "string",
                    "description": "应收费时长(H)（候选filter），模糊匹配 (totalChargeableDuration)。",
                },
                "total_free_duration": {
                    "type": "string",
                    "description": "免单时长(H)（候选filter），模糊匹配 (totalFreeDuration)。",
                },
                "total_hours": {
                    "type": "string",
                    "description": "收费单时长(H)（候选filter），模糊匹配 (totalHours)。",
                },
                "sVars": {
                    "type": "object",
                    "description": (
                        "自定义 sVars 负载。default scope 自动注入 operation=operation、showAmount=showAmount。"
                        "用户传入的 sVars 会覆盖 scope 默认值。"
                        "dataType 优先由 data_type 参数或 scope 默认值决定。"
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
