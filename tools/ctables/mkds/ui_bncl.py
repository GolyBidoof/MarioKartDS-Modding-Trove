# Mario Kart DS Modding Trove
# tools/ctables/mkds/ui_bncl.py — emit a typed JNCL cell list as C
# SPDX-License-Identifier: MIT
"""Round-trip ``.bncl`` (JNCL) cell placement lists through C source."""
from __future__ import annotations

import struct

from .ui_c import CProgram, coord_initializer

MAGIC = b"JNCL"
HEADER_SIZE = 8
ELEMENT_SIZE = 8


def emit_source(data: bytes) -> str:
    """Return a C program that rebuilds ``data`` byte-for-byte."""
    if len(data) < HEADER_SIZE:
        raise ValueError("BNCL: file is shorter than the 8-byte header")
    magic, reserved, count = struct.unpack_from("<4sHH", data, 0)
    if magic != MAGIC:
        raise ValueError("BNCL: bad magic %r" % (magic,))
    expected = HEADER_SIZE + ELEMENT_SIZE * count
    if len(data) != expected:
        raise ValueError(
            "BNCL: %d bytes, expected %d for %d cells"
            % (len(data), expected, count)
        )

    cells = [
        struct.unpack_from("<HHI", data, HEADER_SIZE + ELEMENT_SIZE * index)
        for index in range(count)
    ]

    program = CProgram("ui_bncl", "JNCL/BNCL", "nitro/mkds/ui/bncl.h")
    program.add_decl("\n".join([
        "static const MkdsUiListHeader list_header = {",
        "    .magic = MKDS_UI_BNCL_MAGIC,",
        "    .reserved = %d," % reserved,
        "    .count = %d," % count,
        "};",
    ]))
    program.add_part("&list_header", "sizeof list_header")

    if cells:
        lines = ["static const MkdsUiCellElement cells[] = {"]
        for x, y, cell_id in cells:
            lines.extend([
                "    {",
                "        .x = %s," % coord_initializer(x),
                "        .y = %s," % coord_initializer(y),
                "        .cell_id = %d," % cell_id,
                "    },",
            ])
        lines.append("};")
        program.add_decl("\n".join(lines))
        program.add_assert(
            "_Static_assert(sizeof cells / sizeof cells[0] == %d, "
            '"BNCL cell count");' % count
        )
        program.add_array_part("cells")

    return program.render()
