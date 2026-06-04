"""Module config: 开票记录列表 (FinArInvoiceListAction)"""
from __future__ import annotations
from new_mcp_servers.core.config import EnumField, FieldLabel, FilterDef, ModuleConfig

_BASE_PATH = "/FinArInvoiceListAction"

fin_ar_invoice = ModuleConfig(
    name="query_finarinvoicelistaction",
    display_name="开票记录",
    description="查询开票记录列表（含收款状态）。通过 scope 路由到 default/item/mine 视图。",
    endpoint=_BASE_PATH + "/listQuery",
    scope_endpoints={
        "default": _BASE_PATH + "/listQuery",
        "item": _BASE_PATH + "/listQueryItem",
        "mine": _BASE_PATH + "/listQueryMyItem",
    },
    extra_params=["include_raw"],
    filters=[
        FilterDef("bstatus", "fai.bstatus", "收款状态", "=", enums={1: "已收", 2: "部分已收", 3: "未收"}),
        FilterDef("company_invoice_name", "acii.company_name", "发票抬头", "like"),
        FilterDef("customer_name", "ac.CUSTOMER_NAME_CN", "客户名称", "like"),
        FilterDef("fast_search", "fastSearch", "快速搜索", "like"),
        FilterDef("invoice_no", "faii.invoice_no", "发票号码", "like"),
        FilterDef("order_no", "fai.order_no", "开票编号", "like"),
        FilterDef("rstatus", "fai.rstatus", "单据状态", "=", enums={1: "审核", 2: "暂存", 0: "作废", 3: "等待重新审批", 4: "提交"}),
        FilterDef("saler_no", "sso.sales_order_no", "合同编号", "like"),
        FilterDef("sales_name", "ap3.person_Name", "业务", "like"),
    ],
    field_labels={
        "orderDate": FieldLabel("order_date", "开票日期"),
        "orderNo": FieldLabel("order_no", "开票编号"),
        "salesOrderNo": FieldLabel("sales_order_no", "合同号"),
        "customerNameCn": FieldLabel("customer_name_cn", "客户名称"),
        "requestInvoiceType": FieldLabel("request_invoice_type", "票据类型"),
        "requestInvoiceMedia": FieldLabel("request_invoice_media", "发票介质"),
        "requestAmt": FieldLabel("request_amt", "发票金额"),
        "invoiceNo": FieldLabel("invoice_no", "发票号码"),
        "bstatus": FieldLabel("bstatus", "收款状态"),
        "shippingNo": FieldLabel("shipping_no", "快递单号"),
        "contactName": FieldLabel("contact_name", "接收人"),
        "salesName": FieldLabel("sales_name", "业务"),
        "mobileTelephone": FieldLabel("mobile_telephone", "接收人电话"),
        "applicantName": FieldLabel("applicant_name", "申请人"),
        "detailBstatus": FieldLabel("detail_bstatus", "接收状态"),
        "personName": FieldLabel("person_name", "记录人"),
        "rstatus": FieldLabel("rstatus", "状态"),
        "companyInvoiceName": FieldLabel("company_invoice_name", "发票抬头"),
    },
    enum_fields={
        "bstatus": EnumField({1: "已收", 2: "部分已收", 3: "未收"}),
        "detail_bstatus": EnumField({1: "electron", 2: "已收"}),
        "request_invoice_media": EnumField({1: "电子发票", 2: "纸质发票", 3: "电子+纸质"}),
        "request_invoice_type": EnumField({1: "收据", 2: "增值税专用发票", 3: "增值税普通发票", 4: "形式发票"}),
        "rstatus": EnumField({1: "审核", 2: "暂存", 0: "作废", 3: "等待重新审批", 4: "提交"}),
    },
)
