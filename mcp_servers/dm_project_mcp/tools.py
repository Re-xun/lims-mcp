"""MCP tools for 案件查询 (LIMS DmProjectListAction)."""
from __future__ import annotations

import json
import os
import sys
from typing import Dict, Optional, Tuple

import httpx

JAVA_API_BASE = os.environ.get("JAVA_API_BASE", "http://localhost:8080")

# ── filter field mapping ──────────────────────────────────────────────
# (column_expression, operator_template) — operator_template uses {value} placeholder
_FILTER_CONFIG: Dict[str, Tuple[str, str]] = {
    # ── 核心筛选 ──
    "project_no":                      ("dp.PROJECT_NO",                  "like '%{value}%'"),
    "project_name":                    ("dp.PROJECT_NAME",                "like '%{value}%'"),
    "customer_name":                   ("ac.CUSTOMER_NAME_CN",            "like '%{value}%'"),
    "customer_id":                     ("dp.customer_id",                 "= {value}"),
    "contract_no":                     ("dp.contract_no",                 "like '%{value}%'"),
    "sales_order_no":                  ("sso.sales_order_no",             "like '%{value}%'"),
    # ── 状态筛选 ──
    "bstatus":                         ("dp.BSTATUS",                     "= {value}"),
    "rstatus":                         ("dp.RSTATUS",                     "= {value}"),
    "project_status":                  ("dp.project_status",              "= {value}"),
    "show_flag":                       ("dp.show_flag",                   "= {value}"),
    # ── 日期范围 ──
    "create_on_start":                 ("dp.CREATE_ON",                   ">= '{value}'"),
    "create_on_end":                   ("dp.CREATE_ON",                   "<= '{value}'"),
    "arrival_date_start":              ("dp.arrival_date",                ">= '{value}'"),
    "arrival_date_end":                ("dp.arrival_date",                "<= '{value}'"),
    "plan_end_date_start":             ("dp.plan_end_date",               ">= '{value}'"),
    "plan_end_date_end":               ("dp.plan_end_date",               "<= '{value}'"),
    "closed_date_start":               ("dp.closed_date",                 ">= '{value}'"),
    "closed_date_end":                 ("dp.closed_date",                 "<= '{value}'"),
    "cus_requirement_finish_date_start": ("dp.cus_requirement_finish_date", ">= '{value}'"),
    "cus_requirement_finish_date_end": ("dp.cus_requirement_finish_date", "<= '{value}'"),
    # ── 组织/人员 ──
    "dept_id":                         ("dp.dept_id",                     "= {value}"),
    "manager0":                        ("dp.MANAGER0",                    "= {value}"),
    "manager1":                        ("dp.MANAGER1",                    "= {value}"),
    "manager2":                        ("dp.MANAGER2",                    "= {value}"),
    # ── 分类筛选 ──
    "modular_type":                    ("dp.modular_type",                "= {value}"),
    "project_type":                    ("dp.project_type",                "= {value}"),
    "project_type2":                   ("dp.project_type2",               "= {value}"),
    "urgent_flag":                     ("dp.urgent_flag",                 "= {value}"),
    "complexity":                      ("dp.complexity",                  "= {value}"),
    "service_code":                    ("dp.service_code",                "= {value}"),
    "item_category":                   ("dp.item_category",               "= {value}"),
    "test_type":                       ("dp.test_type",                   "= {value}"),
    "report_label":                    ("dp.report_label",                "= {value}"),
    "bill_type_id":                    ("dp.bill_type_id",                "= {value}"),
    "laboratory_id":                   ("dp.laboratory_id",               "= {value}"),
    # ── 产品/型号 ──
    "sample_id":                       ("dp.sample_id",                   "= {value}"),
    "product_name":                    ("dp.product_name",                "like '%{value}%'"),
    "product_model":                   ("dp.product_model",               "like '%{value}%'"),
    "model_main":                      ("dp.model_main",                  "like '%{value}%'"),
    # ── 编号/证书 ──
    "ccc_no":                          ("dp.ccc_no",                      "like '%{value}%'"),
    "vin_serial_no":                   ("dp.vin_serial_no",               "like '%{value}%'"),
    "external_certificate_no":         ("dp.external_certificate_no",     "like '%{value}%'"),
    "external_report_no":              ("dp.external_report_no",          "like '%{value}%'"),
    # ── 其他 ──
    "service_pro_name":                ("dp.service_pro_name",            "like '%{value}%'"),
    "confirm_standard":                ("dp.confirm_standard",            "like '%{value}%'"),
}


def _build_filter_and_svars(
    keyword: str = None,
    filter: str = None,
    data_type: str = None,
    modular_type: str = None,
    type_: str = None,
    bill_type_id: str = None,
    overdue_status: str = None,
    operation_code: str = None,
    query_method: str = None,
    parent_id_null: bool = None,
    **filter_kwargs,
) -> Tuple[Optional[str], str]:
    """Build the filter SQL expression and sVars JSON string."""
    if filter and not keyword:
        keyword = filter

    conditions = []
    for py_name, (column, op_template) in _FILTER_CONFIG.items():
        val = filter_kwargs.get(py_name)
        if val is not None and val != "":
            conditions.append(f"{column} {op_template.format(value=val)}")

    # PARENT_ID 特殊处理
    if parent_id_null is True:
        conditions.append("dp.PARENT_ID IS NULL")
    elif parent_id_null is False:
        conditions.append("dp.PARENT_ID IS NOT NULL")

    filter_sql = " and ".join(conditions) if conditions else None

    # 组装 sVars
    s_vars = {}
    if data_type:
        s_vars["dataType"] = data_type
    if modular_type:
        s_vars["modularType"] = modular_type
    if type_:
        s_vars["TYPE"] = type_
    if bill_type_id:
        s_vars["BillTypeId"] = bill_type_id
    if overdue_status:
        s_vars["overdueStatus"] = overdue_status
    if operation_code:
        s_vars["operationCode"] = operation_code
    if query_method:
        s_vars["queryMethod"] = query_method

    return filter_sql, json.dumps(s_vars, ensure_ascii=False) if s_vars else "{}"


# ═══════════════════════════════════════════════════════════════════════
# Tool: query_project_list — 标准案件查询
# ═══════════════════════════════════════════════════════════════════════

async def query_project_list(
    token: str,
    # ── pagination ──
    start: int = 0,
    limit: int = 10,
    # ── data view ──
    data_type: str = None,
    modular_type: str = None,
    # ── search ──
    keyword: str = None,
    filter: str = None,
    # ── filter fields ──
    project_no: str = None,
    project_name: str = None,
    customer_name: str = None,
    customer_id: str = None,
    contract_no: str = None,
    sales_order_no: str = None,
    bstatus: int = None,
    rstatus: int = None,
    project_status: str = None,
    show_flag: int = None,
    create_on_start: str = None,
    create_on_end: str = None,
    arrival_date_start: str = None,
    arrival_date_end: str = None,
    plan_end_date_start: str = None,
    plan_end_date_end: str = None,
    closed_date_start: str = None,
    closed_date_end: str = None,
    cus_requirement_finish_date_start: str = None,
    cus_requirement_finish_date_end: str = None,
    dept_id: str = None,
    manager0: str = None,
    manager1: str = None,
    manager2: str = None,
    project_type: str = None,
    project_type2: str = None,
    urgent_flag: str = None,
    complexity: str = None,
    service_code: str = None,
    item_category: str = None,
    test_type: str = None,
    report_label: str = None,
    bill_type_id: str = None,
    laboratory_id: str = None,
    sample_id: str = None,
    product_name: str = None,
    product_model: str = None,
    model_main: str = None,
    ccc_no: str = None,
    vin_serial_no: str = None,
    external_certificate_no: str = None,
    external_report_no: str = None,
    service_pro_name: str = None,
    confirm_standard: str = None,
    parent_id_null: bool = None,
    # ── sVars extras ──
    overdue_status: str = None,
    operation_code: str = None,
    query_method: str = None,
) -> dict:
    """查询案件列表（分页），支持 45+ 筛选条件 AND 组合。

    返回: {"count": <总数>, "resultList": [<案件对象>, ...]}
    """
    if start is None:
        start = 0
    if limit is None:
        limit = 10

    params = {"start": str(start), "limit": str(limit)}

    filter_sql, s_vars_json = _build_filter_and_svars(
        keyword=keyword,
        filter=filter,
        data_type=data_type,
        modular_type=modular_type,
        bill_type_id=bill_type_id,
        overdue_status=overdue_status,
        operation_code=operation_code,
        query_method=query_method,
        parent_id_null=parent_id_null,
        project_no=project_no,
        project_name=project_name,
        customer_name=customer_name,
        customer_id=customer_id,
        contract_no=contract_no,
        sales_order_no=sales_order_no,
        bstatus=bstatus,
        rstatus=rstatus,
        project_status=project_status,
        show_flag=show_flag,
        create_on_start=create_on_start,
        create_on_end=create_on_end,
        arrival_date_start=arrival_date_start,
        arrival_date_end=arrival_date_end,
        plan_end_date_start=plan_end_date_start,
        plan_end_date_end=plan_end_date_end,
        closed_date_start=closed_date_start,
        closed_date_end=closed_date_end,
        cus_requirement_finish_date_start=cus_requirement_finish_date_start,
        cus_requirement_finish_date_end=cus_requirement_finish_date_end,
        dept_id=dept_id,
        manager0=manager0,
        manager1=manager1,
        manager2=manager2,
        project_type=project_type,
        project_type2=project_type2,
        urgent_flag=urgent_flag,
        complexity=complexity,
        service_code=service_code,
        item_category=item_category,
        test_type=test_type,
        report_label=report_label,
        laboratory_id=laboratory_id,
        sample_id=sample_id,
        product_name=product_name,
        product_model=product_model,
        model_main=model_main,
        ccc_no=ccc_no,
        vin_serial_no=vin_serial_no,
        external_certificate_no=external_certificate_no,
        external_report_no=external_report_no,
        service_pro_name=service_pro_name,
        confirm_standard=confirm_standard,
    )

    if filter_sql:
        params["filter"] = filter_sql
    if keyword:
        params["keyword"] = keyword
    params["sVars"] = s_vars_json

    api_url = f"{JAVA_API_BASE}/DmProjectListAction/listQueryAll"
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


# ═══════════════════════════════════════════════════════════════════════
# Tool: query_project_by_id — 按ID查单个案件
# ═══════════════════════════════════════════════════════════════════════

async def query_project_by_id(
    token: str,
    id: str,
) -> dict:
    """按ID查询单个案件详情"""
    api_url = f"{JAVA_API_BASE}/DmProjectListAction/selectById"
    sys.stderr.write(f"\n[API REQUEST] GET {api_url}  id={id}\n\n")
    sys.stderr.flush()

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


# ═══════════════════════════════════════════════════════════════════════
# Tool: query_project_my_all — 我的案件
# ═══════════════════════════════════════════════════════════════════════

async def query_project_my_all(
    token: str,
    # ── pagination ──
    start: int = 0,
    limit: int = 10,
    # ── view type ──
    type_: str = "MY",
    # ── search ──
    keyword: str = None,
    filter: str = None,
    # ── filter fields ──
    project_no: str = None,
    project_name: str = None,
    customer_name: str = None,
    bstatus: int = None,
    rstatus: int = None,
    project_status: str = None,
    create_on_start: str = None,
    create_on_end: str = None,
    plan_end_date_start: str = None,
    plan_end_date_end: str = None,
    closed_date_start: str = None,
    closed_date_end: str = None,
    modular_type: str = None,
    project_type: str = None,
    project_type2: str = None,
    urgent_flag: str = None,
    sales_order_no: str = None,
    contract_no: str = None,
    product_name: str = None,
    product_model: str = None,
    dept_id: str = None,
    show_flag: int = None,
) -> dict:
    """查询我的案件（分页）。

    TYPE=MY 按当前用户的 MANAGER1/2/3/delivery_manager1/person_id/create_by/dept_id 匹配；
    TYPE=MYDEPT 按 department_id/dept_id/delivery_dept_id 匹配。

    返回: {"count": <总数>, "resultList": [<案件对象>, ...]}
    """
    if start is None:
        start = 0
    if limit is None:
        limit = 10

    params = {"start": str(start), "limit": str(limit)}

    filter_sql, s_vars_json = _build_filter_and_svars(
        keyword=keyword,
        filter=filter,
        type_=type_,
        modular_type=modular_type,
        parent_id_null=None,
        project_no=project_no,
        project_name=project_name,
        customer_name=customer_name,
        bstatus=bstatus,
        rstatus=rstatus,
        project_status=project_status,
        create_on_start=create_on_start,
        create_on_end=create_on_end,
        plan_end_date_start=plan_end_date_start,
        plan_end_date_end=plan_end_date_end,
        closed_date_start=closed_date_start,
        closed_date_end=closed_date_end,
        project_type=project_type,
        project_type2=project_type2,
        urgent_flag=urgent_flag,
        sales_order_no=sales_order_no,
        contract_no=contract_no,
        product_name=product_name,
        product_model=product_model,
        dept_id=dept_id,
        show_flag=show_flag,
    )

    if filter_sql:
        params["filter"] = filter_sql
    if keyword:
        params["keyword"] = keyword
    params["sVars"] = s_vars_json

    api_url = f"{JAVA_API_BASE}/DmProjectListAction/listQueryMyAll"
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


# ═══════════════════════════════════════════════════════════════════════
# Tool: query_project_unassigned — 未分配案件
# ═══════════════════════════════════════════════════════════════════════

async def query_project_unassigned(
    token: str,
    start: int = 0,
    limit: int = 10,
    keyword: str = None,
    filter: str = None,
    project_no: str = None,
    project_name: str = None,
    customer_name: str = None,
    create_on_start: str = None,
    create_on_end: str = None,
    modular_type: str = None,
    project_type: str = None,
    dept_id: str = None,
) -> dict:
    """查询未分配案件（分页），即 manager1 IS NULL 且 bstatus NOT IN (6,7,8) 的案件。

    返回: {"count": <总数>, "resultList": [<案件对象>, ...]}
    """
    if start is None:
        start = 0
    if limit is None:
        limit = 10

    params = {"start": str(start), "limit": str(limit)}

    filter_sql, s_vars_json = _build_filter_and_svars(
        keyword=keyword,
        filter=filter,
        modular_type=modular_type,
        project_no=project_no,
        project_name=project_name,
        customer_name=customer_name,
        create_on_start=create_on_start,
        create_on_end=create_on_end,
        project_type=project_type,
        dept_id=dept_id,
    )

    if filter_sql:
        params["filter"] = filter_sql
    if keyword:
        params["keyword"] = keyword
    params["sVars"] = s_vars_json

    api_url = f"{JAVA_API_BASE}/DmProjectListAction/listQueryUnassigned"
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


# ═══════════════════════════════════════════════════════════════════════
# Tool: query_project_for_app — 移动端案件查询
# ═══════════════════════════════════════════════════════════════════════

async def query_project_for_app(
    token: str,
    start: int = 0,
    limit: int = 10,
    query_data: str = None,
    keyword: str = None,
    data_type: str = None,
    project_no: str = None,
    project_name: str = None,
    customer_name: str = None,
    bstatus: int = None,
    create_on_start: str = None,
    create_on_end: str = None,
    plan_end_date_start: str = None,
    plan_end_date_end: str = None,
    modular_type: str = None,
    project_type: str = None,
    project_type2: str = None,
    urgent_flag: str = None,
    show_flag: int = None,
) -> dict:
    """移动端App案件查询（分页）。

    queryData 支持模糊匹配：委托人名称(projectConsignorName) / 案件号(projectNo) / 产品名(productName)。

    返回: {"count": <总数>, "resultList": [<案件对象>, ...]}
    """
    if start is None:
        start = 0
    if limit is None:
        limit = 10

    params = {"start": str(start), "limit": str(limit)}

    filter_sql, s_vars_json = _build_filter_and_svars(
        keyword=keyword,
        data_type=data_type,
        modular_type=modular_type,
        project_no=project_no,
        project_name=project_name,
        customer_name=customer_name,
        bstatus=bstatus,
        create_on_start=create_on_start,
        create_on_end=create_on_end,
        plan_end_date_start=plan_end_date_start,
        plan_end_date_end=plan_end_date_end,
        project_type=project_type,
        project_type2=project_type2,
        urgent_flag=urgent_flag,
        show_flag=show_flag,
    )

    if filter_sql:
        params["filter"] = filter_sql
    if keyword:
        params["keyword"] = keyword
    if query_data:
        s_vars = json.loads(s_vars_json)
        s_vars["queryData"] = query_data
        s_vars_json = json.dumps(s_vars, ensure_ascii=False)
    params["sVars"] = s_vars_json

    api_url = f"{JAVA_API_BASE}/DmProjectListAction/listQuery4App"
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


# ═══════════════════════════════════════════════════════════════════════
# Registry
# ═══════════════════════════════════════════════════════════════════════

TOOL_HANDLERS = {
    "query_project_list": query_project_list,
    "query_project_by_id": query_project_by_id,
    "query_project_my_all": query_project_my_all,
    "query_project_unassigned": query_project_unassigned,
    "query_project_for_app": query_project_for_app,
}

TOOL_SCHEMAS = [
    # ── query_project_list ──────────────────────────────────────────
    {
        "name": "query_project_list",
        "description": (
            "查询案件列表（分页），支持 45+ 筛选条件 AND 组合。"
            "dataType 可选：conduct(进行中)/suspend(未开案/挂起)/closure(已结案)/my(我的)/trueSuspend(暂停中)/urgent(紧急)/toBeAssigned(待分配)。"
            "modularType 可选：EMC/RELIABILITY/GENERAL_EMC/SAFETY/IC/OTHER。"
            "返回分页结果，包含 count(总数) 和 resultList(案件列表)。"
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                # ── pagination ──
                "start": {"type": "integer", "description": "分页起始位置，默认 0"},
                "limit": {"type": "integer", "description": "每页条数，默认 10"},
                # ── data view ──
                "data_type": {
                    "type": "string",
                    "description": (
                        "数据类型：conduct=进行中(bstatus=3), suspend=未开案/挂起(bstatus=2), "
                        "closure=已结案(bstatus=7), my=我的案件, trueSuspend=暂停中(bstatus=5), "
                        "urgent=紧急案件, toBeAssigned=待分配"
                    ),
                },
                "modular_type": {
                    "type": "string",
                    "description": "模块类型：EMC/RELIABILITY/GENERAL_EMC/SAFETY/IC/OTHER",
                },
                # ── search ──
                "keyword": {
                    "type": "string",
                    "description": "通用搜索关键词。如果用户只说一个词没有指定字段（如某个案件号、客户名），就用这个",
                },
                "filter": {
                    "type": "string",
                    "description": "等同于 keyword，自动映射",
                },
                # ── 核心筛选 ──
                "project_no": {"type": "string", "description": "案件编号，模糊匹配 (dp.PROJECT_NO)"},
                "project_name": {"type": "string", "description": "案件名称，模糊匹配 (dp.PROJECT_NAME)"},
                "customer_name": {"type": "string", "description": "客户名称，模糊匹配 (ac.CUSTOMER_NAME_CN)"},
                "customer_id": {"type": "string", "description": "客户ID，精确匹配 (dp.customer_id)"},
                "contract_no": {"type": "string", "description": "合同号，模糊匹配 (dp.contract_no)"},
                "sales_order_no": {"type": "string", "description": "销售订单号，模糊匹配 (sso.sales_order_no)"},
                # ── 状态筛选 ──
                "bstatus": {
                    "type": "integer",
                    "description": (
                        "业务状态：0=待确认开案, 1=待开案, 2=未开案/挂起, 3=案件进行中, "
                        "5=暂停中, 7=结案, 8=取消"
                    ),
                },
                "rstatus": {
                    "type": "integer",
                    "description": "记录状态：0=草稿, 1=已审核, 2=待审核, -1=作废",
                },
                "project_status": {"type": "string", "description": "项目状态 (dp.project_status)"},
                "show_flag": {"type": "integer", "description": "显示标识：1=显示"},
                # ── 日期范围 ──
                "create_on_start": {"type": "string", "description": "创建日期起始 (>=)，格式 YYYY-MM-DD"},
                "create_on_end": {"type": "string", "description": "创建日期截止 (<=)，格式 YYYY-MM-DD"},
                "arrival_date_start": {"type": "string", "description": "到样日期起始 (>=)，格式 YYYY-MM-DD"},
                "arrival_date_end": {"type": "string", "description": "到样日期截止 (<=)，格式 YYYY-MM-DD"},
                "plan_end_date_start": {"type": "string", "description": "计划完成日期起始 (>=)，格式 YYYY-MM-DD"},
                "plan_end_date_end": {"type": "string", "description": "计划完成日期截止 (<=)，格式 YYYY-MM-DD"},
                "closed_date_start": {"type": "string", "description": "结案日期起始 (>=)，格式 YYYY-MM-DD"},
                "closed_date_end": {"type": "string", "description": "结案日期截止 (<=)，格式 YYYY-MM-DD"},
                "cus_requirement_finish_date_start": {"type": "string", "description": "客户要求完成日期起始 (>=)"},
                "cus_requirement_finish_date_end": {"type": "string", "description": "客户要求完成日期截止 (<=)"},
                # ── 组织/人员 ──
                "dept_id": {"type": "string", "description": "部门ID (dp.dept_id)"},
                "manager0": {"type": "string", "description": "销售助理ID (dp.MANAGER0)"},
                "manager1": {"type": "string", "description": "项目工程师ID (dp.MANAGER1)"},
                "manager2": {"type": "string", "description": "交付人员ID (dp.MANAGER2)"},
                # ── 分类 ──
                "project_type": {
                    "type": "string",
                    "description": "项目类型：entrust=委托, reckon-by-time=按时计费",
                },
                "project_type2": {
                    "type": "string",
                    "description": "项目子类型：pretest=预测试, normal=正常",
                },
                "urgent_flag": {"type": "string", "description": "紧急标识"},
                "complexity": {"type": "string", "description": "复杂度"},
                "service_code": {"type": "string", "description": "服务代码"},
                "item_category": {"type": "string", "description": "项目类别"},
                "test_type": {"type": "string", "description": "测试类型"},
                "report_label": {"type": "string", "description": "报告标签"},
                "bill_type_id": {"type": "string", "description": "单据类型ID"},
                "laboratory_id": {"type": "string", "description": "实验室ID"},
                # ── 产品/型号 ──
                "sample_id": {"type": "string", "description": "样品ID (dp.sample_id)"},
                "product_name": {"type": "string", "description": "产品名称，模糊匹配"},
                "product_model": {"type": "string", "description": "产品型号，模糊匹配"},
                "model_main": {"type": "string", "description": "主型号，模糊匹配"},
                # ── 编号/证书 ──
                "ccc_no": {"type": "string", "description": "CCC编号，模糊匹配"},
                "vin_serial_no": {"type": "string", "description": "VIN序列号，模糊匹配"},
                "external_certificate_no": {"type": "string", "description": "外部证书号，模糊匹配"},
                "external_report_no": {"type": "string", "description": "外部报告号，模糊匹配"},
                # ── 其他 ──
                "service_pro_name": {"type": "string", "description": "服务项目名称，模糊匹配"},
                "confirm_standard": {"type": "string", "description": "判定标准，模糊匹配"},
                "parent_id_null": {
                    "type": "boolean",
                    "description": "true=仅主案件(PARENT_ID IS NULL), false=仅子案件(PARENT_ID IS NOT NULL)",
                },
                # ── sVars extras ──
                "overdue_status": {
                    "type": "string",
                    "description": "逾期状态：overdue=已逾期, notOverdue=未逾期",
                },
                "operation_code": {"type": "string", "description": "权限码（可选）"},
                "query_method": {"type": "string", "description": "导出时指定（可选）"},
            },
        },
    },
    # ── query_project_by_id ──────────────────────────────────────────
    {
        "name": "query_project_by_id",
        "description": "按ID查询单个案件详情，返回完整案件信息",
        "inputSchema": {
            "type": "object",
            "properties": {
                "id": {"type": "string", "description": "案件ID (dm_project.ID)"},
            },
            "required": ["id"],
        },
    },
    # ── query_project_my_all ─────────────────────────────────────────
    {
        "name": "query_project_my_all",
        "description": (
            "查询我的案件（分页）。TYPE=MY 按当前用户的多字段匹配（MANAGER1/2/3/delivery_manager1/person_id/create_by/dept_id），"
            "TYPE=MYDEPT 按部门匹配（department_id/dept_id/delivery_dept_id）。"
            "返回分页结果，包含 count(总数) 和 resultList(案件列表)。"
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "start": {"type": "integer", "description": "分页起始位置，默认 0"},
                "limit": {"type": "integer", "description": "每页条数，默认 10"},
                "type_": {
                    "type": "string",
                    "description": "查询类型：MY=我的案件, MYDEPT=我的部门案件。默认 MY",
                },
                "keyword": {"type": "string", "description": "通用搜索关键词"},
                "filter": {"type": "string", "description": "等同于 keyword"},
                "project_no": {"type": "string", "description": "案件编号，模糊匹配"},
                "project_name": {"type": "string", "description": "案件名称，模糊匹配"},
                "customer_name": {"type": "string", "description": "客户名称，模糊匹配"},
                "bstatus": {"type": "integer", "description": "业务状态"},
                "rstatus": {"type": "integer", "description": "记录状态"},
                "project_status": {"type": "string", "description": "项目状态"},
                "create_on_start": {"type": "string", "description": "创建日期起始 (>=)，格式 YYYY-MM-DD"},
                "create_on_end": {"type": "string", "description": "创建日期截止 (<=)，格式 YYYY-MM-DD"},
                "plan_end_date_start": {"type": "string", "description": "计划完成日期起始 (>=)"},
                "plan_end_date_end": {"type": "string", "description": "计划完成日期截止 (<=)"},
                "closed_date_start": {"type": "string", "description": "结案日期起始 (>=)"},
                "closed_date_end": {"type": "string", "description": "结案日期截止 (<=)"},
                "modular_type": {"type": "string", "description": "模块类型"},
                "project_type": {"type": "string", "description": "项目类型"},
                "project_type2": {"type": "string", "description": "项目子类型"},
                "urgent_flag": {"type": "string", "description": "紧急标识"},
                "sales_order_no": {"type": "string", "description": "销售订单号，模糊匹配"},
                "contract_no": {"type": "string", "description": "合同号，模糊匹配"},
                "product_name": {"type": "string", "description": "产品名称，模糊匹配"},
                "product_model": {"type": "string", "description": "产品型号，模糊匹配"},
                "dept_id": {"type": "string", "description": "部门ID"},
                "show_flag": {"type": "integer", "description": "显示标识"},
            },
        },
    },
    # ── query_project_unassigned ─────────────────────────────────────
    {
        "name": "query_project_unassigned",
        "description": (
            "查询未分配案件（分页），即项目工程师(manager1)为空且 bstatus 不在 6/7/8 的案件。"
            "返回分页结果，包含 count(总数) 和 resultList(案件列表)。"
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "start": {"type": "integer", "description": "分页起始位置，默认 0"},
                "limit": {"type": "integer", "description": "每页条数，默认 10"},
                "keyword": {"type": "string", "description": "通用搜索关键词"},
                "filter": {"type": "string", "description": "等同于 keyword"},
                "project_no": {"type": "string", "description": "案件编号，模糊匹配"},
                "project_name": {"type": "string", "description": "案件名称，模糊匹配"},
                "customer_name": {"type": "string", "description": "客户名称，模糊匹配"},
                "create_on_start": {"type": "string", "description": "创建日期起始 (>=)，格式 YYYY-MM-DD"},
                "create_on_end": {"type": "string", "description": "创建日期截止 (<=)，格式 YYYY-MM-DD"},
                "modular_type": {"type": "string", "description": "模块类型"},
                "project_type": {"type": "string", "description": "项目类型"},
                "dept_id": {"type": "string", "description": "部门ID"},
            },
        },
    },
    # ── query_project_for_app ────────────────────────────────────────
    {
        "name": "query_project_for_app",
        "description": (
            "移动端App案件查询（分页）。queryData 支持模糊匹配委托人名称/案件号/产品名三字段。"
            "返回分页结果，包含 count(总数) 和 resultList(案件列表)。"
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "start": {"type": "integer", "description": "分页起始位置，默认 0"},
                "limit": {"type": "integer", "description": "每页条数，默认 10"},
                "query_data": {
                    "type": "string",
                    "description": "App端搜索文本，模糊匹配：委托人名称/案件号/产品名",
                },
                "keyword": {"type": "string", "description": "通用搜索关键词"},
                "data_type": {"type": "string", "description": "数据类型"},
                "project_no": {"type": "string", "description": "案件编号，模糊匹配"},
                "project_name": {"type": "string", "description": "案件名称，模糊匹配"},
                "customer_name": {"type": "string", "description": "客户名称，模糊匹配"},
                "bstatus": {"type": "integer", "description": "业务状态"},
                "create_on_start": {"type": "string", "description": "创建日期起始 (>=)，格式 YYYY-MM-DD"},
                "create_on_end": {"type": "string", "description": "创建日期截止 (<=)，格式 YYYY-MM-DD"},
                "plan_end_date_start": {"type": "string", "description": "计划完成日期起始 (>=)"},
                "plan_end_date_end": {"type": "string", "description": "计划完成日期截止 (<=)"},
                "modular_type": {"type": "string", "description": "模块类型"},
                "project_type": {"type": "string", "description": "项目类型"},
                "project_type2": {"type": "string", "description": "项目子类型"},
                "urgent_flag": {"type": "string", "description": "紧急标识"},
                "show_flag": {"type": "integer", "description": "显示标识"},
            },
        },
    },
]
