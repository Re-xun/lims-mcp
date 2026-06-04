"""Module config: 冲账退款列表 (FinCasReversingListAction)"""
from __future__ import annotations
from new_mcp_servers.core.config import EnumField, FieldLabel, FilterDef, ModuleConfig

_BASE_PATH = "/FinCasReversingListAction"

fin_cas_reversing = ModuleConfig(
    name="query_fincasreversinglistaction",
    display_name="冲账退款",
    description="查询冲账/退款记录列表。",
    endpoint=_BASE_PATH + "/listQuery",
    scope_endpoints={
        "default": _BASE_PATH + "/listQuery",
        "listqueryforsvar": _BASE_PATH + "/listQueryForSVar",
    },
    scope_svars={
        "default": {"operation": "operation", "modType": "modType"},
        "listQueryForSVar": {"operationCode": "'FINCASREVERSING-VIEW'", "modType": "SD"},
    },
    extra_params=["include_raw"],
    filters=[
        FilterDef("fast_search", "fastSearch", "快速搜索", "like"),
        FilterDef("order_date_start", "orderDate", "记录日期起", ">=", is_date_range=True),
        FilterDef("order_date_end", "orderDate", "记录日期止", "<=", is_date_range=True),
        FilterDef("order_no", "orderNo", "退款单号", "like"),
        FilterDef("receiving_company", "receivingCompany", "收款公司", "like"),
        FilterDef("reversed_invoice_amt", "reversedInvoiceAmt", "本次退票金额", "like"),
        FilterDef("reversing_date_start", "reversingDate", "退款日期起", ">=", is_date_range=True),
        FilterDef("reversing_date_end", "reversingDate", "退款日期止", "<=", is_date_range=True),
        FilterDef("reversing_type", "reversingType", "退款方式", "="),
        FilterDef("total_reversing_amt", "totalReversingAmt", "本次退款金额", "like"),
        FilterDef("txn_source_no", "txnSourceNo", "收款单号", "like"),
    ],
    field_labels={
        "orderNo": FieldLabel("order_no", "退款单号"),
        "orderDate": FieldLabel("order_date", "记录日期"),
        "reversingDate": FieldLabel("reversing_date", "退款日期"),
        "txnSourceNo": FieldLabel("txn_source_no", "收款单号"),
        "totalReversingAmt": FieldLabel("total_reversing_amt", "本次退款金额"),
        "reversedInvoiceAmt": FieldLabel("reversed_invoice_amt", "本次退票金额"),
        "reversingType": FieldLabel("reversing_type", "退款方式"),
        "receivingCompany": FieldLabel("receiving_company", "收款公司"),
    },
    enum_fields={
        "reversing_type": EnumField({1: "现金", 2: "转账", 3: "支票", 4: "备用金", 5: "汇票", 6: "支出退款"}),
    },
)
