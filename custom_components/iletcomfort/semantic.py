"""Helpers for vendor semantic state and controls."""

from __future__ import annotations

import re
from collections.abc import Iterator
from typing import Any

SEMANTIC_METADATA_FIELDS = {"cmd_type", "msg_up_type", "query_type", "version"}
SEMANTIC_DIAGNOSTIC_GROUPS = {"2080", "2100"}


def semantic_value(
    data: dict[str, Any] | None,
    field: str,
    group: str | None = None,
) -> Any:
    """Return one semantic field, optionally constrained to a command group."""
    semantic = (data or {}).get("semantic") or {}
    if group is not None:
        values = semantic.get(group.lower()) or semantic.get(group.upper()) or {}
        return values.get(field)
    for values in semantic.values():
        if isinstance(values, dict) and field in values:
            return values[field]
    return None


def coerce_semantic_value(value: Any) -> Any:
    """Convert vendor string values into stable Home Assistant state values."""
    if value is None or value == "invalid":
        return None
    if not isinstance(value, str):
        return value
    if re.fullmatch(r"-?\d+", value):
        return int(value)
    if re.fullmatch(r"-?\d+\.\d+", value):
        return float(value)
    return value


def iter_semantic_fields(
    data: dict[str, Any] | None,
) -> Iterator[tuple[str, str]]:
    """Yield every non-metadata semantic field in deterministic order."""
    semantic = (data or {}).get("semantic") or {}
    for group in sorted(semantic):
        values = semantic[group]
        if not isinstance(values, dict):
            continue
        for field in sorted(values):
            if field not in SEMANTIC_METADATA_FIELDS:
                yield str(group).lower(), str(field)


def semantic_field_name(field: str) -> str:
    """Turn vendor snake/camel case identifiers into readable entity names."""
    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", field.replace("_", " "))
    return " ".join(word.upper() if word in {"dhw", "hmi", "cop", "idu", "odu"} else word.capitalize() for word in spaced.split())
