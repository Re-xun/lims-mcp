"""MCP Server Generator - OpenAPI 3.0 to MCP Server code generator."""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path
from collections import defaultdict
from typing import Optional

from jinja2 import Environment, FileSystemLoader

TEMPLATES_DIR = Path(__file__).parent / "templates"
MCP_SERVERS_DIR = Path(__file__).parent.parent
SPECS_DIR = Path(__file__).parent.parent.parent / "openapi_specs"

TYPE_MAP = {
    "string": "str",
    "integer": "int",
    "number": "float",
    "boolean": "bool",
    "array": "list",
    "object": "dict",
}


def camel_to_snake(name: str) -> str:
    """getUserById -> get_user_by_id"""
    s = re.sub(r"(?<=[a-z])(?=[A-Z])", "_", name)
    return s.lower()


def resolve_schema_name(ref: str) -> str:
    """#/components/schemas/User -> User"""
    return ref.split("/")[-1]


def _describe_response(operation: dict) -> str:
    """Extract a concise response format hint from OpenAPI operation."""
    responses = operation.get("responses", {})
    ok_resp = responses.get("200") or responses.get("201")
    if not ok_resp:
        return ""
    content = ok_resp.get("content", {}).get("application/json", {})
    schema = content.get("schema", {})
    if not schema:
        return ""

    ref = schema.get("$ref", "")
    if ref:
        return f"返回: 单个{resolve_schema_name(ref)}对象"

    schema_type = schema.get("type", "")
    if schema_type == "array":
        items = schema.get("items", {})
        item_ref = items.get("$ref", "")
        if item_ref:
            return f"返回: {resolve_schema_name(item_ref)}对象列表"
        return "返回: 列表"

    props = schema.get("properties", {})
    if "items" in props and "total" in props:
        # Wrapped page response: {total, items: [...]}
        items_schema = props.get("items", {})
        if "$ref" in items_schema.get("items", {}):
            item_name = resolve_schema_name(items_schema["items"]["$ref"])
            return f"返回: 分页结果，包含 total(总数) 和 items({item_name}列表)"
        return "返回: 分页结果，包含 total(总数) 和 items(数据列表)"

    if props:
        return f"返回: 对象，包含 {', '.join(list(props.keys())[:5])} 等字段"

    return ""


def build_tool(operation: dict, path_str: str, method: str) -> dict:
    """Convert one OpenAPI operation into a tool definition for Jinja2."""
    op_id = operation.get("operationId", f"{method}_{path_str.replace('/', '_').strip('_')}")
    function_name = camel_to_snake(op_id)
    summary = (operation.get("summary") or operation.get("description", ""))
    summary = summary.replace('"', "'").replace("\n", " ").strip()
    # Append response format hint to help LLM present results correctly
    resp_hint = _describe_response(operation)
    description = f"{summary}。{resp_hint}" if resp_hint else summary

    params = []
    for p in operation.get("parameters", []):
        schema = p.get("schema", {})
        param_type = schema.get("type", "string")
        params.append({
            "name": camel_to_snake(p["name"]),
            "original_name": p["name"],
            "type_hint": TYPE_MAP.get(param_type, "str"),
            "required": p.get("required", False),
            "description": p.get("description", "").replace('"', "'"),
        })

    # Build JSON schema for the tool's inputSchema
    properties = {}
    required_list = []
    for p in operation.get("parameters", []):
        schema = p.get("schema", {})
        prop = {"type": schema.get("type", "string")}
        if "description" in p:
            prop["description"] = p["description"]
        properties[p["name"]] = prop
        if p.get("required"):
            required_list.append(p["name"])

    input_schema = {
        "type": "object",
        "properties": properties,
    }
    if required_list:
        input_schema["required"] = required_list

    # Build f-string path (replace {param} with {param_snake})
    path_fstring = re.sub(r"\{(\w+)\}", lambda m: "{" + camel_to_snake(m.group(1)) + "}", path_str)

    return {
        "function_name": function_name,
        "description": description,
        "http_method": method.lower(),
        "path_fstring": path_fstring,
        "params": params,
        "input_schema_json": json.dumps(input_schema, indent=8),
    }


def build_schemas(components: dict) -> list[dict]:
    """Extract Pydantic-worthy schemas from OpenAPI components."""
    result = []
    if not components or "schemas" not in components:
        return result

    for name, schema in components["schemas"].items():
        fields = []
        for prop_name, prop_schema in schema.get("properties", {}).items():
            ref = prop_schema.get("$ref")
            if ref:
                type_hint = resolve_schema_name(ref)
            else:
                type_hint = TYPE_MAP.get(prop_schema.get("type", "string"), "str")
                if prop_schema.get("type") == "array":
                    items = prop_schema.get("items", {})
                    items_ref = items.get("$ref", "")
                    if items_ref:
                        type_hint = f"list[{resolve_schema_name(items_ref)}]"
                    else:
                        type_hint = "list"

            fields.append({
                "name": prop_name,
                "type_hint": f"Optional[{type_hint}]" if prop_name not in schema.get("required", []) else type_hint,
                "default": "None" if prop_name not in schema.get("required", []) else None,
                "description": prop_schema.get("description", "").replace('"', "'"),
            })

        result.append({
            "class_name": name,
            "description": schema.get("description", "").replace('"', "'"),
            "fields": fields,
        })
    return result


def parse_openapi(spec_path: Path) -> dict:
    """Parse an OpenAPI 3.0 JSON file and return structured data grouped by tag."""
    with open(spec_path, encoding="utf-8") as f:
        spec = json.load(f)

    paths = spec.get("paths", {})
    tags = defaultdict(list)

    for path_str, path_item in paths.items():
        for method in ["get", "post", "put", "delete", "patch"]:
            operation = path_item.get(method)
            if not operation:
                continue

            # POC: only generate for GET (query-only)
            if method != "get":
                continue

            tool = build_tool(operation, path_str, method)
            # Use first tag as domain group, fallback to "general"
            domain = operation.get("tags", ["general"])[0] if operation.get("tags") else "general"
            tags[domain].append(tool)

    components = spec.get("components", {})
    schemas = build_schemas(components)

    return {
        "domains": dict(tags),
        "schemas": schemas,
        "info": spec.get("info", {}),
    }


def generate(openapi_path: str | None = None) -> list[str]:
    """Generate MCP server packages from OpenAPI spec(s).

    Args:
        openapi_path: Path to a single OpenAPI JSON or a directory of them.
                      Defaults to openapi_specs/ directory.

    Returns:
        List of generated MCP server directory paths.
    """
    env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)), trim_blocks=True, lstrip_blocks=True)

    if openapi_path:
        spec_path = Path(openapi_path)
        if spec_path.is_dir():
            spec_files = list(spec_path.glob("*.json"))
        else:
            spec_files = [spec_path]
    else:
        spec_files = list(SPECS_DIR.glob("*.json")) if SPECS_DIR.exists() else []

    if not spec_files:
        print("No OpenAPI spec files found. Place JSON files in openapi_specs/ directory.")
        return []

    generated = []

    for spec_file in spec_files:
        print(f"Processing: {spec_file.name}")
        data = parse_openapi(spec_file)

        base_name = spec_file.stem.replace("-api", "").replace("_api", "")
        for domain, tools in data["domains"].items():
            # Sanitize domain name: use ASCII, fall back to spec filename prefix
            safe_domain = camel_to_snake(domain)
            if any(ord(c) > 127 for c in safe_domain):
                # Non-ASCII tag: use index-based naming
                idx = list(data["domains"].keys()).index(domain) + 1
                safe_domain = f"{base_name}_domain{idx}"
            domain_name = safe_domain
            output_dir = MCP_SERVERS_DIR / domain_name

            # Clean and recreate output directory
            if output_dir.exists():
                shutil.rmtree(output_dir)
            output_dir.mkdir(parents=True)

            # Render and write __init__.py
            (output_dir / "__init__.py").write_text("", encoding="utf-8")

            # Render schemas.py
            schemas_code = env.get_template("schemas.py.j2").render(
                domain_name=domain_name,
                schemas=data["schemas"],
            )
            (output_dir / "schemas.py").write_text(schemas_code, encoding="utf-8")

            # Render tools.py
            tools_code = env.get_template("tools.py.j2").render(
                domain_name=domain_name,
                tools=tools,
            )
            (output_dir / "tools.py").write_text(tools_code, encoding="utf-8")

            # Render server.py
            server_code = env.get_template("server.py.j2").render(
                domain_name=domain_name,
            )
            (output_dir / "server.py").write_text(server_code, encoding="utf-8")

            print(f"  Generated {domain_name}/ ({len(tools)} tools)")
            generated.append(str(output_dir))

    print(f"Done. Generated {len(generated)} MCP server(s).")
    return generated


if __name__ == "__main__":
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else None
    generate(path)
