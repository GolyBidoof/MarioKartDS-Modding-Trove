# Mario Kart DS Modding Trove
# tools/ctables/mkds/ui_lld.py — emit a typed LLD emblem placement list as C
# SPDX-License-Identifier: MIT
"""Round-trip ``.lld`` emblem placement lists through C source."""
from __future__ import annotations

import struct

from .ui_c import CProgram, byte_array

ELEMENT_SIZE = 8
TRAILER_SIZE = 8


def emit_source(data: bytes) -> str:
    """Return a C program that rebuilds ``data`` byte-for-byte."""
    if len(data) < 2 + TRAILER_SIZE:
        raise ValueError("LLD: file is too short for a count and trailer")
    count = struct.unpack_from("<H", data, 0)[0]
    expected = 2 + ELEMENT_SIZE * count + TRAILER_SIZE
    if len(data) != expected:
        raise ValueError(
            "LLD: %d bytes, expected %d for %d elements and 8 trailing bytes"
            % (len(data), expected, count)
        )

    entries = [
        struct.unpack_from("<HHHH", data, 2 + ELEMENT_SIZE * index)
        for index in range(count)
    ]
    trailer = data[2 + ELEMENT_SIZE * count:]

    program = CProgram("ui_lld", "LLD", "nitro/mkds/ui/lld.h")
    program.add_decl("static const uint16_t emblem_count = %d;" % count)
    program.add_part("&emblem_count", "sizeof emblem_count")

    if entries:
        lines = ["static const MkdsUiEmblemEntry emblems[] = {"]
        for index, (element_id, x, y, flags) in enumerate(entries):
            lines.extend([
                "    {",
                "        .id = %d," % element_id,
                "        .x = %d," % x,
                "        .y = %d," % y,
                "        .flags = %d," % flags,
                "    },",
            ])
        lines.append("};")
        program.add_decl("\n".join(lines))
        program.add_assert(
            "_Static_assert(sizeof emblems / sizeof emblems[0] == %d, "
            '"LLD element count");' % count
        )
        program.add_array_part("emblems")

    lines = ["static const uint8_t lld_trailer[%d] = {" % TRAILER_SIZE]
    lines.extend(byte_array(list(trailer)))
    lines.append("};")
    program.add_decl("\n".join(lines))
    program.add_assert(
        "_Static_assert(sizeof lld_trailer == %d, "
        '"LLD trailing padding");' % TRAILER_SIZE
    )
    program.add_array_part("lld_trailer")

    return program.render()
