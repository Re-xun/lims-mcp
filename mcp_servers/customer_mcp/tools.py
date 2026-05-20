"""MCP tools for customer queries (LIMS AbdCustomerListAction)."""
import json
import os
import sys
import httpx

JAVA_API_BASE = os.environ.get("JAVA_API_BASE", "http://localhost:8080")

# ── filter field mapping ──────────────────────────────────────────
# (column_expression, operator_template) — operator_template uses {value} placeholder
_FILTER_CONFIG: dict[str, tuple[str, str]] = {
    "customer_name":              ("customerNameCn",          "like '%{value}%'"),
    "customer_name_en":           ("customerNameEn",          "like '%{value}%'"),
    "customer_no":                ("customerNo",              "like '%{value}%'"),
    "short_name":                 ("shortName",               "like '%{value}%'"),
    "address":                    ("aca.ADDRESS_CN",          "like '%{value}%'"),
    "responsible_department":     ("ad.department_name",      "like '%{value}%'"),
    "responsible_for_business":   ("ap.PERSON_NAME",          "like '%{value}%'"),
    "customer_status":            ("ac.customerStatus",       "like '%{value}%'"),
    "customer_phase":             ("ac.customerPhase",        "= {value}"),
    "rstatus":                    ("ac.rstatus",              "= {value}"),
    "settlement_type":            ("ac.settlementType",       "= {value}"),
    "create_on_start":            ("ac.createOn",             ">= '{value}'"),
    "create_on_end":              ("ac.createOn",             "<= '{value}'"),
}


async def query_customer_list(
    token: str,
    # ── pagination ──
    start: int = 0,
    limit: int = 10,
    # ── data view ──
    data_type: str = "LIST_ALL_VIEW",
    customer_type: int = None,
    # ── filter conditions ──
    filter: str = None,
    keyword: str = None,
    customer_no: str = None,
    customer_status: str = None,
    customer_phase: int = None,
    customer_name: str = None,
    customer_name_en: str = None,
    short_name: str = None,
    address: str = None,
    responsible_department: str = None,
    responsible_for_business: str = None,
    rstatus: int = None,
    settlement_type: int = None,
    create_on_start: str = None,
    create_on_end: str = None,
) -> dict:
    """查询客户列表（分页）。

    所有 filter 参数均为可选，传入多个条件时进行 AND 组合。
    返回: {"count": <总数>, "resultList": [<客户对象>, ...]}
    """
    if start is None:
        start = 0
    if limit is None:
        limit = 10
    params = {"start": str(start), "limit": str(limit)}

    # 如果 LLM 传了 filter 参数，当作 keyword 别名处理
    if filter and not keyword:
        keyword = filter

    # keyword 作为通用搜索：未指定其他筛选条件时，自动按客户中文名称模糊匹配
    if keyword and not customer_name:
        customer_name = keyword

    # 组装 filter SQL 表达式，例如: customerNameCn like '%深圳%' and ac.rstatus = 2
    conditions = []
    for py_name, (column, op_template) in _FILTER_CONFIG.items():
        val = locals()[py_name]
        if val is not None and val != "":
            conditions.append(f"{column} {op_template.format(value=val)}")

    if conditions:
        params["filter"] = " and ".join(conditions)

    # 组装 sVars
    s_vars = {"dataType": data_type or "LIST_ALL_VIEW"}
    if customer_type is not None:
        s_vars["customerType"] = customer_type
    params["sVars"] = json.dumps(s_vars, ensure_ascii=False)

    api_url = f"{JAVA_API_BASE}/AbdCustomerListAction/listQuery"
    # 后台监控：打印实际发出的请求
    sys.stderr.write(f"\n[API REQUEST] GET {api_url}\n")
    for k, v in params.items():
        sys.stderr.write(f"  {k} = {v}\n")
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
        # 附加调试信息：实际发出的 API 请求
        debug_params = {k: v for k, v in params.items()}
        data["_api_call"] = {
            "method": "GET",
            "url": api_url,
            "params": debug_params,
            "token_masked": token[:8] + "***" if token and len(token) > 8 else "***",
        }
        return data


TOOL_HANDLERS = {"query_customer_list": query_customer_list}

TOOL_SCHEMAS = [
    {
        "name": "query_customer_list",
        "description": (
            "查询客户列表（分页），支持 12 个筛选条件 AND 组合。"
            "返回分页结果，包含 count(总数) 和 resultList(客户列表)。"
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                # ── pagination ──
                "start": {
                    "type": "integer",
                    "description": "分页起始位置，默认 0",
                },
                "limit": {
                    "type": "integer",
                    "description": "每页条数，默认 10",
                },
                # ── data view ──
                "data_type": {
                    "type": "string",
                    "description": (
                        "数据视图类型："
                        "LIST_ALL_VIEW=全部客户, "
                        "LIST_DEPT_VIEW=本部门客户(强制 rstatus=1), "
                        "LIST_RESPONSE_PERSON_ID_MY_VIEW=我负责的客户"
                    ),
                },
                "customer_type": {
                    "type": "integer",
                    "description": "客户类型 ID",
                },
                # ── filter fields ──
                "filter": {
                    "type": "string",
                    "description": "等同于 keyword，自动按客户中文名称模糊匹配",
                },
                "keyword": {
                    "type": "string",
                    "description": "通用搜索关键词，自动按客户中文名称模糊匹配。如果用户只说一个词没有指定字段（如\"深圳\"、\"腾讯\"），就用这个",
                },
                "customer_no": {
                    "type": "string",
                    "description": "客户编号，支持精确/模糊匹配 (q_customerNo → ac.customer_no)",
                },
                "customer_status": {
                    "type": "string",
                    "description": (
                        "客户状态，来自 abd_lookup_code 表(CUSTOMER_STATUS)。"
                        "常用值: 意向客户, 潜在客户, 重点客户 (q_customerStatus → ac.customer_status)"
                    ),
                },
                "customer_phase": {
                    "type": "integer",
                    "description": (
                        "客户阶段 (q_customerPhase → ac.customerPhase): "
                        "1=未合作, 2=已合作"
                    ),
                },
                "customer_name": {
                    "type": "string",
                    "description": "客户中文名称，模糊匹配 (q_customerName → ac.customer_name_cn)",
                },
                "customer_name_en": {
                    "type": "string",
                    "description": "客户英文名称，模糊匹配 (q_customerNameEn → ac.customer_name_en)",
                },
                "short_name": {
                    "type": "string",
                    "description": "客户简称，模糊匹配 (q_shortName → ac.short_name)",
                },
                "address": {
                    "type": "string",
                    "description": "地址，跨表到地址表，模糊匹配 (q_address → aca.ADDRESS_CN)",
                },
                "responsible_department": {
                    "type": "string",
                    "description": "负责部门名称，模糊匹配 (q_responsibleDepartment → ad.department_name)",
                },
                "responsible_for_business": {
                    "type": "string",
                    "description": "负责销售姓名，模糊匹配 (q_responsibleForBusiness → ap.PERSON_NAME)",
                },
                "rstatus": {
                    "type": "integer",
                    "description": (
                        "审核状态 (q_rstatus → ac.rstatus): "
                        "0=已作废, 1=已审核, 2=暂存, 3=等待重新审批, 4=审批中"
                    ),
                },
                "settlement_type": {
                    "type": "integer",
                    "description": (
                        "结算类型 (q_settlementType → ac.settlementType): "
                        "0=非月结, 1=月结客户"
                    ),
                },
                "create_on_start": {
                    "type": "string",
                    "description": "创建日期起始 (>=)，格式 YYYY-MM-DD (q_createOn → ac.create_on)",
                },
                "create_on_end": {
                    "type": "string",
                    "description": "创建日期截止 (<=)，格式 YYYY-MM-DD (q_createOnEnd → ac.create_on)",
                },
            },
        },
    },
]
