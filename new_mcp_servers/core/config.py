"""
Core type definitions for MCP module configuration.

All module configuration is expressed through these dataclasses instead of
YAML or raw dicts — type-safe, IDE-compatible, zero new dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable


@dataclass
class FilterDef:
    """Single filter field definition.

    Each filter maps a user-facing MCP parameter to a backend SQL field
    with a fixed operator.  The operator is part of the config — never
    taken from user input (see security.py — 三防线).
    """

    key: str
    """Python parameter name (snake_case), matches the MCP tool argument."""

    backend_field: str
    """Backend SQL column or field expression, e.g. 'ac.customer_name_cn'."""

    label: str
    """Chinese display label for the filter, shown in descriptions."""

    operator: str
    """SQL operator: '=' | 'like' | '>=' | '<=' | 'in'.
    Hardcoded in config — NOT controllable by the caller.
    """

    is_date_range: bool = False
    """If True, this filter is one side of a date range (start or end)."""

    enums: dict[int, str] | None = None
    """Optional enum mapping {value → display_text}.
    Populated into the JSON Schema description for LLM guidance.
    """


@dataclass
class FieldLabel:
    """Maps a backend response field to its normalized key and Chinese title."""

    key: str
    """Normalized snake_case key used in the final output dict."""

    title: str
    """Chinese column title for display, e.g. '客户名称'."""

    field_extractor: Callable[[dict], str | None] | None = None
    """Optional custom extractor for non-standard field access.
    If None, defaults to ``lambda row: row.get(field_label_key_in_response)``.
    Used for fields that sit at different keys in different scopes.
    """


@dataclass
class EnumField:
    """Enum mapping for a normalized output field."""

    mapping: dict[int | str, str]
    """Value → display text mapping, e.g. {20: '未开案', 30: '案件进行中'}."""


@dataclass
class ModuleConfig:
    """Complete configuration for a single MCP query module.

    One ModuleConfig ＝ one MCP tool (one ``query_xxx_list`` endpoint).
    Modules with multiple tools (e.g. dm_project with 5 tools) need multiple
    ModuleConfig entries.
    """

    # ── identity ────────────────────────────────────────────────────────
    name: str
    """MCP tool name, e.g. 'query_customer_list'."""

    display_name: str
    """Human-readable name in Chinese, e.g. '客户列表'."""

    description: str = ""
    """Long description for the MCP tool."""

    # ── API endpoint ────────────────────────────────────────────────────
    endpoint: str = ""
    """Default API endpoint path, e.g. '/AbdCustomerListAction/listQuery'.
    Used as fallback when neither scope_endpoints nor route_fn applies.
    """

    method: str = "GET"
    """HTTP method: 'GET' (params in query string) or 'POST' (JSON body).
    Defaults to GET to match existing LIMS Java API conventions.
    """

    scope_endpoints: dict[str, str] | None = None
    """Mapping from scope name → endpoint path.
    E.g. {'default': '/.../listQuery', 'my': '/.../listQueryMy'}.
    When a scope key matches params['scope'], this takes priority over
    the fixed endpoint.
    """

    # ── scope-level extra parameters ────────────────────────────────────
    scope_svars: dict[str, dict] = field(default_factory=dict)
    """Extra sVars key-value pairs injected per scope.
    E.g. {'default': {'customerType': 1, 'operation': 'operation'}}
    """

    scope_datatype_defaults: dict[str, str] = field(default_factory=dict)
    """Default dataType value per scope when caller doesn't provide one.
    E.g. {'default': 'Last30days', 'my': 'Last30days'}
    """

    # ── params ──────────────────────────────────────────────────────────
    extra_params: list[str] = field(default_factory=list)
    """List of extra MCP parameter names that are NOT filter fields.
    These are passed through as top-level query params (e.g. 'include_raw',
    'keyword', 'date_enums').
    """

    # ── filters ─────────────────────────────────────────────────────────
    filters: list[FilterDef] = field(default_factory=list)
    """All filter fields exposed by this tool."""

    # ── response normalization ──────────────────────────────────────────
    field_labels: dict[str, FieldLabel] = field(default_factory=dict)
    """Mapping from backend response field name → normalized FieldLabel.
    Used for column definition and row normalization.
    The dict key is the field name as returned by the backend (camelCase).
    """

    enum_fields: dict[str, EnumField] = field(default_factory=dict)
    """Enum mappings keyed by normalized key (FieldLabel.key).
    Used to add ``{key}_text`` fields during normalization.
    """

    # ── pagination ──────────────────────────────────────────────────────
    default_limit: int = 10
    max_limit: int = 200

    # ── custom routing ──────────────────────────────────────────────────
    route_fn: Callable[[dict], str] | None = None
    """Optional custom routing function for complex modules (e.g. dm_project
    that dispatches by data_type + modular_type).
    Receives the full params dict, returns an endpoint path.
    If set, takes priority over scope_endpoints and endpoint.
    """

    # ── custom row extraction ───────────────────────────────────────────
    row_field_map: dict[str, str] | None = None
    """Optional mapping of field_label_key → actual response key.
    Used when a backend returns a field under different keys in different
    scopes. E.g. {'person_name': 'responsePerson'} means the normalized
    field 'person_name' should be read from row['responsePerson'].
    Keys here override the default ``row.get(field_label_key)`` behavior.
    """
