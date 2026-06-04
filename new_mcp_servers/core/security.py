"""
三防线安全校验（Three-layer security validation).

防线1 — 角色门控：scope 必须在 config.scope_endpoints 的 keys 中
防线2 — 字段白名单：所有 filter 参数必须在 FilterDef 列表中声明
防线3 — 操作符绑定：操作符从 FilterDef 中读取，不由用户传入

Note: 防线3 is structural — it's enforced by the fact that
``filter_builder.build()`` reads operators from the config, not from user
input.  This module handles the explicit checks for 防线1 and 防线2.
"""

from __future__ import annotations

from typing import Any

from .config import FilterDef, ModuleConfig


class SecurityError(ValueError):
    """Raised when a security check fails."""
    pass


def validate_scope(config: ModuleConfig, params: dict[str, Any]) -> None:
    """防线1 — 角色门控：验证 scope 值是否在允许范围内。

    If the config has scope_endpoints, the caller's ``scope`` (defaulting to
    ``"default"``) MUST be one of its keys.  If the config has no
    scope_endpoints, any scope is allowed (the fixed endpoint is used).
    """
    if not config.scope_endpoints:
        return

    scope = params.get("scope") or params.get("view") or "default"
    if scope not in config.scope_endpoints:
        allowed = ", ".join(sorted(config.scope_endpoints))
        raise SecurityError(
            f"不支持的 scope 值：'{scope}'。"
            f"模块 '{config.name}' 允许的 scope 值：{allowed}"
        )


def validate_filters(config: ModuleConfig, params: dict[str, Any]) -> None:
    """防线2 — 字段白名单：验证所有参数名是否在配置的 filter 或 extra 列表中。

    Every param key (except known control params) must match a FilterDef or be
    in the extra_params list.
    """
    known_params: set[str] = {
        "scope", "view", "start", "limit", "data_type",
        "include_raw", "token",
    }
    known_params.update(config.extra_params)

    allowed_filter_keys = {f.key for f in config.filters}

    for key in params:
        if key in known_params or key in allowed_filter_keys:
            continue
        raise SecurityError(
            f"不支持的参数：'{key}'。"
            f"模块 '{config.name}' 未声明此字段。"
            f"允许的 filter 字段：{', '.join(sorted(allowed_filter_keys))}"
        )


def validate(config: ModuleConfig, params: dict[str, Any]) -> None:
    """Run all three security validation layers.

    Raises SecurityError on any violation.
    """
    validate_scope(config, params)
    validate_filters(config, params)
    # 防线3 is structural — enforced in filter_builder.build()
