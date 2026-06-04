"""Module config: 临检服务项目 (SdTempTestServiceItemListAction)"""
from __future__ import annotations
from new_mcp_servers.core.config import EnumField, FieldLabel, FilterDef, ModuleConfig

_BASE_PATH = "/SdTempTestServiceItemListAction"

sd_temp_test_service_item = ModuleConfig(
    name="query_sdtemptestserviceitemlistaction",
    display_name="临检服务项目",
    description="查询临时检测服务项目列表。",
    endpoint=_BASE_PATH + "/listQuery",
    scope_endpoints={"default": _BASE_PATH + "/listQuery"},
    extra_params=["include_raw"],
    filters=[
        FilterDef("fast_search", "fastSearch", "快速搜索", "like"),
        FilterDef("item_name", "itemName", "项目名称", "like"),
        FilterDef("item_no", "itemNo", "编号", "like"),
        FilterDef("item_type", "itemType", "项目类型", "="),
        FilterDef("modular_type", "modularType", "模块类型", "="),
        FilterDef("rstatus", "rstatus", "状态", "="),
    ],
    field_labels={
        "itemNo": FieldLabel("item_no", "编号"),
        "departmentName": FieldLabel("department_name", "负责部门"),
        "itemName": FieldLabel("item_name", "项目名称"),
        "unitPrice": FieldLabel("unit_price", "价格"),
        "unitName": FieldLabel("unit_name", "计价单位"),
        "costAssessment": FieldLabel("cost_assessment", "成本预估"),
        "testCapability": FieldLabel("test_capability", "测试能力"),
        "itemType": FieldLabel("item_type", "项目类型"),
        "modularType": FieldLabel("modular_type", "模块类型"),
        "rstatus": FieldLabel("rstatus", "状态"),
        "remark": FieldLabel("remark", "备注"),
    },
    enum_fields={
        "item_type": EnumField({"EMI": "EMI", "EMS": "EMS", "电性能": "电性能", "丰田项目": "丰田项目", "RF": "RF"}),
        "modular_type": EnumField({
            "general_emc": "普通EMC", "rf": "RF", "sar": "SAR", "emc": "汽车电子EMC",
            "electrical_emc": "汽车电子电性能", "reliability": "环境可靠性", "pencil": "线束",
            "safety": "安规实验室", "energy_efficiency": "能效", "sound_pressure": "声压",
            "battery": "电池", "material": "材料", "software": "软件",
            "information_security": "信息安全", "material_pencil": "材料线束", "connector": "连接器",
            "chemistry": "化学实验室", "other": "其他", "optical_property": "光学实验室",
        }),
        "rstatus": EnumField({0: "已作废", 1: "已审核", 2: "暂存", 3: "等待重新审批", 4: "审批中"}),
    },
)
