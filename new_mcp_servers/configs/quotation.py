"""
Module config: 报价单列表 (SdQuotationListAction)

完整迁移自 ``mcp_servers/quotation_mcp/tools.py``。
"""

from __future__ import annotations

from new_mcp_servers.core.config import EnumField, FieldLabel, FilterDef, ModuleConfig

_BASE_PATH = "/SdQuotationListAction"

quotation = ModuleConfig(
    name="query_quotation_list",
    display_name="报价单列表",
    description="查询报价单列表。通过 scope/view 路由到全部(default)、部门(dept)、我的(my)三个后端列表接口。返回 count、columns、data。",
    endpoint=_BASE_PATH + "/listQuery",
    scope_endpoints={
        "default": _BASE_PATH + "/listQuery",
        "dept": _BASE_PATH + "/listQueryDept",
        "my": _BASE_PATH + "/listQueryMy",
    },
    scope_svars={
        "default": {"customerType": 1},
        "dept": {"customerType": 2},
        "my": {"customerType": 3},
    },
    scope_datatype_defaults={
        "default": "Last30days",
        "dept": "listView",
        "my": "listView",
    },
    extra_params=["include_raw"],
    filters=[
        # ── 核心筛选（第 4 节） ──
        FilterDef("bstatus", "sq.bstatus", "报价单状态", "=",
                  enums={1: "未签回", 2: "已签回"}),
        FilterDef("rstatus", "sq.rstatus", "单据状态", "=",
                  enums={0: "已作废", 1: "已审核", 2: "暂存", 3: "等待重新审批", 4: "审批中"}),
        FilterDef("create_on_start", "sq.create_on", "创建日期起", ">=", is_date_range=True),
        FilterDef("create_on_end", "sq.create_on", "创建日期止", "<=", is_date_range=True),
        FilterDef("fast_search", "fastSearch", "快速搜索", "like"),
        FilterDef("quotation_no", "sq.quotation_no", "报价单号", "like"),
        FilterDef("sale_dept", "ad.department_name", "销售部门", "like"),
        FilterDef("sale_person", "ap.PERSON_NAME", "负责销售", "like"),
        FilterDef("sample_model_cn", "sq.sample_model_cn", "样品型号", "like"),
        FilterDef("sample_name_cn", "sq.sample_name_cn", "样品名称", "like"),
        FilterDef("service_item_desc", "sq.service_item_desc", "项目描述", "like"),
        FilterDef("short_customer_name", "ac1.CUSTOMER_NAME_CN", "客户名称", "like"),
        FilterDef("terminal_authorization_customer", "sq.terminal_authorization_customer_name", "授权方终端客户", "like"),
        # ── 候选 filter（第 4.1 节，根据列表返回列反推） ──
        FilterDef("amt_with_tax_currency", "amtWithTaxCurrency", "优惠后金额(候选)", "like"),
        FilterDef("department_name", "departmentName", "部门(候选)", "like"),
        FilterDef("last_update_on_start", "lastUpdateOn", "更新日期起(候选)", ">=", is_date_range=True),
        FilterDef("last_update_on_end", "lastUpdateOn", "更新日期止(候选)", "<=", is_date_range=True),
        FilterDef("net_profits_ratio", "netProfitsRatio", "利润率%(候选)", "like"),
        FilterDef("remark", "remark", "内部备注(候选)", "like"),
        FilterDef("saler_name", "salerName", "销售(候选)", "like"),
        FilterDef("sum_unit_price_with_sub_currency", "sumUnitPriceWithSubCurrency", "报价金额(候选)", "like"),
        FilterDef("terminal_authorization_customer_name", "terminalAuthorizationCustomerName", "终端客户名(候选)", "like"),
    ],
    field_labels={
        "rstatus": FieldLabel("rstatus", "单据状态"),
        "createOn": FieldLabel("create_on", "创建日期"),
        "bstatus": FieldLabel("bstatus", "报价单状态"),
        "lastUpdateOn": FieldLabel("last_update_on", "更新日期"),
        "quotationNo": FieldLabel("quotation_no", "报价单号"),
        "shortCustomerName": FieldLabel("short_customer_name", "客户名称"),
        "terminalAuthorizationCustomerName": FieldLabel("terminal_authorization_customer_name", "授权方终端客户"),
        "serviceItemDesc": FieldLabel("service_item_desc", "项目描述"),
        "sampleNameCn": FieldLabel("sample_name_cn", "样品名称"),
        "sampleModelCn": FieldLabel("sample_model_cn", "样品型号"),
        "sumUnitPriceWithSubCurrency": FieldLabel("sum_unit_price_with_sub_currency", "报价金额"),
        "amtWithTaxCurrency": FieldLabel("amt_with_tax_currency", "优惠后金额"),
        "netProfitsRatio": FieldLabel("net_profits_ratio", "利润率%"),
        "salerName": FieldLabel("saler_name", "销售"),
        "departmentName": FieldLabel("department_name", "部门"),
        "remark": FieldLabel("remark", "内部备注"),
    },
    enum_fields={
        "bstatus": EnumField({1: "未签回", 2: "已签回"}),
        "rstatus": EnumField({0: "已作废", 1: "已审核", 2: "暂存", 3: "等待重新审批", 4: "审批中"}),
    },
)
