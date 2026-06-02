"""Naming and method-scope helpers for MCP agent docs."""

from __future__ import annotations

import re
from pathlib import Path


def slugify(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]+", "_", value).strip("_") or "class"


def snake_case(value: str) -> str:
    value = value.replace("-", "_").replace(".", "_")
    value = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", value)
    value = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", value)
    value = re.sub(r"[^a-zA-Z0-9_]+", "_", value)
    value = re.sub(r"_+", "_", value).strip("_")
    return value.lower() or "field"


def extract_package_tail(java_file: str) -> str:
    parts = Path(java_file).parts
    if "java" in parts:
        idx = parts.index("java")
        return ".".join(parts[idx + 1 : -1])
    return str(Path(java_file).parent)


def to_pretty_tool_name(class_name: str) -> str:
    lower = class_name.lower()
    if "psplan" in lower:
        return "query_contact_plan_list"
    if "quotation" in lower:
        return "query_quotation_list"
    if "salesorder" in lower and "trace" in lower:
        return "query_sales_order_trace_list"
    if "salesorder" in lower:
        return "query_sales_order_list"
    if "customer" in lower:
        return "query_customer_list"
    if "supplier" in lower:
        return "query_supplier_list"
    if "device" in lower:
        return "query_device_list"
    if "opportunity" in lower:
        return "query_sales_opportunity_list"
    if "project" in lower:
        return "query_project_list"
    return f"query_{slugify(class_name).lower()}"


VIEW_KEYWORD_MAP: list[tuple[str, str, str]] = [
    ("listquery", "default", "默认列表查询"),
    ("subcontract", "subcontract", "分包列表视图"),
    ("temporary", "temporary", "临时单据视图"),
    ("material", "material", "物料相关视图"),
    ("reliability", "reliability", "可靠性视图"),
    ("expense", "expense", "费用报销视图"),
    ("emcgen", "emcgen", "EMC-GEN 业务视图"),
    ("select", "select", "选择器/弹窗视图"),
    ("report", "report", "报表视图"),
    ("count", "count", "统计视图"),
    ("saler", "saler", "业务员视图"),
    ("payment", "payment", "付款相关视图"),
    ("safety", "safety", "安全业务视图"),
    ("dept", "dept", "部门范围视图"),
    ("week", "my_week", "我的本周数据视图"),
    ("home", "home", "首页/主页视图"),
    ("emc", "emc", "EMC 业务视图"),
    ("gen", "gen", "GEN 业务视图"),
    ("sfy", "safety", "安全业务视图"),
    ("qm", "qm", "QM 业务视图"),
    ("sd", "sd", "SD 业务视图"),
    ("dm", "dm", "DM 业务视图"),
    ("rf", "rf", "RF 业务视图"),
    ("op", "op", "OP 业务视图"),
    ("biz", "biz", "业务视图"),
    ("all", "all", "全部数据视图"),
    ("my", "mine", "我的数据视图"),
    ("mine", "mine", "我的数据视图"),
    ("forme", "mine", "我的数据视图"),
]


def build_scope_hints(methods: list[str]) -> list[tuple[str, str]]:
    hints: list[tuple[str, str]] = []
    seen: set[str] = set()
    for method in methods:
        lower = method.lower()
        scope = method
        meaning = "按该视图查询"
        for keyword, view_name, desc in VIEW_KEYWORD_MAP:
            if keyword in lower:
                scope = view_name
                meaning = desc
                break
        if scope in seen:
            continue
        seen.add(scope)
        hints.append((scope, meaning))
    return hints
