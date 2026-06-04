"""Module config: 销售机会列表 (PsOpportunityListAction)"""
from __future__ import annotations
from new_mcp_servers.core.config import EnumField, FieldLabel, FilterDef, ModuleConfig

_BASE_PATH = "/PsOpportunityListAction"

ps_opportunity = ModuleConfig(
    name="query_sales_opportunity_list",
    display_name="销售机会",
    description="查询销售机会列表。",
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
        FilterDef("fast_search", "fastSearch", "快速搜索", "like"),
        FilterDef("bstatus", "bstatus", "状态", "=", enums={1: "成功", 2: "失败", 3: "客户咨询中", 4: "已出报价"}),
        FilterDef("case_intending_amt", "caseIntendingAmt", "意向金额", "like"),
        FilterDef("contact_name", "contactName", "联系人", "like"),
        FilterDef("content", "content", "机会内容", "like"),
        FilterDef("create_on_start", "createOn", "创建日期起", ">=", is_date_range=True),
        FilterDef("create_on_end", "createOn", "创建日期止", "<=", is_date_range=True),
        FilterDef("customer_name", "customerName", "客户名称", "like"),
        FilterDef("remarks", "remarks", "备注", "like"),
        FilterDef("response_department_name", "responseDepartmentName", "负责部门", "like"),
        FilterDef("response_person_name", "responsePersonName", "负责人", "like"),
        FilterDef("rstatus", "rstatus", "记录状态", "=", enums={0: "已作废", 1: "已审核", 2: "暂存", 3: "等待重新审批", 4: "审批中"}),
        FilterDef("sample_type", "sampleType", "样品类型", "like"),
    ],
    field_labels={
        "createOn": FieldLabel("create_on", "创建日期"),
        "responsePersonName": FieldLabel("response_person_name", "负责人"),
        "customerName": FieldLabel("customer_name", "客户名称"),
        "contactName": FieldLabel("contact_name", "联系人"),
        "sampleType": FieldLabel("sample_type", "样品类型"),
        "content": FieldLabel("content", "机会内容"),
        "caseIntendingAmt": FieldLabel("case_intending_amt", "意向金额"),
        "bstatus": FieldLabel("bstatus", "状态"),
        "responseDepartmentName": FieldLabel("response_department_name", "负责部门"),
        "remarks": FieldLabel("remarks", "备注"),
        "rstatus": FieldLabel("rstatus", "记录状态"),
    },
    enum_fields={
        "bstatus": EnumField({1: "成功", 2: "失败", 3: "客户咨询中", 4: "已出报价"}),
        "rstatus": EnumField({0: "已作废", 1: "已审核", 2: "暂存", 3: "等待重新审批", 4: "审批中"}),
    },
)
