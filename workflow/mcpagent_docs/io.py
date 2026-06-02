"""File and structured input helpers for MCP agent docs."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

def read_text(path: Path) -> str:
    for encoding in ("utf-8", "utf-8-sig", "gb18030", "gbk", "big5", "latin1"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    return path.read_text(errors="ignore")

def load_candidates(csv_path: Path) -> list[dict[str, str]]:
    with csv_path.open("r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))

def load_inventory(json_path: Path) -> dict[str, Any]:
    return json.loads(read_text(json_path))

def find_line_number(path: Path, pattern: str, start_line: int = 1) -> int | None:
    for line_number, line in enumerate(read_text(path).splitlines(), start=1):
        if line_number < start_line:
            continue
        if pattern in line:
            return line_number
    return None
