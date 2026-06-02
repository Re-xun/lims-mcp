#!/usr/bin/env python3
"""
Scan Java backend controllers and frontend request code to inventory GET APIs.

Outputs a CSV with:
- backend controller path, method name, parameters
- matching frontend GET call sites
- a best-effort note for "filter" style merged string parameters
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable


JAVA_SUFFIXES = {".java"}
FRONTEND_SUFFIXES = {".js", ".jsx", ".ts", ".tsx", ".vue"}
METHOD_PATTERN = re.compile(
    r"(public|protected|private)\s+[\w<>\[\], ?]+\s+(?P<name>\w+)\s*\(",
    re.MULTILINE,
)
CLASS_REQUEST_MAPPING = re.compile(
    r"@RequestMapping\s*\((?P<body>.*?)\)\s*(?:public\s+)?(?:class|interface|enum)\s+\w+",
    re.DOTALL,
)
GET_MAPPING_PATTERN = re.compile(
    r"@(?P<annotation>GetMapping|RequestMapping)\s*\((?P<body>.*?)\)",
    re.DOTALL,
)
REQUEST_METHOD_GET = re.compile(
    r"RequestMethod\s*\.\s*GET|method\s*=\s*\{?\s*RequestMethod\s*\.\s*GET",
    re.DOTALL,
)
PARAM_NAME_PATTERN = re.compile(r'(?:value|name)\s*=\s*"([^"]+)"|"([^"]+)"')
PATH_LITERAL_PATTERN = re.compile(r'(?:value|path)\s*=\s*"([^"]+)"|"([^"]+)"')
FRONTEND_GET_PATTERN = re.compile(
    r"(?P<caller>[\w$.]+)\.get\s*\(\s*(?P<quote>['\"`])(?P<url>.+?)(?P=quote)\s*(?:,\s*(?P<args>\{[\s\S]{0,1500}?\}))?\s*\)",
    re.MULTILINE,
)
FETCH_PATTERN = re.compile(
    r"fetch\s*\(\s*(?P<quote>['\"`])(?P<url>.+?)(?P=quote)\s*,\s*(?P<args>\{[\s\S]{0,1500}?\})\s*\)",
    re.MULTILINE,
)
FILTER_ASSIGN_PATTERN = re.compile(
    r"(?:const|let|var)\s+filter\s*=\s*(?P<expr>[\s\S]{0,1200}?);",
    re.MULTILINE,
)


@dataclass
class BackendParam:
    name: str
    type: str
    source: str
    required: str
    raw: str


@dataclass
class BackendEndpoint:
    path: str
    http_method: str
    java_file: str
    class_name: str
    method_name: str
    backend_params: list[BackendParam]
    mapping_annotation: str


@dataclass
class FrontendCall:
    path: str
    http_method: str
    frontend_file: str
    line: int
    caller: str
    param_keys: list[str]
    filter_hint: str


def walk_files(root: Path, suffixes: set[str]) -> Iterable[Path]:
    if not root.exists():
        return []
    return (path for path in root.rglob("*") if path.is_file() and path.suffix in suffixes)


def read_text(path: Path) -> str:
    for encoding in ("utf-8", "utf-8-sig", "gbk", "latin1"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    return path.read_text(errors="ignore")


def normalize_path(raw: str) -> str:
    raw = raw.strip()
    if not raw:
        return ""
    raw = raw.split("?")[0]
    raw = re.sub(r"https?://[^/]+", "", raw)
    raw = raw.replace("${", "{")
    if not raw.startswith("/"):
        raw = "/" + raw
    raw = re.sub(r"/{2,}", "/", raw)
    return raw


def extract_string_literal(mapping_body: str) -> str:
    match = PATH_LITERAL_PATTERN.search(mapping_body)
    if not match:
        return ""
    return match.group(1) or match.group(2) or ""


def build_full_path(class_path: str, method_path: str) -> str:
    class_path = class_path.strip()
    method_path = method_path.strip()
    parts = [part.strip("/") for part in (class_path, method_path) if part]
    if not parts:
        return "/"
    return "/" + "/".join(parts)


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

        if char in {"'", '"'}:
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


def parse_backend_param(raw_param: str) -> BackendParam:
    source = "raw"
    required = ""
    name = ""
    annotation_match = re.search(r"@(\w+)\s*(\((?P<body>[\s\S]*?)\))?", raw_param)
    cleaned = re.sub(r"@\w+\s*(\([\s\S]*?\))?\s*", "", raw_param).strip()
    cleaned = re.sub(r"\bfinal\b\s+", "", cleaned).strip()

    if annotation_match:
        source = annotation_match.group(1)
        body = annotation_match.group("body") or ""
        required_match = re.search(r"required\s*=\s*(true|false)", body)
        if required_match:
            required = required_match.group(1)
        name_match = PARAM_NAME_PATTERN.search(body)
        if name_match:
            name = name_match.group(1) or name_match.group(2) or ""

    tokens = cleaned.split()
    param_name = tokens[-1] if tokens else ""
    param_type = " ".join(tokens[:-1]) if len(tokens) > 1 else ""
    if not name:
        name = param_name

    return BackendParam(
        name=name,
        type=param_type,
        source=source,
        required=required,
        raw=" ".join(raw_param.split()),
    )


def find_matching_paren(text: str, open_index: int) -> int:
    depth = 0
    in_string: str | None = None
    escape = False
    for index in range(open_index, len(text)):
        char = text[index]
        if in_string:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == in_string:
                in_string = None
            continue
        if char in {"'", '"'}:
            in_string = char
            continue
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0:
                return index
    return -1


def extract_class_name(text: str) -> str:
    match = re.search(r"\bclass\s+(\w+)", text)
    return match.group(1) if match else ""


def extract_class_base_path(text: str) -> str:
    match = CLASS_REQUEST_MAPPING.search(text)
    if not match:
        return ""
    return extract_string_literal(match.group("body"))


def extract_backend_endpoints(java_root: Path) -> list[BackendEndpoint]:
    endpoints: list[BackendEndpoint] = []
    for path in walk_files(java_root, JAVA_SUFFIXES):
        text = read_text(path)
        if "@GetMapping" not in text and "RequestMethod.GET" not in text:
            continue

        class_name = extract_class_name(text)
        class_base_path = extract_class_base_path(text)

        for mapping_match in GET_MAPPING_PATTERN.finditer(text):
            annotation = mapping_match.group("annotation")
            body = mapping_match.group("body")
            if annotation == "RequestMapping" and not REQUEST_METHOD_GET.search(body):
                continue

            method_match = METHOD_PATTERN.search(text, mapping_match.end())
            if not method_match:
                continue

            open_paren = text.find("(", method_match.start())
            close_paren = find_matching_paren(text, open_paren)
            if open_paren == -1 or close_paren == -1:
                continue

            method_signature = text[method_match.start() : close_paren + 1]
            method_name = method_match.group("name")
            params_text = text[open_paren + 1 : close_paren].strip()
            raw_params = split_top_level(params_text) if params_text else []
            backend_params = [parse_backend_param(raw) for raw in raw_params]
            method_path = extract_string_literal(body)

            endpoints.append(
                BackendEndpoint(
                    path=build_full_path(class_base_path, method_path),
                    http_method="GET",
                    java_file=str(path),
                    class_name=class_name,
                    method_name=method_name,
                    backend_params=backend_params,
                    mapping_annotation=" ".join(text[mapping_match.start() : mapping_match.end()].split()),
                )
            )
    return endpoints


def extract_js_object_keys(block: str) -> list[str]:
    keys: list[str] = []
    for item in split_top_level(block):
        item = item.strip()
        if not item or item.startswith("..."):
            continue
        key_match = re.match(r"([A-Za-z_$][\w$-]*)\s*:", item)
        if key_match:
            keys.append(key_match.group(1))
        else:
            short_match = re.match(r"([A-Za-z_$][\w$]*)$", item)
            if short_match:
                keys.append(short_match.group(1))
    return keys


def extract_params_block(args_text: str) -> str:
    match = re.search(r"params\s*:\s*\{(?P<body>[\s\S]{0,1000}?)\}", args_text)
    return match.group("body") if match else ""


def extract_filter_hint(prefix_text: str, args_text: str) -> str:
    hints: list[str] = []
    if "filter" in args_text:
        hints.append("request contains filter parameter")
    match = list(FILTER_ASSIGN_PATTERN.finditer(prefix_text[-3000:]))
    if match:
        expr = " ".join(match[-1].group("expr").split())
        hints.append(f"filter assignment: {expr[:240]}")
    join_match = re.search(r"\.join\(\s*(['\"`].*?['\"`])\s*\)", prefix_text[-3000:])
    if join_match:
        hints.append(f"join delimiter: {join_match.group(1)}")
    return " | ".join(hints)


def extract_frontend_calls(frontend_root: Path) -> list[FrontendCall]:
    calls: list[FrontendCall] = []
    for path in walk_files(frontend_root, FRONTEND_SUFFIXES):
        text = read_text(path)
        matches = list(FRONTEND_GET_PATTERN.finditer(text))
        matches.extend(FETCH_PATTERN.finditer(text))
        for match in matches:
            args_text = match.groupdict().get("args") or ""
            if match.re is FETCH_PATTERN and not re.search(r"method\s*:\s*['\"]GET['\"]", args_text):
                continue

            url = match.group("url")
            params_block = extract_params_block(args_text)
            param_keys = extract_js_object_keys(params_block)
            prefix_text = text[: match.start()]
            line = text.count("\n", 0, match.start()) + 1
            calls.append(
                FrontendCall(
                    path=normalize_path(url),
                    http_method="GET",
                    frontend_file=str(path),
                    line=line,
                    caller=match.groupdict().get("caller") or "fetch",
                    param_keys=param_keys,
                    filter_hint=extract_filter_hint(prefix_text, args_text),
                )
            )
    return calls


def score_path_match(backend_path: str, frontend_path: str) -> int:
    if not backend_path or not frontend_path:
        return 0
    if backend_path == frontend_path:
        return 3
    if backend_path.endswith(frontend_path) or frontend_path.endswith(backend_path):
        return 2
    if backend_path.split("/")[-1] == frontend_path.split("/")[-1]:
        return 1
    return 0


def match_frontend_calls(endpoint: BackendEndpoint, calls: list[FrontendCall]) -> list[FrontendCall]:
    scored = [(score_path_match(endpoint.path, call.path), call) for call in calls]
    scored = [item for item in scored if item[0] > 0]
    scored.sort(key=lambda item: item[0], reverse=True)
    return [call for _, call in scored[:5]]


def serialize_params(params: list[BackendParam]) -> str:
    return json.dumps([asdict(param) for param in params], ensure_ascii=False)


def write_csv(
    output_path: Path,
    endpoints: list[BackendEndpoint],
    frontend_calls: list[FrontendCall],
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "http_method",
                "backend_path",
                "java_file",
                "class_name",
                "method_name",
                "backend_params_json",
                "mapping_annotation",
                "frontend_path",
                "frontend_file",
                "frontend_line",
                "frontend_caller",
                "frontend_param_keys",
                "filter_hint",
            ],
        )
        writer.writeheader()

        if endpoints:
            for endpoint in endpoints:
                matches = match_frontend_calls(endpoint, frontend_calls)
                if not matches:
                    writer.writerow(
                        {
                            "http_method": endpoint.http_method,
                            "backend_path": endpoint.path,
                            "java_file": endpoint.java_file,
                            "class_name": endpoint.class_name,
                            "method_name": endpoint.method_name,
                            "backend_params_json": serialize_params(endpoint.backend_params),
                            "mapping_annotation": endpoint.mapping_annotation,
                            "frontend_path": "",
                            "frontend_file": "",
                            "frontend_line": "",
                            "frontend_caller": "",
                            "frontend_param_keys": "",
                            "filter_hint": "",
                        }
                    )
                    continue

                for match in matches:
                    writer.writerow(
                        {
                            "http_method": endpoint.http_method,
                            "backend_path": endpoint.path,
                            "java_file": endpoint.java_file,
                            "class_name": endpoint.class_name,
                            "method_name": endpoint.method_name,
                            "backend_params_json": serialize_params(endpoint.backend_params),
                            "mapping_annotation": endpoint.mapping_annotation,
                            "frontend_path": match.path,
                            "frontend_file": match.frontend_file,
                            "frontend_line": match.line,
                            "frontend_caller": match.caller,
                            "frontend_param_keys": ",".join(match.param_keys),
                            "filter_hint": match.filter_hint,
                        }
                    )
        else:
            for call in frontend_calls:
                writer.writerow(
                    {
                        "http_method": call.http_method,
                        "backend_path": "",
                        "java_file": "",
                        "class_name": "",
                        "method_name": "",
                        "backend_params_json": "",
                        "mapping_annotation": "",
                        "frontend_path": call.path,
                        "frontend_file": call.frontend_file,
                        "frontend_line": call.line,
                        "frontend_caller": call.caller,
                        "frontend_param_keys": ",".join(call.param_keys),
                        "filter_hint": call.filter_hint,
                    }
                )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract GET APIs from Java backend and frontend request code."
    )
    parser.add_argument(
        "--backend-dir",
        default="backend",
        help="Java backend root directory. Default: backend",
    )
    parser.add_argument(
        "--frontend-dir",
        default="frontend",
        help="Frontend root directory. Default: frontend",
    )
    parser.add_argument(
        "--output",
        default="dist/get_api_inventory.csv",
        help="Output CSV path. Default: dist/get_api_inventory.csv",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    backend_root = Path(args.backend_dir).resolve()
    frontend_root = Path(args.frontend_dir).resolve()
    output_path = Path(args.output).resolve()

    endpoints = extract_backend_endpoints(backend_root)
    frontend_calls = extract_frontend_calls(frontend_root)
    write_csv(output_path, endpoints, frontend_calls)

    print(f"backend GET endpoints: {len(endpoints)}")
    print(f"frontend GET calls: {len(frontend_calls)}")
    print(f"output: {output_path}")


if __name__ == "__main__":
    main()
