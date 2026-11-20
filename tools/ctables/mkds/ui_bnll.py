# Mario Kart DS Modding Trove
# tools/ctables/mkds/ui_bnll.py — emit a typed JNLL label list as C
# SPDX-License-Identifier: MIT
"""Round-trip ``.bnll`` (JNLL) label placement lists through C source."""
from __future__ import annotations

import struct
from typing import Dict, List, Tuple

from .ui_c import (
    CProgram,
    byte_array,
    coord_initializer,
    hex32,
    printable_ascii,
    style_initializer,
    word_array,
)

MAGIC = b"JNLL"
HEADER_SIZE = 8
ELEMENT_SIZE = 12


def _read_utf16z(data: bytes, offset: int) -> Tuple[List[int], int]:
    """Read a NUL-terminated UTF-16LE string; return units and next offset."""
    units: List[int] = []
    cursor = offset
    while cursor + 1 < len(data):
        unit = struct.unpack_from("<H", data, cursor)[0]
        cursor += 2
        units.append(unit)
        if unit == 0:
            return units, cursor
    raise ValueError("BNLL: unterminated string at 0x%X" % offset)


def _string_comment(offset: int, units: List[int]) -> str:
    text = printable_ascii(units)
    if text:
        return 'string at 0x%X: "%s" (%d units)' % (
            offset, text, len(units))
    return "string at 0x%X (%d units)" % (offset, len(units))


def _string_declaration(index: int, units: List[int]) -> str:
    lines = ["static const uint16_t label_string_%d[] = {" % index]
    lines.extend(word_array(units))
    lines.append("};")
    return "\n".join(lines)


def _pool_declaration(pool: bytes) -> str:
    lines = ["static const uint8_t string_pool[] = {"]
    lines.extend(byte_array(list(pool)))
    lines.append("};")
    return "\n".join(lines)


def emit_source(data: bytes) -> str:
    """Return a C program that rebuilds ``data`` byte-for-byte."""
    if len(data) < HEADER_SIZE:
        raise ValueError("BNLL: file is shorter than the 8-byte header")
    magic, reserved, count = struct.unpack_from("<4sHH", data, 0)
    if magic != MAGIC:
        raise ValueError("BNLL: bad magic %r" % (magic,))
    pool_base = HEADER_SIZE + ELEMENT_SIZE * count
    if len(data) < pool_base:
        raise ValueError(
            "BNLL: %d bytes, need at least %d for %d labels"
            % (len(data), pool_base, count)
        )

    records = []
    for index in range(count):
        offset = HEADER_SIZE + ELEMENT_SIZE * index
        x, y = struct.unpack_from("<HH", data, offset)
        h_space, v_space = struct.unpack_from("<bb", data, offset + 4)
        style = struct.unpack_from("<H", data, offset + 6)[0]
        string_offset = struct.unpack_from("<I", data, offset + 8)[0]
        records.append((x, y, h_space, v_space, style, string_offset))

    # Every record points at a real NUL-terminated UTF-16LE string. Stock
    # files store the strings back to back from 8 + 12 * count to EOF.
    strings: Dict[int, List[int]] = {}
    for record in records:
        string_offset = record[5]
        if string_offset < pool_base or string_offset >= len(data):
            raise ValueError(
                "BNLL: string offset 0x%X outside pool at 0x%X"
                % (string_offset, pool_base)
            )
        if (string_offset - pool_base) % 2 != 0:
            raise ValueError(
                "BNLL: unaligned string offset 0x%X" % string_offset)
        units, _ = _read_utf16z(data, string_offset)
        strings[string_offset] = units

    # Prefer one static table per string. Fall back to a raw byte array when
    # the pool has gaps, overlaps or trailing bytes, so every input round-trips.
    ordered_offsets = sorted(strings)
    segments: List[Tuple[int, List[int]]] = []
    cursor = pool_base
    segmentable = True
    for string_offset in ordered_offsets:
        if string_offset != cursor:
            segmentable = False
            break
        units = strings[string_offset]
        segments.append((string_offset, units))
        cursor += 2 * len(units)
    if cursor != len(data):
        segmentable = False

    program = CProgram("ui_bnll", "JNLL/BNLL", "nitro/mkds/ui/bnll.h")
    program.add_decl("\n".join([
        "static const MkdsUiListHeader list_header = {",
        "    .magic = MKDS_UI_BNLL_MAGIC,",
        "    .reserved = %d," % reserved,
        "    .count = %d," % count,
        "};",
    ]))
    program.add_part("&list_header", "sizeof list_header")

    if records:
        lines = ["static const MkdsUiLabelElement labels[] = {"]
        for record in records:
            x, y, h_space, v_space, style, string_offset = record
            lines.extend([
                "    {",
                "        .x = %s," % coord_initializer(x),
                "        .y = %s," % coord_initializer(y),
                "        .h_space = %d," % h_space,
                "        .v_space = %d," % v_space,
                "        .style = %s," % style_initializer(style),
                "        .string_offset = %s," % hex32(string_offset),
                "    },",
            ])
        lines.append("};")
        program.add_decl("\n".join(lines))
        program.add_assert(
            "_Static_assert(sizeof labels / sizeof labels[0] == %d, "
            '"BNLL label count");' % count
        )
        program.add_array_part("labels")

    pool = data[pool_base:]
    if segmentable:
        for index, (string_offset, units) in enumerate(segments):
            program.add_comment(_string_comment(string_offset, units))
            program.add_decl(_string_declaration(index, units))
        for index in range(len(segments)):
            program.add_array_part("label_string_%d" % index)
    elif pool:
        program.add_comment(
            "raw string pool: not a contiguous NUL-terminated string sequence")
        program.add_decl(_pool_declaration(pool))
        program.add_array_part("string_pool")

    return program.render()
