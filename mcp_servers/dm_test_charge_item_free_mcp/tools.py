"""MCP tools for DmTestChargeItemFreeListAction 免单记录 queries."""
from __future__ import annotations

import json
import os
import sys
from typing import Any

import httpx

JAVA_API_BASE = os.environ.get("JAVA_API_BASE", "http://localhost:8080")

SCOPE_TO_ENDPOINT = {
    "default": "/DmTestChargeItemFreeListAction/listQuery",
    "my": "/DmTestChargeItemFreeListAction/listQuery",
}

DEFAULT_SVARS_BY_SCOPE = {
    "default": {
        "modularType": "modularType",
        "operation": "operation",
    },
    "my": {
        "modularType": "modularType",
        "operation": "My",
    },
}

FILTER_CONFIG = {
    # 第 4 节: XML q_condition 查询字段
    "approve_date_end": {"backend_field": "dtcf.approve_date", "template": "<= '{value}'"},
    "approve_date_start": {"backend_field": "dtcf.approve_date", "template": ">= '{value}'"},
    "charge_no": {"backend_field": "dtc.charge_no", "template": "like '%{value}%'"},
    "customer_name_cn": {"backend_field": "ac.CUSTOMER_NAME_CN", "template": "like '%{value}%'"},
    "department_name": {"backend_field": "ad.department_name", "template": "= '{value}'"},
    "fast_search": {"backend_field": "fastSearch", "template": "like '%{value}%'"},
    "person_name": {"backend_field": "ap.PERSON_NAME", "template": "like '%{value}%'"},
    "test_charge_free_no": {"backend_field": "dtcf.test_charge_free_no", "template": "like '%{value}%'"},
    "test_requirement": {"backend_field": "etp.test_requirement", "template": "like '%{value}%'"},
    # 第 4.1 节: Filter 候选字段（基于返回列反推）
    "apply_date_end": {"backend_field": "applyDate", "template": "<= '{value}'"},
    "apply_date_start": {"backend_field": "applyDate", "template": ">= '{value}'"},
    "approver_name": {"backend_field": "approverName", "template": "like '%{value}%'"},
    "free_duration": {"backend_field": "freeDuration", "template": "= {value}"},
    "free_reason": {"backend_field": "freeReason", "template": "like '%{value}%'"},
    "free_rstatus": {"backend_field": "freeRstatus", "template": "= {value}"},
    "location_name": {"backend_field": "locationName", "template": "like '%{value}%'"},
    "plan_end_date_end": {"backend_field": "planEndDate", "template": "<= '{value}'"},
    "plan_end_date_start": {"backend_field": "planEndDate", "template": ">= '{value}'"},
    "plan_start_date_end": {"backend_field": "planStartDate", "template": "<= '{value}'"},
    "plan_start_date_start": {"backend_field": "planStartDate", "template": ">= '{value}'"},
    "project_no": {"backend_field": "projectNo", "template": "like '%{value}%'"},
    "remark": {"backend_field": "remark", "template": "like '%{value}%'"},
    "sales_order_no": {"backend_field": "salesOrderNo", "template": "like '%{value}%'"},
    "test_item_name": {"backend_field": "testItemName", "template": "like '%{value}%'"},
}

FIELD_LABELS = {
    "testChargeFreeNo": {"key": "test_charge_free_no", "title": "免单申请编号"},
    "chargeNo": {"key": "charge_no", "title": "收费单编号"},
    "projectNo": {"key": "project_no", "title": "试验记录编号"},
    "salesOrderNo": {"key": "sales_order_no", "title": "销售合同编号"},
    "freeRstatus": {"key": "free_rstatus", "title": "审批状态"},
    "customerNameCn": {"key": "customer_name_cn", "title": "客户名称"},
    "personName": {"key": "person_name", "title": "负责销售"},
    "testRequirement": {"key": "test_requirement", "title": "实验类型"},
    "departmentName": {"key": "department_name", "title": "负责实验室"},
    "remark": {"key": "remark", "title": "备注（外部）"},
    "testItemName": {"key": "test_item_name", "title": "试验项目"},
    "locationName": {"key": "location_name", "title": "试验场地"},
    "planStartDate": {"key": "plan_start_date", "title": "试验开始时间"},
    "planEndDate": {"key": "plan_end_date", "title": "试验结束时间"},
    "freeDuration": {"key": "free_duration", "title": "免单时长"},
    "freeReason": {"key": "free_reason", "title": "免单原因"},
    "approverName": {"key": "approver_name", "title": "申请人"},
    "applyDate": {"key": "apply_date", "title": "申请日期"},
    "approveDate": {"key": "approve_date", "title": "审批日期"},
}

ENUM_FIELDS = {
    "free_rstatus": {
        0: "已作废",
        1: "已审核",
        2: "暂存",
        3: "等待重新审批",
        4: "审批中",
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
            "不支持的免单记录 scope/view: {}。可选值: {}".format(
                resolved, ", ".join(sorted(SCOPE_TO_ENDPOINT))
            )
        )
    return resolved


def build_filter(
    *,
    approve_date_end: str | None = None,
    approve_date_start: str | None = None,
    charge_no: str | None = None,
    customer_name_cn: str | None = None,
    department_name: str | None = None,
    fast_search: str | None = None,
    person_name: str | None = None,
    test_charge_free_no: str | None = None,
    test_requirement: str | None = None,
    apply_date_end: str | None = None,
    apply_date_start: str | None = None,
    approver_name: str | None = None,
    free_duration: str | None = None,
    free_reason: str | None = None,
    free_rstatus: str | None = None,
    location_name: str | None = None,
    plan_end_date_end: str | None = None,
    plan_end_date_start: str | None = None,
    plan_start_date_end: str | None = None,
    plan_start_date_start: str | None = None,
    project_no: str | None = None,
    remark: str | None = None,
    sales_order_no: str | None = None,
    test_item_name: str | None = None,
) -> str | None:
    values = {
        "approve_date_end": approve_date_end,
        "approve_date_start": approve_date_start,
        "charge_no": charge_no,
        "customer_name_cn": customer_name_cn,
        "department_name": department_name,
        "fast_search": fast_search,
        "person_name": person_name,
        "test_charge_free_no": test_charge_free_no,
        "test_requirement": test_requirement,
        "apply_date_end": apply_date_end,
        "apply_date_start": apply_date_start,
        "approver_name": approver_name,
        "free_duration": free_duration,
        "free_reason": free_reason,
        "free_rstatus": free_rstatus,
        "location_name": location_name,
        "plan_end_date_end": plan_end_date_end,
        "plan_end_date_start": plan_end_date_start,
        "plan_start_date_end": plan_start_date_end,
        "plan_start_date_start": plan_start_date_start,
        "project_no": project_no,
        "remark": remark,
        "sales_order_no": sales_order_no,
        "test_item_name": test_item_name,
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
    scope: str = "default",
    start: int = 0,
    limit: int = 10,
    sVars: dict | None = None,
    approve_date_end: str | None = None,
    approve_date_start: str | None = None,
    charge_no: str | None = None,
    customer_name_cn: str | None = None,
    department_name: str | None = None,
    fast_search: str | None = None,
    person_name: str | None = None,
    test_charge_free_no: str | None = None,
    test_requirement: str | None = None,
    apply_date_end: str | None = None,
    apply_date_start: str | None = None,
    approver_name: str | None = None,
    free_duration: str | None = None,
    free_reason: str | None = None,
    free_rstatus: str | None = None,
    location_name: str | None = None,
    plan_end_date_end: str | None = None,
    plan_end_date_start: str | None = None,
    plan_start_date_end: str | None = None,
    plan_start_date_start: str | None = None,
    project_no: str | None = None,
    remark: str | None = None,
    sales_order_no: str | None = None,
    test_item_name: str | None = None,
) -> dict[str, str]:
    params = {
        "start": str(0 if start is None else start),
        "limit": str(10 if limit is None else limit),
    }

    merged_svars = dict(DEFAULT_SVARS_BY_SCOPE.get(scope, {}))
    if sVars:
        merged_svars.update(sVars)
    params["sVars"] = json.dumps(merged_svars, ensure_ascii=False)

    filter_sql = build_filter(
        approve_date_end=approve_date_end,
        approve_date_start=approve_date_start,
        charge_no=charge_no,
        customer_name_cn=customer_name_cn,
        department_name=department_name,
        fast_search=fast_search,
        person_name=person_name,
        test_charge_free_no=test_charge_free_no,
        test_requirement=test_requirement,
        apply_date_end=apply_date_end,
        apply_date_start=apply_date_start,
        approver_name=approver_name,
        free_duration=free_duration,
        free_reason=free_reason,
        free_rstatus=free_rstatus,
        location_name=location_name,
        plan_end_date_end=plan_end_date_end,
        plan_end_date_start=plan_end_date_start,
        plan_start_date_end=plan_start_date_end,
        plan_start_date_start=plan_start_date_start,
        project_no=project_no,
        remark=remark,
        sales_order_no=sales_order_no,
        test_item_name=test_item_name,
    )
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


async def query_dmtestchargeitemfreelistaction(
    token: str,
    scope: str = "default",
    view: str | None = None,
    start: int = 0,
    limit: int = 10,
    sVars: dict | None = None,
    include_raw: bool = False,
    approve_date_end: str | None = None,
    approve_date_start: str | None = None,
    charge_no: str | None = None,
    customer_name_cn: str | None = None,
    department_name: str | None = None,
    fast_search: str | None = None,
    person_name: str | None = None,
    test_charge_free_no: str | None = None,
    test_requirement: str | None = None,
    apply_date_end: str | None = None,
    apply_date_start: str | None = None,
    approver_name: str | None = None,
    free_duration: str | None = None,
    free_reason: str | None = None,
    free_rstatus: str | None = None,
    location_name: str | None = None,
    plan_end_date_end: str | None = None,
    plan_end_date_start: str | None = None,
    plan_start_date_end: str | None = None,
    plan_start_date_start: str | None = None,
    project_no: str | None = None,
    remark: str | None = None,
    sales_order_no: str | None = None,
    test_item_name: str | None = None,
) -> dict[str, Any]:
    """查询免单记录列表。"""
    resolved_scope = _resolve_scope(scope=scope, view=view)
    params = build_params(
        scope=resolved_scope,
        start=start,
        limit=limit,
        sVars=sVars,
        approve_date_end=approve_date_end,
        approve_date_start=approve_date_start,
        charge_no=charge_no,
        customer_name_cn=customer_name_cn,
        department_name=department_name,
        fast_search=fast_search,
        person_name=person_name,
        test_charge_free_no=test_charge_free_no,
        test_requirement=test_requirement,
        apply_date_end=apply_date_end,
        apply_date_start=apply_date_start,
        approver_name=approver_name,
        free_duration=free_duration,
        free_reason=free_reason,
        free_rstatus=free_rstatus,
        location_name=location_name,
        plan_end_date_end=plan_end_date_end,
        plan_end_date_start=plan_end_date_start,
        plan_start_date_end=plan_start_date_end,
        plan_start_date_start=plan_start_date_start,
        project_no=project_no,
        remark=remark,
        sales_order_no=sales_order_no,
        test_item_name=test_item_name,
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
    "query_dmtestchargeitemfreelistaction": query_dmtestchargeitemfreelistaction,
    "query_dm_test_charge_item_free_list": query_dmtestchargeitemfreelistaction,
}

TOOL_SCHEMAS = [
    {
        "name": "query_dmtestchargeitemfreelistaction",
        "description": (
            "查询免单记录列表。继承 DmTestChargeItemFreeListAction 的默认 /listQuery 视图，"
            "默认返回 count、columns、data/normalized_data，"
            "枚举字段 free_rstatus/test_requirement 同时返回 *_text 中文值。"
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "scope": {
                    "type": "string",
                    "description": (
                        "视图范围：default=默认列表查询（继承 ListBaseAction 的 /listQuery），"
                        "my=我的免单记录列表（自动注入 operation=My 过滤当前用户及共享客户的销售记录）。"
                    ),
                },
                "view": {"type": "string", "description": "scope 的别名；如同时传入，以 scope 为准。"},
                "start": {"type": "integer", "description": "分页起始位置，默认 0。"},
                "limit": {"type": "integer", "description": "分页条数，默认 10。"},
                # 第 4 节 XML q_condition 查询字段
                "approve_date_end": {"type": "string", "description": "审批日期截止，结束时间 (q_approveDateEnd → dtcf.approve_date)。"},
                "approve_date_start": {"type": "string", "description": "审批日期起始，起始时间 (q_approveDateStart → dtcf.approve_date)。"},
                "charge_no": {"type": "string", "description": "收费单编号，模糊匹配 (q_chargeNo → dtc.charge_no)。"},
                "customer_name_cn": {"type": "string", "description": "客户名称，模糊匹配 (q_customerNameCn → ac.CUSTOMER_NAME_CN)。"},
                "department_name": {"type": "string", "description": "负责实验室，精确匹配 (q_departmentName → ad.department_name)。"},
                "fast_search": {"type": "string", "description": "视图搜索词，模糊匹配 (fastSearch → fastSearch)。"},
                "person_name": {"type": "string", "description": "负责销售，模糊匹配 (q_personName → ap.PERSON_NAME)。"},
                "test_charge_free_no": {"type": "string", "description": "免单申请编号，模糊匹配 (q_testChargeFreeNo → dtcf.test_charge_free_no)。"},
                "test_requirement": {
                    "type": "string",
                    "description": (
                        "实验类型，模糊匹配 (q_testRequirement → etp.test_requirement)。"
                        "枚举：scene=现场测试, rectification=案件整改/重测, caseTest=案件测试。"
                    ),
                },
                # 第 4.1 节 Filter 候选字段
                "apply_date_end": {"type": "string", "description": "申请日期截止，结束时间 (applyDate)。"},
                "apply_date_start": {"type": "string", "description": "申请日期起始，起始时间 (applyDate)。"},
                "approver_name": {"type": "string", "description": "申请人，模糊匹配 (approverName)。"},
                "free_duration": {"type": "integer", "description": "免单时长，精确匹配 (freeDuration)。"},
                "free_reason": {"type": "string", "description": "免单原因，模糊匹配 (freeReason)。"},
                "free_rstatus": {
                    "type": "integer",
                    "description": (
                        "审批状态，精确匹配 (freeRstatus)。"
                        "枚举：0=已作废, 1=已审核, 2=暂存, 3=等待重新审批, 4=审批中。"
                    ),
                },
                "location_name": {"type": "string", "description": "试验场地，模糊匹配 (locationName)。"},
                "plan_end_date_end": {"type": "string", "description": "试验结束时间截止，结束时间 (planEndDate)。"},
                "plan_end_date_start": {"type": "string", "description": "试验结束时间起始，起始时间 (planEndDate)。"},
                "plan_start_date_end": {"type": "string", "description": "试验开始时间截止，结束时间 (planStartDate)。"},
                "plan_start_date_start": {"type": "string", "description": "试验开始时间起始，起始时间 (planStartDate)。"},
                "project_no": {"type": "string", "description": "试验记录编号，模糊匹配 (projectNo)。"},
                "remark": {"type": "string", "description": "备注（外部），模糊匹配 (remark)。"},
                "sales_order_no": {"type": "string", "description": "销售合同编号，模糊匹配 (salesOrderNo)。"},
                "test_item_name": {"type": "string", "description": "试验项目，模糊匹配 (testItemName)。"},
                # 杂项
                "sVars": {
                    "type": "object",
                    "description": (
                        "自定义 sVars 负载，会与默认注入的 modularType/operation 合并。"
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
