"""MCP tools for EmcTemporaryTestListAction temporary test list queries.

继承 ListBaseAction，default scope 映射到 /EmcTemporaryTestListAction/listQuery。
"""
from __future__ import annotations

import json
import os
import sys
from typing import Any

import httpx

JAVA_API_BASE = os.environ.get("JAVA_API_BASE", "http://localhost:8080")

SCOPE_TO_ENDPOINT = {
    "default": "/EmcTemporaryTestListAction/listQuery",
    "all": "/EmcTemporaryTestListAction/listQueryForAll",
    "entrust": "/EmcTemporaryTestListAction/listQueryEntrust",
    "listqueryentrust": "/EmcTemporaryTestListAction/listQueryEntrust",
    "for_all": "/EmcTemporaryTestListAction/listQueryForAll",
    "listqueryforall": "/EmcTemporaryTestListAction/listQueryForAll",
    "cockpit": "/EmcTemporaryTestListAction/listQueryForCockpit01",
    "listqueryforcockpit01": "/EmcTemporaryTestListAction/listQueryForCockpit01",
    "dm": "/EmcTemporaryTestListAction/listQueryForDM",
    "dept": "/EmcTemporaryTestListAction/listQueryForDeptSaler",
    "gen": "/EmcTemporaryTestListAction/listQueryForGen",
    "locale": "/EmcTemporaryTestListAction/listQueryForLocale",
    "listqueryforlocale": "/EmcTemporaryTestListAction/listQueryForLocale",
    "mine": "/EmcTemporaryTestListAction/listQueryForMe",
    "op": "/EmcTemporaryTestListAction/listQueryForOp",
    "safety": "/EmcTemporaryTestListAction/listQueryForSFY",
    "saler": "/EmcTemporaryTestListAction/listQueryForSaler",
    "listqueryforsaler": "/EmcTemporaryTestListAction/listQueryForSaler",
}

DEFAULT_SVARS_BY_SCOPE = {
    "default": {"operation": "operation"},
    "all": {"modularType": "emc"},
}

SCOPE_DEFAULT_MODULAR_TYPE = {
    "default": "emc",
    "all": "emc",
    "entrust": "emc",
    "dm": "reliability",
    "gen": "general_emc",
    "op": "optical_property",
    "safety": "safety",
}

SCOPE_DEFAULT_DATA_TYPE = {
    "default": "newDate",
    "dept": "total",
    "dm": "my",
    "entrust": "my",
    "for_all": "total",
    "gen": "newDate",
    "mine": "total",
    "safety": "my",
}

DATA_TYPE_DESCRIPTIONS = {
    "my": "我的现场试验记录",
    "newDate": "当日现场试验记录",
    "yesterday": "昨日现场试验记录",
    "newWeek": "本周现场试验记录",
    "lastWeek": "上周试验记录",
    "newMonth": "本月试验记录",
    "lastMonth": "上月试验记录",
    "yesterdayNoOrder": "昨天未打收费单试验记录",
    "lastWeekNoOrder": "上周未打收费单试验记录",
    "newWeekNoOrder": "本周未打收费单试验记录",
    "total": "所有现场试验记录",
    "converted": "已转销售合同的现场试验",
    "notConverted": "已开单未转销售合同的现场试验",
    "notBilled": "未开单的现场试验",
}

FILTER_CONFIG = {
    # ── 第 4 节查询字段（主视图 XML q_condition）──
    "charge_bstatus": {"backend_field": "dtc.bstatus", "template": "= '{value}'"},
    "charge_no": {"backend_field": "dtc.charge_no", "template": "like '%{value}%'"},
    "consignor_name_cn": {"backend_field": "etp.consignor_name_cn", "template": "like '%{value}%'"},
    "create_on2": {"backend_field": "ett.create_on", "template": "<= '{value} 23:59:59'"},
    "create_on_end": {"backend_field": "ett.create_on", "template": "<= '{value} 23:59:59'"},
    "create_on_start": {"backend_field": "ett.create_on", "template": ">= '{value}'"},
    "customer_name": {"backend_field": "etp.consignor_contacts_cn", "template": "like '%{value}%'"},
    "entrusted_project_no": {"backend_field": "etp.entrusted_project_no", "template": "like '%{value}%'"},
    "fast_search": {"backend_field": "fastSearch", "template": "like '%{value}%'"},
    "location_id": {"backend_field": "tdl.location_id", "template": "= '{value}'"},
    "manager1": {"backend_field": "ap.PERSON_NAME", "template": "like '%{value}%'"},
    "order_description": {"backend_field": "ett.order_description", "template": "= {value}"},
    "order_status": {"backend_field": "ett.order_status", "template": "= {value}"},
    "product_model": {"backend_field": "etp.sample_model_cn", "template": "like '%{value}%'"},
    "product_name": {"backend_field": "etp.sample_name_cn", "template": "like '%{value}%'"},
    "project_no": {"backend_field": "etp.projectNo", "template": "like '%{value}%'"},
    "service_pro_name": {"backend_field": "ett.test_item", "template": "like '%{value}%'"},
    "terminal_authorization_customer": {
        "backend_field": "etp.terminal_authorization_customer",
        "template": "like '%{value}%'",
    },
    # ── 第 4.1 节 Filter 候选字段表（由返回列反推）──
    "charge_date": {"backend_field": "chargeDate", "template": "like '%{value}%'"},
    "charge_person": {"backend_field": "chargePerson", "template": "like '%{value}%'"},
    "charge_time": {"backend_field": "chargeTime", "template": "like '%{value}%'"},
    "docket_person": {"backend_field": "docketPerson", "template": "like '%{value}%'"},
    "engineer_name": {"backend_field": "engineerName", "template": "like '%{value}%'"},
    "locale_customer_engineer": {"backend_field": "localeCustomerEngineer", "template": "like '%{value}%'"},
    "locations": {"backend_field": "locations", "template": "like '%{value}%'"},
    "no_order_description": {"backend_field": "noOrderDescription", "template": "like '%{value}%'"},
    "project_no_main": {"backend_field": "projectNoMain", "template": "like '%{value}%'"},
    "remark": {"backend_field": "remark", "template": "like '%{value}%'"},
    "saler_person_name": {"backend_field": "salerPersonName", "template": "like '%{value}%'"},
    "sample_model_cn": {"backend_field": "sampleModelCn", "template": "like '%{value}%'"},
    "sample_name_cn": {"backend_field": "sampleNameCn", "template": "like '%{value}%'"},
    "sample_no": {"backend_field": "sampleNo", "template": "like '%{value}%'"},
    "test_charge_no": {"backend_field": "testChargeNo", "template": "like '%{value}%'"},
    "test_date": {"backend_field": "testDate", "template": "like '%{value}%'"},
    "test_item": {"backend_field": "testItem", "template": "like '%{value}%'"},
    "test_requirement": {"backend_field": "testRequirement", "template": "= '{value}'"},
    "test_time": {"backend_field": "testTime", "template": "like '%{value}%'"},
}

# ── 第 6 节 FIELD_LABELS（按前端展示顺序）──
FIELD_LABELS = {
    "projectNoMain": {"key": "project_no_main", "title": "现场试验编号"},
    "projectNo": {"key": "project_no", "title": "试验项目编号"},
    "createOn": {"key": "create_on", "title": "创建日期"},
    "consignorNameCn": {"key": "consignor_name_cn", "title": "客户"},
    "localeCustomerEngineer": {"key": "locale_customer_engineer", "title": "现场客户测试工程师"},
    "locations": {"key": "locations", "title": "试验场地"},
    "testItem": {"key": "test_item", "title": "试验项目"},
    "testRequirement": {"key": "test_requirement", "title": "试验类型"},
    "engineerName": {"key": "engineer_name", "title": "试验人员"},
    "testDate": {"key": "test_date", "title": "试验日期"},
    "orderDescription": {"key": "order_description", "title": "收费单说明"},
    "orderStatus": {"key": "order_status", "title": "开单状态"},
    "noOrderDescription": {"key": "no_order_description", "title": "无需收费单原因"},
    "entrustedProjectNo": {"key": "entrusted_project_no", "title": "案件编号"},
    "testTime": {"key": "test_time", "title": "试验时长"},
    "testChargeNo": {"key": "test_charge_no", "title": "收费单编号"},
    "chargeBstatus": {"key": "charge_bstatus", "title": "收费单状态"},
    "chargeTime": {"key": "charge_time", "title": "收费单时长"},
    "chargeDate": {"key": "charge_date", "title": "收费单日期"},
    "chargePerson": {"key": "charge_person", "title": "收费单人"},
    "docketPerson": {"key": "docket_person", "title": "打单人"},
    "sampleNameCn": {"key": "sample_name_cn", "title": "样品名称"},
    "sampleModelCn": {"key": "sample_model_cn", "title": "样品型号"},
    "sampleNo": {"key": "sample_no", "title": "样品编号"},
    "terminalAuthorizationCustomer": {"key": "terminal_authorization_customer", "title": "授权终端客户"},
    "salerPersonName": {"key": "saler_person_name", "title": "负责销售"},
    "remark": {"key": "remark", "title": "项目备注"},
}

# ── 第 8 节枚举字段 ──
ENUM_FIELDS = {
    "charge_bstatus": {
        1: "未转销售合同",
        4: "已转销售合同",
        5: "已收款",
        0: "已作废",
    },
    "order_description": {
        1: "需要",
        2: "不需要",
    },
    "order_status": {
        0: "未开单",
        1: "已开单",
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


def _resolve_scope(scope: str | None = None, view: str | None = None) -> str:
    resolved = (scope or view or "default").strip().lower()
    if resolved not in SCOPE_TO_ENDPOINT:
        raise ValueError(
            "不支持的 scope/view 值：{}。可选值：{}".format(
                resolved, ", ".join(sorted(SCOPE_TO_ENDPOINT))
            )
        )
    return resolved


def build_filter(
    *,
    # 第 4 节查询字段
    charge_bstatus: str | None = None,
    charge_no: str | None = None,
    consignor_name_cn: str | None = None,
    create_on2: str | None = None,
    create_on_end: str | None = None,
    create_on_start: str | None = None,
    customer_name: str | None = None,
    entrusted_project_no: str | None = None,
    fast_search: str | None = None,
    location_id: str | None = None,
    manager1: str | None = None,
    order_description: int | None = None,
    order_status: int | None = None,
    product_model: str | None = None,
    product_name: str | None = None,
    project_no: str | None = None,
    service_pro_name: str | None = None,
    terminal_authorization_customer: str | None = None,
    # 第 4.1 节 Filter 候选字段
    charge_date: str | None = None,
    charge_person: str | None = None,
    charge_time: str | None = None,
    docket_person: str | None = None,
    engineer_name: str | None = None,
    locale_customer_engineer: str | None = None,
    locations: str | None = None,
    no_order_description: str | None = None,
    project_no_main: str | None = None,
    remark: str | None = None,
    saler_person_name: str | None = None,
    sample_model_cn: str | None = None,
    sample_name_cn: str | None = None,
    sample_no: str | None = None,
    test_charge_no: str | None = None,
    test_date: str | None = None,
    test_item: str | None = None,
    test_requirement: str | None = None,
    test_time: str | None = None,
) -> str | None:
    values = {
        "charge_bstatus": charge_bstatus,
        "charge_no": charge_no,
        "consignor_name_cn": consignor_name_cn,
        "create_on2": create_on2,
        "create_on_end": create_on_end,
        "create_on_start": create_on_start,
        "customer_name": customer_name,
        "entrusted_project_no": entrusted_project_no,
        "fast_search": fast_search,
        "location_id": location_id,
        "manager1": manager1,
        "order_description": order_description,
        "order_status": order_status,
        "product_model": product_model,
        "product_name": product_name,
        "project_no": project_no,
        "service_pro_name": service_pro_name,
        "terminal_authorization_customer": terminal_authorization_customer,
        "charge_date": charge_date,
        "charge_person": charge_person,
        "charge_time": charge_time,
        "docket_person": docket_person,
        "engineer_name": engineer_name,
        "locale_customer_engineer": locale_customer_engineer,
        "locations": locations,
        "no_order_description": no_order_description,
        "project_no_main": project_no_main,
        "remark": remark,
        "saler_person_name": saler_person_name,
        "sample_model_cn": sample_model_cn,
        "sample_name_cn": sample_name_cn,
        "sample_no": sample_no,
        "test_charge_no": test_charge_no,
        "test_date": test_date,
        "test_item": test_item,
        "test_requirement": test_requirement,
        "test_time": test_time,
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
    scope: str,
    start: int = 0,
    limit: int = 10,
    # 第 4 节查询字段
    charge_bstatus: str | None = None,
    charge_no: str | None = None,
    consignor_name_cn: str | None = None,
    create_on2: str | None = None,
    create_on_end: str | None = None,
    create_on_start: str | None = None,
    customer_name: str | None = None,
    entrusted_project_no: str | None = None,
    fast_search: str | None = None,
    location_id: str | None = None,
    manager1: str | None = None,
    order_description: int | None = None,
    order_status: int | None = None,
    product_model: str | None = None,
    product_name: str | None = None,
    project_no: str | None = None,
    service_pro_name: str | None = None,
    terminal_authorization_customer: str | None = None,
    # 第 4.1 节 Filter 候选字段
    charge_date: str | None = None,
    charge_person: str | None = None,
    charge_time: str | None = None,
    docket_person: str | None = None,
    engineer_name: str | None = None,
    locale_customer_engineer: str | None = None,
    locations: str | None = None,
    no_order_description: str | None = None,
    project_no_main: str | None = None,
    remark: str | None = None,
    saler_person_name: str | None = None,
    sample_model_cn: str | None = None,
    sample_name_cn: str | None = None,
    sample_no: str | None = None,
    test_charge_no: str | None = None,
    test_date: str | None = None,
    test_item: str | None = None,
    test_requirement: str | None = None,
    test_time: str | None = None,
    data_type: str | None = None,
    modular_type: str | None = None,
    sVars: dict | None = None,
) -> dict[str, str]:
    merged_svars = dict(DEFAULT_SVARS_BY_SCOPE.get(scope, {}))
    provided_svars = dict(sVars or {})
    provided_data_type = provided_svars.pop("dataType", None)
    provided_modular_type = provided_svars.pop("modularType", None)
    merged_svars.update(provided_svars)

    resolved_data_type = data_type
    if resolved_data_type is None:
        resolved_data_type = SCOPE_DEFAULT_DATA_TYPE.get(scope, provided_data_type)
    if resolved_data_type is not None and resolved_data_type != "":
        merged_svars["dataType"] = resolved_data_type

    resolved_modular_type = modular_type
    if resolved_modular_type is None:
        resolved_modular_type = provided_modular_type or SCOPE_DEFAULT_MODULAR_TYPE.get(scope)
    if resolved_modular_type is not None and resolved_modular_type != "":
        merged_svars["modularType"] = resolved_modular_type

    params = {
        "start": str(0 if start is None else start),
        "limit": str(10 if limit is None else limit),
        "sVars": json.dumps(merged_svars, ensure_ascii=False),
    }

    filter_sql = build_filter(
        charge_bstatus=charge_bstatus,
        charge_no=charge_no,
        consignor_name_cn=consignor_name_cn,
        create_on2=create_on2,
        create_on_end=create_on_end,
        create_on_start=create_on_start,
        customer_name=customer_name,
        entrusted_project_no=entrusted_project_no,
        fast_search=fast_search,
        location_id=location_id,
        manager1=manager1,
        order_description=order_description,
        order_status=order_status,
        product_model=product_model,
        product_name=product_name,
        project_no=project_no,
        service_pro_name=service_pro_name,
        terminal_authorization_customer=terminal_authorization_customer,
        charge_date=charge_date,
        charge_person=charge_person,
        charge_time=charge_time,
        docket_person=docket_person,
        engineer_name=engineer_name,
        locale_customer_engineer=locale_customer_engineer,
        locations=locations,
        no_order_description=no_order_description,
        project_no_main=project_no_main,
        remark=remark,
        saler_person_name=saler_person_name,
        sample_model_cn=sample_model_cn,
        sample_name_cn=sample_name_cn,
        sample_no=sample_no,
        test_charge_no=test_charge_no,
        test_date=test_date,
        test_item=test_item,
        test_requirement=test_requirement,
        test_time=test_time,
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


async def query_emctemporarytestlistaction(
    token: str,
    scope: str = "default",
    view: str | None = None,
    start: int = 0,
    limit: int = 10,
    # 第 4 节查询字段
    charge_bstatus: str | None = None,
    charge_no: str | None = None,
    consignor_name_cn: str | None = None,
    create_on2: str | None = None,
    create_on_end: str | None = None,
    create_on_start: str | None = None,
    customer_name: str | None = None,
    entrusted_project_no: str | None = None,
    fast_search: str | None = None,
    location_id: str | None = None,
    manager1: str | None = None,
    order_description: int | None = None,
    order_status: int | None = None,
    product_model: str | None = None,
    product_name: str | None = None,
    project_no: str | None = None,
    service_pro_name: str | None = None,
    terminal_authorization_customer: str | None = None,
    # 第 4.1 节 Filter 候选字段
    charge_date: str | None = None,
    charge_person: str | None = None,
    charge_time: str | None = None,
    docket_person: str | None = None,
    engineer_name: str | None = None,
    locale_customer_engineer: str | None = None,
    locations: str | None = None,
    no_order_description: str | None = None,
    project_no_main: str | None = None,
    remark: str | None = None,
    saler_person_name: str | None = None,
    sample_model_cn: str | None = None,
    sample_name_cn: str | None = None,
    sample_no: str | None = None,
    test_charge_no: str | None = None,
    test_date: str | None = None,
    test_item: str | None = None,
    test_requirement: str | None = None,
    test_time: str | None = None,
    data_type: str | None = None,
    modular_type: str | None = None,
    sVars: dict | None = None,
    include_raw: bool = False,
) -> dict[str, Any]:
    """查询 EmcTemporaryTestListAction 临时测试列表，按 scope 路由不同视图。

    继承 ListBaseAction，default scope 注入 operation=operation。
    """
    resolved_scope = _resolve_scope(scope=scope, view=view)
    params = build_params(
        scope=resolved_scope,
        start=start,
        limit=limit,
        charge_bstatus=charge_bstatus,
        charge_no=charge_no,
        consignor_name_cn=consignor_name_cn,
        create_on2=create_on2,
        create_on_end=create_on_end,
        create_on_start=create_on_start,
        customer_name=customer_name,
        entrusted_project_no=entrusted_project_no,
        fast_search=fast_search,
        location_id=location_id,
        manager1=manager1,
        order_description=order_description,
        order_status=order_status,
        product_model=product_model,
        product_name=product_name,
        project_no=project_no,
        service_pro_name=service_pro_name,
        terminal_authorization_customer=terminal_authorization_customer,
        charge_date=charge_date,
        charge_person=charge_person,
        charge_time=charge_time,
        docket_person=docket_person,
        engineer_name=engineer_name,
        locale_customer_engineer=locale_customer_engineer,
        locations=locations,
        no_order_description=no_order_description,
        project_no_main=project_no_main,
        remark=remark,
        saler_person_name=saler_person_name,
        sample_model_cn=sample_model_cn,
        sample_name_cn=sample_name_cn,
        sample_no=sample_no,
        test_charge_no=test_charge_no,
        test_date=test_date,
        test_item=test_item,
        test_requirement=test_requirement,
        test_time=test_time,
        data_type=data_type,
        modular_type=modular_type,
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
    "query_emctemporarytestlistaction": query_emctemporarytestlistaction,
    "query_emc_temporary_test_list": query_emctemporarytestlistaction,
}

TOOL_SCHEMAS = [
    {
        "name": "query_emctemporarytestlistaction",
        "description": (
            "查询 EmcTemporaryTestListAction 租场试验/现场试验/临时测试列表，按 scope 路由不同视图。"
            "继承 ListBaseAction，default scope 映射到 /EmcTemporaryTestListAction/listQuery。"
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "scope": {
                    "type": "string",
                    "description": (
                        "视图范围：default=默认列表查询（继承 ListBaseAction，注入 operation=operation），"
                        "all=全部数据视图，entrust=委托视图，for_all=listQueryForAll，"
                        "cockpit=驾驶舱视图，dm=DM 业务视图，dept=部门范围视图，gen=GEN 业务视图，"
                        "locale=现场视图，mine=我的数据视图，op=OP 业务视图，safety=安全业务视图，"
                        "saler=销售视图。"
                    ),
                },
                "view": {
                    "type": "string",
                    "description": "scope 的别名；如同时传入，以 scope 为准。",
                },
                "start": {"type": "integer", "description": "分页起始位置，默认 0。"},
                "limit": {"type": "integer", "description": "分页条数，默认 10。"},
                # 第 4 节查询字段
                "charge_bstatus": {
                    "type": "string",
                    "description": "收费单状态，精确匹配 (q_chargeBstatus → dtc.bstatus)：1=未转销售合同, 4=已转销售合同, 5=已收款, 0=已作废。",
                },
                "charge_no": {"type": "string", "description": "收费单编号，模糊匹配 (q_chargeNo → dtc.charge_no)。"},
                "consignor_name_cn": {
                    "type": "string",
                    "description": "客户，模糊匹配 (q_consignorNameCn → etp.consignor_name_cn)。",
                },
                "create_on2": {"type": "string", "description": "创建结束日期 (q_createOn2 → ett.create_on, <= 23:59:59)。"},
                "create_on_end": {"type": "string", "description": "创建结束日期 (q_createOn1 → ett.create_on, <= 23:59:59)。"},
                "create_on_start": {"type": "string", "description": "创建开始日期 (q_createOn1 → ett.create_on, >=)。"},
                "customer_name": {
                    "type": "string",
                    "description": "客户联系人，模糊匹配 (q_customerName → etp.consignor_contacts_cn)。",
                },
                "entrusted_project_no": {
                    "type": "string",
                    "description": "案件编号，模糊匹配 (q_entrustedProjectNo → etp.entrusted_project_no)。",
                },
                "fast_search": {"type": "string", "description": "视图搜索词，模糊匹配 (fastSearch → fastSearch)。"},
                "location_id": {"type": "string", "description": "试验场地，精确匹配，租场试验常用筛选 (q_locationId → tdl.location_id)。"},
                "manager1": {"type": "string", "description": "试验人员，模糊匹配 (q_manager1 → ap.PERSON_NAME)。"},
                "order_description": {
                    "type": "integer",
                    "description": "收费单说明 (q_orderDescription → ett.order_description)：1=需要, 2=不需要。",
                },
                "order_status": {
                    "type": "integer",
                    "description": "开单状态 (q_orderStatus → ett.order_status)：0=未开单, 1=已开单。",
                },
                "product_model": {"type": "string", "description": "样品型号，模糊匹配 (q_productModel → etp.sample_model_cn)。"},
                "product_name": {"type": "string", "description": "样品名称，模糊匹配 (q_productName → etp.sample_name_cn)。"},
                "project_no": {"type": "string", "description": "现场试验/租场试验编号，模糊匹配 (q_projectNo → etp.projectNo)。"},
                "service_pro_name": {"type": "string", "description": "试验项目，模糊匹配，适合按租场试验项目名称检索 (q_serviceProName → ett.test_item)。"},
                "terminal_authorization_customer": {
                    "type": "string",
                    "description": "车企，模糊匹配 (q_terminalAuthorizationCustomer → etp.terminal_authorization_customer)。",
                },
                # 第 4.1 节 Filter 候选字段
                "charge_date": {"type": "string", "description": "收费单日期，候选 filter，模糊匹配 (chargeDate)。"},
                "charge_person": {"type": "string", "description": "收费单人，候选 filter，模糊匹配 (chargePerson)。"},
                "charge_time": {"type": "string", "description": "收费单时长，候选 filter，模糊匹配 (chargeTime)。"},
                "docket_person": {"type": "string", "description": "打单人，候选 filter，模糊匹配 (docketPerson)。"},
                "engineer_name": {"type": "string", "description": "试验人员，候选 filter，模糊匹配 (engineerName)。"},
                "locale_customer_engineer": {"type": "string", "description": "现场客户测试工程师，候选 filter，模糊匹配 (localeCustomerEngineer)。"},
                "locations": {"type": "string", "description": "试验场地，候选 filter，模糊匹配 (locations)。"},
                "no_order_description": {"type": "string", "description": "无需收费单原因，候选 filter，模糊匹配 (noOrderDescription)。"},
                "project_no_main": {"type": "string", "description": "现场试验编号，候选 filter，模糊匹配 (projectNoMain)。"},
                "remark": {"type": "string", "description": "项目备注，候选 filter，模糊匹配 (remark)。"},
                "saler_person_name": {"type": "string", "description": "负责销售，候选 filter，模糊匹配 (salerPersonName)。"},
                "sample_model_cn": {"type": "string", "description": "样品型号，候选 filter，模糊匹配 (sampleModelCn)。"},
                "sample_name_cn": {"type": "string", "description": "样品名称，候选 filter，模糊匹配 (sampleNameCn)。"},
                "sample_no": {"type": "string", "description": "样品编号，候选 filter，模糊匹配 (sampleNo)。"},
                "test_charge_no": {"type": "string", "description": "收费单编号，候选 filter，模糊匹配 (testChargeNo)。"},
                "test_date": {"type": "string", "description": "试验日期，候选 filter，模糊匹配 (testDate)。"},
                "test_item": {"type": "string", "description": "试验项目，候选 filter，模糊匹配 (testItem)。"},
                "test_requirement": {
                    "type": "string",
                    "description": "试验类型，候选 filter，精确匹配 (testRequirement)：scene=现场测试, rectification=案件整改/重测, caseTest=案件测试。",
                },
                "test_time": {"type": "string", "description": "试验时长，候选 filter，模糊匹配 (testTime)。"},
                "data_type": {
                    "type": "string",
                    "description": (
                        "前端 tab/视图条件，写入 sVars.dataType。显式传入时优先；"
                        "未传时按 scope 使用 XML 默认值，例如 default/gen=newDate，dm/safety/entrust=my，"
                        "dept/for_all/mine=total。常见值：my=我的现场试验记录，newDate=当日现场试验记录，"
                        "yesterday=昨日现场试验记录，newWeek=本周现场试验记录，total=所有现场试验记录，"
                        "converted=已转销售合同，notConverted=已开单未转销售合同，notBilled=未开单。"
                    ),
                },
                "modular_type": {
                    "type": "string",
                    "description": (
                        "业务模块类型，写入 sVars.modularType。显式传入时优先；未传时按 scope 默认："
                        "default/all/entrust=emc，dm=reliability，gen=general_emc，op=optical_property，safety=safety。"
                    ),
                },
                "sVars": {"type": "object", "description": "自定义 sVars 负载，会追加其他后端变量；dataType 优先由 data_type 或 scope 默认值决定。"},
                "include_raw": {
                    "type": "boolean",
                    "description": "调试用。默认 false；为 true 时才返回后端原始 raw_resultList/raw_response。",
                },
            },
        },
    },
]
