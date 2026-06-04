"""
Unified query engine — the single execution path for all MCP query tools.

The engine handles:
1. Security validation (三防线)
2. Endpoint resolution (route_fn > scope_endpoints > fixed endpoint)
3. Filter SQL construction
4. Request body building (sVars, pagination, filter)
5. HTTP API call
6. Response extraction & normalization

Usage::

    engine = QueryEngine(http_client)
    result = await engine.execute(config, params, token)
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any

import httpx

from .config import FieldLabel, ModuleConfig
from .filter_builder import build_filter
from .security import validate

JAVA_API_BASE = os.environ.get("JAVA_API_BASE", "http://localhost:3011")


def _mask_token(token: str) -> str:
    if token and len(token) > 8:
        return token[:8] + "***"
    return "***"


def _extract_result_list(payload: dict[str, Any]) -> list[dict[str, Any]]:
    nested_data = payload.get("data")
    if isinstance(nested_data, dict) and isinstance(nested_data.get("resultList"), list):
        return nested_data["resultList"]
    if isinstance(payload.get("resultList"), list):
        return payload["resultList"]
    return []


def _extract_count(payload: dict[str, Any], fallback_count: int) -> int:
    nested_data = payload.get("data")
    if isinstance(nested_data, dict) and isinstance(nested_data.get("count"), int):
        return nested_data["count"]
    if isinstance(payload.get("count"), int):
        return payload["count"]
    return fallback_count


def _enum_text_value(enum_map: dict[int | str, str] | None, value: Any) -> str | None:
    if enum_map is None:
        return None
    if value in enum_map:
        return enum_map[value]
    if value is None:
        return None
    try:
        return enum_map.get(int(value))
    except (TypeError, ValueError):
        return enum_map.get(str(value))


def _build_columns(config: ModuleConfig) -> list[dict[str, str]]:
    return [
        {"field": field_name, "key": fl.key, "title": fl.title}
        for field_name, fl in config.field_labels.items()
    ]


def _normalize_row(row: dict[str, Any], config: ModuleConfig) -> dict[str, Any]:
    """Normalize a single raw backend row using the config's field_labels.

    Supports optional ``row_field_map`` for fields that sit at different
    keys in the backend response than the field_label key.
    """
    normalized: dict[str, Any] = {}
    for field_name, fl in config.field_labels.items():
        # Determine how to extract the value
        if fl.field_extractor:
            value = fl.field_extractor(row)
        elif field_name in row:
            # Direct match — backend returned this field with the expected key
            value = row[field_name]
        elif config.row_field_map and fl.key in config.row_field_map:
            # Fallback: field sits at a different key in this response
            value = row.get(config.row_field_map[fl.key])
        else:
            value = row.get(field_name)

        normalized[fl.key] = value

        # Add enum text if applicable
        enum_field = config.enum_fields.get(fl.key)
        if enum_field:
            text = _enum_text_value(enum_field.mapping, value)
            if text is not None:
                normalized[f"{fl.key}_text"] = text

    return normalized


def _resolve_endpoint(config: ModuleConfig, params: dict[str, Any]) -> str:
    """Resolve the API endpoint using priority: route_fn > scope > fixed.

    Priority:
    1. ``config.route_fn(params)`` — custom routing logic
    2. ``config.scope_endpoints[scope]`` — scope-based routing (90% of modules)
    3. ``config.endpoint`` — fixed endpoint fallback
    """
    # Priority 1: custom route function
    if config.route_fn:
        return config.route_fn(params)

    # Priority 2: scope-based routing
    scope = params.get("scope") or params.get("view") or "default"
    if config.scope_endpoints and scope in config.scope_endpoints:
        return config.scope_endpoints[scope]

    # Priority 3: fixed endpoint
    return config.endpoint


def _build_request_params(config: ModuleConfig, params: dict[str, Any], filter_str: str | None) -> dict[str, str]:
    """Build the HTTP query/body params dict from MCP tool params.

    Handles: pagination (start/limit), sVars (scope-level extras + dataType),
    filter SQL, and pass-through extra params.
    """
    start = params.get("start", 0)
    limit = params.get("limit", config.default_limit)
    # Enforce max_limit
    if limit is not None:
        try:
            limit = min(int(limit), config.max_limit)
        except (TypeError, ValueError):
            limit = config.default_limit
    scope = params.get("scope") or params.get("view") or "default"

    request_params: dict[str, str] = {
        "start": str(0 if start is None else start),
        "limit": str(config.default_limit if limit is None else limit),
    }

    # Build sVars
    svar_data: dict[str, Any] = {}

    # Scope-level extra sVars
    if config.scope_svars and scope in config.scope_svars:
        svar_data.update(config.scope_svars[scope])

    # dataType defaulting
    if config.scope_datatype_defaults and scope in config.scope_datatype_defaults:
        data_type = params.get("data_type") or config.scope_datatype_defaults[scope]
        svar_data["dataType"] = data_type

    if svar_data:
        request_params["sVars"] = json.dumps(svar_data, ensure_ascii=False)

    # Filter SQL
    if filter_str:
        request_params["filter"] = filter_str

    # Pass-through extra params (e.g. keyword, date_enums)
    for extra_key in config.extra_params:
        if extra_key in params and params[extra_key] is not None:
            request_params[extra_key] = str(params[extra_key])

    return request_params


class QueryEngine:
    """Unified execution engine for all MCP query tools.

    Wraps an HTTPX async client for API communication.
    """

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._client = client or httpx.AsyncClient(timeout=30.0)

    async def execute(
        self,
        config: ModuleConfig,
        params: dict[str, Any],
        token: str,
    ) -> dict[str, Any]:
        """Execute a single MCP query.

        Args:
            config: Module configuration describing the endpoint, filters, etc.
            params: MCP tool arguments from the caller (scope, start, limit,
                    filter values, data_type, etc.).
            token: x-access-token for API authentication.

        Returns:
            Normalized response dict with ``success``, ``count``, ``columns``,
            ``data``, ``_api_call`` debug info, and optionally ``_filter_config``
            etc. when debug mode is on.
        """
        # 1. 三防线安全校验
        validate(config, params)

        # 2. 解析端点
        endpoint = _resolve_endpoint(config, params)

        # 3. 构建过滤条件
        filter_str = build_filter(config.filters, params)

        # 4. 构建请求参数
        request_params = _build_request_params(config, params, filter_str)

        # 5. Debug logging
        full_url = f"{JAVA_API_BASE}{endpoint}"
        sys.stderr.write(f"\n[API REQUEST] {config.method} {full_url}\n")
        sys.stderr.write(f"  scope = {params.get('scope') or params.get('view') or 'default'}\n")
        for key, value in request_params.items():
            sys.stderr.write(f"  {key} = {value}\n")
        sys.stderr.write("\n")
        sys.stderr.flush()

        # 6. API 调用 (default GET with query params)
        if config.method == "GET":
            response = await self._client.get(
                full_url,
                headers={"x-access-token": token},
                params=request_params,
            )
        else:
            response = await self._client.post(
                full_url,
                headers={"x-access-token": token},
                json=request_params,
            )
        response.raise_for_status()
        payload = response.json()

        # 7. 提取 & 规范化
        raw_result_list = _extract_result_list(payload)
        normalized_data = [_normalize_row(row, config) for row in raw_result_list]

        result: dict[str, Any] = {
            "success": payload.get("success", True),
            "count": _extract_count(payload, len(raw_result_list)),
            "columns": _build_columns(config),
            "data": normalized_data,
            "normalized_data": normalized_data,
            "_api_call": {
                "method": config.method,
                "url": full_url,
                "scope": params.get("scope") or params.get("view") or "default",
                "params": dict(request_params),
                "token_masked": _mask_token(token),
            },
        }

        # Debug extras
        include_raw = params.get("include_raw", False)
        if include_raw:
            result["raw_resultList"] = raw_result_list
            result["raw_response"] = payload

        return result

    async def close(self) -> None:
        await self._client.aclose()
