#!/usr/bin/env python3
"""
Generate per-interface Markdown context files from frontend/backend match results.

Input:
- JSON produced by scripts/match_frontend_backend_apis.py

Output:
- One Markdown file per frontend call (or best match)
- Optional index.md summary
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path


DEFAULT_SNIPPET_LINES = 40


@dataclass
class MatchDoc:
    frontend_path: str
    frontend_method: str
    frontend_file: str
    frontend_line: int
    frontend_params: list[str]
    backend_path: str
    backend_method: str
    backend_file: str
    backend_class: str
    backend_method_name: str
    backend_params: list[str]
    score: int | None
    confidence: str
    reasons: list[str]


def read_text(path: Path) -> str:
    for encoding in ("utf-8", "utf-8-sig", "gbk", "latin1"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    return path.read_text(errors="ignore")


def slugify(value: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9]+", "_", value).strip("_")
    return value[:120] or "match"


def ensure_code_fence_language(path: str) -> str:
    suffix = Path(path).suffix.lower()
    return {
        ".vue": "vue",
        ".js": "js",
        ".ts": "ts",
        ".tsx": "tsx",
        ".jsx": "jsx",
        ".py": "python",
        ".java": "java",
    }.get(suffix, "")


def extract_frontend_snippet(file_path: Path, line_number: int, radius: int) -> str:
    text = read_text(file_path)
    lines = text.splitlines()
    if not lines:
        return ""
    start = max(1, line_number - radius)
    end = min(len(lines), line_number + radius)
    snippet_lines = []
    for idx in range(start, end + 1):
        marker = ">>" if idx == line_number else "  "
        snippet_lines.append(f"{marker} {idx:5d}: {lines[idx - 1]}")
    return "\n".join(snippet_lines)


def find_matching_brace(text: str, open_index: int) -> int:
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
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return index
    return -1


def extract_backend_method_snippet(file_path: Path, method_name: str) -> str:
    text = read_text(file_path)
    if not text.strip():
        return ""

    pattern = re.compile(rf"\b{re.escape(method_name)}\s*\(", re.MULTILINE)
    match = pattern.search(text)
    if not match:
        return ""

    line_start = text.rfind("\n", 0, match.start())
    search_start = 0 if line_start == -1 else line_start + 1

    open_brace = text.find("{", match.end())
    if open_brace == -1:
        end = min(len(text), match.end() + 1500)
        return text[search_start:end].strip()

    close_brace = find_matching_brace(text, open_brace)
    if close_brace == -1:
        close_brace = min(len(text), open_brace + 2500)

    snippet = text[search_start : close_brace + 1].strip()
    return snippet


def parse_match_docs(match_json: dict, top_only: bool) -> list[MatchDoc]:
    docs: list[MatchDoc] = []
    for item in match_json.get("matches", []):
        frontend = item.get("frontend", {})
        matches = item.get("matches", [])
        if top_only:
            matches = matches[:1]
        if not matches:
            docs.append(
                MatchDoc(
                    frontend_path=frontend.get("path", ""),
                    frontend_method=frontend.get("http_method", ""),
                    frontend_file=frontend.get("frontend_file", ""),
                    frontend_line=int(frontend.get("line", 1) or 1),
                    frontend_params=list(frontend.get("param_keys", []) or []),
                    backend_path="",
                    backend_method="",
                    backend_file="",
                    backend_class="",
                    backend_method_name="",
                    backend_params=[],
                    score=None,
                    confidence="unmatched",
                    reasons=[],
                )
            )
            continue

        for match in matches:
            backend = match.get("backend", {})
            docs.append(
                MatchDoc(
                    frontend_path=frontend.get("path", ""),
                    frontend_method=frontend.get("http_method", ""),
                    frontend_file=frontend.get("frontend_file", ""),
                    frontend_line=int(frontend.get("line", 1) or 1),
                    frontend_params=list(frontend.get("param_keys", []) or []),
                    backend_path=backend.get("path", ""),
                    backend_method=backend.get("http_method", ""),
                    backend_file=backend.get("java_file", ""),
                    backend_class=backend.get("class_name", ""),
                    backend_method_name=backend.get("method_name", ""),
                    backend_params=list(backend.get("params", []) or []),
                    score=match.get("score"),
                    confidence=match.get("confidence", "unknown"),
                    reasons=list(match.get("reasons", []) or []),
                )
            )
    return docs


def make_filename(doc: MatchDoc, index: int) -> str:
    if doc.backend_path:
        base = f"{index:04d}_{doc.backend_method.lower()}_{slugify(doc.backend_path)}"
    else:
        base = f"{index:04d}_{doc.frontend_method.lower()}_{slugify(doc.frontend_path)}_unmatched"
    return f"{base}.md"


def render_doc(doc: MatchDoc, frontend_radius: int) -> str:
    frontend_path = Path(doc.frontend_file)
    frontend_snippet = ""
    if frontend_path.exists():
        frontend_snippet = extract_frontend_snippet(frontend_path, doc.frontend_line, frontend_radius)

    backend_snippet = ""
    if doc.backend_file:
        backend_path = Path(doc.backend_file)
        if backend_path.exists():
            backend_snippet = extract_backend_method_snippet(backend_path, doc.backend_method_name)

    lines: list[str] = []
    title_path = doc.backend_path or doc.frontend_path or "unknown"
    title_method = doc.backend_method or doc.frontend_method or "UNKNOWN"
    lines.append(f"# API Match: {title_method} {title_path}")
    lines.append("")
    lines.append("## Match Summary")
    lines.append(f"- Confidence: `{doc.confidence}`")
    if doc.score is not None:
        lines.append(f"- Score: `{doc.score}`")
    lines.append(f"- Frontend method/path: `{doc.frontend_method} {doc.frontend_path}`")
    if doc.backend_path:
        lines.append(f"- Backend method/path: `{doc.backend_method} {doc.backend_path}`")
    else:
        lines.append("- Backend method/path: `unmatched`")
    lines.append("")

    lines.append("## Frontend")
    lines.append(f"- File: `{doc.frontend_file}`")
    lines.append(f"- Line: `{doc.frontend_line}`")
    lines.append(f"- Params: `{', '.join(doc.frontend_params) if doc.frontend_params else '-'}`")
    lines.append("")
    lines.append("### Frontend Code")
    lines.append(f"```{ensure_code_fence_language(doc.frontend_file)}")
    lines.append(frontend_snippet or "<snippet not found>")
    lines.append("```")
    lines.append("")

    lines.append("## Backend")
    if doc.backend_file:
        lines.append(f"- File: `{doc.backend_file}`")
        lines.append(f"- Class: `{doc.backend_class}`")
        lines.append(f"- Method: `{doc.backend_method_name}`")
        lines.append(f"- Params: `{', '.join(doc.backend_params) if doc.backend_params else '-'}`")
    else:
        lines.append("- File: `unmatched`")
    lines.append("")
    lines.append("### Backend Code")
    lines.append(f"```{ensure_code_fence_language(doc.backend_file)}")
    lines.append(backend_snippet or "<snippet not found>")
    lines.append("```")
    lines.append("")

    lines.append("## Match Reasons")
    if doc.reasons:
        for reason in doc.reasons:
            lines.append(f"- {reason}")
    else:
        lines.append("- No backend match found")
    lines.append("")

    lines.append("## Suggested AI Task")
    lines.append("请基于以上前后端代码，为这个接口生成一个适合智能体调用的 MCP tool。")
    lines.append("要求：")
    lines.append("- 参考现有 mcp_servers 的代码风格")
    lines.append("- 使用语义化 tool 名，不直接照搬后端方法名")
    lines.append("- 如果存在 filter/sVars，请拆成更业务化的参数")
    lines.append("- 输出 tools.py 代码片段、参数设计说明、待人工确认项")
    lines.append("")
    return "\n".join(lines)


def render_index(docs: list[MatchDoc], docs_dir: Path) -> str:
    lines = ["# MCP Context Index", ""]
    lines.append(f"- Total docs: `{len(docs)}`")
    high = sum(1 for doc in docs if doc.confidence == "high")
    medium = sum(1 for doc in docs if doc.confidence == "medium")
    low = sum(1 for doc in docs if doc.confidence == "low")
    unmatched = sum(1 for doc in docs if doc.confidence == "unmatched")
    lines.append(f"- High: `{high}`")
    lines.append(f"- Medium: `{medium}`")
    lines.append(f"- Low: `{low}`")
    lines.append(f"- Unmatched: `{unmatched}`")
    lines.append("")
    lines.append("| # | Confidence | Frontend | Backend | Doc |")
    lines.append("|---|---|---|---|---|")
    for index, doc in enumerate(docs, 1):
        filename = make_filename(doc, index)
        frontend = f"`{doc.frontend_method} {doc.frontend_path}`"
        backend = f"`{doc.backend_method} {doc.backend_path}`" if doc.backend_path else "`unmatched`"
        lines.append(
            f"| {index} | {doc.confidence} | {frontend} | {backend} | [{filename}]({filename}) |"
        )
    lines.append("")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate Markdown docs from frontend/backend match JSON.")
    parser.add_argument(
        "--match-json",
        default="dist/frontend_backend_matches_admin.json",
        help="Path to match JSON generated by scripts/match_frontend_backend_apis.py",
    )
    parser.add_argument(
        "--output-dir",
        default="docs/mcp_context",
        help="Output directory for Markdown docs",
    )
    parser.add_argument(
        "--frontend-radius",
        type=int,
        default=DEFAULT_SNIPPET_LINES,
        help="How many lines before/after the matched frontend line to include",
    )
    parser.add_argument(
        "--top-only",
        action="store_true",
        help="Generate docs only for the top backend match per frontend call",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Optional limit on number of docs to generate, 0 means no limit",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    match_json_path = Path(args.match_json).resolve()
    output_dir = Path(args.output_dir).resolve()

    data = json.loads(match_json_path.read_text(encoding="utf-8"))
    docs = parse_match_docs(data, top_only=args.top_only)
    if args.limit > 0:
        docs = docs[: args.limit]

    output_dir.mkdir(parents=True, exist_ok=True)
    for index, doc in enumerate(docs, 1):
        filename = make_filename(doc, index)
        content = render_doc(doc, args.frontend_radius)
        (output_dir / filename).write_text(content, encoding="utf-8")

    (output_dir / "index.md").write_text(render_index(docs, output_dir), encoding="utf-8")

    print(f"match json: {match_json_path}")
    print(f"output dir: {output_dir}")
    print(f"generated docs: {len(docs)}")


if __name__ == "__main__":
    main()
