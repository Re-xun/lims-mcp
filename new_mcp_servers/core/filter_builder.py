"""
Unified filter builder — converts a list of FilterDef + user params into
a SQL WHERE clause string.

The operator for each field is defined in the FilterDef configuration, NOT
from user input.  Users only provide values, ensuring injection safety.
"""

from __future__ import annotations

from typing import Any

from .config import FilterDef


def _escape_sql(value: str) -> str:
    """Escape single quotes for SQL string literals.

    ANSI SQL doubles single quotes inside string literals: ``O'Reilly`` → ``O''Reilly``.
    """
    return value.replace("'", "''")


def _escape_like(value: str) -> str:
    """Escape special characters for SQL LIKE patterns.

    - ``'`` → ``''`` (SQL string literal escaping)
    - ``%`` → ``[%]`` (escape LIKE wildcard)
    - ``_`` → ``[_]`` (escape LIKE wildcard)

    ``[%]`` and ``[_]`` are the ANSI SQL standard way to escape LIKE wildcards
    without needing an ESCAPE clause.
    """
    value = value.replace("'", "''")
    value = value.replace("%", "[%]")
    value = value.replace("_", "[_]")
    return value


def build_filter(filters: list[FilterDef], params: dict[str, Any]) -> str | None:
    """Build a SQL WHERE clause from configured filters and caller-supplied values.

    Only params whose key matches a FilterDef and whose value is non-None and
    non-empty-string are included.  The operator for each condition is taken
    from the FilterDef — the caller cannot influence it.

    All user-supplied values are escaped to prevent SQL injection:
    - Single quotes are doubled (``'`` → ``''``)
    - LIKE wildcards ``%`` and ``_`` are bracketed (``[%]``, ``[_]``)

    Returns:
        SQL AND-concatenated WHERE clause string, or None if no conditions apply.
    """
    conditions: list[str] = []

    for f in filters:
        value = params.get(f.key)
        if value is None or value == "":
            continue

        if f.operator == "like":
            safe = _escape_like(str(value))
            conditions.append(f"{f.backend_field} like '%{safe}%'")
        elif f.operator == "=":
            if isinstance(value, bool):
                conditions.append(f"{f.backend_field} = {str(value).lower()}")
            elif isinstance(value, int):
                conditions.append(f"{f.backend_field} = {value}")
            else:
                safe = _escape_sql(str(value))
                conditions.append(f"{f.backend_field} = '{safe}'")
        elif f.operator == ">=":
            safe = _escape_sql(str(value))
            conditions.append(f"{f.backend_field} >= '{safe}'")
        elif f.operator == "<=":
            safe = _escape_sql(str(value))
            if f.is_date_range:
                # Date-range end: extend to end-of-day for inclusive matching
                conditions.append(f"{f.backend_field} <= '{safe} 23:59:59'")
            else:
                conditions.append(f"{f.backend_field} <= '{safe}'")
        elif f.operator == "in":
            if isinstance(value, list) and value:
                items = ",".join(
                    str(v) if isinstance(v, (int, bool)) else f"'{_escape_sql(str(v))}'"
                    for v in value
                )
                conditions.append(f"{f.backend_field} in ({items})")
        else:
            # Fallback: generic template
            safe = _escape_sql(str(value))
            conditions.append(f"{f.backend_field} {f.operator} '{safe}'")

    return " and ".join(conditions) if conditions else None
