"""Inventory grouping and candidate metadata helpers."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
import re
from typing import Any

from .io import read_text


LIST_METHOD_PARAM_NAMES = ("start", "limit", "filter", "sVars")


def build_candidate_from_inventory(
    class_name: str,
    java_group: dict[str, list[dict[str, Any]]],
    xml_group: dict[str, list[dict[str, Any]]],
    backend_root: Path,
) -> dict[str, str]:
    java_items = java_group.get(class_name, [])
    xml_items = xml_group.get(class_name, [])
    if not java_items and not xml_items:
        raise KeyError(class_name)

    methods = sorted({item["method_name"] for item in java_items} | {item["query_method"] for item in xml_items})
    java_file = ""
    if java_items:
        java_file = java_items[0]["java_file"]
    else:
        matches = list(backend_root.rglob(f"{class_name}.java"))
        java_file = str(matches[0]) if matches else ""

    return {
        "class_name": class_name,
        "has_filter": str(any(item.get("has_filter") for item in java_items) or bool(xml_items)),
        "has_svars": str(any(item.get("has_svars") for item in java_items) or bool(xml_items)),
        "has_xml_binding": str(bool(xml_items)),
        "method_count": str(len(methods)),
        "methods": ",".join(methods),
        "sample_endpoint": (
            java_items[0].get("endpoint_path", "")
            if java_items
            else (xml_items[0].get("inferred_endpoint_path", "") if xml_items else "")
        ),
        "java_file": java_file,
    }

def infer_business_summary(class_name: str, java_file: str, methods: list[str], query_fields: list[dict[str, Any]]) -> tuple[str, str]:
    lower = class_name.lower()
    file_lower = java_file.lower()
    field_names = {field["name"].lower() for field in query_fields}

    if "psplan" in lower or "\\psplan\\" in file_lower:
        return "客户联系计划列表查询，通常包含全部、部门、我的、本周等联系计划视图。", "高"
    if "psactivity" in lower or "\\psactivity\\" in file_lower:
        return "客户联系记录列表查询，可用于查看全部、部门、我的联系记录，并结合下次联系日期继续推进联系计划。", "高"

    if "opportunity" in lower:
        return "销售机会列表查询，通常包含全部、部门、我的等销售机会视图。", "高"
    if "quotation" in lower:
        return "报价单列表查询，通常包含全部、部门、我的等列表视图。", "高"
    if "salesorder" in lower and "trace" in lower:
        return "销售合同跟踪或经营分析类列表查询。", "中"
    if "salesorder" in lower:
        return "销售合同列表或销售报表查询。", "中"
    if "customer" in lower:
        return "客户列表、客户统计或客户选择类查询。", "中"
    if "supplier" in lower:
        return "供应商列表、供应商统计或选择类查询。", "中"
    if "device" in lower:
        return "设备列表、设备选择或设备业务明细查询。", "中"
    if "location" in lower:
        return "地点、实验室位置或位置选择类查询。", "中"
    if "project" in lower:
        return "项目列表、项目统计或项目跟踪类查询。", "中"
    if "temporarytest" in lower or ("temporary" in lower and "test" in lower):
        return "临时测试、临时委托或测试任务列表查询。", "高"
    if "testplan" in lower:
        return "测试计划或测试计划明细类查询。", "中"
    if "test" in lower:
        return "测试相关列表查询。", "中"
    if "report" in lower:
        return "报告管理、报告统计或报告追踪类查询。", "中"
    if "payment" in lower:
        return "付款申请、付款单或付款明细查询。", "中"
    if "receiving" in lower:
        return "收款通知、收款明细或收款跟踪查询。", "中"
    if "invoice" in lower:
        return "发票列表、开票明细或发票报表查询。", "中"
    if "department" in lower:
        return "部门树、部门列表或部门维度数据查询。", "中"
    if "sample" in lower:
        return "样品列表、样品流转或样品明细查询。", "中"

    if {"q_projectno", "q_testitem", "q_consignornamecn"} & field_names:
        return "项目或测试业务列表查询。", "低"
    if {"q_devicename", "q_model", "q_serialnumber"} & field_names:
        return "设备业务列表查询。", "低"
    if "listquery" in "".join(method.lower() for method in methods) or "listquery" in file_lower:
        return "列表查询接口，建议结合 XML 和前端页面进一步确认业务。", "低"
    return "待结合 XML 和前端页面进一步确认的列表查询。", "低"


def build_inventory_groups(inventory: dict[str, Any]) -> tuple[dict[str, list[dict[str, Any]]], dict[str, list[dict[str, Any]]]]:
    java_group: dict[str, list[dict[str, Any]]] = defaultdict(list)
    xml_group: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for item in inventory.get("java_items", []):
        java_group[item["class_name"]].append(item)
    for item in inventory.get("xml_items", []):
        xml_group[item["inferred_class_name"]].append(item)

    return java_group, xml_group


def find_java_file(class_name: str, java_group: dict[str, list[dict[str, Any]]], backend_root: Path) -> str:
    java_items = java_group.get(class_name, [])
    if java_items:
        return java_items[0].get("java_file", "")
    matches = list(backend_root.rglob(f"{class_name}.java"))
    return str(matches[0]) if matches else ""


def is_list_base_action(java_file: str) -> bool:
    if not java_file:
        return False
    path = Path(java_file)
    if not path.exists():
        return False
    return "extends ListBaseAction" in read_text(path)


def has_list_query_method(items: list[dict[str, Any]]) -> bool:
    return any((item.get("method_name") or "").lower() == "listquery" for item in items)


def build_inherited_list_query_item(class_name: str, java_file: str) -> dict[str, Any]:
    return {
        "class_name": class_name,
        "java_file": java_file,
        "method_name": "listQuery",
        "endpoint_path": f"/{class_name}/listQuery",
        "http_methods": ["GET", "POST"],
        "params": list(LIST_METHOD_PARAM_NAMES),
        "has_filter": True,
        "has_svars": True,
    }


def discover_xml_bindings_by_action_url(class_name: str, backend_root: Path) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    action_pattern = re.compile(
        rf"<query\b[^>]*\bactionUrl\s*=\s*['\"]{re.escape(class_name)}['\"][^>]*/?>"
    )
    query_method_pattern = re.compile(r"\bqueryMethod\s*=\s*['\"]([^'\"]+)['\"]")

    for xml_path in backend_root.rglob("*.xml"):
        if "target/classes" in xml_path.as_posix():
            continue
        text = read_text(xml_path)
        for match in action_pattern.finditer(text):
            query_tag = match.group(0)
            method_match = query_method_pattern.search(query_tag)
            query_method = (method_match.group(1) if method_match else "listQuery").strip()
            if not query_method:
                query_method = "listQuery"
            items.append(
                {
                    "source": "xml",
                    "action_url": class_name,
                    "query_method": query_method,
                    "inferred_endpoint_path": f"/{class_name}/{query_method}",
                    "xml_file": str(xml_path),
                    "inferred_class_name": class_name,
                }
            )
    return items


def ensure_xml_bindings_by_action_url(
    class_name: str,
    xml_group: dict[str, list[dict[str, Any]]],
    backend_root: Path,
) -> None:
    items = xml_group.setdefault(class_name, [])
    seen = {(item.get("xml_file"), item.get("query_method")) for item in items}
    for item in discover_xml_bindings_by_action_url(class_name, backend_root):
        key = (item.get("xml_file"), item.get("query_method"))
        if key not in seen:
            items.append(item)
            seen.add(key)


def ensure_inherited_list_query(
    class_name: str,
    java_group: dict[str, list[dict[str, Any]]],
    backend_root: Path,
) -> None:
    java_file = find_java_file(class_name, java_group, backend_root)
    if not is_list_base_action(java_file):
        return

    items = java_group.setdefault(class_name, [])
    if has_list_query_method(items):
        return
    items.append(build_inherited_list_query_item(class_name, java_file))


def select_candidates(
    candidates: list[dict[str, str]],
    requested_classes: list[str],
    java_group: dict[str, list[dict[str, Any]]],
    xml_group: dict[str, list[dict[str, Any]]],
    backend_root: Path,
) -> list[dict[str, str]]:
    candidate_map = {candidate["class_name"]: candidate for candidate in candidates}
    for class_name in requested_classes:
        ensure_xml_bindings_by_action_url(class_name, xml_group, backend_root)
        ensure_inherited_list_query(class_name, java_group, backend_root)
        if class_name in candidate_map:
            candidate_map[class_name] = build_candidate_from_inventory(class_name, java_group, xml_group, backend_root)
        else:
            candidate_map[class_name] = build_candidate_from_inventory(class_name, java_group, xml_group, backend_root)

    if not requested_classes:
        for class_name in list(candidate_map):
            ensure_inherited_list_query(class_name, java_group, backend_root)
            candidate_map[class_name] = build_candidate_from_inventory(class_name, java_group, xml_group, backend_root)

    return (
        [candidate_map[class_name] for class_name in requested_classes]
        if requested_classes
        else list(candidate_map.values())
    )
