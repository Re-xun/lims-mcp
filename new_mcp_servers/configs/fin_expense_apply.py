"""Module config: 费用报销列表 (FinExpenseApplyListAction)"""
from __future__ import annotations
from new_mcp_servers.core.config import EnumField, FieldLabel, FilterDef, ModuleConfig

_BASE_PATH = "/FinExpenseApplyListAction"

fin_expense_apply = ModuleConfig(
    name="query_daily_expense_apply_list",
    display_name="费用报销",
    description="查询日常费用报销/用车申请列表。",
    endpoint=_BASE_PATH + "/listQueryMyPerson",
    scope_endpoints={
        "mine": _BASE_PATH + "/listQueryMyPerson",
        "dept": _BASE_PATH + "/listQueryMyDept",
        "car_request": _BASE_PATH + "/listQueryCarRequest",
        "all": _BASE_PATH + "/listQuery",
    },
    extra_params=["include_raw"],
    filters=[
        FilterDef("apply_no", "fea.apply_no", "申请编号", "like"),
        FilterDef("bill_biz_type_id", "alc.lookup_name", "申请类别", "like"),
        FilterDef("bstatus", "fead.bstatus", "报销状态", "="),
        FilterDef("department_id", "fea.department_id", "申请部门", "="),
        FilterDef("end_time", "fea.apply_date", "申请日期止", "<=", is_date_range=True),
        FilterDef("fast_search", "fastSearch", "快速搜索", "like"),
        FilterDef("person_id", "ap.PERSON_NAME", "申请人", "like"),
        FilterDef("remark", "fead.remark", "申请内容", "like"),
        FilterDef("rstatus", "fea.rstatus", "审核状态", "=",
                  enums={0: "已作废", 1: "已审核", 2: "暂存", 3: "等待重新审批", 4: "审批中"}),
        FilterDef("start_time", "fea.apply_date", "申请日期起", ">=", is_date_range=True),
    ],
    field_labels={
        "applyNo": FieldLabel("apply_no", "申请编号"),
        "applyDate": FieldLabel("apply_date", "申请日期"),
        "personName": FieldLabel("person_name", "申请人"),
        "lookupName": FieldLabel("lookup_name", "申请类别"),
        "departmentName": FieldLabel("department_name", "申请部门"),
        "tripType": FieldLabel("trip_type", "用车类别"),
        "visitingObject": FieldLabel("visiting_object", "用车对象"),
        "remark": FieldLabel("remark", "申请内容与说明"),
        "salesName": FieldLabel("sales_name", "负责业务"),
        "amt": FieldLabel("amt", "预计支出金额"),
        "attendant": FieldLabel("attendant", "乘客名称"),
        "itemName": FieldLabel("item_name", "预计支出科目"),
        "startTime": FieldLabel("start_time", "用车日期"),
        "rstatus": FieldLabel("rstatus", "审核状态"),
        "courseType": FieldLabel("course_type", "里程类型"),
        "bstatus": FieldLabel("bstatus", "报销状态"),
        "tripOrigin": FieldLabel("trip_origin", "行程起始地址"),
        "isapply": FieldLabel("isapply", "转申请类型"),
        "tripDest": FieldLabel("trip_dest", "行程目的地址"),
        "actAmt": FieldLabel("act_amt", "实际支出金额"),
        "otherRemark": FieldLabel("other_remark", "备注"),
        "paymentAmt": FieldLabel("payment_amt", "实际报销金额"),
        "processDesc": FieldLabel("process_desc", "审批流程"),
        "test": FieldLabel("test", "车牌"),
    },
    enum_fields={
        "bstatus": EnumField({"1": "未报销", "2": "已报销"}),
        "course_type": EnumField({"1": "单程", "2": "往返"}),
        "rstatus": EnumField({0: "已作废", 1: "已审核", 2: "暂存", 3: "等待重新审批", 4: "审批中"}),
        "trip_type": EnumField({"1": "客户接送", "2": "样品接送", "3": "专家接送", "4": "出差用车"}),
    },
)
