"""Module config: 客户联系记录 (PsActivityListAction)"""
from __future__ import annotations
from new_mcp_servers.core.config import FieldLabel, FilterDef, ModuleConfig

_BASE_PATH = "/PsActivityListAction"

ps_activity = ModuleConfig(
    name="query_psactivitylistaction",
    display_name="客户联系记录",
    description="查询客户联系记录列表。通过 scope 路由到默认、部门、我的视图。",
    endpoint=_BASE_PATH + "/listQuery",
    scope_endpoints={
        "default": _BASE_PATH + "/listQuery",
        "dept": _BASE_PATH + "/listQueryDept",
        "mine": _BASE_PATH + "/listQueryMy",
    },
    scope_svars={
        "default": {"customerType": 1},
        "dept": {"customerType": 2},
        "mine": {"customerType": 3},
    },
    extra_params=["include_raw"],
    filters=[
        FilterDef("abd_customer_name", "q_abdCustomerName", "客户名称", "like"),
        FilterDef("contact_name", "q_contactName", "联系对象", "like"),
        FilterDef("fast_search", "fastSearch", "快速搜索", "like"),
        FilterDef("sale_person", "q_salePerson", "负责销售", "like"),
        FilterDef("abd_person_name", "abdPersonName", "负责销售(候选)", "like"),
        FilterDef("act_start_time_start", "actStartTime", "联系日期起", ">=", is_date_range=True),
        FilterDef("act_start_time_end", "actStartTime", "联系日期止", "<=", is_date_range=True),
        FilterDef("create_on_start", "createOn", "创建日期起", ">=", is_date_range=True),
        FilterDef("create_on_end", "createOn", "创建日期止", "<=", is_date_range=True),
        FilterDef("description", "description", "联系内容", "like"),
        FilterDef("fee_amt", "feeAmt", "费用支出", "like"),
        FilterDef("lookup_name", "lookupName", "联系方式", "like"),
        FilterDef("next_action_date_start", "nextActionDate", "下次联系日期起", ">=", is_date_range=True),
        FilterDef("next_action_date_end", "nextActionDate", "下次联系日期止", "<=", is_date_range=True),
    ],
    field_labels={
        "abdCustomerName": FieldLabel("abd_customer_name", "客户名称"),
        "actStartTime": FieldLabel("act_start_time", "联系日期"),
        "lookupName": FieldLabel("lookup_name", "联系方式"),
        "abdPersonName": FieldLabel("abd_person_name", "负责销售"),
        "contactName": FieldLabel("contact_name", "联系对象"),
        "createOn": FieldLabel("create_on", "创建日期"),
        "description": FieldLabel("description", "联系内容"),
        "feeAmt": FieldLabel("fee_amt", "费用支出"),
        "nextActionDate": FieldLabel("next_action_date", "预计下次联系日期"),
    },
)
