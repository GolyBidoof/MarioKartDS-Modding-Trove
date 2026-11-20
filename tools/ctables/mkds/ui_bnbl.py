# Mario Kart DS Modding Trove
# tools/ctables/mkds/ui_bnbl.py — emit a typed JNBL box list as C
# SPDX-License-Identifier: MIT
"""Round-trip ``.bnbl`` (JNBL) touch-box lists through C source."""
from __future__ import annotations

import struct

from .ui_c import CProgram, coord_initializer

MAGIC = b"JNBL"
HEADER_SIZE = 8
ELEMENT_SIZE = 6


def emit_source(data: bytes) -> str:
    """Return a C program that rebuilds ``data`` byte-for-byte."""
    if len(data) < HEADER_SIZE:
        raise ValueError("BNBL: file is shorter than the 8-byte header")
    magic, reserved, count = struct.unpack_from("<4sHH", data, 0)
    if magic != MAGIC:
        raise ValueError("BNBL: bad magic %r" % (magic,))
    expected = HEADER_SIZE + ELEMENT_SIZE * count
    if len(data) != expected:
        raise ValueError(
            "BNBL: %d bytes, expected %d for %d boxes"
            % (len(data), expected, count)
        )

    boxes = [
        struct.unpack_from("<HHBB", data,
                           HEADER_SIZE + ELEMENT_SIZE * index)
        for index in range(count)
    ]

    program = CProgram("ui_bnbl", "JNBL/BNBL", "nitro/mkds/ui/bnbl.h")
    program.add_decl("\n".join([
        "static const MkdsUiListHeader list_header = {",
        "    .magic = MKDS_UI_BNBL_MAGIC,",
        "    .reserved = %d," % reserved,
        "    .count = %d," % count,
        "};",
    ]))
    program.add_part("&list_header", "sizeof list_header")

    if boxes:
        lines = ["static const MkdsUiBoxElement boxes[] = {"]
        for x, y, width, height in boxes:
            lines.extend([
                "    {",
                "        .x = %s," % coord_initializer(x),
                "        .y = %s," % coord_initializer(y),
                "        .width = %d," % width,
                "        .height = %d," % height,
                "    },",
            ])
        lines.append("};")
        program.add_decl("\n".join(lines))
        program.add_assert(
            "_Static_assert(sizeof boxes / sizeof boxes[0] == %d, "
            '"BNBL box count");' % count
        )
        program.add_array_part("boxes")

    return program.render()
