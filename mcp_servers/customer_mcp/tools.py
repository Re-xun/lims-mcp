"""MCP tools for AbdCustomerListAction customer list queries."""
from __future__ import annotations

import json
import os
import sys
from typing import Any

import httpx

JAVA_API_BASE = os.environ.get("JAVA_API_BASE", "http://localhost:8080")

SCOPE_TO_ENDPOINT = {
    "default": "/AbdCustomerListAction/listQuery",
    "dept": "/AbdCustomerListAction/listQueryByDept",
    "mine": "/AbdCustomerListAction/customerMyList",
    "customer_dept": "/AbdCustomerListAction/customerDeptList",
    "colliding_names": "/AbdCustomerListAction/listQueryCollidingNames",
    "listquerycollidingnames": "/AbdCustomerListAction/listQueryCollidingNames",
}

DATA_TYPE_OPTIONS: dict[str, dict[str, str]] = {
    "LIST_ALL_VIEW": {
        "title": "全部客户",
        "source": "CustomerList.xml <date_types defaultType>",
    },
    "listMyView": {
        "title": "我创建的",
        "source": "CustomerList.xml <date_type>",
    },
    "LIST_DEPT_VIEW": {
        "title": "我部门的客户",
        "source": "AbdCustomerListAction.customerDeptList 强制写入",
    },
    "LIST_RESPONSE_PERSON_ID_MY_VIEW": {
        "title": "我的客户",
        "source": "AbdCustomerListAction.customerMyList 强制写入",
    },
}

SCOPE_DEFAULT_DATA_TYPE: dict[str, str] = {
    "default": "LIST_ALL_VIEW",
}

FILTER_CONFIG: dict[str, dict[str, str]] = {
    "address": {"backend_field": "aca.ADDRESS_CN", "template": "like '%{value}%'"},
    "create_on_start": {"backend_field": "ac.create_on", "template": ">= '{value}'"},
    "create_on_end": {"backend_field": "ac.create_on", "template": "<= '{value} 23:59:59'"},
    "customer_name": {"backend_field": "ac.customer_name_cn", "template": "like '%{value}%'"},
    "customer_name_en": {"backend_field": "ac.customer_name_en", "template": "like '%{value}%'"},
    "customer_no": {"backend_field": "ac.customer_no", "template": "like '%{value}%'"},
    "customer_phase": {"backend_field": "ac.customerPhase", "template": "= {value}"},
    "customer_status": {"backend_field": "ac.customer_status", "template": "= '{value}'"},
    "dept": {"backend_field": "ad.department_name", "template": "like '%{value}%'"},
    "fast_search": {"backend_field": "fastSearch", "template": "like '%{value}%'"},
    "responsible_department": {"backend_field": "ad.department_name", "template": "like '%{value}%'"},
    "responsible_for_business": {"backend_field": "ap.PERSON_NAME", "template": "like '%{value}%'"},
    "rstatus": {"backend_field": "ac.rstatus", "template": "= {value}"},
    "settlement_type": {"backend_field": "ac.settlementType", "template": "= {value}"},
    "short_name": {"backend_field": "ac.short_name", "template": "like '%{value}%'"},
    "sub_customer_name": {"backend_field": "q_subCustomerName", "template": "like '%{value}%'"},
    "abd_customer_type_customer_type_name": {
        "backend_field": "abdCustomerType.customerTypeName",
        "template": "like '%{value}%'",
    },
    "abd_department_name": {"backend_field": "abdDepartmentName", "template": "like '%{value}%'"},
    "abd_person_name": {"backend_field": "abdPersonName", "template": "like '%{value}%'"},
    "address_cn": {"backend_field": "addressCn", "template": "like '%{value}%'"},
    "contact_name": {"backend_field": "contactName", "template": "like '%{value}%'"},
    "credit_code": {"backend_field": "creditCode", "template": "like '%{value}%'"},
    "customer_address_name": {"backend_field": "customerAddressName", "template": "like '%{value}%'"},
    "customer_name_cn": {"backend_field": "customerNameCn", "template": "like '%{value}%'"},
    "department_name": {"backend_field": "departmentName", "template": "like '%{value}%'"},
    "latest_contact_on_start": {"backend_field": "latestContactOn", "template": ">= '{value}'"},
    "latest_contact_on_end": {"backend_field": "latestContactOn", "template": "<= '{value} 23:59:59'"},
    "main_product": {"backend_field": "mainProduct", "template": "like '%{value}%'"},
    "main_request": {"backend_field": "mainRequest", "template": "like '%{value}%'"},
    "number_one_year": {"backend_field": "numberOneYear", "template": "like '%{value}%'"},
    "person_name": {"backend_field": "personName", "template": "like '%{value}%'"},
    "share_person_names": {"backend_field": "sharePersonNames", "template": "like '%{value}%'"},
}

FIELD_LABELS: dict[str, dict[str, str]] = {
    "customerName": {"key": "customer_name", "title": "客户名称"},
    "customerPhase": {"key": "customer_phase", "title": "客户阶段"},
    "subCustomerName": {"key": "sub_customer_name", "title": "客户部门"},
    "rstatus": {"key": "rstatus", "title": "状态"},
    "customerNameEn": {"key": "customer_name_en", "title": "名称(英)"},
    "customerNo": {"key": "customer_no", "title": "编号"},
    "customerStatus": {"key": "customer_status", "title": "客户状态"},
    "customerNameCn": {"key": "customer_name_cn", "title": "名称(中)"},
    "personName": {"key": "person_name", "title": "负责人"},
    "departmentName": {"key": "department_name", "title": "销售部门"},
    "shortName": {"key": "short_name", "title": "简称"},
    "customerAddressName": {"key": "customer_address_name", "title": "公司地址"},
    "addressCn": {"key": "address_cn", "title": "地址"},
    "createOn": {"key": "create_on", "title": "创建日期"},
    "contactName": {"key": "contact_name", "title": "联系人名"},
    "latestContactOn": {"key": "latest_contact_on", "title": "最近联系日期"},
    "creditCode": {"key": "credit_code", "title": "统一社会信用代码"},
    "abdCustomerType.customerTypeName": {
        "key": "abd_customer_type_customer_type_name",
        "title": "客户类别",
    },
    "mainProduct": {"key": "main_product", "title": "主要产品"},
    "settlementType": {"key": "settlement_type", "title": "结算类型"},
    "abdDepartmentName": {"key": "abd_department_name", "title": "负责部门"},
    "abdPersonName": {"key": "abd_person_name", "title": "负责业务"},
    "sharePersonNames": {"key": "share_person_names", "title": "共享业务员"},
    "mainRequest": {"key": "main_request", "title": "主要需求"},
    "numberOneYear": {"key": "number_one_year", "title": "一年内订单数"},
}

ENUM_FIELDS = {
    "customer_phase": {1: "未合作", 2: "已合作"},
    "rstatus": {0: "已作废", 1: "已审核", 2: "暂存", 3: "等待重新审批", 4: "审批中"},
    "settlement_type": {1: "月结客户"},
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
    if key == "listquerycollidingnames":
        return "listquerycollidingnames"
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


def _row_get(row: dict[str, Any], field: str) -> Any:
    if field in row:
        return row.get(field)
    if field == "customerNameEn":
        return row.get("customerName_en")
    if field == "customerNameCn":
        return row.get("customerName")
    if field == "personName":
        return row.get("responsePerson")
    if field == "departmentName":
        return row.get("dept")
    if field == "customerAddressName":
        return row.get("customerAddress")
    if field == "addressCn":
        return row.get("address")
    if field == "abdDepartmentName":
        return row.get("responsibleDepartment")
    if field == "abdPersonName":
        return row.get("responsibleForBusiness")
    return None


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
    scope: str = "default",
    start: int = 0,
    limit: int = 10,
    date_enums: str | None = None,
    data_type: str | None = None,
    **filter_values: Any,
) -> dict[str, str]:
    params = {
        "start": str(0 if start is None else start),
        "limit": str(10 if limit is None else limit),
    }

    filter_sql = build_filter(**filter_values)
    if filter_sql:
        params["filter"] = filter_sql

    s_vars: dict[str, Any] = {}
    resolved_data_type = _resolve_data_type(scope, data_type)
    if resolved_data_type:
        s_vars["dataType"] = resolved_data_type
    if date_enums:
        s_vars["dateEnums"] = date_enums
    if s_vars:
        params["sVars"] = json.dumps(s_vars, ensure_ascii=False)

    return params


def _build_columns() -> list[dict[str, str]]:
    return [
        {"field": field, "key": meta["key"], "title": meta["title"]}
        for field, meta in FIELD_LABELS.items()
    ]


def _normalize_row(row: dict[str, Any]) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    for field, meta in FIELD_LABELS.items():
        key = meta["key"]
        value = _row_get(row, field)
        normalized[key] = value
        text = _enum_text(key, value)
        if text is not None:
            normalized[f"{key}_text"] = text
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


async def query_customer_list(
    token: str,
    scope: str = "default",
    view: str | None = None,
    start: int = 0,
    limit: int = 10,
    address: str | None = None,
    create_on_end: str | None = None,
    create_on_start: str | None = None,
    customer_name: str | None = None,
    customer_name_en: str | None = None,
    customer_no: str | None = None,
    customer_phase: int | None = None,
    customer_status: str | None = None,
    date_enums: str | None = None,
    dept: str | None = None,
    fast_search: str | None = None,
    responsible_department: str | None = None,
    responsible_for_business: str | None = None,
    rstatus: int | None = None,
    settlement_type: int | None = None,
    short_name: str | None = None,
    sub_customer_name: str | None = None,
    abd_customer_type_customer_type_name: str | None = None,
    abd_department_name: str | None = None,
    abd_person_name: str | None = None,
    address_cn: str | None = None,
    contact_name: str | None = None,
    credit_code: str | None = None,
    customer_address_name: str | None = None,
    customer_name_cn: str | None = None,
    department_name: str | None = None,
    latest_contact_on_end: str | None = None,
    latest_contact_on_start: str | None = None,
    main_product: str | None = None,
    main_request: str | None = None,
    number_one_year: str | None = None,
    person_name: str | None = None,
    share_person_names: str | None = None,
    data_type: str | None = None,
    include_raw: bool = False,
) -> dict[str, Any]:
    """查询客户列表，按 scope 路由到默认、部门、我的、客户部门或重名客户视图。"""
    resolved_scope = _resolve_scope(scope=scope, view=view)
    params = build_params(
        scope=resolved_scope,
        start=start,
        limit=limit,
        date_enums=date_enums,
        data_type=data_type,
        address=address,
        create_on_end=create_on_end,
        create_on_start=create_on_start,
        customer_name=customer_name,
        customer_name_en=customer_name_en,
        customer_no=customer_no,
        customer_phase=customer_phase,
        customer_status=customer_status,
        dept=dept,
        fast_search=fast_search,
        responsible_department=responsible_department,
        responsible_for_business=responsible_for_business,
        rstatus=rstatus,
        settlement_type=settlement_type,
        short_name=short_name,
        sub_customer_name=sub_customer_name,
        abd_customer_type_customer_type_name=abd_customer_type_customer_type_name,
        abd_department_name=abd_department_name,
        abd_person_name=abd_person_name,
        address_cn=address_cn,
        contact_name=contact_name,
        credit_code=credit_code,
        customer_address_name=customer_address_name,
        customer_name_cn=customer_name_cn,
        department_name=department_name,
        latest_contact_on_end=latest_contact_on_end,
        latest_contact_on_start=latest_contact_on_start,
        main_product=main_product,
        main_request=main_request,
        number_one_year=number_one_year,
        person_name=person_name,
        share_person_names=share_person_names,
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


TOOL_HANDLERS = {"query_customer_list": query_customer_list}

_PROPERTIES: dict[str, dict[str, Any]] = {
    "scope": {
        "type": "string",
        "description": (
            "查询视图: default=默认列表, dept=部门范围, mine=我的客户, "
            "customer_dept=客户部门列表, colliding_names/listQueryCollidingNames=重名客户视图"
        ),
    },
    "view": {"type": "string", "description": "scope 的别名"},
    "start": {"type": "integer", "description": "分页起始位置，默认 0"},
    "limit": {"type": "integer", "description": "每页条数，默认 10"},
    "address": {"type": "string", "description": "地址，模糊匹配 (q_address → aca.ADDRESS_CN)"},
    "create_on_end": {"type": "string", "description": "创建日期截止，结束时间 (q_createOnEnd → ac.create_on)"},
    "create_on_start": {"type": "string", "description": "创建日期起始，起始时间 (q_createOn → ac.create_on)"},
    "customer_name": {"type": "string", "description": "客户名称，模糊匹配 (q_customerName → ac.customer_name_cn)"},
    "customer_name_en": {"type": "string", "description": "英文名称，模糊匹配 (q_customerNameEn → ac.customer_name_en)"},
    "customer_no": {"type": "string", "description": "编号，模糊匹配 (q_customerNo → ac.customer_no)"},
    "customer_phase": {"type": "integer", "description": "客户阶段 (q_customerPhase → ac.customerPhase): 1=未合作, 2=已合作"},
    "customer_status": {"type": "string", "description": "客户状态，精确匹配 (q_customerStatus → ac.customer_status)"},
    "date_enums": {
        "type": "string",
        "description": (
            "创建日期快捷范围: thisYear=本年度, lastYear=上年度, thisQuarter=本季度, "
            "lastQuarter=上季度, thisMonth=本月, lastMonth=上月, thisWeek=本周, lastWeek=上周, free=自定义"
        ),
    },
    "dept": {"type": "string", "description": "销售部门，模糊匹配 (q_dept → ad.department_name)"},
    "fast_search": {"type": "string", "description": "视图/快速搜索，模糊匹配 (fastSearch → fastSearch)"},
    "responsible_department": {"type": "string", "description": "部门，模糊匹配 (q_responsibleDepartment → ad.department_name)"},
    "responsible_for_business": {"type": "string", "description": "业务员，模糊匹配 (q_responsibleForBusiness → ap.PERSON_NAME)"},
    "rstatus": {"type": "integer", "description": "状态 (q_rstatus → ac.rstatus): 0=已作废, 1=已审核, 2=暂存, 3=等待重新审批, 4=审批中"},
    "settlement_type": {"type": "integer", "description": "结算类型 (q_settlementType → ac.settlementType): 1=月结客户"},
    "short_name": {"type": "string", "description": "客户简称，模糊匹配 (q_shortName → ac.short_name)"},
    "sub_customer_name": {"type": "string", "description": "客户部门，模糊匹配 (q_subCustomerName → q_subCustomerName)"},
    "abd_customer_type_customer_type_name": {"type": "string", "description": "客户类别，候选 filter，模糊匹配"},
    "abd_department_name": {"type": "string", "description": "负责部门，候选 filter，模糊匹配"},
    "abd_person_name": {"type": "string", "description": "负责业务，候选 filter，模糊匹配"},
    "address_cn": {"type": "string", "description": "地址，候选 filter，模糊匹配"},
    "contact_name": {"type": "string", "description": "联系人名，候选 filter，模糊匹配"},
    "credit_code": {"type": "string", "description": "统一社会信用代码，候选 filter，模糊匹配"},
    "customer_address_name": {"type": "string", "description": "公司地址，候选 filter，模糊匹配"},
    "customer_name_cn": {"type": "string", "description": "名称(中)，候选 filter，模糊匹配"},
    "department_name": {"type": "string", "description": "销售部门，候选 filter，模糊匹配"},
    "latest_contact_on_end": {"type": "string", "description": "最近联系日期截止，候选 filter，结束时间"},
    "latest_contact_on_start": {"type": "string", "description": "最近联系日期起始，候选 filter，起始时间"},
    "main_product": {"type": "string", "description": "主要产品，候选 filter，模糊匹配"},
    "main_request": {"type": "string", "description": "主要需求，候选 filter，模糊匹配"},
    "number_one_year": {"type": "string", "description": "一年内订单数，候选 filter，模糊匹配"},
    "person_name": {"type": "string", "description": "负责人，候选 filter，模糊匹配"},
    "share_person_names": {"type": "string", "description": "共享业务员，候选 filter，模糊匹配"},
    "data_type": {
        "type": "string",
        "description": (
            "可选 sVars.dataType；不传时 default 自动使用 LIST_ALL_VIEW。"
            "mine/customer_dept 不自动传，让 Java 分别强制为 LIST_RESPONSE_PERSON_ID_MY_VIEW/LIST_DEPT_VIEW；"
            "可选值包括 LIST_ALL_VIEW=全部客户, listMyView=我创建的, "
            "LIST_DEPT_VIEW=我部门的客户, LIST_RESPONSE_PERSON_ID_MY_VIEW=我的客户"
        ),
    },
    "include_raw": {"type": "boolean", "description": "调试开关；true 时返回 raw_resultList/raw_response"},
}

TOOL_SCHEMAS = [
    {
        "name": "query_customer_list",
        "description": (
            "查询客户列表，支持默认、部门、我的、客户部门和重名客户视图；"
            "返回 count、columns、data/normalized_data。"
        ),
        "inputSchema": {"type": "object", "properties": _PROPERTIES},
    }
]
