"""MCP tools for quotation list queries (LIMS SdQuotationListAction).

Source: SdQuotationListAction.java
  com.yiuser.lims.sd.sdquotation.SdQuotationListAction

XML bindings:
  SdQuotationListV2.xml  (scope=default)
  SdQuotationDeptListV2.xml (scope=dept)
  SdQuotationMyListV2.xml   (scope=my)
"""
from __future__ import annotations

import json
import os
import sys
from typing import Any

import httpx

JAVA_API_BASE = os.environ.get("JAVA_API_BASE", "http://localhost:8080")

# ── scope → endpoint + sVar ──────────────────────────────────────────
SCOPE_TO_ACTION = {
    "default": "listQuery",
    "dept": "listQueryDept",
    "my": "listQueryMy",
}

SCOPE_TO_CUSTOMER_TYPE = {
    "default": 1,
    "dept": 2,
    "my": 3,
}

SCOPE_DATATYPE_OPTIONS: dict[str, list[str]] = {
    "default": ["listView", "Last30days", "NotSignedBack"],
    "dept": ["listView", "Last30days", "Month", "LastMonth"],
    "my": ["listView", "Last30days", "Month", "LastMonth"],
}

SCOPE_DATATYPE_DEFAULTS: dict[str, str] = {
    "default": "Last30days",
    "dept": "listView",
    "my": "listView",
}

# ── filter config (section 4 查询字段 + section 4.1 候选字段) ──────
FILTER_CONFIG: dict[str, dict[str, str]] = {
    # ── 核心筛选（第 4 节） ──
    "bstatus": {"backend_field": "sq.bstatus", "template": "= {value}"},
    "create_on_end": {"backend_field": "sq.create_on", "template": "<= '{value}'"},
    "create_on_start": {"backend_field": "sq.create_on", "template": ">= '{value}'"},
    "fast_search": {"backend_field": "fastSearch", "template": "like '%{value}%'"},
    "quotation_no": {"backend_field": "sq.quotation_no", "template": "like '%{value}%'"},
    "rstatus": {"backend_field": "sq.rstatus", "template": "= {value}"},
    "sale_dept": {"backend_field": "ad.department_name", "template": "like '%{value}%'"},
    "sale_person": {"backend_field": "ap.PERSON_NAME", "template": "like '%{value}%'"},
    "sample_model_cn": {"backend_field": "sq.sample_model_cn", "template": "like '%{value}%'"},
    "sample_name_cn": {"backend_field": "sq.sample_name_cn", "template": "like '%{value}%'"},
    "service_item_desc": {"backend_field": "sq.service_item_desc", "template": "like '%{value}%'"},
    "short_customer_name": {"backend_field": "ac1.CUSTOMER_NAME_CN", "template": "like '%{value}%'"},
    "terminal_authorization_customer": {"backend_field": "sq.terminal_authorization_customer_name", "template": "like '%{value}%'"},
    # ── 候选 filter（第 4.1 节，根据列表返回列反推） ──
    "amt_with_tax_currency": {"backend_field": "amtWithTaxCurrency", "template": "like '%{value}%'"},
    "department_name": {"backend_field": "departmentName", "template": "like '%{value}%'"},
    "last_update_on_end": {"backend_field": "lastUpdateOn", "template": "<= '{value}'"},
    "last_update_on_start": {"backend_field": "lastUpdateOn", "template": ">= '{value}'"},
    "net_profits_ratio": {"backend_field": "netProfitsRatio", "template": "like '%{value}%'"},
    "remark": {"backend_field": "remark", "template": "like '%{value}%'"},
    "saler_name": {"backend_field": "salerName", "template": "like '%{value}%'"},
    "sum_unit_price_with_sub_currency": {"backend_field": "sumUnitPriceWithSubCurrency", "template": "like '%{value}%'"},
    "terminal_authorization_customer_name": {"backend_field": "terminalAuthorizationCustomerName", "template": "like '%{value}%'"},
}

# ── FIELD_LABELS（第 6 节，按前端展示顺序） ──────────────────────
FIELD_LABELS: dict[str, dict[str, str]] = {
    "rstatus": {"key": "rstatus", "title": "单据状态"},
    "createOn": {"key": "create_on", "title": "创建日期"},
    "bstatus": {"key": "bstatus", "title": "报价单状态"},
    "lastUpdateOn": {"key": "last_update_on", "title": "更新日期"},
    "quotationNo": {"key": "quotation_no", "title": "报价单号"},
    "shortCustomerName": {"key": "short_customer_name", "title": "客户名称"},
    "terminalAuthorizationCustomerName": {"key": "terminal_authorization_customer_name", "title": "授权方终端客户"},
    "serviceItemDesc": {"key": "service_item_desc", "title": "项目描述"},
    "sampleNameCn": {"key": "sample_name_cn", "title": "样品名称"},
    "sampleModelCn": {"key": "sample_model_cn", "title": "样品型号"},
    "sumUnitPriceWithSubCurrency": {"key": "sum_unit_price_with_sub_currency", "title": "报价金额"},
    "amtWithTaxCurrency": {"key": "amt_with_tax_currency", "title": "优惠后金额"},
    "netProfitsRatio": {"key": "net_profits_ratio", "title": "利润率%"},
    "salerName": {"key": "saler_name", "title": "销售"},
    "departmentName": {"key": "department_name", "title": "部门"},
    "remark": {"key": "remark", "title": "内部备注"},
}

# ── ENUM_FIELDS（第 8 节） ────────────────────────────────────────
ENUM_FIELDS: dict[str, dict[int, str]] = {
    "bstatus": {
        1: "未签回",
        2: "已签回",
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
    if resolved not in SCOPE_TO_ACTION:
        raise ValueError(
            "不支持的 scope/view 值：{}。可选值：{}".format(
                resolved, ", ".join(sorted(SCOPE_TO_ACTION))
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
    *,
    scope: str,
    start: int = 0,
    limit: int = 10,
    data_type: str | None = None,
    **filter_values: Any,
) -> dict[str, str]:
    params: dict[str, str] = {
        "start": str(0 if start is None else start),
        "limit": str(10 if limit is None else limit),
    }

    svar_data: dict[str, Any] = {
        "customerType": SCOPE_TO_CUSTOMER_TYPE[scope],
    }
    resolved_data_type = data_type or SCOPE_DATATYPE_DEFAULTS.get(scope)
    if resolved_data_type:
        svar_data["dataType"] = resolved_data_type
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


async def query_quotation_list(
    token: str,
    scope: str = "default",
    view: str | None = None,
    start: int = 0,
    limit: int = 10,
    data_type: str | None = None,
    # ── 核心筛选（第 4 节） ──
    bstatus: int | None = None,
    create_on_end: str | None = None,
    create_on_start: str | None = None,
    fast_search: str | None = None,
    quotation_no: str | None = None,
    rstatus: int | None = None,
    sale_dept: str | None = None,
    sale_person: str | None = None,
    sample_model_cn: str | None = None,
    sample_name_cn: str | None = None,
    service_item_desc: str | None = None,
    short_customer_name: str | None = None,
    terminal_authorization_customer: str | None = None,
    # ── 候选 filter（第 4.1 节） ──
    amt_with_tax_currency: str | None = None,
    department_name: str | None = None,
    last_update_on_end: str | None = None,
    last_update_on_start: str | None = None,
    net_profits_ratio: str | None = None,
    remark: str | None = None,
    saler_name: str | None = None,
    sum_unit_price_with_sub_currency: str | None = None,
    terminal_authorization_customer_name: str | None = None,
    include_raw: bool = False,
) -> dict[str, Any]:
    """查询报价单列表，通过 scope/view 路由到全部、部门、我的三个后端列表接口。

    继承自 ListBaseAction，default 包含 /SdQuotationListAction/listQuery。
    """
    resolved_scope = _resolve_scope(scope=scope, view=view)
    params = build_params(
        scope=resolved_scope,
        start=start,
        limit=limit,
        data_type=data_type,
        # 核心
        bstatus=bstatus,
        create_on_end=create_on_end,
        create_on_start=create_on_start,
        fast_search=fast_search,
        quotation_no=quotation_no,
        rstatus=rstatus,
        sale_dept=sale_dept,
        sale_person=sale_person,
        sample_model_cn=sample_model_cn,
        sample_name_cn=sample_name_cn,
        service_item_desc=service_item_desc,
        short_customer_name=short_customer_name,
        terminal_authorization_customer=terminal_authorization_customer,
        # 候选
        amt_with_tax_currency=amt_with_tax_currency,
        department_name=department_name,
        last_update_on_end=last_update_on_end,
        last_update_on_start=last_update_on_start,
        net_profits_ratio=net_profits_ratio,
        remark=remark,
        saler_name=saler_name,
        sum_unit_price_with_sub_currency=sum_unit_price_with_sub_currency,
        terminal_authorization_customer_name=terminal_authorization_customer_name,
    )
    api_url = "{}/SdQuotationListAction/{}".format(JAVA_API_BASE, SCOPE_TO_ACTION[resolved_scope])

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


async def query_quotation_list_by_customer_id(
    token: str,
    data_id: str,
    start: int = 0,
    limit: int = 10,
) -> dict[str, Any]:
    """按客户 ID 查询关联报价单明细列表，对应 SdQuotationListAction/AGridSelectAll。"""
    params = {
        "start": str(0 if start is None else start),
        "limit": str(10 if limit is None else limit),
        "dataId": data_id,
        "sVars": json.dumps({}, ensure_ascii=False),
    }
    api_url = "{}/SdQuotationListAction/AGridSelectAll".format(JAVA_API_BASE)

    sys.stderr.write("\n[API REQUEST] GET {}\n".format(api_url))
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
        data = response.json()
        data["_api_call"] = {
            "method": "GET",
            "url": api_url,
            "params": dict(params),
            "token_masked": _mask_token(token),
        }
        return data


TOOL_HANDLERS = {
    "query_quotation_list": query_quotation_list,
    "query_quotation_list_by_customer_id": query_quotation_list_by_customer_id,
}

_PROPERTIES: dict[str, dict[str, Any]] = {
    "scope": {
        "type": "string",
        "description": (
            "视图范围：default=全部报价单 (listQuery/SdQuotationListV2.xml), "
            "dept=部门报价单 (listQueryDept/SdQuotationDeptListV2.xml), "
            "my=我的报价单 (listQueryMy/SdQuotationMyListV2.xml)。"
            "default 包含继承的 /SdQuotationListAction/listQuery。"
        ),
    },
    "view": {"type": "string", "description": "scope 的别名参数；如果同时传入 scope 和 view，则以 scope 为准。"},
    "start": {"type": "integer", "description": "分页起始位置，默认 0。"},
    "limit": {"type": "integer", "description": "每页条数，默认 10。"},
    "data_type": {
        "type": "string",
        "description": (
            "日期筛选视图（sVars.dataType），按 scope 不同可选值各异。"
            "default=全部：listView(全部报价单)/Last30days(最近30天报价单)/NotSignedBack(全部未签回报价单)，默认 Last30days；"
            "dept=部门：listView(我部门全部报价单)/Last30days(我部门最近30天报价单)/Month(我部门本月报价单)/LastMonth(我部门上月报价单)，默认 listView；"
            "my=我的：listView(我的全部报价单)/Last30days(我的最近30天报价单)/Month(我的本月报价单)/LastMonth(我的上月报价单)，默认 listView。"
        ),
    },
    # ── 核心筛选（第 4 节） ──
    "bstatus": {
        "type": "integer",
        "description": "报价单状态 (q_bstatus → sq.bstatus): 1=未签回, 2=已签回。枚举 ref_id: com.yiuser.lims.sd.bstatus。",
    },
    "create_on_end": {
        "type": "string",
        "description": "创建日期截止，格式 YYYY-MM-DD (query_todate → sq.create_on, <=)。仅 listQuery (SdQuotationListV2.xml) 有此条件。",
    },
    "create_on_start": {
        "type": "string",
        "description": "创建日期起始，格式 YYYY-MM-DD (query_fromdate → sq.create_on, >=)。仅 listQuery (SdQuotationListV2.xml) 有此条件。",
    },
    "fast_search": {
        "type": "string",
        "description": "视图快速搜索，模糊匹配 (fastSearch → fastSearch)。",
    },
    "quotation_no": {
        "type": "string",
        "description": "报价单号，模糊匹配 (quotationNo → sq.quotation_no)。",
    },
    "rstatus": {
        "type": "integer",
        "description": "单据状态 (q_rstatus → sq.rstatus): 0=已作废, 1=已审核, 2=暂存, 3=等待重新审批, 4=审批中。枚举 ref_id: com.yiuser.base.ab.rstatus。",
    },
    "sale_dept": {
        "type": "string",
        "description": "销售部门，模糊匹配 (querySaleDept → ad.department_name)。",
    },
    "sale_person": {
        "type": "string",
        "description": "负责销售，模糊匹配 (querySalePerson → ap.PERSON_NAME)。",
    },
    "sample_model_cn": {
        "type": "string",
        "description": (
            "样品型号，模糊匹配 (sampleModelCn → sq.sample_model_cn)。"
            "说明：`SdQuotationMyListV2.xml` 曾出现映射到 `sq.sample_name_en` 的差异，"
            "当前 MCP 默认按主列表/部门列表的稳定映射处理。"
        ),
    },
    "sample_name_cn": {
        "type": "string",
        "description": "样品名称，模糊匹配 (sampleNameCn → sq.sample_name_cn)。",
    },
    "service_item_desc": {
        "type": "string",
        "description": "项目描述，模糊匹配 (serviceItemDesc → sq.service_item_desc)。",
    },
    "short_customer_name": {
        "type": "string",
        "description": "客户名称，模糊匹配 (shortCustomerName → ac1.CUSTOMER_NAME_CN)。",
    },
    "terminal_authorization_customer": {
        "type": "string",
        "description": "授权方终端客户，模糊匹配 (terminalAuthorizationCustomer → sq.terminal_authorization_customer_name)。",
    },
    # ── 候选 filter（第 4.1 节，根据列表返回列反推） ──
    "amt_with_tax_currency": {
        "type": "string",
        "description": "优惠后金额，候选 filter，模糊匹配 (amtWithTaxCurrency → amtWithTaxCurrency)，置信度：低。",
    },
    "department_name": {
        "type": "string",
        "description": "部门，候选 filter，模糊匹配 (departmentName → departmentName)，置信度：低。",
    },
    "last_update_on_end": {
        "type": "string",
        "description": "更新日期结束，候选 filter，格式 YYYY-MM-DD (lastUpdateOn, <=)，置信度：中。",
    },
    "last_update_on_start": {
        "type": "string",
        "description": "更新日期开始，候选 filter，格式 YYYY-MM-DD (lastUpdateOn, >=)，置信度：中。",
    },
    "net_profits_ratio": {
        "type": "string",
        "description": "利润率%，候选 filter，模糊匹配 (netProfitsRatio → netProfitsRatio)，置信度：低。",
    },
    "remark": {
        "type": "string",
        "description": "内部备注，候选 filter，模糊匹配 (remark → remark)，置信度：低。",
    },
    "saler_name": {
        "type": "string",
        "description": "销售，候选 filter，模糊匹配 (salerName → salerName)，置信度：低。",
    },
    "sum_unit_price_with_sub_currency": {
        "type": "string",
        "description": "报价金额，候选 filter，模糊匹配 (sumUnitPriceWithSubCurrency → sumUnitPriceWithSubCurrency)，置信度：低。",
    },
    "terminal_authorization_customer_name": {
        "type": "string",
        "description": "授权方终端客户，候选 filter，模糊匹配 (terminalAuthorizationCustomerName → terminalAuthorizationCustomerName)，置信度：低。",
    },
    "include_raw": {
        "type": "boolean",
        "description": "调试用。默认 false；为 true 时才返回后端原始 raw_resultList/raw_response。",
    },
}

TOOL_SCHEMAS = [
    {
        "name": "query_quotation_list",
        "description": (
            "查询报价单列表。通过 scope/view 路由到全部(default)、部门(dept)、我的(my)三个后端列表接口，"
            "继承自 ListBaseAction，default 包含 /SdQuotationListAction/listQuery。"
            "暴露第 4 节核心 filter 与第 4.1 节候选 filter，返回 count、columns、data/normalized_data。"
            "源码：com.yiuser.lims.sd.sdquotation.SdQuotationListAction。"
        ),
        "inputSchema": {"type": "object", "properties": _PROPERTIES},
    },
    {
        "name": "query_quotation_list_by_customer_id",
        "description": "按客户 ID 查询关联报价单明细列表，对应 SdQuotationListAction/AGridSelectAll。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "data_id": {
                    "type": "string",
                    "description": "客户 ID，必填 (dataId → dataId)。",
                },
                "start": {
                    "type": "integer",
                    "description": "分页起始位置，默认 0。",
                },
                "limit": {
                    "type": "integer",
                    "description": "每页条数，默认 10。",
                },
            },
            "required": ["data_id"],
        },
    },
]
