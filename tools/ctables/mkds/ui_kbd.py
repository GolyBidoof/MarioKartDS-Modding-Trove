# Mario Kart DS Modding Trove
# tools/ctables/mkds/ui_kbd.py — emit KBD keyboard hit rectangles as C
# SPDX-License-Identifier: MIT
"""Round-trip ``.kbd`` keyboard hit-rectangle tables through C source."""
from __future__ import annotations

import struct

from .ui_c import CProgram

ELEMENT_SIZE = 8


def emit_source(data: bytes) -> str:
    """Return a C program that rebuilds ``data`` byte-for-byte."""
    if len(data) % ELEMENT_SIZE != 0:
        raise ValueError(
            "KBD: %d bytes is not a multiple of %d"
            % (len(data), ELEMENT_SIZE)
        )
    count = len(data) // ELEMENT_SIZE
    keys = [
        struct.unpack_from("<BBBBhH", data, ELEMENT_SIZE * index)
        for index in range(count)
    ]

    program = CProgram("ui_kbd", "KBD", "nitro/mkds/ui/kbd.h")
    if keys:
        lines = ["static const MkdsUiKeyEntry keys[] = {"]
        for index, (x, y, width, height, chain_step, key_id) in enumerate(keys):
            lines.extend([
                "    {",
                "        .x = %d," % x,
                "        .y = %d," % y,
                "        .width = %d," % width,
                "        .height = %d," % height,
                "        .chain_step = %d," % chain_step,
                "        .key_id = %d," % key_id,
                "    },",
            ])
        lines.append("};")
        program.add_decl("\n".join(lines))
        program.add_assert(
            "_Static_assert(sizeof keys / sizeof keys[0] == %d, "
            '"KBD key count");' % count
        )
        program.add_array_part("keys")

    return program.render()
