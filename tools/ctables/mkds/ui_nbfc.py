# Mario Kart DS Modding Trove
# tools/ctables/mkds/ui_nbfc.py — emit an NBFC 4bpp tile image as C
# SPDX-License-Identifier: MIT
"""Round-trip ``.nbfc`` 32x32 4bpp banner images through C source."""
from __future__ import annotations

from .ui_c import CProgram, hex8

SIZE = 512
TILES = 16
TILE_WIDTH = 8
TILE_HEIGHT = 8
ROW_BYTES = 4


def emit_source(data: bytes) -> str:
    """Return a C program that rebuilds ``data`` byte-for-byte."""
    if len(data) != SIZE:
        raise ValueError("NBFC: %d bytes, expected %d" % (len(data), SIZE))

    program = CProgram("ui_nbfc", "NBFC", "nitro/mkds/ui/nbfc.h")
    program.add_decl("\n".join([
        "typedef struct {",
        "    uint8_t packed_row[4];",
        "} MkdsUiBannerTileRow;",
    ]))
    program.add_assert(
        "_Static_assert(sizeof(MkdsUiBannerTileRow) == 4, "
        '"NBFC tile row");'
    )
    lines = [
        "static const MkdsUiBannerTileRow "
        "banner_tiles[MKDS_UI_NBFC_TILES][MKDS_UI_NBFC_TILE_HEIGHT] = {",
    ]
    for tile in range(TILES):
        tile_x = (tile % 4) * TILE_WIDTH
        tile_y = (tile // 4) * TILE_HEIGHT
        pass
        lines.append("    {")
        base = tile * 32
        for row in range(TILE_HEIGHT):
            offset = base + row * ROW_BYTES
            packed = data[offset:offset + ROW_BYTES]
            lines.append(
                "        { .packed_row = { %s, %s, %s, %s } },"
                % (hex8(packed[0]), hex8(packed[1]),
                   hex8(packed[2]), hex8(packed[3]))
            )
        lines.append("    },")
    lines.append("};")
    program.add_decl("\n".join(lines))
    program.add_assert(
        "_Static_assert(sizeof banner_tiles == MKDS_UI_NBFC_SIZE, "
        '"NBFC image size");'
    )
    program.add_assert(
        "_Static_assert(sizeof banner_tiles / sizeof banner_tiles[0] == "
        'MKDS_UI_NBFC_TILES, "NBFC tile count");'
    )
    program.add_array_part("banner_tiles")

    return program.render()
