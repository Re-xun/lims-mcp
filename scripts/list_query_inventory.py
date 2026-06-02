#!/usr/bin/env python3
"""
Inventory backend listQuery-style interfaces from Java actions and XML list views.

Outputs:
- CSV: flattened rows for easy filtering in Excel
- JSON: structured data for downstream LLM / MCP generation

Typical usage:
    python scripts/list_query_inventory.py --backend-root F:\lims-server\lims-admin
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable
from xml.etree import ElementTree as ET


JAVA_SUFFIXES = {".java"}
XML_SUFFIXES = {".xml"}
EXCLUDED_DIRS = {"target", ".git", ".idea", ".vscode", "build", "out"}

CLASS_REQUEST_MAPPING = re.compile(
    r"@RequestMapping\s*\((?P<body>.*?)\)\s*(?:@\w+(?:\([^)]*\))?\s*)*(?:public\s+)?(?:class|interface|enum)\s+(?P<name>\w+)",
    re.DOTALL,
)
CLASS_FALLBACK = re.compile(r"(?:public\s+)?class\s+(?P<name>\w+)")
METHOD_SIGNATURE_PATTERN = re.compile(
    r"^[ \t]*(?:public|protected|private)\s+[\w<>\[\], ?@]+\s+(?P<name>listQuery\w*)\s*\(",
    re.MULTILINE,
)
NEAREST_MAPPING_PATTERN = re.compile(
    r"@(?P<annotation>GetMapping|PostMapping|PutMapping|DeleteMapping|PatchMapping|RequestMapping)\s*\((?P<body>.*?)\)",
    re.DOTALL,
)
REQUEST_METHOD_PATTERN = re.compile(r"RequestMethod\s*\.\s*(GET|POST|PUT|DELETE|PATCH)")
EXPLICIT_PATH_PATTERN = re.compile(r'(?:value|path)\s*=\s*"([^"]+)"')
EXPLICIT_PARAM_NAME_PATTERN = re.compile(r'(?:value|name)\s*=\s*"([^"]+)"')
FIRST_STRING_LITERAL_PATTERN = re.compile(r'"([^"]+)"')
LIST_QUERY_METHOD_PATTERN = re.compile(r"^listQuery\w*$", re.IGNORECASE)


@dataclass
class JavaListQueryEndpoint:
    class_name: str
    java_file: str
    method_name: str
    endpoint_path: str
    http_methods: list[str]
    params: list[str]
    has_filter: bool
    has_svars: bool
    source_type: str = "java"


@dataclass
class XmlListQueryBinding:
    action_url: str
    query_method: str
    xml_file: str
    inferred_class_name: str
    inferred_endpoint_path: str
    source_type: str = "xml"


def walk_files(root: Path, suffixes: set[str]) -> Iterable[Path]:
    if not root.exists():
        return []

    def _iter() -> Iterable[Path]:
        for path in root.rglob("*"):
            if not path.is_file() or path.suffix not in suffixes:
                continue
            if any(part in EXCLUDED_DIRS for part in path.parts):
                continue
            yield path

    return _iter()


def read_text(path: Path) -> str:
    for encoding in ("utf-8", "utf-8-sig", "gbk", "latin1"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    return path.read_text(errors="ignore")


def split_top_level(text: str, delimiter: str = ",") -> list[str]:
    parts: list[str] = []
    current: list[str] = []
    depth_angle = depth_round = depth_square = depth_curly = 0
    in_string: str | None = None
    escape = False

    for char in text:
        if in_string:
            current.append(char)
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == in_string:
                in_string = None
            continue

        if char in {"'", '"', "`"}:
            in_string = char
            current.append(char)
            continue

        if char == "<":
            depth_angle += 1
        elif char == ">":
            depth_angle = max(0, depth_angle - 1)
        elif char == "(":
            depth_round += 1
        elif char == ")":
            depth_round = max(0, depth_round - 1)
        elif char == "[":
            depth_square += 1
        elif char == "]":
            depth_square = max(0, depth_square - 1)
        elif char == "{":
            depth_curly += 1
        elif char == "}":
            depth_curly = max(0, depth_curly - 1)

        if (
            char == delimiter
            and depth_angle == 0
            and depth_round == 0
            and depth_square == 0
            and depth_curly == 0
        ):
            part = "".join(current).strip()
            if part:
                parts.append(part)
            current = []
            continue

        current.append(char)

    tail = "".join(current).strip()
    if tail:
        parts.append(tail)
    return parts


def extract_method_params_from_open_paren(content: str, open_idx: int) -> str:
    depth = 0
    in_string: str | None = None
    escape = False
    for idx in range(open_idx, len(content)):
        char = content[idx]
        if in_string:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == in_string:
                in_string = None
            continue

        if char in {'"', "'", "`"}:
            in_string = char
            continue
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0:
                return content[open_idx + 1 : idx]
    return ""


def extract_string_literal(mapping_body: str) -> str:
    body = mapping_body or ""
    match = EXPLICIT_PATH_PATTERN.search(body)
    if match:
        return match.group(1) or ""
    fallback = FIRST_STRING_LITERAL_PATTERN.search(body)
    return fallback.group(1) if fallback else ""


def normalize_path(raw: str) -> str:
    raw = (raw or "").strip()
    if not raw:
        return ""
    if not raw.startswith("/"):
        raw = "/" + raw
    raw = re.sub(r"/{2,}", "/", raw)
    return raw


def build_full_path(class_path: str, method_path: str) -> str:
    class_path = class_path.strip("/")
    method_path = method_path.strip("/")
    parts = [part for part in (class_path, method_path) if part]
    return normalize_path("/".join(parts)) if parts else "/"


def parse_param_name(raw_param: str) -> str:
    annotation_match = re.search(r"@(\w+)\s*(\((?P<body>[\s\S]*?)\))?", raw_param)
    if annotation_match:
        body = annotation_match.group("body") or ""
        name_match = EXPLICIT_PARAM_NAME_PATTERN.search(body)
        if name_match:
            annotated = name_match.group(1)
            if annotated:
                return annotated

    cleaned = re.sub(r"@\w+\s*(\([\s\S]*?\))?\s*", "", raw_param).strip()
    cleaned = re.sub(r"\bfinal\b\s+", "", cleaned).strip()
    tokens = cleaned.split()
    return tokens[-1] if tokens else raw_param.strip()


def parse_class_info(content: str, java_path: Path) -> tuple[str, str]:
    class_match = CLASS_REQUEST_MAPPING.search(content)
    class_name = ""
    class_path = ""
    if class_match:
        class_name = class_match.group("name")
        class_path = extract_string_literal(class_match.group("body"))
    else:
        fallback = CLASS_FALLBACK.search(content)
        class_name = fallback.group("name") if fallback else java_path.stem
    return class_name, class_path


def infer_http_methods(annotation: str, body: str) -> list[str]:
    if annotation == "GetMapping":
        return ["GET"]
    if annotation == "PostMapping":
        return ["POST"]
    if annotation == "PutMapping":
        return ["PUT"]
    if annotation == "DeleteMapping":
        return ["DELETE"]
    if annotation == "PatchMapping":
        return ["PATCH"]

    methods = REQUEST_METHOD_PATTERN.findall(body or "")
    if methods:
        return sorted(set(methods))
    return ["GET", "POST"]


def find_nearest_mapping_before(content: str, method_start: int) -> tuple[str, str]:
    search_window = content[max(0, method_start - 1200) : method_start]
    matches = list(NEAREST_MAPPING_PATTERN.finditer(search_window))
    if not matches:
        return "RequestMapping", ""
    match = matches[-1]
    return match.group("annotation"), match.group("body") or ""


def scan_java_list_queries(backend_root: Path) -> list[JavaListQueryEndpoint]:
    results: list[JavaListQueryEndpoint] = []
    for java_path in walk_files(backend_root, JAVA_SUFFIXES):
        content = read_text(java_path)
        class_name, class_path = parse_class_info(content, java_path)

        for match in METHOD_SIGNATURE_PATTERN.finditer(content):
            method_name = match.group("name")
            mapping_annotation, mapping_body = find_nearest_mapping_before(content, match.start())
            params_raw = extract_method_params_from_open_paren(content, match.end() - 1)
            endpoint_path = build_full_path(class_path, extract_string_literal(mapping_body))
            http_methods = infer_http_methods(mapping_annotation, mapping_body)
            params = [parse_param_name(part) for part in split_top_level(params_raw) if part.strip()]
            lowered = {param.lower() for param in params}

            results.append(
                JavaListQueryEndpoint(
                    class_name=class_name,
                    java_file=str(java_path),
                    method_name=method_name,
                    endpoint_path=endpoint_path,
                    http_methods=http_methods,
                    params=params,
                    has_filter="filter" in lowered,
                    has_svars="svars" in lowered,
                )
            )
    return sorted(results, key=lambda item: (item.class_name.lower(), item.method_name.lower(), item.endpoint_path))


def scan_xml_list_query_bindings(backend_root: Path) -> list[XmlListQueryBinding]:
    results: list[XmlListQueryBinding] = []
    for xml_path in walk_files(backend_root, XML_SUFFIXES):
        try:
            root = ET.fromstring(read_text(xml_path))
        except ET.ParseError:
            continue

        for elem in root.iter():
            action_url = (elem.attrib.get("actionUrl") or "").strip()
            query_method = (elem.attrib.get("queryMethod") or "").strip()
            if not action_url or not query_method:
                continue
            if not LIST_QUERY_METHOD_PATTERN.match(query_method):
                continue

            inferred_class_name = action_url.split("/")[-1]
            inferred_endpoint_path = build_full_path(action_url, query_method)
            results.append(
                XmlListQueryBinding(
                    action_url=action_url,
                    query_method=query_method,
                    xml_file=str(xml_path),
                    inferred_class_name=inferred_class_name,
                    inferred_endpoint_path=inferred_endpoint_path,
                )
            )

    unique: dict[tuple[str, str, str], XmlListQueryBinding] = {}
    for item in results:
        unique[(item.action_url, item.query_method, item.xml_file)] = item
    return sorted(unique.values(), key=lambda item: (item.inferred_class_name.lower(), item.query_method.lower(), item.xml_file))


def write_csv(
    csv_path: Path,
    java_items: list[JavaListQueryEndpoint],
    xml_items: list[XmlListQueryBinding],
) -> None:
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=[
                "source_type",
                "class_name",
                "method_name",
                "endpoint_path",
                "http_methods",
                "params",
                "has_filter",
                "has_svars",
                "java_or_xml_file",
                "action_url",
                "query_method",
            ],
        )
        writer.writeheader()

        for item in java_items:
            writer.writerow(
                {
                    "source_type": item.source_type,
                    "class_name": item.class_name,
                    "method_name": item.method_name,
                    "endpoint_path": item.endpoint_path,
                    "http_methods": ",".join(item.http_methods),
                    "params": ",".join(item.params),
                    "has_filter": "yes" if item.has_filter else "no",
                    "has_svars": "yes" if item.has_svars else "no",
                    "java_or_xml_file": item.java_file,
                    "action_url": "",
                    "query_method": "",
                }
            )

        for item in xml_items:
            writer.writerow(
                {
                    "source_type": item.source_type,
                    "class_name": item.inferred_class_name,
                    "method_name": item.query_method,
                    "endpoint_path": item.inferred_endpoint_path,
                    "http_methods": "",
                    "params": "",
                    "has_filter": "",
                    "has_svars": "",
                    "java_or_xml_file": item.xml_file,
                    "action_url": item.action_url,
                    "query_method": item.query_method,
                }
            )


def build_summary(java_items: list[JavaListQueryEndpoint], xml_items: list[XmlListQueryBinding]) -> dict:
    classes = sorted({item.class_name for item in java_items} | {item.inferred_class_name for item in xml_items})
    methods = sorted({item.method_name for item in java_items} | {item.query_method for item in xml_items})
    return {
        "java_list_query_methods": len(java_items),
        "xml_list_query_bindings": len(xml_items),
        "distinct_classes": len(classes),
        "distinct_method_names": methods,
        "classes": classes,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Inventory listQuery-style backend interfaces.")
    parser.add_argument("--backend-root", required=True, help="Backend project root, e.g. F:\\lims-server\\lims-admin")
    parser.add_argument(
        "--csv-out",
        default=str(Path("dist") / "list_query_inventory.csv"),
        help="CSV output path",
    )
    parser.add_argument(
        "--json-out",
        default=str(Path("dist") / "list_query_inventory.json"),
        help="JSON output path",
    )
    args = parser.parse_args()

    backend_root = Path(args.backend_root)
    java_items = scan_java_list_queries(backend_root)
    xml_items = scan_xml_list_query_bindings(backend_root)
    summary = build_summary(java_items, xml_items)

    csv_path = Path(args.csv_out)
    json_path = Path(args.json_out)
    write_csv(csv_path, java_items, xml_items)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(
        json.dumps(
            {
                "backend_root": str(backend_root),
                "summary": summary,
                "java_items": [asdict(item) for item in java_items],
                "xml_items": [asdict(item) for item in xml_items],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print(f"Backend root: {backend_root}")
    print(f"Java listQuery methods: {len(java_items)}")
    print(f"XML listQuery bindings: {len(xml_items)}")
    print(f"Distinct classes: {summary['distinct_classes']}")
    print(f"CSV written to: {csv_path}")
    print(f"JSON written to: {json_path}")


if __name__ == "__main__":
    main()
