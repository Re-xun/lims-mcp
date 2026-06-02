"""MCP tools for AbdSupplierListAction supplier list queries."""
from __future__ import annotations

import json
import os
import sys
from typing import Any

import httpx

JAVA_API_BASE = os.environ.get("JAVA_API_BASE", "http://localhost:8080")

SCOPE_TO_ENDPOINT = {
    "default": "/AbdSupplierListAction/listQuery",
    "select": "/AbdSupplierListAction/listQuerySelect",
    "payment": "/AbdSupplierListAction/supplierPaymentQuery",
    "qm": "/AbdSupplierListAction/listQuery",
    "dept": "/AbdSupplierListAction/listQuery",
    "my": "/AbdSupplierListAction/listQuery",
}

SCOPE_DEFAULT_SVARS: dict[str, dict[str, str]] = {
    "default": {"operation": "operation"},
    "qm": {"scope": "qm"},
    "dept": {"show_dept": "1"},
    "my": {"operation": "My"},
}

FILTER_CONFIG: dict[str, dict[str, str]] = {
    # ── 核心筛选（第 4 节） ──
    "dept": {"backend_field": "asu.filing_department_id", "template": "= '{value}'"},
    "description": {"backend_field": "description", "template": "like '%{value}%'"},
    "fast_search": {"backend_field": "fastSearch", "template": "like '%{value}%'"},
    "person": {"backend_field": "p.PERSON_NAME", "template": "like '%{value}%'"},
    "rstatus": {"backend_field": "asu.bstatus", "template": "= {value}"},
    "rstatus2": {"backend_field": "asu.rstatus", "template": "= {value}"},
    "supplier_grade_id": {"backend_field": "supplierGradeId", "template": "= '{value}'"},
    "supplier_manage_category": {"backend_field": "asu.manage_category", "template": "= '{value}'"},
    "supplier_name": {"backend_field": "supplierName", "template": "like '%{value}%'"},
    "supplier_no": {"backend_field": "supplierNo", "template": "like '%{value}%'"},
    "supplier_type_id": {"backend_field": "asu.supplier_type_id", "template": "= '{value}'"},
    # ── 候选 filter（第 4.1 节） ──
    "address": {"backend_field": "address", "template": "like '%{value}%'"},
    "amt_local": {"backend_field": "amtLocal", "template": "like '%{value}%'"},
    "annual_review_date_end": {"backend_field": "annualReviewDate", "template": "<= '{value} 23:59:59'"},
    "annual_review_date_start": {"backend_field": "annualReviewDate", "template": ">= '{value}'"},
    "annual_review_status": {"backend_field": "annualReviewStatus", "template": "= '{value}'"},
    "area_name": {"backend_field": "areaName", "template": "like '%{value}%'"},
    "bstatus": {"backend_field": "bstatus", "template": "= '{value}'"},
    "contact_name": {"backend_field": "contactName", "template": "like '%{value}%'"},
    "create_on_end": {"backend_field": "createOn", "template": "<= '{value} 23:59:59'"},
    "create_on_start": {"backend_field": "createOn", "template": ">= '{value}'"},
    "evaluation_date_end": {"backend_field": "evaluationDate", "template": "<= '{value} 23:59:59'"},
    "evaluation_date_start": {"backend_field": "evaluationDate", "template": ">= '{value}'"},
    "filing_date_end": {"backend_field": "filingDate", "template": "<= '{value} 23:59:59'"},
    "filing_date_start": {"backend_field": "filingDate", "template": ">= '{value}'"},
    "last_collaboration_date_end": {"backend_field": "lastCollaborationDate", "template": "<= '{value} 23:59:59'"},
    "last_collaboration_date_start": {"backend_field": "lastCollaborationDate", "template": ">= '{value}'"},
    "mobile_telephone": {"backend_field": "mobileTelephone", "template": "like '%{value}%'"},
    "person_name": {"backend_field": "personName", "template": "like '%{value}%'"},
    "tax_ratio": {"backend_field": "taxRatio", "template": "like '%{value}%'"},
}

FIELD_LABELS: dict[str, dict[str, str]] = {
    "supplierNo": {
        "key": "supplier_no",
        "title": "供应商编号",
    },
    "supplierName": {
        "key": "supplier_name",
        "title": "供应商名称",
    },
    "amtLocal": {
        "key": "amt_local",
        "title": "付款总计",
    },
    "supplierTypeName": {
        "key": "supplier_type_name",
        "title": "供应商类别",
    },
    "description": {
        "key": "description",
        "title": "服务项目",
    },
    "supplierGradeName": {
        "key": "supplier_grade_name",
        "title": "供应商等级",
    },
    "areaName": {
        "key": "area_name",
        "title": "国家或地区",
    },
    "address": {
        "key": "address",
        "title": "地址",
    },
    "contactName": {
        "key": "contact_name",
        "title": "联系人",
    },
    "mobileTelephone": {
        "key": "mobile_telephone",
        "title": "电话",
    },
    "filingDate": {
        "key": "filing_date",
        "title": "备案日期",
    },
    "evaluationDate": {
        "key": "evaluation_date",
        "title": "评价日期",
    },
    "createOn": {
        "key": "create_on",
        "title": "创建日期",
    },
    "lastCollaborationDate": {
        "key": "last_collaboration_date",
        "title": "最近一次合作日期",
    },
    "annualReviewDate": {
        "key": "annual_review_date",
        "title": "年度评价日期",
    },
    "annualReviewStatus": {
        "key": "annual_review_status",
        "title": "年度评价状态",
    },
    "departmentName": {
        "key": "department_name",
        "title": "负责部门",
    },
    "taxRatio": {
        "key": "tax_ratio",
        "title": "税率",
    },
    "personName": {
        "key": "person_name",
        "title": "负责人",
    },
    "bstatus": {
        "key": "bstatus",
        "title": "供应商状态",
    },
    "rstatus": {
        "key": "rstatus",
        "title": "审核状态",
    },
}

ENUM_FIELDS = {
    "annual_review_status": {
        10: "有效",
        20: "过期",
    },
    "bstatus": {
        1: "合作中",
        2: "暂停合作",
        3: "黑名单",
        4: "待审核",
        5: "审核中",
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


def _resolve_svars(scope: str, user_svars: dict[str, Any] | None = None) -> dict[str, Any] | None:
    defaults = SCOPE_DEFAULT_SVARS.get(scope, {})
    if not defaults and not user_svars:
        return None
    merged = dict(defaults)
    if user_svars:
        merged.update(user_svars)
    return merged


def build_filter(
    *,
    dept: str | None = None,
    description: str | None = None,
    fast_search: str | None = None,
    person: str | None = None,
    rstatus: int | None = None,
    rstatus2: int | None = None,
    supplier_grade_id: str | None = None,
    supplier_manage_category: str | None = None,
    supplier_name: str | None = None,
    supplier_no: str | None = None,
    supplier_type_id: str | None = None,
    address: str | None = None,
    amt_local: str | None = None,
    annual_review_date_end: str | None = None,
    annual_review_date_start: str | None = None,
    annual_review_status: str | None = None,
    area_name: str | None = None,
    bstatus: str | None = None,
    contact_name: str | None = None,
    create_on_end: str | None = None,
    create_on_start: str | None = None,
    evaluation_date_end: str | None = None,
    evaluation_date_start: str | None = None,
    filing_date_end: str | None = None,
    filing_date_start: str | None = None,
    last_collaboration_date_end: str | None = None,
    last_collaboration_date_start: str | None = None,
    mobile_telephone: str | None = None,
    person_name: str | None = None,
    tax_ratio: str | None = None,
) -> str | None:
    values: dict[str, Any] = {
        "dept": dept,
        "description": description,
        "fast_search": fast_search,
        "person": person,
        "rstatus": rstatus,
        "rstatus2": rstatus2,
        "supplier_grade_id": supplier_grade_id,
        "supplier_manage_category": supplier_manage_category,
        "supplier_name": supplier_name,
        "supplier_no": supplier_no,
        "supplier_type_id": supplier_type_id,
        "address": address,
        "amt_local": amt_local,
        "annual_review_date_end": annual_review_date_end,
        "annual_review_date_start": annual_review_date_start,
        "annual_review_status": annual_review_status,
        "area_name": area_name,
        "bstatus": bstatus,
        "contact_name": contact_name,
        "create_on_end": create_on_end,
        "create_on_start": create_on_start,
        "evaluation_date_end": evaluation_date_end,
        "evaluation_date_start": evaluation_date_start,
        "filing_date_end": filing_date_end,
        "filing_date_start": filing_date_start,
        "last_collaboration_date_end": last_collaboration_date_end,
        "last_collaboration_date_start": last_collaboration_date_start,
        "mobile_telephone": mobile_telephone,
        "person_name": person_name,
        "tax_ratio": tax_ratio,
    }

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
    sVars: dict[str, Any] | None = None,
    **filter_values: Any,
) -> dict[str, str]:
    params = {
        "start": str(0 if start is None else start),
        "limit": str(10 if limit is None else limit),
    }

    resolved_svars = _resolve_svars(scope, sVars)
    if resolved_svars is not None:
        params["sVars"] = json.dumps(resolved_svars, ensure_ascii=False)

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


async def query_supplier_list(
    token: str,
    scope: str = "default",
    view: str | None = None,
    start: int = 0,
    limit: int = 10,
    # ── 核心筛选（第 4 节） ──
    dept: str | None = None,
    description: str | None = None,
    fast_search: str | None = None,
    person: str | None = None,
    rstatus: int | None = None,
    rstatus2: int | None = None,
    supplier_grade_id: str | None = None,
    supplier_manage_category: str | None = None,
    supplier_name: str | None = None,
    supplier_no: str | None = None,
    supplier_type_id: str | None = None,
    # ── 候选 filter（第 4.1 节） ──
    address: str | None = None,
    amt_local: str | None = None,
    annual_review_date_end: str | None = None,
    annual_review_date_start: str | None = None,
    annual_review_status: str | None = None,
    area_name: str | None = None,
    bstatus: str | None = None,
    contact_name: str | None = None,
    create_on_end: str | None = None,
    create_on_start: str | None = None,
    evaluation_date_end: str | None = None,
    evaluation_date_start: str | None = None,
    filing_date_end: str | None = None,
    filing_date_start: str | None = None,
    last_collaboration_date_end: str | None = None,
    last_collaboration_date_start: str | None = None,
    mobile_telephone: str | None = None,
    person_name: str | None = None,
    tax_ratio: str | None = None,
    sVars: dict[str, Any] | None = None,
    include_raw: bool = False,
) -> dict[str, Any]:
    """查询供应商列表，按 scope 路由到默认、选择、付款、QM 或部门视图。"""
    resolved_scope = _resolve_scope(scope=scope, view=view)
    params = build_params(
        scope=resolved_scope,
        start=start,
        limit=limit,
        dept=dept,
        description=description,
        fast_search=fast_search,
        person=person,
        rstatus=rstatus,
        rstatus2=rstatus2,
        supplier_grade_id=supplier_grade_id,
        supplier_manage_category=supplier_manage_category,
        supplier_name=supplier_name,
        supplier_no=supplier_no,
        supplier_type_id=supplier_type_id,
        address=address,
        amt_local=amt_local,
        annual_review_date_end=annual_review_date_end,
        annual_review_date_start=annual_review_date_start,
        annual_review_status=annual_review_status,
        area_name=area_name,
        bstatus=bstatus,
        contact_name=contact_name,
        create_on_end=create_on_end,
        create_on_start=create_on_start,
        evaluation_date_end=evaluation_date_end,
        evaluation_date_start=evaluation_date_start,
        filing_date_end=filing_date_end,
        filing_date_start=filing_date_start,
        last_collaboration_date_end=last_collaboration_date_end,
        last_collaboration_date_start=last_collaboration_date_start,
        mobile_telephone=mobile_telephone,
        person_name=person_name,
        tax_ratio=tax_ratio,
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
    "query_supplier_list": query_supplier_list,
}

_PROPERTIES: dict[str, dict[str, Any]] = {
    "scope": {
        "type": "string",
        "description": (
            "查询视图: default=默认列表（自动注入 operation=operation），"
            "select=选择器视图，payment=付款视图，"
            "qm=QM 供应商列表（自动注入 scope=qm），"
            "dept=部门视图（自动注入 show_dept=1）。"
            "my=我的供应商视图（自动注入 operation=My）。"
            "default 包含继承的 /AbdSupplierListAction/listQuery。"
        ),
    },
    "view": {"type": "string", "description": "scope 的别名"},
    "start": {"type": "integer", "description": "分页起始位置，默认 0"},
    "limit": {"type": "integer", "description": "每页条数，默认 10"},
    # ── 核心筛选（第 4 节） ──
    "dept": {"type": "string", "description": "负责部门，精确匹配 (q_dept → asu.filing_department_id)"},
    "description": {"type": "string", "description": "服务项目，模糊匹配 (description → description)"},
    "fast_search": {"type": "string", "description": "视图，模糊匹配 (fastSearch → fastSearch)"},
    "person": {"type": "string", "description": "负责人，模糊匹配 (q_person → p.PERSON_NAME)"},
    "rstatus": {
        "type": "integer",
        "description": "供应商状态 (q_rstatus → asu.bstatus): 1=合作中, 2=暂停合作, 3=黑名单, 4=待审核, 5=审核中",
    },
    "rstatus2": {
        "type": "integer",
        "description": "审核状态 (q_rstatus2 → asu.rstatus): 0=已作废, 1=已审核, 2=暂存, 3=等待重新审批, 4=审批中",
    },
    "supplier_grade_id": {"type": "string", "description": "供应商等级，精确匹配 (supplierGradeId → supplierGradeId)"},
    "supplier_manage_category": {"type": "string", "description": "供应商管理类别，精确匹配 (supplierManageCategory → asu.manage_category)"},
    "supplier_name": {"type": "string", "description": "供应商名称，模糊匹配 (supplierName → supplierName)"},
    "supplier_no": {"type": "string", "description": "供应商编号，模糊匹配 (supplierNo → supplierNo)"},
    "supplier_type_id": {"type": "string", "description": "供应商类别，精确匹配 (supplierTypeId → asu.supplier_type_id)"},
    # ── 候选 filter（第 4.1 节） ──
    "address": {"type": "string", "description": "地址，候选 filter，模糊匹配"},
    "amt_local": {"type": "string", "description": "付款总计，候选 filter，模糊匹配"},
    "annual_review_date_end": {"type": "string", "description": "年度评价日期结束，候选 filter，结束时间"},
    "annual_review_date_start": {"type": "string", "description": "年度评价日期开始，候选 filter，起始时间"},
    "annual_review_status": {"type": "string", "description": "年度评价状态，候选 filter，精确匹配"},
    "area_name": {"type": "string", "description": "国家或地区，候选 filter，模糊匹配"},
    "bstatus": {"type": "string", "description": "供应商状态，候选 filter，精确匹配"},
    "contact_name": {"type": "string", "description": "联系人，候选 filter，模糊匹配"},
    "create_on_end": {"type": "string", "description": "创建日期结束，候选 filter，结束时间"},
    "create_on_start": {"type": "string", "description": "创建日期开始，候选 filter，起始时间"},
    "evaluation_date_end": {"type": "string", "description": "评价日期结束，候选 filter，结束时间"},
    "evaluation_date_start": {"type": "string", "description": "评价日期开始，候选 filter，起始时间"},
    "filing_date_end": {"type": "string", "description": "备案日期结束，候选 filter，结束时间"},
    "filing_date_start": {"type": "string", "description": "备案日期开始，候选 filter，起始时间"},
    "last_collaboration_date_end": {"type": "string", "description": "最近一次合作日期结束，候选 filter，结束时间"},
    "last_collaboration_date_start": {"type": "string", "description": "最近一次合作日期开始，候选 filter，起始时间"},
    "mobile_telephone": {"type": "string", "description": "电话，候选 filter，模糊匹配"},
    "person_name": {"type": "string", "description": "负责人，候选 filter，模糊匹配"},
    "tax_ratio": {"type": "string", "description": "税率，候选 filter，模糊匹配"},
    "sVars": {
        "type": "object",
        "description": (
            "自定义 sVars 负载。default scope 自动注入 operation=operation，"
            "qm scope 自动注入 scope=qm，"
            "dept scope 自动注入 show_dept=1。"
            "用户传入的 sVars 会覆盖 scope 默认值。"
            "本工具不会根据未在文档第 7 节出现的 dataType 来源注入默认 dataType。"
        ),
    },
    "include_raw": {
        "type": "boolean",
        "description": "调试用。默认 false；为 true 时才返回后端原始 raw_resultList/raw_response。",
    },
}

TOOL_SCHEMAS = [
    {
        "name": "query_supplier_list",
        "description": (
            "查询供应商列表，通过 scope 路由到默认、选择、付款、QM 或部门视图，"
            "default 包含继承的 /AbdSupplierListAction/listQuery。"
            "返回 count、columns、data/normalized_data。"
        ),
        "inputSchema": {"type": "object", "properties": _PROPERTIES},
    }
]
