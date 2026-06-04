"""Module config: 开票申请 (SdInvoiceRequestListAction)"""
from __future__ import annotations
from new_mcp_servers.core.config import EnumField, FieldLabel, FilterDef, ModuleConfig

_BASE_PATH = "/SdInvoiceRequestListAction"

sd_invoice_request = ModuleConfig(
    name="query_sdinvoicerequestlistaction",
    display_name="开票申请",
    description="查询开票申请列表。",
    endpoint=_BASE_PATH + "/listQuery",
    scope_endpoints={
        "default": _BASE_PATH + "/listQuery",
        "mine": _BASE_PATH + "/listQueryMy",
    },
    extra_params=["include_raw"],
    filters=[
        FilterDef("bstatus", "sia.bstatus", "状态", "=", enums={1: "已开", 2: "未开"}),
        FilterDef("customer_name", "ac.CUSTOMER_NAME_CN", "客户名称", "like"),
        FilterDef("fast_search", "fastSearch", "快速搜索", "like"),
        FilterDef("order_no", "orderNo", "申请编号", "like"),
        FilterDef("rstatus", "sia.rstatus", "记录状态", "=",
                  enums={0: "已作废", 1: "已审核", 2: "暂存", 3: "等待重新审批", 4: "审批中"}),
        FilterDef("saler_no", "sso.sales_order_no", "合同号", "like"),
        FilterDef("order_date_start", "orderDate", "开票日期起", ">=", is_date_range=True),
        FilterDef("order_date_end", "orderDate", "开票日期止", "<=", is_date_range=True),
        FilterDef("request_amt", "requestAmt", "发票金额", "like"),
        FilterDef("request_desc", "requestDesc", "备注", "like"),
        FilterDef("request_invoice_media", "requestInvoiceMedia", "发票介质", "=",
                  enums={1: "电子发票", 2: "纸质发票", 3: "电子+纸质"}),
        FilterDef("request_invoice_type", "requestInvoiceType", "票据类型", "=",
                  enums={1: "收据", 2: "增值税专用发票", 3: "增值税普通发票", 4: "形式发票"}),
        FilterDef("sales_order_no", "salesOrderNo", "合同号(候选)", "like"),
        FilterDef("source_name", "sourceName", "来源", "like"),
        FilterDef("tax_id", "taxId", "税号", "like"),
        FilterDef("tax_name", "taxName", "发票抬头", "like"),
    ],
    field_labels={
        "rstatus": FieldLabel("rstatus", "状态"),
        "orderDate": FieldLabel("order_date", "开票日期"),
        "orderNo": FieldLabel("order_no", "开票编号"),
        "customerName": FieldLabel("customer_name", "客户名称"),
        "requestInvoiceType": FieldLabel("request_invoice_type", "票据类型"),
        "requestInvoiceMedia": FieldLabel("request_invoice_media", "发票介质"),
        "requestAmt": FieldLabel("request_amt", "发票金额"),
        "taxName": FieldLabel("tax_name", "发票抬头"),
        "taxId": FieldLabel("tax_id", "税号"),
        "taxRemark": FieldLabel("tax_remark", "备注"),
        "sourceName": FieldLabel("source_name", "来源"),
        "salesOrderNo": FieldLabel("sales_order_no", "合同号"),
        "bstatus": FieldLabel("bstatus", "状态"),
        "requestDesc": FieldLabel("request_desc", "备注"),
        "finArInvoiceNo": FieldLabel("fin_ar_invoice_no", "开票记录编号"),
    },
    enum_fields={
        "bstatus": EnumField({1: "已开", 2: "未开"}),
        "request_invoice_media": EnumField({1: "电子发票", 2: "纸质发票", 3: "电子+纸质"}),
        "request_invoice_type": EnumField({1: "收据", 2: "增值税专用发票", 3: "增值税普通发票", 4: "形式发票"}),
        "rstatus": EnumField({0: "已作废", 1: "已审核", 2: "暂存", 3: "等待重新审批", 4: "审批中"}),
    },
)
