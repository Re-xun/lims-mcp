"""Module config: 分包申请 (PurOutgoingRequestFormListAction)"""
from __future__ import annotations
from new_mcp_servers.core.config import EnumField, FieldLabel, FilterDef, ModuleConfig

_BASE_PATH = "/PurOutgoingRequestFormListAction"

pur_outgoing = ModuleConfig(
    name="query_puroutgoingrequestformlistaction",
    display_name="分包申请",
    description="查询分包申请列表。",
    endpoint=_BASE_PATH + "/listQuery",
    scope_endpoints={
        "default": _BASE_PATH + "/listQuery",
        "mine": _BASE_PATH + "/listQuery",
    },
    scope_svars={
        "default": {"operation": "operation"},
        "mine": {"operation": "My"},
    },
    extra_params=["include_raw"],
    filters=[
        FilterDef("fast_search", "fastSearch", "快速搜索", "like"),
        FilterDef("applt_person_name", "appltPersonName", "申请人", "like"),
        FilterDef("bstatus", "bstatus", "是否已转分包申请", "=", enums={1: "已转", 2: "未转"}),
        FilterDef("consignor_name_cn", "consignorNameCn", "合同方", "like"),
        FilterDef("order_date_start", "orderDate", "申请日期起", ">=", is_date_range=True),
        FilterDef("order_date_end", "orderDate", "申请日期止", "<=", is_date_range=True),
        FilterDef("order_no", "orderNo", "申请单编号", "like"),
        FilterDef("purchase_desc", "subcontractItems", "申请分包项目", "like"),
        FilterDef("rstatus", "rstatus", "审核状态", "="),
        FilterDef("saler_name", "salerName", "负责业务员", "like"),
        FilterDef("txn_core_no", "sourceBizNo", "单源号", "like"),
    ],
    field_labels={
        "rstatus": FieldLabel("rstatus", "审核状态"),
        "bstatus": FieldLabel("bstatus", "是否已转分包申请"),
        "orderNo": FieldLabel("order_no", "申请单编号"),
        "orderDate": FieldLabel("order_date", "申请日期"),
        "salerName": FieldLabel("saler_name", "负责业务员"),
        "appltPersonName": FieldLabel("applt_person_name", "申请人"),
        "purchaseDesc": FieldLabel("purchase_desc", "申请分包项目"),
        "txnCoreNo": FieldLabel("txn_core_no", "单源号"),
        "consignorNameCn": FieldLabel("consignor_name_cn", "合同方"),
    },
    enum_fields={
        "bstatus": EnumField({1: "已转", 2: "未转"}),
        "rstatus": EnumField({0: "已作废", 1: "已审核", 2: "暂存", 3: "等待重新审批", 4: "审批中"}),
    },
)
