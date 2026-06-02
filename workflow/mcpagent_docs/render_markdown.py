"""Markdown rendering for MCP agent docs."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .inventory import infer_business_summary
from .naming import build_scope_hints, extract_package_tail, snake_case, to_pretty_tool_name
from .xml_extractors import (
    build_enum_output_fields,
    build_filter_candidates,
    enum_value_text,
    merge_data_type_views,
    merge_query_fields,
    merge_return_fields,
    parse_data_type_views,
    parse_query_fields,
    parse_return_fields,
)

def build_query_description(field: dict[str, Any], enum_index: dict[str, dict[str, Any]]) -> str:
    label = field["label"] or field["name"]
    mapping = field["find_field"] or field["name"]
    description = f"{label}，{field['match_text']} ({field['name']} → {mapping})"
    ref_id = field.get("ref_id") or ""
    if ref_id and ref_id in enum_index:
        enum_text = enum_value_text(enum_index[ref_id])
        if enum_text:
            description = f"{label} ({field['name']} → {mapping}): {enum_text}"
    return description

def build_return_enum_text(field: dict[str, Any], enum_index: dict[str, dict[str, Any]]) -> str:
    ref_ids = field.get("ref_ids") or []
    parts = []
    for ref_id in ref_ids:
        enum_meta = enum_index.get(ref_id, {})
        text = enum_value_text(enum_meta)
        if text:
            parts.append(f"{ref_id}: {text}")
    return "；".join(parts)

def render_field_labels(return_fields: list[dict[str, Any]]) -> str:
    lines = ["FIELD_LABELS = {"]
    for field in return_fields:
        key = snake_case(field["field"])
        title = field["label"] or field["name"]
        lines.append(f'    "{field["field"]}": {{')
        lines.append(f'        "key": "{key}",')
        lines.append(f'        "title": "{title}",')
        lines.append("    },")
    lines.append("}")
    return "\n".join(lines)

def python_literal(value: str) -> str:
    if re.fullmatch(r"-?\d+", value or ""):
        return value
    return json.dumps(value, ensure_ascii=False)

def render_enum_fields_code(enum_output_fields: dict[str, dict[str, str]]) -> str:
    lines = ["ENUM_FIELDS = {"]
    for key, values in enum_output_fields.items():
        lines.append(f'    "{key}": {{')
        for value, label in values.items():
            lines.append(f"        {python_literal(value)}: {json.dumps(label, ensure_ascii=False)},")
        lines.append("    },")
    lines.append("}")
    lines.append("")
    lines.append("def _enum_text(key: str, value: Any) -> str | None:")
    lines.append("    enum_map = ENUM_FIELDS.get(key)")
    lines.append("    if not enum_map:")
    lines.append("        return None")
    lines.append("    if value in enum_map:")
    lines.append("        return enum_map[value]")
    lines.append("    if value is None:")
    lines.append("        return None")
    lines.append("    try:")
    lines.append("        return enum_map.get(int(value))")
    lines.append("    except (TypeError, ValueError):")
    lines.append("        return enum_map.get(str(value))")
    lines.append("")
    lines.append("def _normalize_row(row: dict[str, Any]) -> dict[str, Any]:")
    lines.append("    normalized: dict[str, Any] = {}")
    lines.append("    for field, meta in FIELD_LABELS.items():")
    lines.append("        key = meta[\"key\"]")
    lines.append("        value = row.get(field)")
    lines.append("        normalized[key] = value")
    lines.append("        text = _enum_text(key, value)")
    lines.append("        if text is not None:")
    lines.append("            normalized[f\"{key}_text\"] = text")
    lines.append("    return normalized")
    return "\n".join(lines)

def render_schema_snippet(query_fields: list[dict[str, Any]], enum_index: dict[str, dict[str, Any]]) -> str:
    lines = ["{", '    "type": "object",', '    "properties": {']
    for index, field in enumerate(query_fields):
        comma = "," if index < len(query_fields) - 1 else ""
        description = build_query_description(field, enum_index).replace('"', '\\"')
        lines.append(f'        "{field["param_name"]}": {{')
        lines.append(f'            "type": "{field["type"]}",')
        lines.append(f'            "description": "{description}"')
        lines.append(f"        }}{comma}")
    lines.append("    }")
    lines.append("}")
    return "\n".join(lines)

def build_endpoint_rows(java_items: list[dict[str, Any]], xml_items: list[dict[str, Any]]) -> list[dict[str, str]]:
    rows: dict[tuple[str, str], dict[str, str]] = {}
    for item in java_items:
        method_name = item.get("method_name", "")
        endpoint_path = item.get("endpoint_path", "")
        if not method_name or not endpoint_path:
            continue
        rows[(method_name, endpoint_path)] = {
            "http": ",".join(item.get("http_methods", [])) or "GET,POST",
            "path": endpoint_path,
            "method": method_name,
            "params": ", ".join(item.get("params", [])) or "-",
        }

    for item in xml_items:
        method_name = item.get("query_method", "")
        endpoint_path = item.get("inferred_endpoint_path", "")
        if not method_name or not endpoint_path:
            continue
        rows.setdefault(
            (method_name, endpoint_path),
            {
                "http": "GET,POST",
                "path": endpoint_path,
                "method": method_name,
                "params": "start, limit, filter, sVars（根据 XML 绑定推断）",
            },
        )
    return sorted(rows.values(), key=lambda row: (row["method"].lower(), row["path"].lower()))

def render_doc(
    candidate: dict[str, str],
    java_items: list[dict[str, Any]],
    xml_items: list[dict[str, Any]],
    enum_index: dict[str, dict[str, Any]],
    frontend_svars: list[dict[str, str]],
) -> str:
    class_name = candidate["class_name"]
    java_file = candidate["java_file"]
    methods = sorted({item["method_name"] for item in java_items} | {item["query_method"] for item in xml_items})
    package_tail = extract_package_tail(java_file)
    xml_files = sorted({item["xml_file"] for item in xml_items})

    # Identify the primary XML (the default list view).
    # Its stem (without version suffix) matches class_name without "Action".
    primary_stem = class_name.replace("Action", "")
    primary_xmls = [f for f in xml_files if re.sub(r"V\d+$", "", Path(f).stem) == primary_stem]
    primary_xml = primary_xmls[0] if primary_xmls else (xml_files[0] if xml_files else "")
    other_xmls = [f for f in xml_files if f != primary_xml]

    all_query_fields: list[dict[str, Any]] = []
    all_return_fields: list[dict[str, Any]] = []
    if primary_xml:
        all_query_fields.extend(parse_query_fields(Path(primary_xml)))
        all_return_fields.extend(parse_return_fields(Path(primary_xml)))
    all_data_type_views: list[dict[str, Any]] = []
    for item in xml_items:
        xml_file = item.get("xml_file")
        query_method = item.get("query_method") or ""
        if xml_file:
            all_data_type_views.extend(parse_data_type_views(Path(xml_file), query_method))

    query_fields, query_notes = merge_query_fields(all_query_fields)
    return_fields, return_notes = merge_return_fields(all_return_fields)
    filter_candidates = build_filter_candidates(query_fields, return_fields)
    data_type_views = merge_data_type_views(all_data_type_views)
    enum_output_fields = build_enum_output_fields(query_fields, return_fields, enum_index)

    business_summary, confidence = infer_business_summary(class_name, java_file, methods, query_fields)
    scope_hints = build_scope_hints(methods)

    enum_rows = [field for field in query_fields if field.get("ref_id")]
    enum_row_map: dict[str, dict[str, Any]] = {}
    for field in enum_rows:
        enum_row_map[field["param_name"]] = field

    lines: list[str] = []
    lines.append(f"# {class_name}")
    lines.append("")
    lines.append("## 1. 基本信息")
    lines.append(f"- 类名：`{class_name}`")
    lines.append(f"- Java 文件：`{java_file}`")
    lines.append(f"- 包路径：`{package_tail}`")
    lines.append(f"- 业务推断：{business_summary}")
    lines.append(f"- 置信度：`{confidence}`")
    lines.append(f"- 是否带 filter：`{candidate.get('has_filter', '')}`")
    lines.append(f"- 是否带 sVars：`{candidate.get('has_svars', '')}`")
    lines.append(f"- 是否有 XML 绑定：`{candidate.get('has_xml_binding', '')}`")
    if frontend_svars:
        lines.append(f"- 前端 sVar 注入：`{len(frontend_svars)}` 项")
    lines.append("")

    lines.append("## 2. 接口方法")
    endpoint_rows = build_endpoint_rows(java_items, xml_items)
    if endpoint_rows:
        for item in endpoint_rows:
            lines.append(f"- `{item['http']} {item['path']}`")
            lines.append(f"  方法：`{item['method']}`")
            lines.append(f"  参数：`{item['params']}`")
    else:
        lines.append("- 未发现列表查询接口。")
    lines.append("")

    lines.append("## 3. XML 绑定")
    if primary_xml:
        lines.append(f"- **主视图**: `{Path(primary_xml).name}`")
    if other_xmls:
        lines.append("- 其他视图:")
        for xml_file in other_xmls:
            lines.append(f"  - `{Path(xml_file).name}`")
    if not xml_files:
        lines.append("- 未发现 XML 绑定")
    lines.append("")

    lines.append("## 4. 查询字段标准化表")
    if primary_xml:
        lines.append(f"- 来源：主视图 XML `{Path(primary_xml).name}`")
    if query_fields:
        lines.append("| MCP 参数 | 中文名 | 类型 | 匹配方式 | 前端字段 | 后端字段 | 控件 | 枚举 | 来源 XML |")
        lines.append("|---|---|---|---|---|---|---|---|---|")
        for field in query_fields:
            lines.append(
                f"| `{field['param_name']}` | {field['label']} | `{field['type']}` | {field['match_text']} | "
                f"`{field['name']}` | `{field['find_field'] or '-'}` | `{field['ctype'] or '-'}` | "
                f"`{field['ref_id'] or '-'}` | {', '.join(f'`{name}`' for name in field['xml_files'])} |"
            )
        lines.append("")
        lines.append("### 推荐 schema 片段")
        lines.append("```json")
        lines.append(render_schema_snippet(query_fields, enum_index))
        lines.append("```")
    else:
        lines.append("- 未从 XML 中提取到查询字段。")
    if len(query_fields) == 1 and query_fields[0]["param_name"] == "fast_search":
        lines.append("")
        lines.append("### 查询字段说明")
        lines.append("- 当前页面的 XML 查询区仅暴露了 `fastSearch`，更细的精确筛选条件未在 `q_condition` 中配置。")
    if query_notes:
        lines.append("")
        lines.append("### 查询字段备注")
        for note in query_notes:
            lines.append(f"- {note}")
    lines.append("")

    lines.append("## 4.1 Filter 候选字段表")
    if filter_candidates:
        lines.append("| MCP 参数 | 中文名 | 类型 | 推断匹配 | 推断后端字段 | 来源返回列 | 枚举 |")
        lines.append("|---|---|---|---|---|---|---|")
        for candidate_item in filter_candidates:
            lines.append(
                f"| `{candidate_item['param_name']}` | {candidate_item['label']} | `{candidate_item['type']}` | "
                f"{candidate_item['match_text']} | `{candidate_item['backend_field']}` | "
                f"{candidate_item['source_names'] or '-'} | `{','.join(candidate_item['ref_ids']) or '-'}` |"
            )
        lines.append("")
        lines.append("说明：本表不是直接来自 `q_condition`，而是根据列表返回列反推的 filter 候选字段，适合继续用于 MCP 设计。")
    else:
        lines.append("- 未从返回列中推断出可用的 filter 候选字段。")
    lines.append("")

    lines.append("## 5. 枚举字段展开表")
    if enum_row_map:
        lines.append("| MCP 参数 | 中文名 | 枚举 ID | 枚举值 | 枚举定义文件 |")
        lines.append("|---|---|---|---|---|")
        for param_name, field in sorted(enum_row_map.items()):
            ref_id = field["ref_id"]
            enum_meta = enum_index.get(ref_id, {})
            lines.append(
                f"| `{param_name}` | {field['label']} | `{ref_id}` | {enum_value_text(enum_meta) or '未解析到'} | "
                f"`{enum_meta.get('xml_file', '-')}` |"
            )
    else:
        lines.append("- 当前未发现带 `ref_id` 的查询枚举字段。")
    lines.append("")

    lines.append("## 6. 返回字段表（按前端展示顺序）")
    if primary_xml:
        lines.append(f"- 来源：主视图 XML `{Path(primary_xml).name}`")
    if return_fields:
        lines.append("- 说明：本表按 XML `component_set` 中的列顺序生成，对应前端列表页从左到右的展示逻辑。")
        lines.append("")
        lines.append("| 展示顺序 | 返回字段 | 标准 key | 中文列名 | 类型 | 控件 | 枚举 | 枚举值 | 来源列名 | 来源 XML |")
        lines.append("|---:|---|---|---|---|---|---|---|---|---|")
        for index, field in enumerate(return_fields, start=1):
            lines.append(
                f"| {index} | `{field['field']}` | `{snake_case(field['field'])}` | {field['label']} | `{field['type']}` | "
                f"`{field['ctype'] or '-'}` | `{','.join(field['ref_ids']) or '-'}` | "
                f"{build_return_enum_text(field, enum_index) or '-'} | "
                f"{', '.join(f'`{name}`' for name in field['names'])} | {', '.join(f'`{name}`' for name in field['xml_files'])} |"
            )
        lines.append("")
        lines.append("### FIELD_LABELS 建议")
        lines.append("```python")
        lines.append(render_field_labels(return_fields))
        lines.append("```")
    else:
        lines.append("- 未从列表 XML 中提取到返回字段。")
    if return_notes:
        lines.append("")
        lines.append("### 返回字段备注")
        for note in return_notes:
            lines.append(f"- {note}")
    lines.append("")

    lines.append("## 7. sVars / dataType 来源定位")
    lines.append("- 本节只记录 `sVars` / `dataType` 在源码中的位置和值，不直接推断业务含义。")
    lines.append("- 如果实际请求出现 `sVars.dataType`，应回到下表列出的 XML 节点、前端注入点或抓包数据确认其含义。")
    lines.append("- 读取文档的 LLM 应结合 Action 方法、XML 配置、前端请求和业务上下文自行判断是否需要暴露 MCP 参数。")
    if data_type_views:
        lines.append("")
        lines.append("### 7.1 XML dataType 节点")
        lines.append("| 接口方法 | 来源 XML | 节点位置 | defaultType | 行号 |")
        lines.append("|---|---|---|---|---:|")
        for item in data_type_views:
            lines.append(
                f"| `{item['query_method']}` | `{item['xml_name']}` | `{item['node_path']}` | "
                f"`{item.get('default') or '-'}` | {item.get('line') or '-'} |"
            )
        lines.append("")
        lines.append("### 7.2 date_type 原始取值")
        lines.append("| 接口方法 | 来源 XML | name | viewName | 资源 label | 节点位置 | 行号 |")
        lines.append("|---|---|---|---|---|---|---:|")
        for item in data_type_views:
            for value in item.get("values", []):
                lines.append(
                    f"| `{item['query_method']}` | `{item['xml_name']}` | `{value['value']}` | "
                    f"`{value['view_name'] or '-'}` | {value['label'] or '-'} | "
                    f"`{value['node_path']}` | {value.get('line') or '-'} |"
                )
    else:
        lines.append("- 未在 XML 中发现 `<date_types name=\"dataType\">`。如前端实际请求仍携带 `sVars.dataType`，需要结合前端代码或抓包补充来源位置。")
    lines.append("")
    lines.append("### 7.3 视图 sVar 对照表")
    lines.append("- 说明：按视图分组展示前端 `form.addSVar(...)` 注入值，可据此路由 MCP 的 `scope` 参数。")
    if frontend_svars:
        lines.append("")
        lines.append("| 视图 | 对应方法 | 对应 XML | sVar Key | sVar Value | 来源文件 | 行号 |")
        lines.append("|---|---|---|---|---|---|---:|")
        for item in frontend_svars:
            lines.append(
                f"| `{item['view']}` | `{item['methods']}` | `{item['xml_names']}` | "
                f"`{item['key']}` | `{item['value']}` | "
                f"`{item['source_file']}` | {item.get('line') or '-'} |"
            )
    else:
        lines.append("- 未从前端 `form.addSVar(...)` 中识别到固定注入值。")
    lines.append("")

    lines.append("## 8. 枚举字段输出规范")
    if enum_output_fields:
        lines.append("- MCP 标准化返回时，枚举字段必须同时保留原始值和中文显示值。")
        lines.append("- 输出字段规则：`字段名` 保留原值，`字段名_text` 输出中文值，例如 `order_status=0` 与 `order_status_text=未开单`。")
        lines.append("- 枚举值来源于 XML `ref_id` 对应的枚举定义，不能让 LLM 临场猜测。")
        lines.append("")
        lines.append("```python")
        lines.append(render_enum_fields_code(enum_output_fields))
        lines.append("```")
    else:
        lines.append("- 当前未发现可用于 `_text` 输出的枚举字段。")
    lines.append("")

    lines.append("## 9. MCP 设计建议")
    lines.append(f"- 推荐工具名：`{to_pretty_tool_name(class_name)}`")
    lines.append("- 推荐做法：将同类 `listQuery*` 方法合并为一个 MCP，通过 `scope` 或 `view` 参数路由。")
    if scope_hints:
        lines.append("- 建议 scope 映射：")
        for scope, meaning in scope_hints:
            lines.append(f"  - `{scope}`：{meaning}")
    if frontend_svars:
        lines.append("- 按视图注入的 sVar：")
        for item in frontend_svars:
            lines.append(f"  - `{item['view']}` 视图注入 `{item['key']}={item['value']}`，见第 7.3 节源码位置。")
    lines.append("- `dataType` / `sVars` 只应按第 7 节列出的位置回溯确认，不要仅凭字段名或生成器推断业务含义。")
    if query_fields:
        lines.append(
            "- 推荐对外参数："
            + "、".join(f"`{field['param_name']}`" for field in query_fields)
            + "，以及分页参数 `start`、`limit`。"
        )
    if filter_candidates:
        lines.append(
            "- 如需增强型 MCP，可追加暴露这些候选 filter 参数："
            + "、".join(f"`{item['param_name']}`" for item in filter_candidates[:12])
            + (" 等。" if len(filter_candidates) > 12 else "。")
        )
    if return_fields:
        lines.append("- 返回解析建议：先读取 `payload['data']['resultList']`，若不存在再回退到 `payload['resultList']`。")
        lines.append("- `columns` 和 `data/normalized_data` 必须按前端 XML `component_set` 的展示列顺序输出，字段命名和中文列名以第 6 节为准。")
        lines.append("- 默认返回轻量结构：`count`、`columns`、标准化后的 `data/normalized_data`，不要默认返回后端原始 `data.resultList` 或 `raw_resultList`。")
        lines.append("- 仅在显式调试参数 `include_raw=true` 时返回 `raw_resultList/raw_response`，避免关联对象完整数据把 MCP 响应放大。")
    lines.append("- 不建议直接暴露：原始 `filter`、原始 `sVars`、后端内部拼接逻辑。")
    lines.append("")

    lines.append("## 10. 生成依据")
    lines.append("- Java 接口方法名、URL、参数签名。")
    lines.append("- XML 中的 `queryMethod`、`q_condition`、`component_set`、`resource/rs/lang`、`ref_id`。")
    lines.append("- 枚举定义 XML 中的 `<enum id>`、`<item value>`、`resource/rs/lang`。")
    lines.append("- `dataType` / `sVars` 需要同时交叉核对 Action 方法、XML 节点位置、前端 `form.addSVar(...)` / 实际请求参数，不能只看一个来源。")
    lines.append("- 返回数据解析需要优先判断是否存在嵌套 `data.resultList`；抽取后按前端列表展示列顺序生成标准化字段给 LLM，原始行仅用于显式调试。")
    lines.append("- 对于枚举类型、状态类型、下拉框类型字段，必须进一步读取对应 XML 中的 `ref_id`、`enum`、`resource` 配置，识别其可选值及中文含义；这类字段在 MCP 中应按精确匹配处理，不能仅根据字段名猜测。")
    lines.append("")
    return "\n".join(lines)

def render_index(rows: list[dict[str, str]]) -> str:
    lines = ["# MCPAgent Context Index", ""]
    lines.append(f"- 总候选类数：`{len(rows)}`")
    lines.append("- 说明：以下文档用于批量生成 MCP 设计文档，不是最终代码。")
    lines.append("")
    lines.append("| 类名 | has_filter | has_svars | method_count | 文档 |")
    lines.append("|---|---|---:|---:|---|")
    for row in sorted(rows, key=lambda item: item["class_name"]):
        filename = f"{row['class_name']}.md"
        lines.append(
            f"| `{row['class_name']}` | `{row.get('has_filter', '')}` | `{row.get('has_svars', '')}` | "
            f"`{row.get('method_count', '')}` | [{filename}]({filename}) |"
        )
    lines.append("")
    return "\n".join(lines)
