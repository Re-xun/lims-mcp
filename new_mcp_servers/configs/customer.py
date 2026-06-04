"""
Module config: 客户列表 (AbdCustomerListAction)

完整迁移自 ``mcp_servers/customer_mcp/tools.py``。
"""

from __future__ import annotations

from new_mcp_servers.core.config import EnumField, FieldLabel, FilterDef, ModuleConfig

_BASE_PATH = "/AbdCustomerListAction"

customer = ModuleConfig(
    name="query_customer_list",
    display_name="客户列表",
    description="查询客户列表，支持默认、部门、我的、客户部门和重名客户视图；返回 count、columns、data。",
    endpoint=_BASE_PATH + "/listQuery",
    scope_endpoints={
        "default": _BASE_PATH + "/listQuery",
        "dept": _BASE_PATH + "/listQueryByDept",
        "mine": _BASE_PATH + "/customerMyList",
        "customer_dept": _BASE_PATH + "/customerDeptList",
        "colliding_names": _BASE_PATH + "/listQueryCollidingNames",
        "listquerycollidingnames": _BASE_PATH + "/listQueryCollidingNames",
    },
    scope_datatype_defaults={
        "default": "LIST_ALL_VIEW",
    },
    extra_params=["date_enums", "include_raw"],
    filters=[
        # ── 核心筛选 ──
        FilterDef("address", "aca.ADDRESS_CN", "地址", "like"),
        FilterDef("customer_name", "ac.customer_name_cn", "客户名称", "like"),
        FilterDef("customer_name_en", "ac.customer_name_en", "英文名称", "like"),
        FilterDef("customer_no", "ac.customer_no", "编号", "like"),
        FilterDef("customer_phase", "ac.customerPhase", "客户阶段", "=",
                  enums={1: "未合作", 2: "已合作"}),
        FilterDef("customer_status", "ac.customer_status", "客户状态", "="),
        FilterDef("dept", "ad.department_name", "销售部门", "like"),
        FilterDef("fast_search", "fastSearch", "快速搜索", "like"),
        FilterDef("responsible_department", "ad.department_name", "负责部门", "like"),
        FilterDef("responsible_for_business", "ap.PERSON_NAME", "负责业务", "like"),
        FilterDef("rstatus", "ac.rstatus", "状态", "=",
                  enums={0: "已作废", 1: "已审核", 2: "暂存", 3: "等待重新审批", 4: "审批中"}),
        FilterDef("settlement_type", "ac.settlementType", "结算类型", "=",
                  enums={1: "月结客户"}),
        FilterDef("short_name", "ac.short_name", "简称", "like"),
        FilterDef("sub_customer_name", "q_subCustomerName", "客户部门", "like"),
        # ── 日期范围 ──
        FilterDef("create_on_start", "ac.create_on", "创建日期起", ">=", is_date_range=True),
        FilterDef("create_on_end", "ac.create_on", "创建日期止", "<=", is_date_range=True),
        FilterDef("latest_contact_on_start", "latestContactOn", "最近联系日期起", ">=", is_date_range=True),
        FilterDef("latest_contact_on_end", "latestContactOn", "最近联系日期止", "<=", is_date_range=True),
        # ── 候选 filter ──
        FilterDef("abd_customer_type_customer_type_name", "abdCustomerType.customerTypeName", "客户类别", "like"),
        FilterDef("abd_department_name", "abdDepartmentName", "负责部门(候选)", "like"),
        FilterDef("abd_person_name", "abdPersonName", "负责业务(候选)", "like"),
        FilterDef("address_cn", "addressCn", "地址(候选)", "like"),
        FilterDef("contact_name", "contactName", "联系人名", "like"),
        FilterDef("credit_code", "creditCode", "统一社会信用代码", "like"),
        FilterDef("customer_address_name", "customerAddressName", "公司地址(候选)", "like"),
        FilterDef("customer_name_cn", "customerNameCn", "名称(中)(候选)", "like"),
        FilterDef("department_name", "departmentName", "销售部门(候选)", "like"),
        FilterDef("main_product", "mainProduct", "主要产品", "like"),
        FilterDef("main_request", "mainRequest", "主要需求", "like"),
        FilterDef("number_one_year", "numberOneYear", "一年内订单数", "like"),
        FilterDef("person_name", "personName", "负责人(候选)", "like"),
        FilterDef("share_person_names", "sharePersonNames", "共享业务员", "like"),
    ],
    field_labels={
        "customerName": FieldLabel("customer_name", "客户名称"),
        "customerPhase": FieldLabel("customer_phase", "客户阶段"),
        "subCustomerName": FieldLabel("sub_customer_name", "客户部门"),
        "rstatus": FieldLabel("rstatus", "状态"),
        "customerNameEn": FieldLabel("customer_name_en", "名称(英)"),
        "customerNo": FieldLabel("customer_no", "编号"),
        "customerStatus": FieldLabel("customer_status", "客户状态"),
        "customerNameCn": FieldLabel("customer_name_cn", "名称(中)"),
        "personName": FieldLabel("person_name", "负责人"),
        "departmentName": FieldLabel("department_name", "销售部门"),
        "shortName": FieldLabel("short_name", "简称"),
        "customerAddressName": FieldLabel("customer_address_name", "公司地址"),
        "addressCn": FieldLabel("address_cn", "地址"),
        "createOn": FieldLabel("create_on", "创建日期"),
        "contactName": FieldLabel("contact_name", "联系人名"),
        "latestContactOn": FieldLabel("latest_contact_on", "最近联系日期"),
        "creditCode": FieldLabel("credit_code", "统一社会信用代码"),
        "abdCustomerType.customerTypeName": FieldLabel("abd_customer_type_customer_type_name", "客户类别"),
        "mainProduct": FieldLabel("main_product", "主要产品"),
        "settlementType": FieldLabel("settlement_type", "结算类型"),
        "abdDepartmentName": FieldLabel("abd_department_name", "负责部门"),
        "abdPersonName": FieldLabel("abd_person_name", "负责业务"),
        "sharePersonNames": FieldLabel("share_person_names", "共享业务员"),
        "mainRequest": FieldLabel("main_request", "主要需求"),
        "numberOneYear": FieldLabel("number_one_year", "一年内订单数"),
    },
    enum_fields={
        "customer_phase": EnumField({1: "未合作", 2: "已合作"}),
        "rstatus": EnumField({0: "已作废", 1: "已审核", 2: "暂存", 3: "等待重新审批", 4: "审批中"}),
        "settlement_type": EnumField({1: "月结客户"}),
    },
    row_field_map={
        # Special field mappings: some backend fields sit at different keys
        "customer_name_cn": "customerName",      # Backend uses 'customerName' not 'customerNameCn'
        "customer_name_en": "customerName_en",    # Backend uses 'customerName_en' not 'customerNameEn'
        "person_name": "responsePerson",
        "department_name": "dept",
        "customer_address_name": "customerAddress",
        "address_cn": "address",
        "abd_department_name": "responsibleDepartment",
        "abd_person_name": "responsibleForBusiness",
    },
)
