#!/usr/bin/env python3
"""
Generate MCP-oriented context docs for classes that extend ListBaseAction.

Compared with generate_mcpagent_docs.py, this script:
1. selects candidate classes by Java inheritance (`extends ListBaseAction`)
2. injects an inherited `/ClassName/listQuery` endpoint when the class does
   not declare it explicitly but should support the base listQuery pattern

Output:
- docs/mcpagent_listbase/index.md
- docs/mcpagent_listbase/<ClassName>.md
"""

from __future__ import annotations

import argparse
import re
from collections import defaultdict
from copy import deepcopy
from pathlib import Path
from typing import Any

import generate_mcpagent_docs as base


DEFAULT_OUTPUT_DIR = "docs/mcpagent_listbase"
LIST_METHOD_PARAM_NAMES = ("start", "limit", "filter", "sVars")


def discover_list_base_action_classes(backend_root: Path) -> dict[str, str]:
    class_to_java: dict[str, str] = {}
    for java_path in backend_root.rglob("*ListAction.java"):
        text = base.read_text(java_path)
        if "extends ListBaseAction" not in text:
            continue
        class_name = java_path.stem
        class_to_java[class_name] = str(java_path)
    return class_to_java


def has_list_query_method(items: list[dict[str, Any]]) -> bool:
    return any((item.get("method_name") or "").lower() == "listquery" for item in items)


def build_inherited_list_query_item(class_name: str, java_file: str) -> dict[str, Any]:
    return {
        "class_name": class_name,
        "java_file": java_file,
        "method_name": "listQuery",
        "endpoint_path": f"/{class_name}/listQuery",
        "http_methods": ["GET", "POST"],
        "params": ["start", "limit", "filter", "sVars"],
        "has_filter": True,
        "has_svars": True,
    }


def parse_request_mapping_methods(class_name: str, java_file: str) -> list[dict[str, Any]]:
    text = base.read_text(Path(java_file))
    items: list[dict[str, Any]] = []
    pattern = re.compile(
        r'@RequestMapping\s*\(\s*value\s*=\s*"(?P<path>/[^"]+)"(?P<mapping_body>[\s\S]*?)\)\s*'
        r'(?:@[^\n]+\s*)*'
        r'public[\s\S]*?\s+(?P<method>\w+)\s*\((?P<params>[\s\S]*?)\)\s*\{',
        re.MULTILINE,
    )

    for match in pattern.finditer(text):
        method_name = match.group("method")
        params_text = match.group("params")
        if "List" not in method_name and "list" not in method_name:
            continue
        if not all(re.search(rf'\b{name}\b', params_text) for name in LIST_METHOD_PARAM_NAMES):
            continue

        mapping_text = match.group(0)
        http_methods = []
        if "RequestMethod.GET" in mapping_text:
            http_methods.append("GET")
        if "RequestMethod.POST" in mapping_text:
            http_methods.append("POST")
        if not http_methods:
            http_methods = ["GET", "POST"]

        items.append(
            {
                "class_name": class_name,
                "java_file": java_file,
                "method_name": method_name,
                "endpoint_path": f"/{class_name}{match.group('path')}",
                "http_methods": http_methods,
                "params": list(LIST_METHOD_PARAM_NAMES),
                "has_filter": True,
                "has_svars": True,
            }
        )
    return items


def append_missing_list_methods(class_name: str, java_file: str, items: list[dict[str, Any]]) -> None:
    existing_methods = {item.get("method_name") for item in items}
    for item in parse_request_mapping_methods(class_name, java_file):
        if item["method_name"] in existing_methods:
            continue
        items.append(item)
        existing_methods.add(item["method_name"])


def build_candidates(
    *,
    inventory: dict[str, Any],
    requested_classes: list[str],
) -> tuple[list[dict[str, str]], dict[str, list[dict[str, Any]]], dict[str, list[dict[str, Any]]], Path]:
    java_group: dict[str, list[dict[str, Any]]] = defaultdict(list)
    xml_group: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for item in inventory.get("java_items", []):
        java_group[item["class_name"]].append(deepcopy(item))
    for item in inventory.get("xml_items", []):
        xml_group[item["inferred_class_name"]].append(deepcopy(item))

    backend_root = Path(inventory["backend_root"])
    list_base_classes = discover_list_base_action_classes(backend_root)

    selected_class_names = requested_classes or sorted(list_base_classes)
    candidates: list[dict[str, str]] = []

    for class_name in selected_class_names:
        java_file = list_base_classes.get(class_name)
        if not java_file:
            continue

        items = java_group.setdefault(class_name, [])
        if not has_list_query_method(items):
            items.append(build_inherited_list_query_item(class_name, java_file))
        append_missing_list_methods(class_name, java_file, items)

        candidate = base.build_candidate_from_inventory(class_name, java_group, xml_group, backend_root)
        candidate["java_file"] = java_file
        candidates.append(candidate)

    return candidates, java_group, xml_group, backend_root


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate MCP agent docs for ListBaseAction classes.")
    parser.add_argument("--inventory-json", default=base.DEFAULT_INVENTORY)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--frontend-root", default=base.DEFAULT_FRONTEND_ROOT)
    parser.add_argument(
        "--class-name",
        action="append",
        default=[],
        help="Generate doc for a specific ListBaseAction class. Can be passed multiple times.",
    )
    args = parser.parse_args()

    inventory = base.load_inventory(Path(args.inventory_json))
    frontend_root = Path(args.frontend_root) if args.frontend_root else None

    candidates, java_group, xml_group, backend_root = build_candidates(
        inventory=inventory,
        requested_classes=args.class_name,
    )

    enum_index = base.build_enum_index(backend_root)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    for candidate in candidates:
        class_name = candidate["class_name"]
        content = base.render_doc(
            candidate,
            java_group.get(class_name, []),
            xml_group.get(class_name, []),
            enum_index,
            base.parse_frontend_svars(class_name, frontend_root),
        )
        (output_dir / f"{class_name}.md").write_text(content, encoding="utf-8")

    (output_dir / "index.md").write_text(base.render_index(candidates), encoding="utf-8")
    print(f"Generated {len(candidates)} docs in {output_dir}")


if __name__ == "__main__":
    main()
