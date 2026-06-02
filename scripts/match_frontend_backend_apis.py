#!/usr/bin/env python3
"""
Match frontend request call sites to backend Java controller endpoints.

The matcher uses multiple signals:
- HTTP method
- normalized path similarity
- overlapping parameter names
- important parameter names such as filter/sVars/action/id
- domain/module hints from file paths and URL segments

Outputs:
- CSV report for manual review
- JSON report with structured match reasons
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


JAVA_SUFFIXES = {".java"}
FRONTEND_SUFFIXES = {".js", ".jsx", ".ts", ".tsx", ".vue", ".py"}
KEY_PARAM_BONUS = {"filter", "svars", "action", "id", "start", "limit", "page", "size", "keyword"}
EXCLUDED_FRONTEND_DIRS = {"node_modules", ".git", "dist", "build", "coverage", ".idea", ".vscode"}
EXCLUDED_BACKEND_DIRS = {"target", ".git", ".idea", ".vscode", "build", "out"}
LIKELY_FRONTEND_CALLERS = {
    "axios",
    "request",
    "http",
    "service",
    "api",
    "$http",
    "$axios",
    "defhttp",
    "fetch",
    "getbyparams",
    "python_client",
}

METHOD_PATTERN = re.compile(
    r"(public|protected|private)\s+[\w<>\[\], ?]+\s+(?P<name>\w+)\s*\(",
    re.MULTILINE,
)
CLASS_REQUEST_MAPPING = re.compile(
    r"@RequestMapping\s*\((?P<body>.*?)\)\s*(?:@\w+(?:\([^)]*\))?\s*)*(?:public\s+)?(?:class|interface|enum)\s+\w+",
    re.DOTALL,
)
MAPPING_PATTERN = re.compile(
    r"@(?P<annotation>GetMapping|PostMapping|PutMapping|DeleteMapping|PatchMapping|RequestMapping)\s*\((?P<body>.*?)\)",
    re.DOTALL,
)
REQUEST_METHOD_PATTERN = re.compile(r"RequestMethod\s*\.\s*(GET|POST|PUT|DELETE|PATCH)")
PARAM_NAME_PATTERN = re.compile(r'(?:value|name)\s*=\s*"([^"]+)"|"([^"]+)"')
PATH_LITERAL_PATTERN = re.compile(r'(?:value|path)\s*=\s*"([^"]+)"|"([^"]+)"')

FRONTEND_GET_PATTERN = re.compile(
    r"(?P<caller>[\w$.]+)\.(?P<method>get|post|put|patch|delete)\s*\(\s*(?P<quote>['\"`])(?P<url>.+?)(?P=quote)\s*(?:,\s*(?P<args>\{[\s\S]{0,2200}?\}))?\s*\)",
    re.MULTILINE,
)
FETCH_PATTERN = re.compile(
    r"fetch\s*\(\s*(?P<quote>['\"`])(?P<url>.+?)(?P=quote)\s*,\s*(?P<args>\{[\s\S]{0,2200}?\})\s*\)",
    re.MULTILINE,
)
GET_BY_PARAMS_PATTERN = re.compile(
    r"getByParams\s*\(\s*(?P<quote>['\"`])(?P<url>.+?)(?P=quote)\s*,\s*\{(?P<body>[\s\S]{0,2200}?)\}\s*(?:,|\))",
    re.MULTILINE,
)
AXIOS_PATTERN = re.compile(
    r"axios\.(?P<method>get|post|put|patch|delete)\s*\(\s*(?P<quote>['\"`])(?P<url>.+?)(?P=quote)\s*(?:,\s*(?P<args>[\s\S]{0,2200}?))?\)",
    re.MULTILINE,
)
PY_HTTPX_PATTERN = re.compile(
    r"\.(?P<method>get|post|put|patch|delete)\s*\(\s*f?(?P<quote>['\"])(?P<url>.+?)(?P=quote)\s*,(?P<args>[\s\S]{0,2200}?)\)",
    re.MULTILINE,
)


@dataclass
class BackendParam:
    name: str
    type: str
    source: str
    required: str


@dataclass
class BackendEndpoint:
    path: str
    http_method: str
    java_file: str
    class_name: str
    method_name: str
    params: list[str]
    params_detail: list[BackendParam]
    domain_hints: list[str]


@dataclass
class FrontendCall:
    path: str
    http_method: str
    frontend_file: str
    line: int
    caller: str
    param_keys: list[str]
    domain_hints: list[str]


def walk_files(root: Path, suffixes: set[str], excluded_dir_names: set[str]) -> Iterable[Path]:
    if not root.exists():
        return []

    def _iter() -> Iterable[Path]:
        for path in root.rglob("*"):
            if not path.is_file() or path.suffix not in suffixes:
                continue
            if any(part in excluded_dir_names for part in path.parts):
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


def normalize_path(raw: str) -> str:
    raw = (raw or "").strip()
    if not raw:
        return ""
    raw = raw.split("?")[0].strip()
    raw = raw.replace("${", "{")
    raw = re.sub(r"https?://[^/]+", "", raw)
    raw = re.sub(r"\{JAVA_API_BASE\}", "", raw)
    if not raw.startswith("/") and not raw.startswith("modal://"):
        raw = "/" + raw
    raw = re.sub(r"/{2,}", "/", raw)
    return raw


def normalize_token(token: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", token.lower()).strip("_")


def path_segments(path: str) -> list[str]:
    return [normalize_token(seg) for seg in path.strip("/").split("/") if normalize_token(seg)]


def is_likely_api_path(path: str) -> bool:
    normalized = normalize_path(path)
    if not normalized or normalized == "/":
        return False
    if any(marker in normalized for marker in ("Action", "/api/", "/server/", "/Storage/", "/Login", "modal://")):
        return True
    return len(path_segments(normalized)) >= 2


def is_likely_frontend_caller(caller: str) -> bool:
    normalized = normalize_token(caller)
    if normalized in LIKELY_FRONTEND_CALLERS:
        return True
    return any(token in normalized for token in ("axios", "request", "http", "service", "api", "client"))


def infer_domain_hints(file_path: str, path: str, class_name: str = "") -> list[str]:
    hints: set[str] = set()
    normalized_file = file_path.replace("\\", "/").lower()
    for token in re.findall(r"[a-zA-Z][a-zA-Z0-9]+", normalized_file):
        token = normalize_token(token)
        if token and token not in {"src", "main", "java", "views", "components", "api", "utils"}:
            hints.add(token)
    for segment in path_segments(path):
        if segment not in {"api", "modal"}:
            hints.add(segment)
    if class_name:
        hints.add(normalize_token(class_name.replace("controller", "").replace("action", "")))
    return sorted(h for h in hints if h)


def extract_string_literal(mapping_body: str) -> str:
    match = PATH_LITERAL_PATTERN.search(mapping_body or "")
    if not match:
        return ""
    return match.group(1) or match.group(2) or ""


def build_full_path(class_path: str, method_path: str) -> str:
    parts = [part.strip("/") for part in (class_path.strip(), method_path.strip()) if part.strip()]
    if not parts:
        return "/"
    return "/" + "/".join(parts)


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

    return BackendParam(name=name, type=param_type, source=source, required=required)


def extract_class_name(text: str) -> str:
    match = re.search(r"\bclass\s+(\w+)", text)
    return match.group(1) if match else ""


def extract_class_base_path(text: str) -> str:
    match = CLASS_REQUEST_MAPPING.search(text)
    if not match:
        return ""
    return extract_string_literal(match.group("body"))


def resolve_mapping_method(annotation: str, body: str) -> str | None:
    if annotation == "RequestMapping":
        match = REQUEST_METHOD_PATTERN.search(body or "")
        return match.group(1) if match else None
    return {
        "GetMapping": "GET",
        "PostMapping": "POST",
        "PutMapping": "PUT",
        "DeleteMapping": "DELETE",
        "PatchMapping": "PATCH",
    }.get(annotation)


def extract_backend_endpoints(java_root: Path) -> list[BackendEndpoint]:
    endpoints: list[BackendEndpoint] = []
    for path in walk_files(java_root, JAVA_SUFFIXES, EXCLUDED_BACKEND_DIRS):
        text = read_text(path)
        if "Mapping" not in text:
            continue

        class_name = extract_class_name(text)
        class_base_path = extract_class_base_path(text)

        for mapping_match in MAPPING_PATTERN.finditer(text):
            annotation = mapping_match.group("annotation")
            body = mapping_match.group("body")
            http_method = resolve_mapping_method(annotation, body)
            if not http_method:
                continue

            method_match = METHOD_PATTERN.search(text, mapping_match.end())
            if not method_match:
                continue

            open_paren = text.find("(", method_match.start())
            close_paren = find_matching_paren(text, open_paren)
            if open_paren == -1 or close_paren == -1:
                continue

            method_name = method_match.group("name")
            params_text = text[open_paren + 1 : close_paren].strip()
            raw_params = split_top_level(params_text) if params_text else []
            param_details = [parse_backend_param(raw) for raw in raw_params]
            params = [normalize_token(param.name) for param in param_details if param.name]
            method_path = extract_string_literal(body)
            full_path = normalize_path(build_full_path(class_base_path, method_path))

            endpoints.append(
                BackendEndpoint(
                    path=full_path,
                    http_method=http_method,
                    java_file=str(path),
                    class_name=class_name,
                    method_name=method_name,
                    params=sorted(set(params)),
                    params_detail=param_details,
                    domain_hints=infer_domain_hints(str(path), full_path, class_name),
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
    if not args_text:
        return ""
    params_match = re.search(r"params\s*:\s*\{(?P<body>[\s\S]{0,1600}?)\}", args_text)
    if params_match:
        return params_match.group("body")
    direct_match = re.search(r"\{(?P<body>[\s\S]{0,1600})\}", args_text)
    return direct_match.group("body") if direct_match else ""


def extract_fetch_method(args_text: str) -> str:
    method_match = re.search(r"method\s*:\s*['\"]([A-Za-z]+)['\"]", args_text or "")
    return method_match.group(1).upper() if method_match else "GET"


def build_frontend_call(path: Path, text: str, start_index: int, method: str, url: str, caller: str, args_text: str) -> FrontendCall:
    params_block = extract_params_block(args_text)
    param_keys = sorted({normalize_token(key) for key in extract_js_object_keys(params_block) if normalize_token(key)})
    normalized_url = normalize_path(url)
    line = text.count("\n", 0, start_index) + 1
    return FrontendCall(
        path=normalized_url,
        http_method=method.upper(),
        frontend_file=str(path),
        line=line,
        caller=caller,
        param_keys=param_keys,
        domain_hints=infer_domain_hints(str(path), normalized_url),
    )


def extract_frontend_calls(frontend_root: Path) -> list[FrontendCall]:
    calls: list[FrontendCall] = []
    for path in walk_files(frontend_root, FRONTEND_SUFFIXES, EXCLUDED_FRONTEND_DIRS):
        text = read_text(path)

        for match in FRONTEND_GET_PATTERN.finditer(text):
            if not is_likely_frontend_caller(match.group("caller")):
                continue
            if not is_likely_api_path(match.group("url")):
                continue
            calls.append(
                build_frontend_call(
                    path=path,
                    text=text,
                    start_index=match.start(),
                    method=match.group("method"),
                    url=match.group("url"),
                    caller=match.group("caller"),
                    args_text=match.group("args") or "",
                )
            )

        for match in AXIOS_PATTERN.finditer(text):
            if not is_likely_api_path(match.group("url")):
                continue
            calls.append(
                build_frontend_call(
                    path=path,
                    text=text,
                    start_index=match.start(),
                    method=match.group("method"),
                    url=match.group("url"),
                    caller="axios",
                    args_text=match.group("args") or "",
                )
            )

        for match in FETCH_PATTERN.finditer(text):
            args_text = match.group("args") or ""
            if not is_likely_api_path(match.group("url")):
                continue
            calls.append(
                build_frontend_call(
                    path=path,
                    text=text,
                    start_index=match.start(),
                    method=extract_fetch_method(args_text),
                    url=match.group("url"),
                    caller="fetch",
                    args_text=args_text,
                )
            )

        for match in GET_BY_PARAMS_PATTERN.finditer(text):
            if not is_likely_api_path(match.group("url")):
                continue
            calls.append(
                build_frontend_call(
                    path=path,
                    text=text,
                    start_index=match.start(),
                    method="GET",
                    url=match.group("url"),
                    caller="getByParams",
                    args_text="{" + (match.group("body") or "") + "}",
                )
            )

        if path.suffix == ".py":
            for match in PY_HTTPX_PATTERN.finditer(text):
                if not is_likely_api_path(match.group("url")):
                    continue
                calls.append(
                    build_frontend_call(
                        path=path,
                        text=text,
                        start_index=match.start(),
                        method=match.group("method"),
                        url=match.group("url"),
                        caller="python_client",
                        args_text=match.group("args") or "",
                    )
                )

    return deduplicate_frontend_calls(calls)


def deduplicate_frontend_calls(calls: list[FrontendCall]) -> list[FrontendCall]:
    dedup: dict[tuple[str, str, str, int], FrontendCall] = {}
    for call in calls:
        key = (call.frontend_file, call.http_method, call.path, call.line)
        existing = dedup.get(key)
        if not existing:
            dedup[key] = call
            continue
        existing.param_keys = sorted(set(existing.param_keys) | set(call.param_keys))
        existing.domain_hints = sorted(set(existing.domain_hints) | set(call.domain_hints))
    return list(dedup.values())


def score_path(backend_path: str, frontend_path: str) -> tuple[int, list[str]]:
    score = 0
    reasons: list[str] = []
    backend_segments = path_segments(backend_path)
    frontend_segments = path_segments(frontend_path)

    if backend_path == frontend_path and backend_path:
        score += 50
        reasons.append("same path")
        return score, reasons

    if backend_path and frontend_path:
        if backend_path.endswith(frontend_path) or frontend_path.endswith(backend_path):
            score += 35
            reasons.append("path suffix/prefix match")

        if backend_segments and frontend_segments:
            shared_suffix = 0
            for left, right in zip(reversed(backend_segments), reversed(frontend_segments)):
                if left == right:
                    shared_suffix += 1
                else:
                    break
            if shared_suffix:
                suffix_score = min(30, shared_suffix * 12)
                score += suffix_score
                reasons.append(f"shared path suffix segments: {shared_suffix}")

            overlap = set(backend_segments) & set(frontend_segments)
            if overlap:
                overlap_score = min(15, len(overlap) * 4)
                score += overlap_score
                reasons.append(f"shared path tokens: {', '.join(sorted(overlap)[:5])}")

    return score, reasons


def score_params(backend_params: list[str], frontend_params: list[str]) -> tuple[int, list[str]]:
    score = 0
    reasons: list[str] = []
    backend_set = set(backend_params)
    frontend_set = set(frontend_params)
    shared = sorted(backend_set & frontend_set)
    if shared:
        overlap_score = min(25, len(shared) * 5)
        score += overlap_score
        reasons.append(f"shared params: {', '.join(shared[:8])}")

    shared_key = sorted((backend_set & frontend_set) & KEY_PARAM_BONUS)
    if shared_key:
        bonus = min(20, len(shared_key) * 8)
        score += bonus
        reasons.append(f"shared key params: {', '.join(shared_key[:8])}")

    return score, reasons


def score_domain_hints(backend_hints: list[str], frontend_hints: list[str]) -> tuple[int, list[str]]:
    shared = sorted(set(backend_hints) & set(frontend_hints))
    if not shared:
        return 0, []
    score = min(15, len(shared) * 3)
    return score, [f"shared module hints: {', '.join(shared[:8])}"]


def confidence_label(score: int) -> str:
    if score >= 80:
        return "high"
    if score >= 50:
        return "medium"
    return "low"


def match_calls_to_endpoints(
    frontend_calls: list[FrontendCall],
    backend_endpoints: list[BackendEndpoint],
    top_n: int,
    min_score: int,
) -> list[dict]:
    matches: list[dict] = []
    for call in frontend_calls:
        ranked: list[tuple[int, BackendEndpoint, list[str]]] = []
        for endpoint in backend_endpoints:
            score = 0
            reasons: list[str] = []

            if call.http_method == endpoint.http_method:
                score += 15
                reasons.append(f"same HTTP method: {call.http_method}")
            else:
                if call.http_method == "GET" and endpoint.http_method == "POST":
                    score -= 10
                else:
                    score -= 15

            path_score, path_reasons = score_path(endpoint.path, call.path)
            param_score, param_reasons = score_params(endpoint.params, call.param_keys)
            domain_score, domain_reasons = score_domain_hints(endpoint.domain_hints, call.domain_hints)

            score += path_score + param_score + domain_score
            reasons.extend(path_reasons)
            reasons.extend(param_reasons)
            reasons.extend(domain_reasons)

            if score >= min_score:
                ranked.append((score, endpoint, reasons))

        ranked.sort(key=lambda item: item[0], reverse=True)
        if not ranked:
            matches.append(
                {
                    "frontend": asdict(call),
                    "matches": [],
                }
            )
            continue

        matches.append(
            {
                "frontend": asdict(call),
                "matches": [
                    {
                        "score": score,
                        "confidence": confidence_label(score),
                        "backend": {
                            "path": endpoint.path,
                            "http_method": endpoint.http_method,
                            "java_file": endpoint.java_file,
                            "class_name": endpoint.class_name,
                            "method_name": endpoint.method_name,
                            "params": endpoint.params,
                        },
                        "reasons": reasons,
                    }
                    for score, endpoint, reasons in ranked[:top_n]
                ],
            }
        )
    return matches


def write_csv(output_path: Path, matched: list[dict]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "frontend_method",
                "frontend_path",
                "frontend_file",
                "frontend_line",
                "frontend_params",
                "backend_method",
                "backend_path",
                "backend_file",
                "backend_class",
                "backend_method_name",
                "backend_params",
                "score",
                "confidence",
                "match_reasons",
            ],
        )
        writer.writeheader()

        for item in matched:
            frontend = item["frontend"]
            matches = item["matches"] or [None]
            for match in matches:
                if not match:
                    writer.writerow(
                        {
                            "frontend_method": frontend["http_method"],
                            "frontend_path": frontend["path"],
                            "frontend_file": frontend["frontend_file"],
                            "frontend_line": frontend["line"],
                            "frontend_params": ",".join(frontend["param_keys"]),
                            "backend_method": "",
                            "backend_path": "",
                            "backend_file": "",
                            "backend_class": "",
                            "backend_method_name": "",
                            "backend_params": "",
                            "score": "",
                            "confidence": "unmatched",
                            "match_reasons": "",
                        }
                    )
                    continue

                backend = match["backend"]
                writer.writerow(
                    {
                        "frontend_method": frontend["http_method"],
                        "frontend_path": frontend["path"],
                        "frontend_file": frontend["frontend_file"],
                        "frontend_line": frontend["line"],
                        "frontend_params": ",".join(frontend["param_keys"]),
                        "backend_method": backend["http_method"],
                        "backend_path": backend["path"],
                        "backend_file": backend["java_file"],
                        "backend_class": backend["class_name"],
                        "backend_method_name": backend["method_name"],
                        "backend_params": ",".join(backend["params"]),
                        "score": match["score"],
                        "confidence": match["confidence"],
                        "match_reasons": " | ".join(match["reasons"]),
                    }
                )


def build_summary(matched: list[dict]) -> dict:
    total_calls = len(matched)
    matched_calls = 0
    high = 0
    medium = 0
    low = 0

    for item in matched:
        if not item["matches"]:
            continue
        matched_calls += 1
        confidence = item["matches"][0]["confidence"]
        if confidence == "high":
            high += 1
        elif confidence == "medium":
            medium += 1
        else:
            low += 1

    return {
        "total_frontend_calls": total_calls,
        "matched_frontend_calls": matched_calls,
        "unmatched_frontend_calls": total_calls - matched_calls,
        "top_match_confidence": {
            "high": high,
            "medium": medium,
            "low": low,
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Match frontend request calls to backend Java endpoints.")
    parser.add_argument("--backend-dir", required=True, help="Backend project root or src directory")
    parser.add_argument("--frontend-dir", required=True, help="Frontend project root or src directory")
    parser.add_argument(
        "--csv-output",
        default="dist/frontend_backend_matches.csv",
        help="CSV output path",
    )
    parser.add_argument(
        "--json-output",
        default="dist/frontend_backend_matches.json",
        help="JSON output path",
    )
    parser.add_argument("--top-n", type=int, default=3, help="Top N backend matches per frontend call")
    parser.add_argument("--min-score", type=int, default=35, help="Minimum score to keep a match")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    backend_root = Path(args.backend_dir).resolve()
    frontend_root = Path(args.frontend_dir).resolve()
    csv_output = Path(args.csv_output).resolve()
    json_output = Path(args.json_output).resolve()

    backend_endpoints = extract_backend_endpoints(backend_root)
    frontend_calls = extract_frontend_calls(frontend_root)
    matched = match_calls_to_endpoints(frontend_calls, backend_endpoints, args.top_n, args.min_score)
    summary = build_summary(matched)

    write_csv(csv_output, matched)
    json_output.parent.mkdir(parents=True, exist_ok=True)
    json_output.write_text(
        json.dumps(
            {
                "summary": summary,
                "backend_endpoint_count": len(backend_endpoints),
                "frontend_call_count": len(frontend_calls),
                "matches": matched,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print(f"backend endpoints: {len(backend_endpoints)}")
    print(f"frontend calls: {len(frontend_calls)}")
    print(f"matched frontend calls: {summary['matched_frontend_calls']}")
    print(f"csv: {csv_output}")
    print(f"json: {json_output}")


if __name__ == "__main__":
    main()
