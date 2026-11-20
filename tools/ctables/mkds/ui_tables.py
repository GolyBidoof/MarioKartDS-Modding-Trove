# Mario Kart DS Modding Trove
# tools/ctables/mkds/ui_tables.py — dispatch for typed MKDS UI C-table emitters
# SPDX-License-Identifier: MIT
"""Typed C-source emitters for the MKDS/JNLib UI container formats.

Each format module exposes ``emit_source(data: bytes) -> str``. The returned
program includes the matching header from ``include/nitro/mkds``, stores the
records in static tables with designated initializers, and writes the original
bytes to the path in ``argv[1]``.

Formats: BNCL/JNCL, BNLL/JNLL, BNBL/JNBL, KBD, KBDMAP, LLD, NBFP and NBFC.
"""
from __future__ import annotations

from typing import Callable, Dict

from . import ui_bncl as bncl
from . import ui_bnbl as bnbl
from . import ui_bnll as bnll
from . import ui_kbd as kbd
from . import ui_kbdmap as kbdmap
from . import ui_lld as lld
from . import ui_nbfc as nbfc
from . import ui_nbfp as nbfp

Emitter = Callable[[bytes], str]

FORMATS: Dict[str, Emitter] = {
    "bncl": bncl.emit_source,
    "bnll": bnll.emit_source,
    "bnbl": bnbl.emit_source,
    "kbd": kbd.emit_source,
    "kbdmap": kbdmap.emit_source,
    "lld": lld.emit_source,
    "nbfp": nbfp.emit_source,
    "nbfc": nbfc.emit_source,
}

ALIASES = {
    "jncl": "bncl",
    "jnll": "bnll",
    "jnbl": "bnbl",
    "banner-palette": "nbfp",
    "banner-image": "nbfc",
}

# Convenience names for callers that prefer one function per format.
emit_bncl = bncl.emit_source
emit_bnll = bnll.emit_source
emit_bnbl = bnbl.emit_source
emit_kbd = kbd.emit_source
emit_kbdmap = kbdmap.emit_source
emit_lld = lld.emit_source
emit_nbfp = nbfp.emit_source
emit_nbfc = nbfc.emit_source


def emit_source(format_name: str, data: bytes) -> str:
    """Emit a C program for ``format_name`` (``.bncl``, ``JNCL``, etc.)."""
    key = format_name.strip().lower().lstrip(".")
    key = ALIASES.get(key, key)
    try:
        emitter = FORMATS[key]
    except KeyError:
        raise ValueError(
            "unknown UI table format %r; choose one of %s"
            % (format_name, ", ".join(sorted(FORMATS)))
        ) from None
    return emitter(data)
