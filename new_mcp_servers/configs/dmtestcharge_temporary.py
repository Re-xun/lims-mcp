"""Module config: 临时收费单 (DmTestChargeTemporaryListAction)"""
from __future__ import annotations
from new_mcp_servers.core.config import EnumField, FieldLabel, FilterDef, ModuleConfig

_BASE_PATH = "/DmTestChargeTemporaryListAction"

dmtestcharge_temporary = ModuleConfig(
    name="query_dmtestchargetemporarylistaction",
    display_name="临时收费单",
    description="查询临时收费单列表。",
    endpoint=_BASE_PATH + "/listQuery",
    scope_endpoints={
        "default": _BASE_PATH + "/listQuery",
        "dm": _BASE_PATH + "/listQueryDm",
        "gen": _BASE_PATH + "/listQueryGen",
        "op": _BASE_PATH + "/listQueryOp",
        "rf": _BASE_PATH + "/listQueryRf",
        "safety": _BASE_PATH + "/listQuerySFY",
    },
    extra_params=["include_raw"],
    filters=[
        FilterDef("bstatus", "bstatus", "收费单状态", "="),
        FilterDef("charge_no", "chargeNo", "收费单编号", "like"),
        FilterDef("customer_contact", "customerContact", "客户联系人", "like"),
        FilterDef("customer_name", "customerName", "客户名称", "like"),
        FilterDef("locations", "locations", "试验场地", "like"),
        FilterDef("order_date_start", "orderDate", "收费单日期起", ">=", is_date_range=True),
        FilterDef("order_date_end", "orderDate", "收费单日期止", "<=", is_date_range=True),
        FilterDef("order_name", "orderName", "开单人", "like"),
        FilterDef("saler_name", "salerName", "负责销售", "like"),
        FilterDef("sample_model", "sampleModel", "样品型号", "like"),
        FilterDef("sample_name", "sampleName", "样品名称", "like"),
        FilterDef("sign_status", "signStatus", "签字状态", "="),
        FilterDef("test_date", "testDate", "试验日期", "like"),
        FilterDef("test_engineer_name", "testEngineerName", "试验人员", "like"),
        FilterDef("test_item", "testItem", "试验项目", "like"),
        FilterDef("test_time", "testTime", "试验时长", "like"),
        FilterDef("total_hours", "totalHours", "收费单时长(H)", "like"),
    ],
    field_labels={
        "chargeNo": FieldLabel("charge_no", "收费单编号"),
        "orderDate": FieldLabel("order_date", "收费单日期"),
        "totalHours": FieldLabel("total_hours", "收费单时长(H)"),
        "orderName": FieldLabel("order_name", "开单人"),
        "signStatus": FieldLabel("sign_status", "签字状态"),
        "bstatus": FieldLabel("bstatus", "收费单状态"),
        "customerName": FieldLabel("customer_name", "客户名称"),
        "customerContact": FieldLabel("customer_contact", "客户联系人"),
        "sampleName": FieldLabel("sample_name", "样品名称"),
        "sampleModel": FieldLabel("sample_model", "样品型号"),
        "locations": FieldLabel("locations", "试验场地"),
        "testItem": FieldLabel("test_item", "试验项目"),
        "testDate": FieldLabel("test_date", "试验日期"),
        "testEngineerName": FieldLabel("test_engineer_name", "试验人员"),
        "testTime": FieldLabel("test_time", "试验时长"),
        "salerName": FieldLabel("saler_name", "负责销售"),
    },
    enum_fields={
        "bstatus": EnumField({1: "未转销售合同", 4: "已转销售合同", 5: "已收款", 0: "已作废"}),
        "sign_status": EnumField({0: "未签字", 1: "已签字"}),
    },
)
