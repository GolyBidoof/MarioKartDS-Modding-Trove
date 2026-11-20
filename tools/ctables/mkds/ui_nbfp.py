# Mario Kart DS Modding Trove
# tools/ctables/mkds/ui_nbfp.py — emit an NBFP RGB555 palette as C
# SPDX-License-Identifier: MIT
"""Round-trip ``.nbfp`` 16-colour RGB555 palettes through C source."""
from __future__ import annotations

import struct

from .ui_c import CProgram, hex16

COLOR_COUNT = 16
SIZE = 32


def emit_source(data: bytes) -> str:
    """Return a C program that rebuilds ``data`` byte-for-byte."""
    if len(data) != SIZE:
        raise ValueError("NBFP: %d bytes, expected %d" % (len(data), SIZE))
    colors = list(struct.unpack("<%dH" % COLOR_COUNT, data))

    program = CProgram("ui_nbfp", "NBFP", "nitro/mkds/ui/nbfp.h")
    lines = [
        "static const MkdsUiBannerColor palette[MKDS_UI_NBFP_COLOR_COUNT] = {"
    ]
    for index, raw in enumerate(colors):
        red = raw & 0x1F
        green = (raw >> 5) & 0x1F
        blue = (raw >> 10) & 0x1F
        reserved = (raw >> 15) & 0x1
        lines.append(
            "    { .bits = { .red = %d, .green = %d, .blue = %d, "
            ".reserved = %d } },"
            % (red, green, blue, reserved)
        )
    lines.append("};")
    program.add_decl("\n".join(lines))
    program.add_assert(
        '_Static_assert(sizeof palette == MKDS_UI_NBFP_SIZE, "NBFP size");'
    )
    program.add_assert(
        "_Static_assert(sizeof palette / sizeof palette[0] == "
        'MKDS_UI_NBFP_COLOR_COUNT, "NBFP colour count");'
    )
    program.add_array_part("palette")

    return program.render()
