"""XML and frontend extraction helpers for MCP agent docs."""

from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
import re
from typing import Any
from xml.etree import ElementTree as ET

from .config import (
    DATE_CANDIDATE_CTYPES,
    DATE_TYPES,
    EXACT_TYPES,
    EXCLUDED_GRID_NAMES,
    FILTER_CANDIDATE_CTYPES,
    TEXT_TYPES,
)
from .io import find_line_number, read_text
from .naming import snake_case

def parse_xml(path: Path) -> ET.Element | None:
    try:
        return ET.fromstring(read_text(path))
    except ET.ParseError:
        return None

def _extract_core_prefix(class_name: str) -> str:
    for suffix in ("ListAction", "SelectAction", "DetailAction", "Action"):
        if class_name.endswith(suffix):
            return class_name[: -len(suffix)]
    return class_name


def _detect_view_from_stem(class_name: str, stem: str) -> str:
    """Detect which view a form/XML stem belongs to.

    Returns a view identifier string, e.g. ``"subcontract"``, ``"dept"``,
    ``"home"``, ``"all"``, ``"default"``.
    """
    core = _extract_core_prefix(class_name)

    # Strip List/Select/Detail suffix from stem
    clean = stem
    for suffix in ("List", "Select", "Detail"):
        if clean.endswith(suffix):
            clean = clean[: -len(suffix)]
            break

    if clean.lower() == core.lower():
        return "default"

    if clean.lower().startswith(core.lower()):
        view = clean[len(core) :]
        if view:
            return view.lower()
        return "default"

    # Keyword-based fallback – ordered longest-first so "subcontract"
    # matches before "count" / "report" etc.
    stem_lower = stem.lower()
    keywords = [
        ("subcontract", "subcontract"),
        ("emcgen", "emcgen"),
        ("temporary", "temporary"),
        ("expense", "expense"),
        ("material", "material"),
        ("reliability", "reliability"),
        ("safety", "safety"),
        ("saler", "saler"),
        ("select", "select"),
        ("report", "report"),
        ("count", "count"),
        ("payment", "payment"),
        ("home", "home"),
        ("dept", "dept"),
        ("emc", "emc"),
        ("gen", "gen"),
        ("dm", "dm"),
        ("rf", "rf"),
        ("sfy", "sfy"),
        ("qm", "qm"),
        ("sd", "sd"),
        ("op", "op"),
        ("as", "all"),
        ("all", "all"),
        ("biz", "biz"),
        ("my", "mine"),
        ("mine", "mine"),
        ("week", "my_week"),
    ]
    # Pick the longest match appearing closest to the end of the stem
    # (view part usually follows the class prefix)
    matches = [(k, v, stem_lower.rfind(k)) for k, v in keywords if k in stem_lower]
    if matches:
        matches.sort(key=lambda x: (-len(x[0]), -x[2]))
        return matches[0][1]

    return "default"


def parse_frontend_svars(
    class_name: str,
    frontend_root: Path | None,
    xml_items: list[dict[str, Any]] | None = None,
) -> list[dict[str, str]]:
    if frontend_root is None or not frontend_root.exists():
        return []

    view_root = frontend_root / "src" / "views"
    target_prefix = class_name.replace("Action", "")
    if not view_root.exists():
        return []

    # Build stem -> (view, methods, xml_files) mapping from XML bindings
    stem_info: dict[str, dict[str, Any]] = {}
    for item in xml_items or []:
        xml_file = item.get("xml_file") or ""
        if not xml_file:
            continue
        xml_stem = re.sub(r"V\d+$", "", Path(xml_file).stem)
        if not xml_stem:
            continue
        if xml_stem not in stem_info:
            stem_info[xml_stem] = {
                "view": _detect_view_from_stem(class_name, xml_stem),
                "methods": [],
                "xml_names": [],
            }
        method = item.get("query_method") or ""
        xml_name = Path(xml_file).name
        if method and method not in stem_info[xml_stem]["methods"]:
            stem_info[xml_stem]["methods"].append(method)
        if xml_name and xml_name not in stem_info[xml_stem]["xml_names"]:
            stem_info[xml_stem]["xml_names"].append(xml_name)

    # Ensure the base form stem (class prefix + "List") is always searched,
    # even when no XML binding is found for it.
    base_stems = {
        target_prefix,
        *{re.sub(r"V\d+$", "", Path(item["xml_file"]).stem) for item in xml_items or [] if item.get("xml_file")},
    }

    svars: list[dict[str, str]] = []
    seen: set[tuple[str, str, str]] = set()

    for stem in sorted(base_stems):
        info = stem_info.get(stem)
        view = info["view"] if info else _detect_view_from_stem(class_name, stem)
        methods = info["methods"] if info else []
        xml_names = info["xml_names"] if info else []

        for js_path in sorted(view_root.rglob(f"{stem}Form.js")):
            text = read_text(js_path)
            for match in re.finditer(r"form\.addSVar\s*\(\s*\{(?P<body>[\s\S]*?)\}\s*\)", text):
                body = match.group("body")
                line_number = text.count("\n", 0, match.start()) + 1
                for key, value in re.findall(r"['\"]?(\w+)['\"]?\s*:\s*['\"]?([^,'\"\r\n}]+)['\"]?", body):
                    item = {
                        "view": view,
                        "methods": ", ".join(methods) if methods else "-",
                        "xml_names": ", ".join(xml_names) if xml_names else "-",
                        "key": key,
                        "value": value.strip(),
                        "source_file": str(js_path),
                        "line": str(line_number),
                        "node_path": "form.addSVar({...})",
                    }
                    dedup_key = (item["view"], item["key"], item["value"])
                    if dedup_key not in seen:
                        seen.add(dedup_key)
                        svars.append(item)

    return sorted(svars, key=lambda item: (item["view"], item["key"], item["value"]))

def parse_data_type_views(xml_path: Path, query_method: str) -> list[dict[str, Any]]:
    root = parse_xml(xml_path)
    if root is None:
        return []
    resources = parse_resource_labels(root)

    date_types = None
    for elem in root.findall(".//date_types"):
        if (elem.attrib.get("name") or "").strip() == "dataType":
            date_types = elem
            break
    if date_types is None:
        return []

    default_type = (date_types.attrib.get("defaultType") or "").strip()
    date_types_line = find_line_number(xml_path, '<date_types name="dataType"') or find_line_number(
        xml_path, "name=\"dataType\""
    )
    values: list[dict[str, str]] = []
    for date_type in date_types.findall("./date_type"):
        name = (date_type.attrib.get("name") or "").strip()
        if not name:
            continue
        view_name = (date_type.attrib.get("viewName") or name).strip()
        line_number = find_line_number(xml_path, f'<date_type name="{name}"')
        values.append(
            {
                "value": name,
                "view_name": view_name,
                "label": preferred_label(name, resources),
                "node_path": f'.//date_types[@name="dataType"]/date_type[@name="{name}"]',
                "line": str(line_number or ""),
            }
        )

    return [
        {
            "query_method": query_method,
            "xml_file": str(xml_path),
            "xml_name": xml_path.name,
            "node_path": './/date_types[@name="dataType"]',
            "line": str(date_types_line or ""),
            "default": default_type,
            "values": values,
        }
    ]

def merge_data_type_views(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    for item in items:
        key = (
            item["query_method"],
            item["xml_name"],
            item.get("default", ""),
        )
        if key not in grouped:
            grouped[key] = dict(item)
            grouped[key]["values"] = list(item.get("values", []))
            continue

        existing_values = {value["value"] for value in grouped[key].get("values", [])}
        for value in item.get("values", []):
            if value["value"] not in existing_values:
                grouped[key]["values"].append(value)
                existing_values.add(value["value"])

    return sorted(grouped.values(), key=lambda item: (item["query_method"], item["xml_name"]))

def parse_resource_labels(root: ET.Element) -> dict[str, dict[str, str]]:
    resources: dict[str, dict[str, str]] = defaultdict(dict)
    for rs in root.findall(".//resource/rs"):
        name = (rs.attrib.get("name") or "").strip()
        if not name:
            continue
        for lang in rs.findall("./lang"):
            locale = (lang.attrib.get("locale") or "").strip()
            value = (lang.attrib.get("value") or "").strip()
            if locale:
                resources[name][locale] = value
    return dict(resources)

def preferred_label(name: str, resources: dict[str, dict[str, str]]) -> str:
    localized = resources.get(name, {})
    for locale in ("zh_CN", "zh_TW", "en"):
        value = (localized.get(locale) or "").strip()
        if value:
            return value
    return name

def normalize_range_label(param_name: str, label: str) -> str:
    """Keep generated start/end date labels aligned with their parameter suffix."""
    if not label:
        return label

    if param_name.endswith("_start"):
        if "结束" in label:
            return label.replace("结束", "开始")
        if "截止" in label:
            return label.replace("截止", "开始")
        if "开始" not in label and "起始" not in label:
            return f"{label}开始"

    if param_name.endswith("_end"):
        if "开始" in label:
            return label.replace("开始", "结束")
        if "起始" in label:
            return label.replace("起始", "结束")
        if "结束" not in label and "截止" not in label:
            return f"{label}结束"

    return label

def infer_operator(component: ET.Element) -> str:
    operation = (component.attrib.get("operation") or "").strip()
    if operation:
        return operation
    ctype = (component.attrib.get("ctype") or "").strip().lower()
    if ctype in {value.lower() for value in TEXT_TYPES}:
        return "like"
    if ctype in {value.lower() for value in DATE_TYPES}:
        return "="
    if ctype in {value.lower() for value in EXACT_TYPES}:
        return "="
    return "="

def infer_value_type(ftype: str, ref_id: str, ctype: str) -> str:
    lower = (ftype or "").strip().lower()
    ctype_lower = (ctype or "").strip().lower()
    if ref_id:
        if lower in {"int", "integer", "long"}:
            return "integer"
        return "string"
    if lower in {"int", "integer", "long"}:
        return "integer"
    if lower in {"double", "float", "bigdecimal", "number"}:
        return "number"
    if lower in {"boolean", "bool"}:
        return "boolean"
    if lower in {"date", "datetime", "timestamp"} or ctype_lower in {value.lower() for value in DATE_TYPES}:
        return "string"
    return "string"

def infer_match_text(operator: str, ctype: str) -> str:
    ctype_lower = (ctype or "").strip().lower()
    if operator == ">=":
        return "起始时间"
    if operator == "<=":
        return "结束时间"
    if operator == "like" or ctype_lower in {value.lower() for value in TEXT_TYPES}:
        return "模糊匹配"
    return "精确匹配"

def extract_field_tail(find_field: str) -> str:
    field = (find_field or "").strip()
    if not field:
        return ""
    field = field.split("(")[0].strip()
    if "." in field:
        field = field.split(".")[-1]
    return snake_case(field)

def infer_param_name(name: str, find_field: str, operator: str) -> str:
    if name.startswith("q_"):
        base = name[2:]
        if operator == ">=":
            source = extract_field_tail(find_field)
            return f"{source or snake_case(base)}_start"
        if operator == "<=":
            source = extract_field_tail(find_field)
            return f"{source or snake_case(base)}_end"
        return snake_case(base)
    if name.lower().startswith("query_from"):
        source = extract_field_tail(find_field)
        return f"{source or snake_case(name[11:])}_start"
    if name.lower().startswith("query_to"):
        source = extract_field_tail(find_field)
        return f"{source or snake_case(name[8:])}_end"
    if name.lower().startswith("query"):
        base = name[5:]
        base = base[0].lower() + base[1:] if base else name
        return snake_case(base)
    return snake_case(name)

def parse_query_fields(xml_path: Path) -> list[dict[str, Any]]:
    root = parse_xml(xml_path)
    if root is None:
        return []
    resources = parse_resource_labels(root)
    q_condition = root.find(".//q_condition")
    if q_condition is None:
        return []

    fields: list[dict[str, Any]] = []
    for component in q_condition.findall("./component"):
        name = (component.attrib.get("name") or "").strip()
        if not name:
            continue
        find_field = (component.attrib.get("find_field") or component.attrib.get("field") or "").strip()
        ctype = (component.attrib.get("ctype") or "").strip()
        ftype = (component.attrib.get("ftype") or "").strip()
        ref_id = (component.attrib.get("ref_id") or "").strip()
        operator = infer_operator(component)
        label = preferred_label(name, resources)

        fields.append(
            {
                "xml_file": str(xml_path),
                "name": name,
                "label": label,
                "find_field": find_field,
                "ctype": ctype,
                "ftype": ftype,
                "ref_id": ref_id,
                "operator": operator,
                "param_name": infer_param_name(name, find_field, operator),
                "type": infer_value_type(ftype, ref_id, ctype),
                "match_text": infer_match_text(operator, ctype),
            }
        )
    return fields

def parse_return_fields(xml_path: Path) -> list[dict[str, Any]]:
    root = parse_xml(xml_path)
    if root is None:
        return []
    resources = parse_resource_labels(root)
    columns: list[dict[str, Any]] = []

    display_order = 0
    for component_set in root.findall(".//component_set"):
        grid_name = (component_set.attrib.get("name") or "").strip()
        query_name = (component_set.attrib.get("queryName") or "").strip()
        if grid_name.lower() in EXCLUDED_GRID_NAMES:
            continue
        for component in component_set.findall("./component"):
            field = (component.attrib.get("field") or "").strip()
            name = (component.attrib.get("name") or "").strip()
            if not field or not name:
                continue
            ctype = (component.attrib.get("ctype") or "").strip()
            ftype = (component.attrib.get("ftype") or "").strip()
            ref_id = (component.attrib.get("ref_id") or "").strip()
            label = preferred_label(name, resources)
            display_order += 1
            columns.append(
                {
                    "xml_file": str(xml_path),
                    "display_order": display_order,
                    "grid_name": grid_name,
                    "query_name": query_name,
                    "name": name,
                    "label": label,
                    "field": field,
                    "ctype": ctype,
                    "ftype": ftype,
                    "ref_id": ref_id,
                    "type": infer_value_type(ftype, ref_id, ctype),
                }
            )
    return columns

def build_enum_index(backend_root: Path) -> dict[str, dict[str, Any]]:
    enum_index: dict[str, dict[str, Any]] = {}
    for xml_path in backend_root.rglob("*.xml"):
        if any(part in {"target", ".git", ".idea", ".vscode", "build", "out"} for part in xml_path.parts):
            continue
        root = parse_xml(xml_path)
        if root is None:
            continue
        for enum_elem in root.findall(".//enum"):
            enum_id = (enum_elem.attrib.get("id") or "").strip()
            if not enum_id:
                continue
            enum_type = (enum_elem.attrib.get("type") or "").strip()
            resource_labels = parse_resource_labels(enum_elem)
            items: list[dict[str, str]] = []
            for item in enum_elem.findall("./item"):
                item_name = (item.attrib.get("name") or "").strip()
                value = (item.attrib.get("value") or "").strip()
                label = preferred_label(item_name, resource_labels)
                if item_name or value:
                    items.append({"name": item_name, "value": value, "label": label})
            enum_index[enum_id] = {
                "id": enum_id,
                "type": enum_type,
                "xml_file": str(xml_path),
                "items": items,
            }
    return enum_index

def merge_query_fields(items: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[str]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in items:
        grouped[item["param_name"]].append(item)

    merged: list[dict[str, Any]] = []
    notes: list[str] = []
    for param_name, variants in sorted(grouped.items(), key=lambda pair: pair[0]):
        preferred = max(
            variants,
            key=lambda item: (
                bool(item["find_field"]),
                bool(item["ref_id"]),
                len(item["xml_file"]),
            ),
        )
        # If any variant has a text-like ctype, force fuzzy match regardless
        # of which variant was selected as "preferred".
        text_ctypes = {t.lower() for t in TEXT_TYPES}
        variant_ctypes = {item.get("ctype", "").lower() for item in variants}
        if variant_ctypes & text_ctypes:
            preferred["operator"] = "like"
            preferred["match_text"] = "模糊匹配"
        find_fields = sorted({item["find_field"] for item in variants if item["find_field"]})
        names = sorted({item["name"] for item in variants})
        labels = [item["label"] for item in variants if item["label"]]
        label = Counter(labels).most_common(1)[0][0] if labels else preferred["name"]
        label = normalize_range_label(param_name, label)
        xml_files = sorted({Path(item["xml_file"]).name for item in variants})
        merged_item = dict(preferred)
        merged_item["label"] = label
        merged_item["xml_files"] = xml_files
        merged_item["source_names"] = names
        merged_item["all_find_fields"] = find_fields
        merged.append(merged_item)

        if len(find_fields) > 1:
            notes.append(
                f"`{param_name}` 在不同 XML 中映射字段不一致："
                + ", ".join(f"`{field}`" for field in find_fields)
            )

    # Second pass: coalesce groups that share the same backend field but
    # were split by different frontend field names (e.g. q_customerName /
    # q_customerNameCn / customerShortName all map to ac.CUSTOMER_NAME_CN).
    find_field_groups: dict[str, list[int]] = defaultdict(list)
    for i, item in enumerate(merged):
        ff = (item.get("find_field") or "").strip().lower()
        if ff:
            find_field_groups[ff].append(i)

    skip_indices: set[int] = set()
    for ff, indices in find_field_groups.items():
        if len(indices) <= 1:
            continue
        group = [merged[i] for i in indices]

        # Do NOT coalesce _start / _end pairs — they are intentional
        # date-range endpoints sharing the same backend field.
        operators = {item.get("operator", "") for item in group}
        if ">=" in operators and "<=" in operators:
            continue
        best = max(
            group,
            key=lambda item: (
                len(item["xml_files"]),
                bool(item.get("ref_id")),
                len(item.get("name", "")),
            ),
        )
        all_xml = sorted({f for item in group for f in item["xml_files"]})
        all_names = sorted({n for item in group for n in item["source_names"]})
        all_labels = [item["label"] for item in group if item["label"]]
        best_label = Counter(all_labels).most_common(1)[0][0] if all_labels else best["label"]
        best_label = normalize_range_label(best["param_name"], best_label)
        all_ff = sorted({ff for item in group for ff in item["all_find_fields"]})

        coalesced = dict(best)
        coalesced["label"] = best_label
        coalesced["xml_files"] = all_xml
        coalesced["source_names"] = all_names
        coalesced["all_find_fields"] = all_ff

        prev_by_name = {item["param_name"] for item in group}
        if len(prev_by_name) > 1:
            primary = best["param_name"]
            others = sorted(prev_by_name - {primary})
            notes.append(
                f"`{primary}` 合并自同后端字段 `{ff}` 的多个前端字段: "
                + ", ".join(f"`{n}`" for n in sorted({it["name"] for it in group}))
            )

        # Replace best item in-place, mark others for removal
        best_idx = indices[0]
        merged[best_idx] = coalesced
        for i in indices[1:]:
            skip_indices.add(i)

    merged = [item for i, item in enumerate(merged) if i not in skip_indices]
    merged.sort(key=lambda item: item["param_name"])
    return merged, notes

def merge_return_fields(items: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[str]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in items:
        grouped[item["field"]].append(item)

    merged: list[dict[str, Any]] = []
    notes: list[str] = []
    for field, variants in grouped.items():
        labels = [item["label"] for item in variants if item["label"]]
        label = Counter(labels).most_common(1)[0][0] if labels else variants[0]["name"]
        names = sorted({item["name"] for item in variants})
        refs = sorted({item["ref_id"] for item in variants if item["ref_id"]})
        grids = sorted({item["grid_name"] for item in variants if item["grid_name"]})
        xml_files = sorted({Path(item["xml_file"]).name for item in variants})
        preferred = max(variants, key=lambda item: (bool(item["ref_id"]), -item.get("display_order", 0)))
        merged_item = dict(preferred)
        merged_item["label"] = label
        merged_item["names"] = names
        merged_item["grid_names"] = grids
        merged_item["xml_files"] = xml_files
        merged_item["ref_ids"] = refs
        merged_item["display_order"] = min(item.get("display_order", 999999) for item in variants)
        merged.append(merged_item)

        if len(names) > 1:
            notes.append(
                f"返回字段 `{field}` 在不同 XML 中使用了多个列名："
                + ", ".join(f"`{name}`" for name in names)
            )
    return sorted(merged, key=lambda item: item.get("display_order", 999999)), notes

def build_filter_candidates(
    query_fields: list[dict[str, Any]],
    return_fields: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    existing_params = {field["param_name"] for field in query_fields}
    candidates: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()

    for field in return_fields:
        ctype = (field.get("ctype") or "").strip()
        ctype_lower = ctype.lower()
        if ctype not in FILTER_CANDIDATE_CTYPES and ctype_lower not in {item.lower() for item in FILTER_CANDIDATE_CTYPES}:
            continue

        base_label = field["label"] or field["field"]
        backend_field = field["field"]
        ref_ids = field.get("ref_ids") or []
        field_type = field.get("type") or "string"
        source_names = ", ".join(field.get("names") or [field.get("name", "")])
        is_date = ctype_lower in {item.lower() for item in DATE_CANDIDATE_CTYPES}

        if is_date:
            for suffix, label_suffix, match_text in (
                ("_start", "开始", "起始时间"),
                ("_end", "结束", "结束时间"),
            ):
                param_name = f"{snake_case(backend_field)}{suffix}"
                if param_name in existing_params or (param_name, backend_field) in seen:
                    continue
                seen.add((param_name, backend_field))
                candidates.append(
                    {
                        "param_name": param_name,
                        "label": f"{base_label}{label_suffix}",
                        "type": "string",
                        "match_text": match_text,
                        "backend_field": backend_field,
                        "source_names": source_names,
                        "ref_ids": ref_ids,
                    }
                )
            continue

        param_name = snake_case(backend_field)
        if param_name in existing_params or (param_name, backend_field) in seen:
            continue
        seen.add((param_name, backend_field))

        match_text = "精确匹配" if ref_ids or field_type in {"integer", "number", "boolean"} else "模糊匹配"
        candidates.append(
            {
                "param_name": param_name,
                "label": base_label,
                "type": field_type,
                "match_text": match_text,
                "backend_field": backend_field,
                "source_names": source_names,
                "ref_ids": ref_ids,
            }
        )

    return sorted(candidates, key=lambda item: item["param_name"])

def enum_value_text(enum_meta: dict[str, Any]) -> str:
    parts = []
    for item in enum_meta.get("items", []):
        value = item.get("value", "")
        label = item.get("label") or item.get("name") or value
        parts.append(f"{value}={label}")
    return ", ".join(parts)

def build_enum_output_fields(
    query_fields: list[dict[str, Any]],
    return_fields: list[dict[str, Any]],
    enum_index: dict[str, dict[str, Any]],
) -> dict[str, dict[str, str]]:
    enum_fields: dict[str, dict[str, str]] = {}

    for field in return_fields:
        for ref_id in field.get("ref_ids") or []:
            enum_meta = enum_index.get(ref_id)
            if not enum_meta:
                continue
            values = {
                item.get("value", ""): item.get("label") or item.get("name") or item.get("value", "")
                for item in enum_meta.get("items", [])
                if item.get("value", "") != ""
            }
            if values:
                enum_fields.setdefault(snake_case(field["field"]), values)

    return dict(sorted(enum_fields.items(), key=lambda pair: pair[0]))
