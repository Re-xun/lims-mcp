"""Module config: 收款通知单 (FinReceivingNoticeListAction)"""
from __future__ import annotations
from new_mcp_servers.core.config import FieldLabel, FilterDef, ModuleConfig

_BASE_PATH = "/FinReceivingNoticeListAction"

fin_receiving_notice = ModuleConfig(
    name="query_finreceivingnoticelistaction",
    display_name="收款通知单",
    description="查询收款通知单列表。",
    endpoint=_BASE_PATH + "/listQuery",
    scope_endpoints={
        "default": _BASE_PATH + "/listQuery",
        "dept": _BASE_PATH + "/listQueryDept",
        "mine": _BASE_PATH + "/listQueryMy",
    },
    scope_svars={
        "default": {"customerType": "1"},
        "dept": {"customerType": "1"},
        "mine": {"customerType": "1"},
    },
    scope_datatype_defaults={
        "dept": "listView",
        "mine": "listView",
    },
    extra_params=["include_raw"],
    filters=[
        FilterDef("create_on", "frn.create_on", "创建日期", "="),
        FilterDef("currency_id", "ac.CUSTOMER_NAME_CN", "客户名称", "like"),
        FilterDef("fast_search", "fastSearch", "快速搜索", "like"),
        FilterDef("order_no", "frn.order_no", "通知单编号", "like"),
        FilterDef("bank_name", "bankName", "收款银行", "like"),
        FilterDef("create_on_start", "createOn", "创建日期起", ">=", is_date_range=True),
        FilterDef("create_on_end", "createOn", "创建日期止", "<=", is_date_range=True),
        FilterDef("currency_name", "currencyName", "币种", "like"),
        FilterDef("customer_name", "customerName", "客户名称(候选)", "like"),
        FilterDef("receiving_notice_date_format", "receivingNoticeDateFormat", "通知日期", "like"),
        FilterDef("remark", "remark", "备注", "like"),
        FilterDef("sum_order_amt", "sumOrderAmt", "总金额", "like"),
        FilterDef("sum_receivable_amt", "sumReceivableAmt", "应收余额", "like"),
        FilterDef("sum_received_amt", "sumReceivedAmt", "已收金额", "like"),
    ],
    field_labels={
        "createOn": FieldLabel("create_on", "创建日期"),
        "orderNo": FieldLabel("order_no", "通知单编号"),
        "customerName": FieldLabel("customer_name", "客户名称"),
        "receivingNoticeDateFormat": FieldLabel("receiving_notice_date_format", "通知日期"),
        "totalAmt": FieldLabel("total_amt", "通知总金额"),
        "sumOrderAmt": FieldLabel("sum_order_amt", "合同总金额"),
        "currencyName": FieldLabel("currency_name", "币种"),
        "sumReceivedAmt": FieldLabel("sum_received_amt", "已收金额"),
        "sumReceivableAmt": FieldLabel("sum_receivable_amt", "应收余额"),
        "bankName": FieldLabel("bank_name", "收款银行"),
        "userName": FieldLabel("user_name", "经办人"),
        "remark": FieldLabel("remark", "备注"),
    },
)
