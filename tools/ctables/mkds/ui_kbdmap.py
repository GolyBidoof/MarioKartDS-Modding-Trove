# Mario Kart DS Modding Trove
# tools/ctables/mkds/ui_kbdmap.py — emit a KBDMAP UTF-16LE character list as C
# SPDX-License-Identifier: MIT
"""Round-trip ``.kbdmap`` BOM-prefixed UTF-16LE character lists through C."""
from __future__ import annotations

import struct

from .ui_c import CProgram, word_array

BOM = b"\xFF\xFE"
PREFIX_SIZE = 2


def emit_source(data: bytes) -> str:
    """Return a C program that rebuilds ``data`` byte-for-byte."""
    if len(data) < PREFIX_SIZE:
        raise ValueError("KBDMAP: file is shorter than the BOM")
    if data[:PREFIX_SIZE] != BOM:
        raise ValueError(
            "KBDMAP: expected UTF-16LE BOM FF FE, got %s"
            % data[:PREFIX_SIZE].hex().upper()
        )
    payload = data[PREFIX_SIZE:]
    if len(payload) % 2 != 0:
        raise ValueError(
            "KBDMAP: %d payload bytes is not a whole number of UTF-16 units"
            % len(payload)
        )
    characters = list(struct.unpack("<%dH" % (len(payload) // 2), payload))

    program = CProgram("ui_kbdmap", "KBDMAP", "nitro/mkds/ui/kbdmap.h")
    program.add_decl("\n".join([
                "static const uint8_t kbdmap_bom[MKDS_UI_KBDMAP_PREFIX_SIZE] = {",
        "    0xFF, 0xFE,",
        "};",
    ]))
    program.add_part("kbdmap_bom", "sizeof kbdmap_bom")

    if characters:
        lines = ["static const uint16_t characters[] = {"]
        lines.extend(word_array(characters))
        lines.append("};")
        program.add_decl("\n".join(lines))
        program.add_assert(
            "_Static_assert(sizeof characters / sizeof characters[0] == %d, "
            '"KBDMAP character count");' % len(characters)
        )
        program.add_array_part("characters")

    return program.render()
