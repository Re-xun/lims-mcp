"""Module config: 客户联系人列表 (AbdCustomerContactListAction)"""
from __future__ import annotations
from new_mcp_servers.core.config import EnumField, FieldLabel, FilterDef, ModuleConfig

_BASE_PATH = "/AbdCustomerContactListAction"

customer_contact = ModuleConfig(
    name="query_customer_contact_list",
    display_name="客户联系人",
    description="查询客户联系人列表。",
    endpoint=_BASE_PATH + "/listQuery",
    scope_endpoints={
        "default": _BASE_PATH + "/listQuery",
        "dept": _BASE_PATH + "/listQueryDept",
        "mine": _BASE_PATH + "/listQueryMy",
    },
    scope_svars={
        "default": {"customerType": "1"},
    },
    extra_params=["include_raw"],
    filters=[
        FilterDef("contact_name", "acc.CONTACT_NAME", "联系人名称", "like"),
        FilterDef("customer_name", "ac.CUSTOMER_NAME_CN", "客户名称", "like"),
        FilterDef("fast_search", "fastSearch", "快速搜索", "like"),
        FilterDef("rstatus", "acc.RSTATUS", "状态", "=",
                  enums={0: "已作废", 1: "已审核", 2: "暂存", 3: "等待重新审批", 4: "审批中"}),
        FilterDef("adress1", "adress1", "地址1", "like"),
        FilterDef("adress2", "adress2", "地址2", "like"),
        FilterDef("contact_name_en", "contactNameEn", "名称(英)", "like"),
        FilterDef("customer_name_cn", "customerNameCn", "客户(候选)", "like"),
        FilterDef("email", "email", "电子邮箱", "like"),
        FilterDef("home_telephone", "homeTelephone", "家庭电话", "like"),
        FilterDef("mobile_telephone", "mobileTelephone", "移动电话", "like"),
        FilterDef("title", "title", "职位", "like"),
        FilterDef("work_telephone", "workTelephone", "办公电话", "like"),
    ],
    field_labels={
        "rstatus": FieldLabel("rstatus", "状态"),
        "customerNameCn": FieldLabel("customer_name_cn", "客户"),
        "contactName": FieldLabel("contact_name", "名称(中)"),
        "contactNameEn": FieldLabel("contact_name_en", "名称(英)"),
        "title": FieldLabel("title", "职位"),
        "email": FieldLabel("email", "电子邮箱"),
        "mobileTelephone": FieldLabel("mobile_telephone", "移动电话"),
        "workTelephone": FieldLabel("work_telephone", "办公电话"),
        "homeTelephone": FieldLabel("home_telephone", "家庭电话"),
        "adress1": FieldLabel("adress1", "地址1"),
        "adress2": FieldLabel("adress2", "地址2"),
        "mainContact": FieldLabel("main_contact", "主要联系人"),
    },
    enum_fields={
        "rstatus": EnumField({0: "已作废", 1: "已审核", 2: "暂存", 3: "等待重新审批", 4: "审批中"}),
    },
)
