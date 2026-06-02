"""MCP tools for FinExpenseApplyListAction daily expense application queries."""
from __future__ import annotations

import json
import os
import sys
from typing import Any

import httpx

JAVA_API_BASE = os.environ.get("JAVA_API_BASE", "http://localhost:8080")

SCOPE_TO_ENDPOINT = {
    "mine": "/FinExpenseApplyListAction/listQueryMyPerson",
    "dept": "/FinExpenseApplyListAction/listQueryMyDept",
    "car_request": "/FinExpenseApplyListAction/listQueryCarRequest",
    "all": "/FinExpenseApplyListAction/listQuery",
}

FILTER_CONFIG = {
    "apply_no": {"backend_field": "fea.apply_no", "template": "like '%{value}%'"},
    "bill_biz_type_id": {"backend_field": "alc.lookup_name", "template": "like '%{value}%'"},
    "bstatus": {"backend_field": "fead.bstatus", "template": "= '{value}'"},
    "department_id": {"backend_field": "fea.department_id", "template": "= '{value}'"},
    "end_time": {"backend_field": "fea.apply_date", "template": "<= '{value} 23:59:59'"},
    "fast_search": {"backend_field": "fastSearch", "template": "like '%{value}%'"},
    "person_id": {"backend_field": "ap.PERSON_NAME", "template": "like '%{value}%'"},
    "remark": {"backend_field": "fead.remark", "template": "like '%{value}%'"},
    "rstatus": {"backend_field": "fea.rstatus", "template": "= {value}"},
    "start_time": {"backend_field": "fea.apply_date", "template": ">= '{value}'"},
}

FIELD_LABELS = {
    "applyNo": {"key": "apply_no", "title": "申请编号"},
    "applyDate": {"key": "apply_date", "title": "申请日期"},
    "personName": {"key": "person_name", "title": "申请人"},
    "lookupName": {"key": "lookup_name", "title": "申请类别"},
    "departmentName": {"key": "department_name", "title": "申请部门"},
    "tripType": {"key": "trip_type", "title": "用车类别"},
    "visitingObject": {"key": "visiting_object", "title": "用车对象"},
    "remark": {"key": "remark", "title": "申请内容与说明"},
    "salesName": {"key": "sales_name", "title": "负责业务"},
    "amt": {"key": "amt", "title": "预计支出金额"},
    "attendant": {"key": "attendant", "title": "乘客名称"},
    "itemName": {"key": "item_name", "title": "预计支出科目"},
    "startTime": {"key": "start_time", "title": "用车日期"},
    "rstatus": {"key": "rstatus", "title": "审核状态"},
    "courseType": {"key": "course_type", "title": "里程类型"},
    "bstatus": {"key": "bstatus", "title": "报销状态"},
    "tripOrigin": {"key": "trip_origin", "title": "行程起始地址"},
    "isapply": {"key": "isapply", "title": "转申请类型"},
    "tripDest": {"key": "trip_dest", "title": "行程目的地址"},
    "actAmt": {"key": "act_amt", "title": "实际支出金额"},
    "otherRemark": {"key": "other_remark", "title": "备注"},
    "paymentAmt": {"key": "payment_amt", "title": "实际报销金额"},
    "processDesc": {"key": "process_desc", "title": "审批流程"},
    "test": {"key": "test", "title": "车牌"},
}

ENUM_FIELDS = {
    "bstatus": {
        "1": "未报销",
        "2": "已报销",
    },
    "course_type": {
        "1": "单程",
        "2": "往返",
    },
    "rstatus": {
        0: "已作废",
        1: "已审核",
        2: "暂存",
        3: "等待重新审批",
        4: "审批中",
    },
    "trip_type": {
        "1": "客户接送",
        "2": "样品接送",
        "3": "专家接送",
        "4": "出差用车",
        "5": "其它",
    },
}


def _mask_token(token: str) -> str:
    if token and len(token) > 8:
        return token[:8] + "***"
    return "***"


def _resolve_scope(scope: str | None = None, view: str | None = None) -> str:
    resolved = (scope or view or "mine").strip().lower()
    if resolved not in SCOPE_TO_ENDPOINT:
        raise ValueError(
            "不支持的 scope/view 值：{}。可选值：{}".format(
                resolved, ", ".join(sorted(SCOPE_TO_ENDPOINT))
            )
        )
    return resolved


def build_filter(
    *,
    apply_no: str | None = None,
    bill_biz_type_id: str | None = None,
    bstatus: str | None = None,
    department_id: str | None = None,
    end_time: str | None = None,
    fast_search: str | None = None,
    person_id: str | None = None,
    remark: str | None = None,
    rstatus: int | None = None,
    start_time: str | None = None,
) -> str | None:
    values = {
        "apply_no": apply_no,
        "bill_biz_type_id": bill_biz_type_id,
        "bstatus": bstatus,
        "department_id": department_id,
        "end_time": end_time,
        "fast_search": fast_search,
        "person_id": person_id,
        "remark": remark,
        "rstatus": rstatus,
        "start_time": start_time,
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
    apply_no: str | None = None,
    bill_biz_type_id: str | None = None,
    bstatus: str | None = None,
    department_id: str | None = None,
    end_time: str | None = None,
    fast_search: str | None = None,
    person_id: str | None = None,
    remark: str | None = None,
    rstatus: int | None = None,
    start_time: str | None = None,
    sVars: dict | None = None,
) -> dict[str, str]:
    merged_svars = dict(sVars or {})
    params = {
        "start": str(0 if start is None else start),
        "limit": str(10 if limit is None else limit),
        "sVars": json.dumps(merged_svars, ensure_ascii=False),
    }

    filter_sql = build_filter(
        apply_no=apply_no,
        bill_biz_type_id=bill_biz_type_id,
        bstatus=bstatus,
        department_id=department_id,
        end_time=end_time,
        fast_search=fast_search,
        person_id=person_id,
        remark=remark,
        rstatus=rstatus,
        start_time=start_time,
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


async def query_daily_expense_apply_list(
    token: str,
    scope: str = "mine",
    view: str | None = None,
    start: int = 0,
    limit: int = 10,
    apply_no: str | None = None,
    bill_biz_type_id: str | None = None,
    bstatus: str | None = None,
    department_id: str | None = None,
    end_time: str | None = None,
    fast_search: str | None = None,
    person_id: str | None = None,
    remark: str | None = None,
    rstatus: int | None = None,
    start_time: str | None = None,
    sVars: dict | None = None,
    include_raw: bool = False,
) -> dict[str, Any]:
    """查询日常申请列表，默认查询我的申请，显式 scope=all 时查询全部日常申请。"""
    resolved_scope = _resolve_scope(scope=scope, view=view)
    params = build_params(
        start=start,
        limit=limit,
        apply_no=apply_no,
        bill_biz_type_id=bill_biz_type_id,
        bstatus=bstatus,
        department_id=department_id,
        end_time=end_time,
        fast_search=fast_search,
        person_id=person_id,
        remark=remark,
        rstatus=rstatus,
        start_time=start_time,
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
    "query_daily_expense_apply_list": query_daily_expense_apply_list,
}

TOOL_SCHEMAS = [
    {
        "name": "query_daily_expense_apply_list",
        "description": (
            "查询日常申请列表。默认查询我的申请；可显式 scope=all 查询全部日常申请，"
            "该范围数据敏感，不会作为默认值。"
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "scope": {
                    "type": "string",
                    "description": (
                        "视图范围：mine=我的日常申请，dept=我部门日常申请，"
                        "car_request=用车申请，all=全部日常申请（敏感范围，必须显式指定）。"
                    ),
                },
                "view": {
                    "type": "string",
                    "description": "scope 的别名；如同时传入，以 scope 为准。",
                },
                "start": {"type": "integer", "description": "分页起始位置，默认 0。"},
                "limit": {"type": "integer", "description": "分页条数，默认 10。"},
                "apply_no": {"type": "string", "description": "申请编号，模糊匹配 (applyNo -> fea.apply_no)。"},
                "bill_biz_type_id": {"type": "string", "description": "申请类别，模糊匹配 (billBizTypeId -> alc.lookup_name)。"},
                "bstatus": {"type": "string", "description": "报销状态，精确匹配 (q_bstatus -> fead.bstatus)：1=未报销, 2=已报销。"},
                "department_id": {"type": "string", "description": "申请部门，精确匹配 (q_departmentId -> fea.department_id)。"},
                "end_time": {"type": "string", "description": "申请日期结束，格式 YYYY-MM-DD (endTime -> fea.apply_date, <= 23:59:59)。"},
                "fast_search": {"type": "string", "description": "快速搜索词，模糊匹配 (fastSearch -> fastSearch)。"},
                "person_id": {"type": "string", "description": "申请人，模糊匹配 (q_personId -> ap.PERSON_NAME)。"},
                "remark": {"type": "string", "description": "申请内容与说明，模糊匹配 (remark -> fead.remark)。"},
                "rstatus": {
                    "type": "integer",
                    "description": "审核状态，精确匹配 (q_rstatus -> fea.rstatus)：0=已作废, 1=已审核, 2=暂存, 3=等待重新审批, 4=审批中。",
                },
                "start_time": {"type": "string", "description": "申请日期开始，格式 YYYY-MM-DD (startTime -> fea.apply_date, >=)。"},
                "sVars": {
                    "type": "object",
                    "description": "高级兼容参数。默认不注入 dataType；只有明确需要时才传自定义 sVars。",
                },
                "include_raw": {
                    "type": "boolean",
                    "description": "调试用。默认 false；为 true 时才返回后端原始 raw_resultList/raw_response。",
                },
            },
        },
    },
]
