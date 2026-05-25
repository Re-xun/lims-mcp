from __future__ import annotations

import argparse
import ast
import json
import keyword
import re
from pathlib import Path
from typing import Any

HTTP_METHODS = ["get", "post", "put", "patch", "delete"]

TYPE_MAP = {
    "integer": "int",
    "number": "float",
    "boolean": "bool",
    "array": "list",
    "object": "dict",
    "string": "str",
}

JAVA_TYPE_MAP = {
    "String": "string",
    "Long": "integer",
    "Integer": "integer",
    "Short": "integer",
    "Double": "number",
    "Float": "number",
    "BigDecimal": "number",
    "Boolean": "boolean",
    "LocalDate": "string",
    "LocalDateTime": "string",
    "Date": "string",
}

MAPPING_METHOD_MAP = {
    "GetMapping": "GET",
    "PostMapping": "POST",
    "PutMapping": "PUT",
    "DeleteMapping": "DELETE",
    "PatchMapping": "PATCH",
}


def to_snake(name: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_]", "_", name)
    snake = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", cleaned)
    snake = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", snake)
    snake = re.sub(r"_+", "_", snake).strip("_").lower()
    if not snake:
        snake = "field"
    if keyword.iskeyword(snake):
        snake += "_"
    return snake


def to_tool_name(operation: dict[str, Any], method: str, path: str) -> str:
    op_id = operation.get("operationId")
    if op_id:
        return to_snake(op_id)
    parts = [method.lower()] + [to_snake(p) for p in path.strip("/").split("/") if p]
    return "_".join(parts)


def py_type_from_schema(schema: dict[str, Any] | None) -> str:
    if not schema:
        return "str"
    schema_type = schema.get("type", "string")
    return TYPE_MAP.get(schema_type, "str")


def collect_parameters(operation: dict[str, Any]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for p in operation.get("parameters", []):
        name = p["name"]
        schema = p.get("schema", {})
        result.append(
            {
                "name": name,
                "py_name": to_snake(name),
                "in": p.get("in", "query"),
                "required": bool(p.get("required", False)),
                "description": p.get("description", ""),
                "schema": schema,
                "type": py_type_from_schema(schema),
            }
        )

    request_body = operation.get("requestBody") or {}
    content = request_body.get("content", {})
    body_schema = (content.get("application/json") or {}).get("schema")
    if body_schema and body_schema.get("type") == "object":
        required_set = set(body_schema.get("required", []))
        for name, schema in body_schema.get("properties", {}).items():
            result.append(
                {
                    "name": name,
                    "py_name": to_snake(name),
                    "in": "body",
                    "required": name in required_set,
                    "description": schema.get("description", ""),
                    "schema": schema,
                    "type": py_type_from_schema(schema),
                }
            )

    return result


def _extract_first_path(annotation_args: str | None) -> str:
    if not annotation_args:
        return ""

    explicit = re.search(r"(?:value|path)\s*=\s*\{?\s*\"([^\"]+)\"", annotation_args)
    if explicit:
        return explicit.group(1)

    direct = re.search(r"\"([^\"]+)\"", annotation_args)
    if direct:
        return direct.group(1)

    return ""


def _extract_request_method(annotation_args: str | None) -> str:
    if not annotation_args:
        return "GET"

    m = re.search(r"RequestMethod\.([A-Z]+)", annotation_args)
    if m:
        return m.group(1)
    return "GET"


def _join_path(base: str, sub: str) -> str:
    b = (base or "").strip()
    s = (sub or "").strip()
    if not b and not s:
        return "/"
    if not b:
        b = ""
    if not s:
        s = ""
    path = f"/{b.strip('/')}/{s.strip('/')}"
    path = re.sub(r"/+", "/", path)
    return path if path else "/"


def _java_schema_from_type(java_type: str) -> dict[str, Any]:
    raw = java_type.strip()
    raw = raw.replace("final ", "")
    raw = re.sub(r"@\w+", "", raw).strip()
    raw = raw.split("<", 1)[0].split("[", 1)[0].strip()
    type_name = raw.split(".")[-1]
    schema_type = JAVA_TYPE_MAP.get(type_name, "string")
    return {"type": schema_type}


def _parse_java_parameters(signature_params: str) -> list[dict[str, Any]]:
    params: list[dict[str, Any]] = []
    if not signature_params.strip():
        return params

    for chunk in [c.strip() for c in signature_params.split(",") if c.strip()]:
        loc = "query"
        required = False

        if "@PathVariable" in chunk:
            loc = "path"
            required = True
        elif "@RequestBody" in chunk:
            loc = "body"
            required = True
        elif "@RequestParam" in chunk:
            loc = "query"
            required = "required = true" in chunk or "required=true" in chunk

        clean = re.sub(r"@\w+(\([^)]*\))?", "", chunk).strip()
        parts = clean.split()
        if len(parts) < 2:
            continue

        var_name = parts[-1]
        var_type = " ".join(parts[:-1])
        schema = _java_schema_from_type(var_type)

        params.append(
            {
                "name": var_name,
                "py_name": to_snake(var_name),
                "in": loc,
                "required": required,
                "description": "",
                "schema": schema,
                "type": py_type_from_schema(schema),
            }
        )

    return params


def collect_operations_from_java(java_root: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []

    class_base_pattern = re.compile(
        r"@RequestMapping\s*\((?P<args>[^)]*)\)\s*(?:@\w+(?:\([^)]*\))?\s*)*(?:public\s+)?class\s+(?P<classname>\w+)",
        re.S,
    )

    method_pattern = re.compile(
        r"@(?P<anno>GetMapping|PostMapping|PutMapping|DeleteMapping|PatchMapping|RequestMapping)\s*(?:\((?P<args>[^)]*)\))?\s*"
        r"(?:@\w+(?:\([^)]*\))?\s*)*"
        r"(?:public|protected|private)\s+[\w<>,\[\]\.?\s]+\s+(?P<method>\w+)\s*\((?P<params>.*?)\)\s*(?:throws[^\{]+)?\{",

        re.S,
    )

    for java_file in java_root.rglob("*.java"):
        text = java_file.read_text(encoding="utf-8", errors="ignore")

        class_name = java_file.stem
        base_path = ""
        class_match = class_base_pattern.search(text)
        if class_match:
            class_name = class_match.group("classname")
            base_path = _extract_first_path(class_match.group("args"))

        domain = to_snake(class_name.replace("Controller", "") or class_name) + "_mcp"

        for m in method_pattern.finditer(text):
            anno = m.group("anno")
            anno_args = m.group("args")
            method_name = m.group("method")
            signature_params = m.group("params")

            if anno == "RequestMapping":
                http_method = _extract_request_method(anno_args)
            else:
                http_method = MAPPING_METHOD_MAP.get(anno, "GET")

            sub_path = _extract_first_path(anno_args)
            full_path = _join_path(base_path, sub_path)
            parameters = _parse_java_parameters(signature_params)

            operation = {
                "operationId": method_name,
                "summary": method_name,
                "description": f"from {java_file.name}",
                "parameters": [
                    {
                        "name": p["name"],
                        "in": p["in"],
                        "required": p["required"],
                        "schema": p["schema"],
                    }
                    for p in parameters
                    if p["in"] != "body"
                ],
            }

            if any(p["in"] == "body" for p in parameters):
                body_required = [p["name"] for p in parameters if p["in"] == "body" and p["required"]]
                operation["requestBody"] = {
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {p["name"]: p["schema"] for p in parameters if p["in"] == "body"},
                                "required": body_required,
                            }
                        }
                    }
                }

            normalized_params = collect_parameters(operation)
            records.append(
                {
                    "domain": domain,
                    "tool_name": to_tool_name(operation, http_method.lower(), full_path),
                    "method": http_method,
                    "path": full_path,
                    "summary": operation["summary"],
                    "description": operation["description"],
                    "operation_id": operation["operationId"],
                    "parameters": normalized_params,
                    "required_count": sum(1 for p in normalized_params if p["required"]),
                    "parameter_count": len(normalized_params),
                    "source_file": str(java_file),
                }
            )

    return records


def collect_operations_from_spec(spec: dict[str, Any]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for path, path_item in spec.get("paths", {}).items():
        if not isinstance(path_item, dict):
            continue

        common_params = path_item.get("parameters", [])

        for method in HTTP_METHODS:
            operation = path_item.get(method)
            if not operation:
                continue

            full_operation = dict(operation)
            if common_params:
                full_operation["parameters"] = common_params + operation.get("parameters", [])

            tool_name = to_tool_name(full_operation, method, path)
            tags = full_operation.get("tags") or ["misc_mcp"]
            domain = to_snake(tags[0])
            params = collect_parameters(full_operation)
            required_count = sum(1 for p in params if p["required"])

            records.append(
                {
                    "domain": domain,
                    "tool_name": tool_name,
                    "method": method.upper(),
                    "path": path,
                    "summary": full_operation.get("summary") or tool_name,
                    "description": full_operation.get("description") or full_operation.get("summary") or tool_name,
                    "operation_id": full_operation.get("operationId"),
                    "parameters": params,
                    "required_count": required_count,
                    "parameter_count": len(params),
                }
            )
    return records


def _extract_path_vars(path: str) -> list[str]:
    vars_ = re.findall(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}", path or "")
    return [v for v in vars_ if not v.isupper()]


def _infer_domain_from_path_or_url(source_file: Path, path: str) -> str:
    normalized_file = str(source_file).replace("\\", "/").lower()
    m_file = re.search(r"/mcp_servers/([^/]+)/", normalized_file)
    if m_file:
        domain = to_snake(m_file.group(1))
        return domain if domain.endswith("_mcp") else f"{domain}_mcp"

    if path:
        m_action = re.search(r"/([A-Za-z0-9_]*Action)(?:/|$)", path)
        if m_action:
            return f"{to_snake(m_action.group(1))}_mcp"

    stem = source_file.stem
    if stem:
        base = to_snake(stem.replace("Controller", ""))
        return f"{base}_mcp"

    return "misc_mcp"


def _extract_object_keys(text: str) -> set[str]:
    return set(re.findall(r"([A-Za-z_][A-Za-z0-9_]*)\s*:", text or ""))


def _extract_keys_from_python_call(node: ast.Call, assigned_dict_keys: dict[str, set[str]]) -> tuple[set[str], set[str], bool]:
    query_keys: set[str] = set()
    body_keys: set[str] = set()
    smartview_sql = False

    for kw in node.keywords:
        if kw.arg not in {"params", "json"}:
            continue

        target = query_keys if kw.arg == "params" else body_keys
        value = kw.value

        if isinstance(value, ast.Dict):
            for k in value.keys:
                if isinstance(k, ast.Constant) and isinstance(k.value, str):
                    target.add(k.value)
                    if k.value == "filters":
                        smartview_sql = True
        elif isinstance(value, ast.Name):
            target.update(assigned_dict_keys.get(value.id, set()))
        elif isinstance(value, ast.Call):
            func = value.func
            if isinstance(func, ast.Attribute) and func.attr == "dumps" and value.args:
                target.add("sVars")
                if isinstance(value.args[0], ast.Dict):
                    for k in value.args[0].keys:
                        if isinstance(k, ast.Constant) and isinstance(k.value, str):
                            target.add(k.value)
                elif isinstance(value.args[0], ast.Name):
                    target.update(assigned_dict_keys.get(value.args[0].id, set()))
            elif isinstance(func, ast.Name) and func.id == "dict":
                for arg in value.keywords:
                    if arg.arg:
                        target.add(arg.arg)

    return query_keys, body_keys, smartview_sql


def _extract_httpx_call_name(node: ast.Call) -> str:
    fn = node.func
    if isinstance(fn, ast.Attribute):
        return fn.attr
    if isinstance(fn, ast.Name):
        return fn.id
    return ""


def _is_httpx_like_call(node: ast.Call) -> bool:
    fn = node.func
    if not isinstance(fn, ast.Attribute):
        return False

    owner = fn.value
    if isinstance(owner, ast.Name) and owner.id in {"client", "httpx"}:
        return True

    if isinstance(owner, ast.Attribute) and isinstance(owner.value, ast.Name) and owner.value.id == "httpx":
        return True

    return False


def _expr_to_string_template(expr: ast.AST, assigned_str_values: dict[str, str]) -> str:
    if isinstance(expr, ast.Constant) and isinstance(expr.value, str):
        return expr.value
    if isinstance(expr, ast.Name):
        return assigned_str_values.get(expr.id, "")
    if isinstance(expr, ast.JoinedStr):
        parts: list[str] = []
        for v in expr.values:
            if isinstance(v, ast.Constant) and isinstance(v.value, str):
                parts.append(v.value)
            elif isinstance(v, ast.FormattedValue):
                inner = v.value
                if isinstance(inner, ast.Name):
                    parts.append("{" + inner.id + "}")
                else:
                    parts.append("{var}")
        return "".join(parts)
    if isinstance(expr, ast.BinOp) and isinstance(expr.op, ast.Add):
        left = _expr_to_string_template(expr.left, assigned_str_values)
        right = _expr_to_string_template(expr.right, assigned_str_values)
        if left or right:
            return left + right
    return ""


def _extract_httpx_method_path(node: ast.Call, assigned_str_values: dict[str, str]) -> tuple[str, str]:
    call_name = _extract_httpx_call_name(node)
    method = "GET"
    path = ""

    if call_name in {"get", "post", "put", "patch", "delete"}:
        method = call_name.upper()
        if node.args:
            path = _expr_to_string_template(node.args[0], assigned_str_values)
    elif call_name in {"request", "stream"}:
        if len(node.args) >= 1:
            m = _expr_to_string_template(node.args[0], assigned_str_values)
            if m:
                method = m.upper()
        if len(node.args) >= 2:
            path = _expr_to_string_template(node.args[1], assigned_str_values)

    for kw in node.keywords:
        if kw.arg == "method":
            m = _expr_to_string_template(kw.value, assigned_str_values)
            if m:
                method = m.upper()
        if kw.arg == "url":
            p = _expr_to_string_template(kw.value, assigned_str_values)
            if p:
                path = p

    return method, path


def _normalize_scanned_path(path: str) -> str:
    p = (path or "").strip()
    p = p.replace("{JAVA_API_BASE}", "")
    p = re.sub(r"^\{[A-Z0-9_]+\}", "", p)
    if p.startswith("http://") or p.startswith("https://"):
        m = re.match(r"https?://[^/]+(/.*)$", p)
        if m:
            p = m.group(1)
    if p and not p.startswith("/") and not p.startswith("modal://"):
        p = "/" + p
    return p or "/unknown"


def _operation_from_scanned_call(scanned: dict[str, Any]) -> dict[str, Any]:
    path = _normalize_scanned_path(scanned.get("path") or "/unknown")
    method = (scanned.get("method") or "GET").upper()
    query_keys = sorted(scanned.get("query_keys") or [])
    body_keys = sorted(scanned.get("body_keys") or [])
    smartview_sql = bool(scanned.get("smartview_sql"))
    source_file = scanned.get("source_file") or "unknown"

    param_specs: list[dict[str, Any]] = []
    path_vars = set(_extract_path_vars(path))
    for p in sorted(path_vars):
        param_specs.append({"name": p, "in": "path", "required": True, "schema": {"type": "string"}})

    for q in query_keys:
        if q in path_vars:
            continue
        desc = ""
        if q == "filters" and smartview_sql:
            desc = "SmartView SQL WHERE clause"
        param_specs.append({"name": q, "in": "query", "required": False, "schema": {"type": "string"}, "description": desc})

    operation: dict[str, Any] = {
        "operationId": f"{method.lower()}_{to_snake(path)}",
        "summary": scanned.get("summary") or f"{method} {path}",
        "description": f"from {Path(source_file).name}",
        "parameters": param_specs,
    }

    if body_keys:
        operation["requestBody"] = {
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {k: {"type": "string"} for k in body_keys},
                        "required": [],
                    }
                }
            }
        }

    normalized_params = collect_parameters(operation)

    record = {
        "domain": scanned.get("domain") or "misc_mcp",
        "tool_name": to_tool_name(operation, method.lower(), path),
        "method": method,
        "path": path,
        "summary": operation["summary"],
        "description": operation["description"],
        "operation_id": operation["operationId"],
        "parameters": normalized_params,
        "required_count": sum(1 for p in normalized_params if p["required"]),
        "parameter_count": len(normalized_params),
        "source_file": source_file,
    }
    if smartview_sql:
        record["filter_mode"] = "smartview_sql"
    return record


def _scan_python_requests(file_path: Path) -> list[dict[str, Any]]:
    text = file_path.read_text(encoding="utf-8", errors="ignore")
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return []

    assigned_dict_keys: dict[str, set[str]] = {}
    assigned_str_values: dict[str, str] = {}
    results: list[dict[str, Any]] = []

    class Visitor(ast.NodeVisitor):
        def visit_Assign(self, node: ast.Assign) -> Any:
            if isinstance(node.value, ast.Dict):
                keys = {k.value for k in node.value.keys if isinstance(k, ast.Constant) and isinstance(k.value, str)}
                for t in node.targets:
                    if isinstance(t, ast.Name):
                        assigned_dict_keys[t.id] = set(keys)

            if isinstance(node.value, ast.Call):
                func = node.value.func
                if isinstance(func, ast.Attribute) and func.attr == "dumps" and node.value.args and isinstance(node.value.args[0], ast.Name):
                    dumped_from = node.value.args[0].id
                    for t in node.targets:
                        if isinstance(t, ast.Name):
                            assigned_dict_keys[t.id] = set(assigned_dict_keys.get(dumped_from, set())) | {"sVars"}

            str_value = _expr_to_string_template(node.value, assigned_str_values)
            if str_value:
                for t in node.targets:
                    if isinstance(t, ast.Name):
                        assigned_str_values[t.id] = str_value

            for t in node.targets:
                if isinstance(t, ast.Subscript) and isinstance(t.value, ast.Name):
                    dict_name = t.value.id
                    sub = t.slice
                    key_name = None
                    if isinstance(sub, ast.Constant) and isinstance(sub.value, str):
                        key_name = sub.value
                    elif isinstance(sub, ast.Index) and isinstance(sub.value, ast.Constant) and isinstance(sub.value.value, str):
                        key_name = sub.value.value
                    if key_name:
                        assigned_dict_keys.setdefault(dict_name, set()).add(key_name)
                        if key_name == "sVars" and isinstance(node.value, ast.Name):
                            assigned_dict_keys[dict_name].update(assigned_dict_keys.get(node.value.id, set()))

            self.generic_visit(node)

        def visit_Call(self, node: ast.Call) -> Any:
            name = _extract_httpx_call_name(node)
            if _is_httpx_like_call(node) and name in {"get", "post", "put", "patch", "delete", "request", "stream"}:
                method, path = _extract_httpx_method_path(node, assigned_str_values)
                if path:
                    query_keys, body_keys, smartview_sql = _extract_keys_from_python_call(node, assigned_dict_keys)
                    results.append(
                        {
                            "source_file": str(file_path),
                            "method": method,
                            "path": path,
                            "query_keys": query_keys,
                            "body_keys": body_keys,
                            "smartview_sql": smartview_sql or ("filters" in query_keys),
                            "domain": _infer_domain_from_path_or_url(file_path, path),
                            "operation_id": to_snake(f"{method}_{path}"),
                        }
                    )
            self.generic_visit(node)

    Visitor().visit(tree)
    return results


def _parse_js_object_keys(block: str) -> tuple[set[str], bool]:
    keys = _extract_object_keys(block)
    smartview_sql = bool(re.search(r"filters\s*:\s*([`\"']).*?\1", block, re.S))
    return keys, smartview_sql


def _scan_js_ts_requests(file_path: Path) -> list[dict[str, Any]]:
    text = file_path.read_text(encoding="utf-8", errors="ignore")
    results: list[dict[str, Any]] = []

    for m in re.finditer(r"getByParams\s*\(\s*['\"]([^'\"]+)['\"]\s*,\s*\{([\s\S]*?)\}\s*,", text):
        path = m.group(1)
        keys, smartview_sql = _parse_js_object_keys(m.group(2))
        results.append(
            {
                "source_file": str(file_path),
                "method": "GET",
                "path": path,
                "query_keys": keys,
                "body_keys": set(),
                "smartview_sql": smartview_sql or ("filters" in keys),
                "domain": _infer_domain_from_path_or_url(file_path, path),
                "operation_id": to_snake(f"get_{path}"),
            }
        )

    for m in re.finditer(r"showModal\s*\(\s*\{([\s\S]*?)\}\s*\)", text):
        modal_block = m.group(1)
        acvar = re.search(r"ACvar\s*:\s*\{([\s\S]*?)\}", modal_block)
        if not acvar:
            continue
        keys, smartview_sql = _parse_js_object_keys(acvar.group(1))
        form_key = ""
        fm = re.search(r"formKey\s*:\s*['\"]([^'\"]+)['\"]", modal_block)
        if fm:
            form_key = fm.group(1)
        path = f"modal://{form_key}" if form_key else "/modal/select"
        results.append(
            {
                "source_file": str(file_path),
                "method": "GET",
                "path": path,
                "query_keys": keys,
                "body_keys": set(),
                "smartview_sql": smartview_sql or ("filters" in keys),
                "domain": _infer_domain_from_path_or_url(file_path, path),
                "operation_id": to_snake(f"modal_{form_key or 'select'}"),
            }
        )

    for m in re.finditer(r"addSVar\s*\(\s*\{([\s\S]*?)\}\s*\)", text):
        keys, _ = _parse_js_object_keys(m.group(1))
        results.append(
            {
                "source_file": str(file_path),
                "method": "GET",
                "path": "/smartview/svar",
                "query_keys": keys | {"sVars"},
                "body_keys": set(),
                "smartview_sql": False,
                "domain": _infer_domain_from_path_or_url(file_path, "/smartview/svar"),
                "operation_id": to_snake("smartview_add_svar"),
            }
        )

    for m in re.finditer(r"axios\.(get|post|put|patch|delete)\s*\(\s*['\"]([^'\"]+)['\"]\s*,\s*([\s\S]*?)\)", text):
        method = m.group(1).upper()
        path = m.group(2)
        block = m.group(3)
        keys, smartview_sql = _parse_js_object_keys(block)
        results.append(
            {
                "source_file": str(file_path),
                "method": method,
                "path": path,
                "query_keys": keys if "params" in block else set(),
                "body_keys": keys if "data" in block or method in {"POST", "PUT", "PATCH"} else set(),
                "smartview_sql": smartview_sql,
                "domain": _infer_domain_from_path_or_url(file_path, path),
                "operation_id": to_snake(f"{method}_{path}"),
            }
        )

    for m in re.finditer(r"fetch\s*\(\s*['\"]([^'\"]+)['\"]\s*,\s*\{([\s\S]*?)\}\s*\)", text):
        path = m.group(1)
        cfg = m.group(2)
        method = "GET"
        mm = re.search(r"method\s*:\s*['\"]([A-Za-z]+)['\"]", cfg)
        if mm:
            method = mm.group(1).upper()
        body_keys: set[str] = set()
        jm = re.search(r"JSON\.stringify\s*\(\s*\{([\s\S]*?)\}\s*\)", cfg)
        if jm:
            body_keys = _extract_object_keys(jm.group(1))
        results.append(
            {
                "source_file": str(file_path),
                "method": method,
                "path": path,
                "query_keys": set(),
                "body_keys": body_keys,
                "smartview_sql": False,
                "domain": _infer_domain_from_path_or_url(file_path, path),
                "operation_id": to_snake(f"{method}_{path}"),
            }
        )

    return results


def _should_skip_scan_file(file_path: Path) -> bool:
    normalized = str(file_path).replace("\\", "/").lower()
    if "/__pycache__/" in normalized:
        return True
    if normalized.endswith(".generated.py"):
        return True
    if "/mcp_server/" in normalized:
        return True
    return False


def collect_operations_from_frontend(frontend_root: Path) -> list[dict[str, Any]]:
    scanned_calls: list[dict[str, Any]] = []

    for file_path in frontend_root.rglob("*.py"):
        if _should_skip_scan_file(file_path):
            continue
        scanned_calls.extend(_scan_python_requests(file_path))
    for pattern in ("*.js", "*.ts", "*.tsx"):
        for file_path in frontend_root.rglob(pattern):
            if _should_skip_scan_file(file_path):
                continue
            scanned_calls.extend(_scan_js_ts_requests(file_path))

    dedup: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    for call in scanned_calls:
        key = (call.get("domain", "misc_mcp"), call.get("method", "GET"), call.get("path", "/unknown"), call.get("operation_id", ""))
        if key not in dedup:
            dedup[key] = {
                **call,
                "query_keys": set(call.get("query_keys") or []),
                "body_keys": set(call.get("body_keys") or []),
            }
            continue
        dedup[key]["query_keys"].update(call.get("query_keys") or [])
        dedup[key]["body_keys"].update(call.get("body_keys") or [])
        dedup[key]["smartview_sql"] = bool(dedup[key].get("smartview_sql") or call.get("smartview_sql"))

    return [_operation_from_scanned_call(v) for v in dedup.values()]


def build_inventory(operations: list[dict[str, Any]]) -> dict[str, Any]:
    by_domain: dict[str, list[dict[str, Any]]] = {}
    for op in operations:
        by_domain.setdefault(op["domain"], []).append(op)

    return {
        "total_operations": len(operations),
        "domains": {k: len(v) for k, v in sorted(by_domain.items())},
        "operations": operations,
    }


def _schema_for_param(param: dict[str, Any]) -> dict[str, Any]:
    schema = dict(param.get("schema") or {})
    if not schema:
        schema = {"type": "string"}
    if param.get("description"):
        schema["description"] = param["description"]
    return schema


def _signature_line(params: list[dict[str, Any]]) -> str:
    required = [p for p in params if p["required"]]
    optional = [p for p in params if not p["required"]]

    chunks = ["token: str"]
    for p in required:
        chunks.append(f"{p['py_name']}: {p['type']}")
    for p in optional:
        chunks.append(f"{p['py_name']}: {p['type']} = None")
    return ",\n    ".join(chunks)


def _build_url_expr(path: str, params: list[dict[str, Any]]) -> str:
    path_params = [p for p in params if p["in"] == "path"]
    if not path_params:
        return f'f"{{JAVA_API_BASE}}{path}"'

    replacements = path
    for p in path_params:
        replacements = replacements.replace("{" + p["name"] + "}", "{" + p["py_name"] + "}")
    return f'f"{{JAVA_API_BASE}}{replacements}"'


def _build_query_params_dict_lines(params: list[dict[str, Any]]) -> list[str]:
    query_params = [p for p in params if p["in"] == "query"]
    lines = ["    params = {}"]
    for p in query_params:
        lines.append(f"    if {p['py_name']} is not None:")
        lines.append(f"        params['{p['name']}'] = {p['py_name']}")
    return lines


def _build_json_payload_lines(params: list[dict[str, Any]]) -> list[str]:
    body_params = [p for p in params if p["in"] == "body"]
    if not body_params:
        return ["    json_payload = None"]

    lines = ["    json_payload = {}"]
    for p in body_params:
        lines.append(f"    if {p['py_name']} is not None:")
        lines.append(f"        json_payload['{p['name']}'] = {p['py_name']}")
    return lines


def generate_tools_file(domain: str, operations: list[dict[str, Any]], output_path: Path) -> None:
    lines: list[str] = []
    lines.extend(
        [
            f'"""Auto-generated tools for {domain} MCP.',
            "",
            "DO NOT EDIT MANUALLY. Run `python -m mcp_servers.generator.generate` to regenerate.",
            '"""',
            "import os",
            "import httpx",
            "",
            'JAVA_API_BASE = os.environ.get("JAVA_API_BASE", "http://localhost:8080")',
            "",
        ]
    )

    for op in operations:
        params = op["parameters"]
        signature = _signature_line(params)
        summary = op["summary"].replace("\n", " ").strip()
        url_expr = _build_url_expr(op["path"], params)
        query_lines = _build_query_params_dict_lines(params)
        body_lines = _build_json_payload_lines(params)

        lines.extend(
            [
                f"async def {op['tool_name']}(\n    {signature},\n) -> dict:",
                f'    """{summary}"""',
                f"    url = {url_expr}",
                *query_lines,
                *body_lines,
                "    async with httpx.AsyncClient(timeout=30.0) as client:",
                "        response = await client.request(",
                f"            \"{op['method']}\",",
                "            url,",
                "            headers={\"x-access-token\": token},",
                "            params=params if params else None,",
                "            json=json_payload if json_payload else None,",
                "        )",
                "        response.raise_for_status()",
                "        return response.json()",
                "",
            ]
        )

    lines.append("TOOL_HANDLERS = {")
    for op in operations:
        lines.append(f'    "{op["tool_name"]}": {op["tool_name"]},')
    lines.append("}")
    lines.append("")

    lines.append("TOOL_SCHEMAS = [")
    for op in operations:
        lines.append("    {")
        lines.append(f'        "name": "{op["tool_name"]}",')
        lines.append(f'        "description": {json.dumps(op["description"], ensure_ascii=False)},')
        lines.append('        "inputSchema": {')
        lines.append('            "type": "object",')
        lines.append('            "properties": {')
        required_props: list[str] = []
        for p in op["parameters"]:
            prop_schema = _schema_for_param(p)
            lines.append(f'                "{p["name"]}": {json.dumps(prop_schema, ensure_ascii=False)},')
            if p["required"]:
                required_props.append(p["name"])
        lines.append("            },")
        if required_props:
            lines.append(f'            "required": {json.dumps(required_props, ensure_ascii=False)},')
        lines.append("        },")
        lines.append("    },")
    lines.append("]")

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Batch inventory OpenAPI/Java/Frontend and generate MCP tools.py")
    source_group = parser.add_mutually_exclusive_group(required=False)
    source_group.add_argument("--spec", help="OpenAPI/Swagger JSON path")
    source_group.add_argument("--java-root", help="Java project root path for source scan")
    source_group.add_argument("--frontend-root", help="Frontend/source root path for request scan")
    parser.add_argument(
        "--inventory-out",
        default="openapi_specs/endpoint_catalog.json",
        help="Normalized endpoint inventory JSON output path",
    )
    parser.add_argument(
        "--domain",
        help="Generate only this domain/tag (e.g. user_mcp, customer_mcp). If omitted, only inventory is generated.",
    )
    parser.add_argument(
        "--output",
        help="Output tools.py path. Default: mcp_servers/<domain>/tools.generated.py",
    )

    args = parser.parse_args()

    if not args.spec and not args.java_root and not args.frontend_root:
        args.spec = "openapi_specs/lims-api.json"

    if args.java_root:
        java_root = Path(args.java_root)
        if not java_root.exists() or not java_root.is_dir():
            raise FileNotFoundError(f"Java root directory not found: {java_root}")
        operations = collect_operations_from_java(java_root)
    elif args.frontend_root:
        frontend_root = Path(args.frontend_root)
        if not frontend_root.exists() or not frontend_root.is_dir():
            raise FileNotFoundError(f"Frontend root directory not found: {frontend_root}")
        operations = collect_operations_from_frontend(frontend_root)
    else:
        spec_path = Path(args.spec)
        if not spec_path.exists():
            raise FileNotFoundError(f"Spec file not found: {spec_path}")
        spec = json.loads(spec_path.read_text(encoding="utf-8"))
        operations = collect_operations_from_spec(spec)

    inventory = build_inventory(operations)

    inventory_path = Path(args.inventory_out)
    inventory_path.parent.mkdir(parents=True, exist_ok=True)
    inventory_path.write_text(json.dumps(inventory, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[OK] inventory generated: {inventory_path} | total_operations={inventory['total_operations']}")
    print(f"[OK] domain counts: {inventory['domains']}")

    if not args.domain:
        return

    domain_ops = [op for op in inventory["operations"] if op["domain"] == args.domain]
    if not domain_ops:
        raise ValueError(f"No operations found for domain={args.domain}")

    output = Path(args.output) if args.output else Path(f"mcp_servers/{args.domain}/tools.generated.py")
    output.parent.mkdir(parents=True, exist_ok=True)
    generate_tools_file(args.domain, domain_ops, output)
    print(f"[OK] tools generated: {output} | tools={len(domain_ops)}")


if __name__ == "__main__":
    main()
