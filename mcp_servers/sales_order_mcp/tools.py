"""MCP tools for sales order/合同 queries (LIMS SdSalesOrderListAction)."""
import json
import os
import sys
import httpx

JAVA_API_BASE = os.environ.get("JAVA_API_BASE", "http://localhost:8080")

_FILTER_CONFIG: dict[str, tuple[str, str]] = {
    "sales_order_no":                  ("sso.sales_order_no",                       "like '%{value}%'"),
    "customer_short_name":             ("ac.CUSTOMER_NAME_CN",                      "like '%{value}%'"),
    "terminal_authorization_customer":  ("sso.terminal_authorization_customer_name", "like '%{value}%'"),
    "query_sale_person":               ("ap.PERSON_NAME",                           "like '%{value}%'"),
    "query_sale_dept":                 ("ad.department_name",                       "like '%{value}%'"),
    "delivery_specialist":             ("ap2.PERSON_NAME",                          "like '%{value}%'"),
    "service_item":                    ("sso.service_item_desc",                    "like '%{value}%'"),
    "sample_name_cn":                  ("sso.sample_name_cn",                       "like '%{value}%'"),
    "sample_model_cn":                 ("sso.sample_model_cn",                      "like '%{value}%'"),
    "sales_order_type":                ("sso.bill_type_id",                         "like '%{value}%'"),
    "invoice_status":                  ("sso.invoice_status",                       "= {value}"),
    "bstatus_receive":                 ("sso.bstatus_receive",                      "= {value}"),
    "contract_amount":                 ("sso.amt_with_tax_local",                   "= {value}"),
    "create_on_start":                 ("sso.create_on",                            ">= '{value}'"),
    "create_on_end":                   ("sso.create_on",                            "<= '{value}'"),
    "sales_date_start":                ("sso.sales_date",                           ">= '{value}'"),
    "sales_date_end":                  ("sso.sales_date",                           "<= '{value}'"),
    "latest_payment_date_start":       ("sso.latest_payment_date",                  ">= '{value}'"),
    "latest_payment_date_end":         ("sso.latest_payment_date",                  "<= '{value}'"),
    "latest_expense_date_start":       ("sso.latest_expense_date",                  ">= '{value}'"),
    "latest_expense_date_end":         ("sso.latest_expense_date",                  "<= '{value}'"),
    "bstatus_attachment":              ("sso.bstatus_attachment",                   "= {value}"),
    "bstatus":                         ("sso.bstatus",                              "= {value}"),
    "bstatus_project":                 ("sso.bstatus_project",                      "= {value}"),
    "invoiced_amt":                    ("sso.invoiced_amt",                         "> {value}"),
    "rstatus":                         ("sso.rstatus",                              "= {value}"),
    "project_date_start":              ("sso.start_date",                           ">= '{value}'"),
    "project_date_end":                ("sso.start_date",                           "<= '{value}'"),
    "actuality_finish_date_start":     ("sso.actuality_finish_date",                ">= '{value}'"),
    "actuality_finish_date_end":       ("sso.actuality_finish_date",                "<= '{value}'"),
}


async def query_sales_order_list(
    token: str,
    action: str = "listQuery",
    start: int = 0,
    limit: int = 10,
    data_type: str = "LIST_ALL_VIEW",
    filter: str = None,
    keyword: str = None,
    sales_order_no: str = None,
    customer_short_name: str = None,
    terminal_authorization_customer: str = None,
    query_sale_person: str = None,
    query_sale_dept: str = None,
    delivery_specialist: str = None,
    service_item: str = None,
    sample_name_cn: str = None,
    sample_model_cn: str = None,
    sales_order_type: str = None,
    invoice_status: int = None,
    bstatus_receive: int = None,
    contract_amount: float = None,
    create_on_start: str = None,
    create_on_end: str = None,
    sales_date_start: str = None,
    sales_date_end: str = None,
    latest_payment_date_start: str = None,
    latest_payment_date_end: str = None,
    latest_expense_date_start: str = None,
    latest_expense_date_end: str = None,
    bstatus_attachment: int = None,
    bstatus: int = None,
    bstatus_project: int = None,
    invoiced_amt: float = None,
    rstatus: int = None,
    project_date_start: str = None,
    project_date_end: str = None,
    actuality_finish_date_start: str = None,
    actuality_finish_date_end: str = None,
) -> dict:
    """查询销售订单/合同列表（分页），支持多筛选条件 AND 组合。
    返回: {"count": <总数>, "resultList": [<销售订单对象>, ...]}
    """
    if start is None:
        start = 0
    if limit is None:
        limit = 10
    if not action:
        action = "listQuery"

    params = {"start": str(start), "limit": str(limit)}

    if filter and not keyword:
        keyword = filter

    if keyword and not customer_short_name:
        customer_short_name = keyword

    conditions = []
    for py_name, (column, op_template) in _FILTER_CONFIG.items():
        val = locals()[py_name]
        if val is not None and val != "":
            conditions.append(f"{column} {op_template.format(value=val)}")

    if conditions:
        params["filter"] = " and ".join(conditions)

    s_vars = {"dataType": data_type or "LIST_ALL_VIEW"}
    params["sVars"] = json.dumps(s_vars, ensure_ascii=False)

    if not action:
        action = "listQuery"
    api_url = f"{JAVA_API_BASE}/SdSalesOrderListAction/{action}"
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
        debug_params = {k: v for k, v in params.items()}
        data["_api_call"] = {
            "method": "GET",
            "url": api_url,
            "params": debug_params,
            "token_masked": token[:8] + "***" if token and len(token) > 8 else "***",
        }
        return data


async def query_sales_order_by_id(
    token: str,
    id: str,
) -> dict:
    """按ID查询销售订单/合同详情"""
    api_url = f"{JAVA_API_BASE}/SdSalesOrderListAction/getOneById"
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            api_url,
            headers={"x-access-token": token},
            params={"id": id},
        )
        response.raise_for_status()
        data = response.json()
        data["_api_call"] = {
            "method": "GET",
            "url": api_url,
            "params": {"id": id},
            "token_masked": token[:8] + "***" if token and len(token) > 8 else "***",
        }
        return data


TOOL_HANDLERS = {
    "query_sales_order_list": query_sales_order_list,
    "query_sales_order_by_id": query_sales_order_by_id,
}

TOOL_SCHEMAS = [
    {
        "name": "query_sales_order_list",
        "description": (
            "查询销售订单/合同列表（分页），支持多筛选条件 AND 组合。"
            "action可选：listQuery(默认), listQueryMy(我的), listQueryDept(部门), "
            "listQueryUnpaid(未付款), listQueryInvoice(已开票), "
            "listQueryApprovedUninvoiced(已审批未开票), listQueryFinal(已结案未完票), "
            "listQueryUnderway(进行中), listQueryCancel(已作废), "
            "listQueryTop10SaleAmt(金额Top10), listQueryMyUnReceive(我的未收款)。"
            "返回分页结果，包含 count(总数) 和 resultList(销售订单列表)。"
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "查询类型，默认listQuery",
                },
                "start": {
                    "type": "integer",
                    "description": "分页起始位置，默认0",
                },
                "limit": {
                    "type": "integer",
                    "description": "每页条数，默认10",
                },
                "filter": {
                    "type": "string",
                    "description": "等同于 keyword，自动按客户名称模糊匹配",
                },
                "keyword": {
                    "type": "string",
                    "description": "通用搜索关键词，自动按客户名称模糊匹配。如果用户只说一个词没有指定字段，就用这个",
                },
                "sales_order_no": {
                    "type": "string",
                    "description": "销售合同号，模糊匹配 (sso.sales_order_no)",
                },
                "customer_short_name": {
                    "type": "string",
                    "description": "客户名称，模糊匹配，跨表到客户表 (ac.CUSTOMER_NAME_CN)",
                },
                "terminal_authorization_customer": {
                    "type": "string",
                    "description": "授权方/终端客户，模糊匹配 (sso.terminal_authorization_customer_name)",
                },
                "query_sale_person": {
                    "type": "string",
                    "description": "负责销售姓名，模糊匹配 (ap.PERSON_NAME)",
                },
                "query_sale_dept": {
                    "type": "string",
                    "description": "销售部门，模糊匹配 (ad.department_name)",
                },
                "delivery_specialist": {
                    "type": "string",
                    "description": "交付专员，模糊匹配 (ap2.PERSON_NAME)",
                },
                "service_item": {
                    "type": "string",
                    "description": "服务项目/合同描述，模糊匹配 (sso.service_item_desc)",
                },
                "sample_name_cn": {
                    "type": "string",
                    "description": "样品名称，模糊匹配 (sso.sample_name_cn)",
                },
                "sample_model_cn": {
                    "type": "string",
                    "description": "样品型号，模糊匹配 (sso.sample_model_cn)",
                },
                "sales_order_type": {
                    "type": "string",
                    "description": (
                        "合同类别 (sso.bill_type_id): "
                        "SO-01=服务合同, SO-02=租场试验"
                    ),
                },
                "invoice_status": {
                    "type": "integer",
                    "description": (
                        "开票状态 (sso.invoice_status): "
                        "20=未开票, 30=已部分开票, 40=不开票, 50=开齐票"
                    ),
                },
                "bstatus_receive": {
                    "type": "integer",
                    "description": (
                        "收款状态 (sso.bstatus_receive): "
                        "20=未收款, 30=已收部分款, 50=结清"
                    ),
                },
                "contract_amount": {
                    "type": "number",
                    "description": "人民币合同金额，等值匹配 (sso.amt_with_tax_local)",
                },
                "create_on_start": {
                    "type": "string",
                    "description": "合同创建日期起始 (>=)，格式 YYYY-MM-DD (sso.create_on)",
                },
                "create_on_end": {
                    "type": "string",
                    "description": "合同创建日期截止 (<=)，格式 YYYY-MM-DD (sso.create_on)",
                },
                "sales_date_start": {
                    "type": "string",
                    "description": "开单日期起始 (>=)，格式 YYYY-MM-DD (sso.sales_date)",
                },
                "sales_date_end": {
                    "type": "string",
                    "description": "开单日期截止 (<=)，格式 YYYY-MM-DD (sso.sales_date)",
                },
                "latest_payment_date_start": {
                    "type": "string",
                    "description": "最新收款日期起始 (>=)，格式 YYYY-MM-DD (sso.latest_payment_date)",
                },
                "latest_payment_date_end": {
                    "type": "string",
                    "description": "最新收款日期截止 (<=)，格式 YYYY-MM-DD (sso.latest_payment_date)",
                },
                "latest_expense_date_start": {
                    "type": "string",
                    "description": "最新付款日期起始 (>=)，格式 YYYY-MM-DD (sso.latest_expense_date)",
                },
                "latest_expense_date_end": {
                    "type": "string",
                    "description": "最新付款日期截止 (<=)，格式 YYYY-MM-DD (sso.latest_expense_date)",
                },
                "bstatus_attachment": {
                    "type": "integer",
                    "description": (
                        "附件状态 (sso.bstatus_attachment): "
                        "0=无附件, 1=有附件"
                    ),
                },
                "bstatus": {
                    "type": "integer",
                    "description": (
                        "合同业务状态 (sso.bstatus): "
                        "20=未开案, 30=案件进行中, 40=结案收款中, 45=结案已收款, 50=结束, 60=取消"
                    ),
                },
                "bstatus_project": {
                    "type": "integer",
                    "description": (
                        "开案状态 (sso.bstatus_project): "
                        "0=未开案, 1=已开案, 2=开案中"
                    ),
                },
                "invoiced_amt": {
                    "type": "number",
                    "description": "已开票金额，大于该值 (sso.invoiced_amt)",
                },
                "rstatus": {
                    "type": "integer",
                    "description": (
                        "审核状态 (sso.rstatus): "
                        "0=草稿, 1=已审核, 2=待审核, -1=作废"
                    ),
                },
                "project_date_start": {
                    "type": "string",
                    "description": "开案日期起始 (>=)，格式 YYYY-MM-DD (sso.start_date)",
                },
                "project_date_end": {
                    "type": "string",
                    "description": "开案日期截止 (<=)，格式 YYYY-MM-DD (sso.start_date)",
                },
                "actuality_finish_date_start": {
                    "type": "string",
                    "description": "结束日期起始 (>=)，格式 YYYY-MM-DD (sso.actuality_finish_date)",
                },
                "actuality_finish_date_end": {
                    "type": "string",
                    "description": "结束日期截止 (<=)，格式 YYYY-MM-DD (sso.actuality_finish_date)",
                },
            },
        },
    },
    {
        "name": "query_sales_order_by_id",
        "description": "按ID查询销售订单/合同详情",
        "inputSchema": {
            "type": "object",
            "properties": {
                "id": {
                    "type": "string",
                    "description": "销售订单ID",
                },
            },
            "required": ["id"],
        },
    },
]
