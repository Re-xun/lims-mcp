"""Module config: 联系计划列表 (PsPlanListAction)"""
from __future__ import annotations
from new_mcp_servers.core.config import EnumField, FieldLabel, FilterDef, ModuleConfig

_BASE_PATH = "/PsPlanListAction"

ps_plan = ModuleConfig(
    name="query_contact_plan_list",
    display_name="联系计划",
    description="查询联系计划列表。",
    endpoint=_BASE_PATH + "/listQuery",
    scope_endpoints={
        "default": _BASE_PATH + "/listQuery",
        "dept": _BASE_PATH + "/listQueryDept",
        "mine": _BASE_PATH + "/listQueryMy",
        "my_week": _BASE_PATH + "/listQueryMyWeek",
    },
    scope_svars={
        "default": {"customerType": 1},
        "dept": {"customerType": 2},
        "mine": {"customerType": 3},
        "my_week": {"customerType": 3},
    },
    scope_datatype_defaults={
        "default": "listView",
        "dept": "LIST_SALES_DEP_ID_VIEW",
        "mine": "LIST_CREAT_MY_VIEW",
        "my_week": "LIST_CREAT_MY_VIEW_WEEK",
    },
    extra_params=["include_raw"],
    filters=[
        FilterDef("fast_search", "fastSearch", "快速搜索", "like"),
        FilterDef("bstatus", "bstatus", "联系状态", "=", enums={1: "计划中", 2: "已联系", 3: "未联系"}),
        FilterDef("contact_obj_name", "contactObjName", "联系对象", "like"),
        FilterDef("customer_obj_name", "customerObjName", "客户名称", "like"),
        FilterDef("description", "description", "计划内容", "like"),
        FilterDef("lookup_name", "lookupName", "联系方式", "like"),
        FilterDef("plan_start_time_start", "planStartTime", "计划日期起", ">=", is_date_range=True),
        FilterDef("plan_start_time_end", "planStartTime", "计划日期止", "<=", is_date_range=True),
        FilterDef("remark", "remark", "备注", "like"),
        FilterDef("sales_dep_obj_name", "salesDepObjName", "销售部门", "like"),
        FilterDef("sales_person_obj_name", "salesPersonObjName", "销售人员", "like"),
    ],
    field_labels={
        "planStartTime": FieldLabel("plan_start_time", "联系日期"),
        "salesPersonObjName": FieldLabel("sales_person_obj_name", "销售人员"),
        "lookupName": FieldLabel("lookup_name", "联系方式"),
        "contactObjName": FieldLabel("contact_obj_name", "联系对象"),
        "customerObjName": FieldLabel("customer_obj_name", "客户"),
        "description": FieldLabel("description", "计划内容"),
        "bstatus": FieldLabel("bstatus", "联系状态"),
        "salesDepObjName": FieldLabel("sales_dep_obj_name", "销售部门"),
        "remark": FieldLabel("remark", "备注"),
    },
    enum_fields={
        "bstatus": EnumField({1: "计划中", 2: "已联系", 3: "未联系"}),
    },
)
