# Mario Kart DS Modding Trove
# tools/ctables/common/cnames.py — map numeric values to public enum constants
# SPDX-License-Identifier: MIT
"""Read enum names from the public headers so generated tables can use them.

The emitters are allowed to read the headers: they are the shared contract.
This module never invents a name. If a value is not present in a declared
enum, callers keep the numeric form and may add a comment.
"""
from __future__ import annotations

import functools
import re
from pathlib import Path

_INCLUDE = Path(__file__).resolve().parents[3] / "include"

_ENUM_RE = re.compile(
    r"typedef\s+enum(?:\s+\w+)?\s*\{([^{}]*)\}\s*(\w+)\s*;",
    re.S,
)
_VALUE_RE = re.compile(
    r"^\s*([A-Z][A-Z0-9_]*)\s*=\s*(0x[0-9A-Fa-f]+|\d+)",
    re.M,
)


@functools.lru_cache(maxsize=None)
def _enums() -> dict[str, dict[int, str]]:
    result: dict[str, dict[int, str]] = {}
    try:
        paths = sorted(_INCLUDE.rglob("*.h"))
    except OSError:
        return result
    for path in paths:
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        for match in _ENUM_RE.finditer(text):
            type_name = match.group(2)
            names = result.setdefault(type_name, {})
            for name, raw in _VALUE_RE.findall(match.group(1)):
                names.setdefault(int(raw, 0), name)
    return result


def enum_name(type_name: str, value: int) -> str | None:
    """Return the declared constant for this type/value, or None."""
    return _enums().get(type_name, {}).get(value)


def enum_names(type_name: str) -> dict[int, str]:
    """Return a copy of the value -> name map for one enum type."""
    return dict(_enums().get(type_name, {}))
