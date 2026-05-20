"""MCP tools for 交付中心案件管理 (LIMS DmProjectListAction).

交付中心核心功能：案件查询、派工、交付跟进
"""
import json
import os
import sys
import httpx

JAVA_API_BASE = os.environ.get("JAVA_API_BASE", "http://localhost:8080")

# -- filter field mapping ------------------------------------------
# (column_expression, operator_template) -- operator_template uses {value} placeholder
_FILTER_CONFIG: dict[str, tuple[str, str]] = {
    # 基础信息字段（文本模糊匹配）
    "project_no":           ("PROJECT_NO",           "like '%{value}%'"),
    "project_name":         ("PROJECT_NAME",         "like '%{value}%'"),
    "contract_no":          ("contract_no",          "like '%{value}%'"),
    "product_no":           ("product_no",           "like '%{value}%'"),
    "txn_source_no":        ("txn_source_no",        "like '%{value}%'"),
    "terminal_customer":    ("terminal_authorization_customer", "like '%{value}%'"),
    
    # 人员/部门字段（ID精确匹配）
    "manager1":             ("MANAGER1",             "= '{value}'"),      # 责任工程师
    "manager2":             ("MANAGER2",             "= '{value}'"),      # 交付专员
    "manager3":             ("MANAGER3",             "= '{value}'"),      # 主管
    "delivery_manager1":    ("delivery_manager1",    "= '{value}'"),      # 客服工程师
    "dept_id":              ("dept_id",              "= '{value}'"),
    "delivery_dept_id":     ("delivery_dept_id",     "= '{value}'"),
    "create_by":            ("CREATE_BY",            "= '{value}'"),
    
    # 客户/合同关联（ID精确匹配）
    "customer_id":          ("customer_id",          "= '{value}'"),
    "sales_order_id":       ("sales_order_id",       "= '{value}'"),
    "applicant_id":         ("applicant_id",         "= '{value}'"),
    
    # 日期范围字段
    "arrival_date_start":   ("arrival_date",         ">= '{value}'"),
    "arrival_date_end":     ("arrival_date",         "<= '{value}'"),
    "start_up_date_start":  ("start_up_date",        ">= '{value}'"),
    "start_up_date_end":    ("start_up_date",        "<= '{value}'"),
    "plan_delivery_date_start":   ("planDeliveryDate",     ">= '{value}'"),  # 核心：计划交付日期
    "plan_delivery_date_end":     ("planDeliveryDate",     "<= '{value}'"),
    "actual_delivery_date_start": ("actualDeliveryDate",   ">= '{value}'"),
    "actual_delivery_date_end":   ("actualDeliveryDate",   "<= '{value}'"),
    "finish_date_start":    ("finish_date",          ">= '{value}'"),
    "finish_date_end":      ("finish_date",          "<= '{value}'"),
    "closed_date_start":    ("closed_date",          ">= '{value}'"),
    "closed_date_end":      ("closed_date",          "<= '{value}'"),
    "create_on_start":      ("CREATE_ON",            ">= '{value}'"),
    "create_on_end":        ("CREATE_ON",            "<= '{value}'"),
    
    # 状态字段（精确匹配）
    "bstatus":              ("BSTATUS",              "= {value}"),        # 案件业务状态
    "rstatus":              ("RSTATUS",              "= {value}"),        # 记录状态
    "is_urgent":            ("isUrgent",             "= {value}"),        # 是否紧急
    "is_public":            ("isPublic",             "= {value}"),        # 是否公海
    
    # 业务类型
    "business_type":        ("businessType",         "= '{value}'"),      # gen/emc/ic/safety/op
}


async def query_project_list(
    token: str,
    # -- action & pagination --
    action: str = "listQuery",
    start: int = 0,
    limit: int = 20,
    # -- data view --
    data_type: str = "conduct",
    # -- filter conditions --
    filter: str = None,
    keyword: str = None,
    # 基础信息
    project_no: str = None,
    project_name: str = None,
    contract_no: str = None,
    product_no: str = None,
    txn_source_no: str = None,
    terminal_customer: str = None,
    # 人员/部门
    manager1: str = None,           # 责任工程师
    manager2: str = None,           # 交付专员
    manager3: str = None,           # 主管
    delivery_manager1: str = None,  # 客服工程师
    dept_id: str = None,
    delivery_dept_id: str = None,
    create_by: str = None,
    # 客户/合同
    customer_id: str = None,
    sales_order_id: str = None,
    applicant_id: str = None,
    # 日期范围
    arrival_date_start: str = None,
    arrival_date_end: str = None,
    start_up_date_start: str = None,
    start_up_date_end: str = None,
    plan_delivery_date_start: str = None,    # 计划交付日期（核心）
    plan_delivery_date_end: str = None,
    actual_delivery_date_start: str = None,
    actual_delivery_date_end: str = None,
    finish_date_start: str = None,
    finish_date_end: str = None,
    closed_date_start: str = None,
    closed_date_end: str = None,
    create_on_start: str = None,
    create_on_end: str = None,
    # 状态
    bstatus: int = None,            # 20=未开案,30=进行中,40=结案收款中,45=结案已收款,50=结束,60=取消,13=已交付
    rstatus: int = None,            # 0=草稿,1=已审核,2=待审核,-1=作废
    is_urgent: int = None,          # 1=紧急
    is_public: int = None,
    # 业务类型
    business_type: str = None,      # gen/emc/ic/safety/op
) -> dict:
    """查询交付中心案件/项目列表（分页），支持多筛选条件 AND 组合。
    
    交付中心核心场景：
    - 交付专员查询【我的案件】（action=listQueryMyAll 或 data_type=my）
    - 客服主管查询【待分配案件】（action=listQueryUnassigned）
    - 查询【即将逾期】案件（plan_delivery_date_end=今天+3天 and bstatus=30）
    
    返回: {"count": <总数>, "resultList": [<案件对象>, ...]}
    """
    # 兜底默认值
    if start is None:
        start = 0
    if limit is None:
        limit = 20
    if not action:
        action = "listQuery"

    params = {"start": str(start), "limit": str(limit)}

    # keyword/filter 处理逻辑
    if filter and not keyword:
        keyword = filter

    # keyword 智能映射：P开头->案件编号，C开头->合同编号，否则->案件名称
    if keyword:
        keyword_upper = keyword.upper()
        if keyword_upper.startswith('P'):
            if not project_no:
                project_no = keyword
        elif keyword_upper.startswith('C'):
            if not contract_no:
                contract_no = keyword
        else:
            if not project_name:
                project_name = keyword

    # 组装 filter SQL 表达式
    conditions = []
    for py_name, (column, op_template) in _FILTER_CONFIG.items():
        val = locals()[py_name]
        if val is not None and val != "":
            conditions.append(f"{column} {op_template.format(value=val)}")

    if conditions:
        params["filter"] = " and ".join(conditions)

    # 组装 sVars
    s_vars = {"dataType": data_type or "conduct"}
    params["sVars"] = json.dumps(s_vars, ensure_ascii=False)

    api_url = f"{JAVA_API_BASE}/DmProjectListAction/{action}"
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


async def query_project_by_id(
    token: str,
    id: str,
) -> dict:
    """按ID查询案件/项目详情（含子项、试验计划、附件、操作日志）"""
    api_url = f"{JAVA_API_BASE}/DmProjectListAction/selectById"
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


async def query_delivery_reminder(
    token: str,
    start: int = 0,
    limit: int = 20,
) -> dict:
    """查询交付提醒列表（首页逾期/即将到期提醒）
    
    自动按当前用户过滤，返回：
    - 即将到期：planDeliveryDate <= 今天+3天 且未结案
    - 已逾期：planDeliveryDate < 今天 且未结案
    - 今日交付：planDeliveryDate = 今天
    """
    if start is None:
        start = 0
    if limit is None:
        limit = 20

    params = {"start": str(start), "limit": str(limit)}
    
    api_url = f"{JAVA_API_BASE}/DmProjectListAction/listQueryDeliveryReminder"
    sys.stderr.write(f"\n[API REQUEST] GET {api_url}\n")
    sys.stderr.write(f"  start = {start}\n")
    sys.stderr.write(f"  limit = {limit}\n")
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
            "params": params,
            "token_masked": token[:8] + "***" if token and len(token) > 8 else "***",
        }
        return data


TOOL_HANDLERS = {
    "query_project_list": query_project_list,
    "query_project_by_id": query_project_by_id,
    "query_delivery_reminder": query_delivery_reminder,
}

TOOL_SCHEMAS = [
    {
        "name": "query_project_list",
        "description": (
            "查询交付中心案件/项目列表（分页），支持多筛选条件 AND 组合。\n"
            "交付中心核心场景：交付专员查【我的案件】、客服主管查【待分配】、查【即将逾期】。\n"
            "action可选：listQuery(标准), listQueryAll(全部), listQueryMyAll(我的), "
            "listQueryUnassigned(待分配), listQueryDeliveryReminder(交付提醒), "
            "listQueryForGen(EMC常规), listQueryForIc(国际认证), listQueryForSafety(安全), listQueryForOP(OP)。\n"
            "dataType可选：conduct(进行中), my(我的), closure(已结案), suspend(未开始/暂停), "
            "urgent(紧急), toBeAssigned(待分配), overdueAndUnresolvedCases(超期未结), unresolvedCases(未结)。\n"
            "返回分页结果，包含 count(总数) 和 resultList(案件列表)。"
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                # Action & Pagination
                "action": {
                    "type": "string",
                    "description": "查询端点，默认listQuery",
                },
                "start": {
                    "type": "integer",
                    "description": "分页起始位置，默认0",
                },
                "limit": {
                    "type": "integer",
                    "description": "每页条数，默认20",
                },
                # Data View
                "data_type": {
                    "type": "string",
                    "description": (
                        "数据范围/业务状态，用于sVars.dataType: "
                        "conduct=进行中(默认), my=我的, closure=已结案, suspend=未开始/暂停, "
                        "urgent=紧急, toBeAssigned=待分配, trueSuspend=暂停中, "
                        "overdueAndUnresolvedCases=超期未结, unresolvedCases=未结, ClosedCasesList=已结案列表"
                    ),
                },
                # Keyword
                "filter": {
                    "type": "string",
                    "description": "等同于 keyword，用于通用搜索",
                },
                "keyword": {
                    "type": "string",
                    "description": "通用搜索关键词。P开头->案件编号，C开头->合同编号，其他->案件名称模糊匹配",
                },
                # 基础信息
                "project_no": {
                    "type": "string",
                    "description": "案件编号，模糊匹配 (PROJECT_NO)",
                },
                "project_name": {
                    "type": "string",
                    "description": "案件名称，模糊匹配 (PROJECT_NAME)",
                },
                "contract_no": {
                    "type": "string",
                    "description": "合同编号，模糊匹配 (contract_no)",
                },
                "product_no": {
                    "type": "string",
                    "description": "样品编码，模糊匹配 (product_no)",
                },
                "txn_source_no": {
                    "type": "string",
                    "description": "来源单据编号 (txn_source_no)",
                },
                "terminal_customer": {
                    "type": "string",
                    "description": "终端客户/授权方，模糊匹配 (terminal_authorization_customer)",
                },
                # 人员/部门（核心）
                "manager1": {
                    "type": "string",
                    "description": "责任工程师ID (MANAGER1)",
                },
                "manager2": {
                    "type": "string",
                    "description": "交付专员ID (MANAGER2)。交付专员查询【我的案件】时用",
                },
                "manager3": {
                    "type": "string",
                    "description": "主管ID (MANAGER3)",
                },
                "delivery_manager1": {
                    "type": "string",
                    "description": "客服工程师ID (delivery_manager1)。客服工程师查询【我的案件】时用",
                },
                "dept_id": {
                    "type": "string",
                    "description": "部门ID (dept_id)",
                },
                "delivery_dept_id": {
                    "type": "string",
                    "description": "客服部门ID (delivery_dept_id)",
                },
                "create_by": {
                    "type": "string",
                    "description": "创建人ID (CREATE_BY)",
                },
                # 客户/合同
                "customer_id": {
                    "type": "string",
                    "description": "客户ID (customer_id)",
                },
                "sales_order_id": {
                    "type": "string",
                    "description": "销售合同ID (sales_order_id)",
                },
                "applicant_id": {
                    "type": "string",
                    "description": "申请商ID (applicant_id)",
                },
                # 日期范围
                "arrival_date_start": {
                    "type": "string",
                    "description": "到案日期起始 (>=)，格式 YYYY-MM-DD (arrival_date)",
                },
                "arrival_date_end": {
                    "type": "string",
                    "description": "到案日期截止 (<=)，格式 YYYY-MM-DD (arrival_date)",
                },
                "start_up_date_start": {
                    "type": "string",
                    "description": "启动日期起始 (>=)，格式 YYYY-MM-DD (start_up_date)",
                },
                "start_up_date_end": {
                    "type": "string",
                    "description": "启动日期截止 (<=)，格式 YYYY-MM-DD (start_up_date)",
                },
                "plan_delivery_date_start": {
                    "type": "string",
                    "description": "【核心】计划交付日期起始 (>=)，格式 YYYY-MM-DD (planDeliveryDate)。查【即将逾期】时用",
                },
                "plan_delivery_date_end": {
                    "type": "string",
                    "description": "【核心】计划交付日期截止 (<=)，格式 YYYY-MM-DD (planDeliveryDate)",
                },
                "actual_delivery_date_start": {
                    "type": "string",
                    "description": "实际交付日期起始 (>=)，格式 YYYY-MM-DD (actualDeliveryDate)",
                },
                "actual_delivery_date_end": {
                    "type": "string",
                    "description": "实际交付日期截止 (<=)，格式 YYYY-MM-DD (actualDeliveryDate)",
                },
                "finish_date_start": {
                    "type": "string",
                    "description": "结束日期起始 (>=)，格式 YYYY-MM-DD (finish_date)",
                },
                "finish_date_end": {
                    "type": "string",
                    "description": "结束日期截止 (<=)，格式 YYYY-MM-DD (finish_date)",
                },
                "closed_date_start": {
                    "type": "string",
                    "description": "结案日期起始 (>=)，格式 YYYY-MM-DD (closed_date)",
                },
                "closed_date_end": {
                    "type": "string",
                    "description": "结案日期截止 (<=)，格式 YYYY-MM-DD (closed_date)",
                },
                "create_on_start": {
                    "type": "string",
                    "description": "创建日期起始 (>=)，格式 YYYY-MM-DD (CREATE_ON)",
                },
                "create_on_end": {
                    "type": "string",
                    "description": "创建日期截止 (<=)，格式 YYYY-MM-DD (CREATE_ON)",
                },
                # 状态
                "bstatus": {
                    "type": "integer",
                    "description": (
                        "案件业务状态 (BSTATUS): "
                        "20=未开案, 30=案件进行中(核心), 40=结案收款中, "
                        "45=结案已收款, 50=结束, 60=取消, 13=已交付"
                    ),
                },
                "rstatus": {
                    "type": "integer",
                    "description": (
                        "记录状态/审核状态 (RSTATUS): "
                        "0=草稿, 1=已审核, 2=待审核, -1=作废"
                    ),
                },
                "is_urgent": {
                    "type": "integer",
                    "description": "是否紧急 (isUrgent): 1=紧急, 0=否",
                },
                "is_public": {
                    "type": "integer",
                    "description": "是否公海 (isPublic): 1=是, 0=否",
                },
                # 业务类型
                "business_type": {
                    "type": "string",
                    "description": "业务类型 (businessType): gen=EMC常规, ic=国际认证, safety=安全, op=OP",
                },
            },
        },
    },
    {
        "name": "query_project_by_id",
        "description": "按ID查询案件/项目详情（含子项、试验计划、附件、操作日志）",
        "inputSchema": {
            "type": "object",
            "properties": {
                "id": {
                    "type": "string",
                    "description": "案件ID",
                },
            },
            "required": ["id"],
        },
    },
    {
        "name": "query_delivery_reminder",
        "description": (
            "查询交付提醒列表（首页逾期/即将到期提醒）。\n"
            "自动按当前用户身份过滤，返回：\n"
            "- 即将到期：planDeliveryDate <= 今天+3天\n"
            "- 已逾期：planDeliveryDate < 今天\n"
            "- 今日交付：planDeliveryDate = 今天"
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "start": {
                    "type": "integer",
                    "description": "分页起始位置，默认0",
                },
                "limit": {
                    "type": "integer",
                    "description": "每页条数，默认20",
                },
            },
        },
    },
]
