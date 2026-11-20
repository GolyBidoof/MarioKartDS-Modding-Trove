# Mario Kart DS Modding Trove
# tools/ctables/generic/g2d_tables.py — typed C emitters for Nitro G2D resources
# SPDX-License-Identifier: MIT
"""Emit complete C programs that rebuild Nitro G2D resource bytes.

Every emitter takes an in-memory resource and returns one self-contained C
translation unit.  The program includes the real declarations from
``include/nitro/g2d.h``, spells out block headers and record arrays as typed
``static const`` objects, keeps bulk bitmap/tile data in static payload
arrays, and writes the rebuilt file to ``argv[1]``.

Offsets in comments are hexadecimal; block sizes, counts and strides are
decimal.  Packed words that the headers model as unions are emitted through
their ``.raw`` member so the C source never re-derives bit positions.

The emitters preserve the on-disk envelope verbatim, including legacy magic,
declared sizes that disagree with the real file length, unaligned blocks and
trailing bytes.  They do not require the resource to be semantically valid;
the only goal is byte-exact reconstruction for round-trip verification.
"""
from __future__ import annotations

import struct
from typing import Callable, Sequence

# Field kinds mirror the widths used by include/nitro/g2d/*.h.
_KIND_SIZES = {
    "magic4": 4,
    "u8": 1,
    "i8": 1,
    "u16": 2,
    "i16": 2,
    "u32": 4,
    "union32": 4,
}

Layout = Sequence[tuple[str, str]]

# Common envelope and shared extension block.
FILE_HEADER: Layout = (
    ("magic", "magic4"),
    ("byte_order", "u16"),
    ("version", "u16"),
    ("file_size", "u32"),
    ("header_size", "u16"),
    ("block_count", "u16"),
)
BLOCK_HEADER: Layout = (("magic", "magic4"), ("block_size", "u32"))
UEXT_BLOCK: Layout = (
    ("magic", "magic4"),
    ("block_size", "u32"),
    ("value", "u32"),
)

# NCGR.
NCGR_CHAR: Layout = (
    ("magic", "magic4"),
    ("block_size", "u32"),
    ("height", "u16"),
    ("width", "u16"),
    ("color_format", "u32"),
    ("mapping_type", "u32"),
    ("character_format", "union32"),
    ("data_size", "u32"),
    ("data_offset", "u32"),
)
NCGR_CPOS: Layout = (
    ("magic", "magic4"),
    ("block_size", "u32"),
    ("x", "u16"),
    ("y", "u16"),
    ("width", "u16"),
    ("height", "u16"),
)

# NCLR.
NCLR_PLTT: Layout = (
    ("magic", "magic4"),
    ("block_size", "u32"),
    ("palette_format", "u32"),
    ("extended", "u32"),
    ("data_size", "u32"),
    ("data_offset", "u32"),
)
NCLR_PCMP: Layout = (
    ("magic", "magic4"),
    ("block_size", "u32"),
    ("palette_count", "u16"),
    ("reserved", "u16"),
    ("index_offset", "u32"),
)

# NSCR.
NSCR_SCRN: Layout = (
    ("magic", "magic4"),
    ("block_size", "u32"),
    ("width", "u16"),
    ("height", "u16"),
    ("color_mode", "u16"),
    ("screen_format", "u16"),
    ("data_size", "u32"),
)

# NCER.
NCER_CEBK: Layout = (
    ("magic", "magic4"),
    ("block_size", "u32"),
    ("cell_count", "u16"),
    ("attributes", "u16"),
    ("cell_data_offset", "u32"),
    ("mapping_mode", "u32"),
    ("vram_transfer_offset", "u32"),
    ("string_bank", "u32"),
    ("extended_data", "u32"),
)
NCER_CELL: Layout = (
    ("oam_count", "u16"),
    ("attributes", "u16"),
    ("oam_offset", "u32"),
)
NCER_CELL_BBOX: Layout = (
    ("oam_count", "u16"),
    ("attributes", "u16"),
    ("oam_offset", "u32"),
    ("max_x", "i16"),
    ("max_y", "i16"),
    ("min_x", "i16"),
    ("min_y", "i16"),
)

# NANR.
NANR_KNBA: Layout = (
    ("magic", "magic4"),
    ("block_size", "u32"),
    ("animation_count", "u16"),
    ("frame_count", "u16"),
    ("animation_offset", "u32"),
    ("frame_offset", "u32"),
    ("frame_data_offset", "u32"),
)
NANR_ANIMATION: Layout = (
    ("frame_count", "u16"),
    ("loop_start_frame", "u16"),
    ("animation_type", "union32"),
    ("play_mode", "u32"),
    ("first_frame_offset", "u32"),
)
NANR_FRAME: Layout = (
    ("data_offset", "u32"),
    ("duration", "u16"),
    ("reserved", "u16"),
)

# NFTR.
NFTR_INFO: Layout = (
    ("magic", "magic4"),
    ("block_size", "u32"),
    ("font_type", "u8"),
    ("line_feed", "u8"),
    ("alternate_index", "u16"),
    ("default_left", "i8"),
    ("default_glyph_width", "u8"),
    ("default_char_width", "i8"),
    ("encoding", "u8"),
    ("glyph_offset", "u32"),
    ("width_offset", "u32"),
    ("code_map_offset", "u32"),
)
NFTR_INFO_OLD: Layout = (
    ("magic", "magic4"),
    ("block_size", "u32"),
    ("font_type", "u8"),
    ("line_feed", "u8"),
    ("alternate_index", "u16"),
    ("default_left", "i8"),
    ("default_glyph_width", "u8"),
    ("encoding", "u8"),
    ("reserved", "u8"),
    ("glyph_offset", "u32"),
    ("width_offset", "u32"),
    ("code_map_offset", "u32"),
)
NFTR_GLYPH: Layout = (
    ("magic", "magic4"),
    ("block_size", "u32"),
    ("cell_width", "u8"),
    ("cell_height", "u8"),
    ("cell_size", "u16"),
    ("baseline", "i8"),
    ("max_char_width", "u8"),
    ("bpp", "u8"),
    ("reserved", "u8"),
)
NFTR_WIDTH: Layout = (
    ("magic", "magic4"),
    ("block_size", "u32"),
    ("index_begin", "u16"),
    ("index_end", "u16"),
    ("next_offset", "u32"),
)
NFTR_CHAR_WIDTH: Layout = (
    ("left", "i8"),
    ("width", "u8"),
    ("advance", "i8"),
)
NFTR_CHAR_WIDTH_OLD: Layout = (("left", "i8"), ("width", "u8"))
NFTR_CODE_MAP: Layout = (
    ("magic", "magic4"),
    ("block_size", "u32"),
    ("code_begin", "u16"),
    ("code_end", "u16"),
    ("mapping_method", "u16"),
    ("reserved", "u16"),
    ("next_offset", "u32"),
)
NFTR_SCAN_ENTRY: Layout = (("character_code", "u16"), ("glyph_index", "u16"))


def _u16(data: bytes, offset: int) -> int:
    return struct.unpack_from("<H", data, offset)[0]


def _u32(data: bytes, offset: int) -> int:
    return struct.unpack_from("<I", data, offset)[0]


def _layout_size(layout: Layout) -> int:
    return sum(_KIND_SIZES[kind] for _, kind in layout)


def _field_value(kind: str, data: bytes, offset: int) -> str:
    if kind == "magic4":
        return "{" + ", ".join(_c_char(b) for b in data[offset:offset + 4]) + "}"
    if kind == "u8":
        return f"0x{data[offset]:02X}"
    if kind == "i8":
        return str(struct.unpack_from("<b", data, offset)[0])
    if kind == "u16":
        return f"0x{_u16(data, offset):04X}u"
    if kind == "i16":
        return str(struct.unpack_from("<h", data, offset)[0])
    if kind == "u32":
        return f"0x{_u32(data, offset):08X}u"
    if kind == "union32":
        return f"{{ .raw = 0x{_u32(data, offset):08X}u }}"
    raise ValueError(f"unknown field kind {kind}")


def _c_char(value: int) -> str:
    if 0x20 <= value < 0x7F and value not in (ord("'"), ord("\\")):
        return repr(chr(value))
    return f"0x{value:02X}"


def _struct_initializer(layout: Layout, data: bytes, indent: str = "    ") -> str:
    if len(data) != _layout_size(layout):
        raise ValueError("struct slice does not match its declared layout")
    lines = ["{"]
    offset = 0
    for name, kind in layout:
        value = _field_value(kind, data, offset)
        lines.append(f"{indent}.{name} = {value},")
        offset += _KIND_SIZES[kind]
    lines.append(indent[:-4] + "}")
    return "\n".join(lines)


def _byte_array(var: str, data: bytes, indent: str = "    ") -> str:
    lines = [f"static const uint8_t {var}[{len(data)}] = {{"]
    for base in range(0, len(data), 12):
        chunk = data[base:base + 12]
        values = ", ".join(f"0x{value:02X}" for value in chunk)
        lines.append(f"{indent}{values},")
    lines.append("};")
    return "\n".join(lines)


def _u16_array(var: str, data: bytes, count: int, indent: str = "    ") -> str:
    lines = [f"static const uint16_t {var}[{count}] = {{"]
    for base in range(0, count * 2, 32):
        values = [
            f"0x{_u16(data, base + index):04X}u"
            for index in range(0, min(32, count * 2 - base), 2)
        ]
        lines.append(f"{indent}{', '.join(values)},")
    lines.append("};")
    return "\n".join(lines)


def _struct_array(var: str, type_name: str, layout: Layout,
                  data: bytes, count: int) -> str:
    size = _layout_size(layout)
    if count < 0 or len(data) < count * size:
        raise ValueError("struct array slice is too short")
    lines = [f"static const {type_name} {var}[{count}] = {{"]
    for index in range(count):
        start = index * size
        body = _struct_initializer(layout, data[start:start + size], "        ")
        lines.append(f"    {body},")
    lines.append("};")
    return "\n".join(lines)


class _Builder:
    """Collect declarations and the matching write sequence."""

    def __init__(self) -> None:
        self.declarations: list[str] = []
        self.writes: list[str] = []

    def add_struct(self, var: str, type_name: str, layout: Layout,
                   data: bytes) -> None:
        self.declarations.append(
            f"static const {type_name} {var} = "
            f"{_struct_initializer(layout, data)};")
        self.writes.append(var)

    def add_struct_array(self, var: str, type_name: str, layout: Layout,
                         data: bytes, count: int) -> None:
        if not count:
            return
        self.declarations.append(
            _struct_array(var, type_name, layout, data, count))
        self.writes.append(var)

    def add_bytes(self, var: str, data: bytes) -> None:
        if not data:
            return
        self.declarations.append(_byte_array(var, data))
        self.writes.append(var)

    def add_u16(self, var: str, value: int) -> None:
        self.declarations.append(
            f"static const uint16_t {var} = 0x{value:04X}u;")
        self.writes.append(var)

    def add_u16_array(self, var: str, data: bytes, count: int) -> None:
        if not count:
            return
        self.declarations.append(_u16_array(var, data, count))
        self.writes.append(var)

    def merge(self, other: "_Builder") -> None:
        self.declarations.extend(other.declarations)
        self.writes.extend(other.writes)


def _fallback_block(builder: _Builder, prefix: str, block: bytes) -> None:
    """Emit an unmodelled block as its typed envelope plus a payload array."""
    builder.add_struct(f"{prefix}_header", "G2dBlockHeader",
                       BLOCK_HEADER, block[:8])
    builder.add_bytes(f"{prefix}_payload", block[8:])


def _plain_block(builder: _Builder, prefix: str, block: bytes) -> None:
    if len(block) == 12 and block[:4] == b"TXEU":
        builder.add_struct(f"{prefix}_uext", "G2dUextBlock",
                           UEXT_BLOCK, block)
        return
    _fallback_block(builder, prefix, block)


def _blocks(data: bytes) -> tuple[int, int, list[tuple[int, bytes]], bytes]:
    """Return (header_size, block_count, blocks, trailing_bytes).

    Blocks are walked by their declared size.  A truncated or nonsensical size
    stops the walk so the unparsed remainder can be kept verbatim.
    """
    header_size = _u16(data, 0x0C)
    block_count = _u16(data, 0x0E)
    if header_size < 0x10:
        return header_size, block_count, [], data[0x10:]
    offset = header_size
    blocks: list[tuple[int, bytes]] = []
    for _ in range(block_count):
        if offset + 8 > len(data):
            break
        size = _u32(data, offset + 4)
        if size < 8 or offset + size > len(data):
            break
        blocks.append((offset, data[offset:offset + size]))
        offset += size
    return header_size, block_count, blocks, data[offset:]


def _emit_ncgr_block(builder: _Builder, prefix: str, block: bytes) -> None:
    magic = block[:4]
    if magic == b"RAHC" and len(block) >= 32:
        builder.add_struct(f"{prefix}_char", "NcgrCharBlock",
                           NCGR_CHAR, block[:32])
        builder.add_bytes(f"{prefix}_char_data", block[32:])
        return
    if magic == b"SOPC" and len(block) >= 16:
        builder.add_struct(f"{prefix}_cpos", "NcgrCposBlock",
                           NCGR_CPOS, block[:16])
        builder.add_bytes(f"{prefix}_cpos_data", block[16:])
        return
    _plain_block(builder, prefix, block)


def _emit_nclr_block(builder: _Builder, prefix: str, block: bytes) -> None:
    magic = block[:4]
    if magic == b"TTLP" and len(block) >= 24:
        builder.add_struct(f"{prefix}_pltt", "NclrPlttBlock",
                           NCLR_PLTT, block[:24])
        builder.add_bytes(f"{prefix}_palette", block[24:])
        return
    if magic == b"PMCP" and len(block) >= 16:
        builder.add_struct(f"{prefix}_pcmp", "NclrPcmpBlock",
                           NCLR_PCMP, block[:16])
        count = _u16(block, 0x08)
        index_base = 0x08 + _u32(block, 0x0C)
        if 0x10 <= index_base <= len(block):
            builder.add_bytes(f"{prefix}_pcmp_gap", block[0x10:index_base])
            region = block[index_base:]
            if count and count * 2 <= len(region):
                builder.add_u16_array(f"{prefix}_pcmp_indices", region, count)
                builder.add_bytes(f"{prefix}_pcmp_tail",
                                  region[count * 2:])
            else:
                builder.add_bytes(f"{prefix}_pcmp_indices_raw", region)
        else:
            builder.add_bytes(f"{prefix}_pcmp_payload", block[0x10:])
        return
    _plain_block(builder, prefix, block)


def _emit_nscr_block(builder: _Builder, prefix: str, block: bytes) -> None:
    if block[:4] == b"NRCS" and len(block) >= 20:
        builder.add_struct(f"{prefix}_scrn", "NscrScreenBlock",
                           NSCR_SCRN, block[:20])
        payload = block[20:]
        count = len(payload) // 2
        builder.add_u16_array(f"{prefix}_entries", payload, count)
        builder.add_bytes(f"{prefix}_entries_tail", payload[count * 2:])
        return
    _plain_block(builder, prefix, block)


def _emit_ncer_block(builder: _Builder, prefix: str, block: bytes) -> None:
    magic = block[:4]
    if magic == b"KBEC" and len(block) >= 32:
        builder.add_struct(f"{prefix}_cebk", "NcerCebkHeader",
                           NCER_CEBK, block[:32])
        count = _u16(block, 0x08)
        attributes = _u16(block, 0x0A)
        cell_base = 0x08 + _u32(block, 0x0C)
        layout = NCER_CELL_BBOX if attributes & 1 else NCER_CELL
        type_name = "NcerCellBbox" if attributes & 1 else "NcerCell"
        stride = _layout_size(layout)
        end = cell_base + count * stride
        if count and 0x20 <= cell_base and end <= len(block):
            builder.add_bytes(f"{prefix}_cell_gap", block[0x20:cell_base])
            builder.add_struct_array(f"{prefix}_cells", type_name, layout,
                                     block[cell_base:end], count)
            builder.add_bytes(f"{prefix}_oam", block[end:])
        elif not count and 0x20 <= cell_base <= len(block):
            builder.add_bytes(f"{prefix}_cell_gap", block[0x20:cell_base])
            builder.add_bytes(f"{prefix}_oam", block[cell_base:])
        else:
            builder.add_bytes(f"{prefix}_payload", block[0x20:])
        return
    if magic == b"LBAL" and len(block) >= 8:
        builder.add_struct(f"{prefix}_labl", "G2dBlockHeader",
                           BLOCK_HEADER, block[:8])
        builder.add_bytes(f"{prefix}_labels", block[8:])
        return
    _plain_block(builder, prefix, block)


def _emit_nanr_block(builder: _Builder, prefix: str, block: bytes) -> None:
    magic = block[:4]
    if magic == b"KNBA" and len(block) >= 24:
        builder.add_struct(f"{prefix}_knba", "NanrKnbaHeader",
                           NANR_KNBA, block[:24])
        animations = _u16(block, 0x08)
        frames = _u16(block, 0x0A)
        animation_base = 0x08 + _u32(block, 0x0C)
        frame_base = 0x08 + _u32(block, 0x10)
        data_base = 0x08 + _u32(block, 0x14)
        animation_end = animation_base + animations * 16
        frame_end = frame_base + frames * 8
        if (0x18 <= animation_base <= frame_base <= data_base <= len(block)
                and animation_end <= frame_base
                and frame_end <= data_base):
            builder.add_bytes(f"{prefix}_knba_pad", block[0x18:animation_base])
            builder.add_struct_array(
                f"{prefix}_animations", "NanrAnimation",
                NANR_ANIMATION, block[animation_base:animation_end],
                animations)
            builder.add_bytes(f"{prefix}_animation_gap",
                              block[animation_end:frame_base])
            builder.add_struct_array(
                f"{prefix}_frames", "NanrFrame", NANR_FRAME,
                block[frame_base:frame_end], frames)
            builder.add_bytes(f"{prefix}_frame_gap",
                              block[frame_end:data_base])
            builder.add_bytes(f"{prefix}_frame_data", block[data_base:])
        else:
            builder.add_bytes(f"{prefix}_payload", block[0x18:])
        return
    if magic == b"LBAL" and len(block) >= 8:
        builder.add_struct(f"{prefix}_labl", "G2dBlockHeader",
                           BLOCK_HEADER, block[:8])
        builder.add_bytes(f"{prefix}_labels", block[8:])
        return
    _plain_block(builder, prefix, block)


def _emit_nftr_block(builder: _Builder, prefix: str, block: bytes,
                     version: int) -> None:
    magic = block[:4]
    if magic == b"FNIF" and len(block) >= 28:
        layout = NFTR_INFO_OLD if version == 0x0001 else NFTR_INFO
        type_name = ("NftrInfoBlockOld" if version == 0x0001
                     else "NftrInfoBlock")
        builder.add_struct(f"{prefix}_finf", type_name, layout, block[:28])
        builder.add_bytes(f"{prefix}_finf_tail", block[28:])
        return
    if magic == b"PLGC" and len(block) >= 16:
        builder.add_struct(f"{prefix}_cglp", "NftrGlyphBlock",
                           NFTR_GLYPH, block[:16])
        builder.add_bytes(f"{prefix}_glyphs", block[16:])
        return
    if magic == b"HDWC" and len(block) >= 16:
        builder.add_struct(f"{prefix}_cwdh", "NftrWidthBlock",
                           NFTR_WIDTH, block[:16])
        payload = block[16:]
        if version == 0x0001:
            entry_layout = NFTR_CHAR_WIDTH_OLD
            entry_type = "NftrCharWidthOld"
            entry_size = 2
        else:
            entry_layout = NFTR_CHAR_WIDTH
            entry_type = "NftrCharWidth"
            entry_size = 3
        count = len(payload) // entry_size
        builder.add_struct_array(f"{prefix}_widths", entry_type,
                                 entry_layout, payload, count)
        builder.add_bytes(f"{prefix}_width_tail", payload[count * entry_size:])
        return
    if magic == b"PAMC" and len(block) >= 20:
        builder.add_struct(f"{prefix}_cmap", "NftrCodeMapBlock",
                           NFTR_CODE_MAP, block[:20])
        payload = block[20:]
        method = _u16(block, 0x0C)
        first = _u16(block, 0x08)
        last = _u16(block, 0x0A)
        if method == 0:
            if len(payload) >= 2:
                builder.add_u16(f"{prefix}_glyph_base", _u16(payload, 0))
                builder.add_bytes(f"{prefix}_cmap_tail", payload[2:])
            else:
                builder.add_bytes(f"{prefix}_cmap_payload", payload)
        elif method == 1:
            count = last - first + 1 if last >= first else 0
            if count and count * 2 <= len(payload):
                builder.add_u16_array(f"{prefix}_table", payload, count)
                builder.add_bytes(f"{prefix}_cmap_tail", payload[count * 2:])
            else:
                builder.add_bytes(f"{prefix}_cmap_payload", payload)
        elif method == 2:
            if len(payload) >= 2:
                count = _u16(payload, 0)
                if 2 + count * 4 <= len(payload):
                    builder.add_u16(f"{prefix}_scan_count", count)
                    builder.add_struct_array(
                        f"{prefix}_scan", "NftrScanEntry", NFTR_SCAN_ENTRY,
                        payload[2:], count)
                    builder.add_bytes(f"{prefix}_cmap_tail",
                                      payload[2 + count * 4:])
                else:
                    builder.add_bytes(f"{prefix}_cmap_payload", payload)
            else:
                builder.add_bytes(f"{prefix}_cmap_payload", payload)
        else:
            builder.add_bytes(f"{prefix}_cmap_payload", payload)
        return
    _plain_block(builder, prefix, block)


_BlockEmitter = Callable[[_Builder, str, bytes], None]
_NftrBlockEmitter = Callable[[_Builder, str, bytes, int], None]


def _emit(data: bytes, magic: bytes | tuple[bytes, ...], title: str,
          block_emitter: _BlockEmitter | _NftrBlockEmitter) -> str:
    accepted = (magic,) if isinstance(magic, bytes) else magic
    if len(data) < 16 or data[:4] not in accepted:
        raise ValueError(f"not a {title} file")

    builder = _Builder()
    builder.add_struct("file_header", "G2dFileHeader", FILE_HEADER, data[:16])
    header_size, block_count, blocks, trailing = _blocks(data)
    if header_size > 0x10:
        builder.add_bytes("header_extra", data[0x10:header_size])

    version = _u16(data, 0x06)
    for index, (offset, block) in enumerate(blocks):
        prefix = f"blk{index}"
        block_builder = _Builder()
        if block_emitter is _emit_nftr_block:
            block_emitter(block_builder, prefix, block, version)
        else:
            block_emitter(block_builder, prefix, block)
        if not block_builder.declarations:
            _fallback_block(block_builder, prefix, block)
        builder.merge(block_builder)
        builder.declarations.insert(
            len(builder.declarations) - len(block_builder.declarations),
            "")

    builder.add_bytes("trailer", trailing)
    builder.declarations.insert(
        0, f"/* {title}: {block_count} blocks, "
           f"{len(blocks)} parsed, {len(data)} file bytes */")

    write_lines = "\n".join(f"    PUT({name});" for name in builder.writes)
    declarations = "\n\n".join(builder.declarations)
    return f"""\
/* Mario Kart DS Modding Trove
 * Generated by tools/ctables/generic/g2d_tables.py — {title}
 * SPDX-License-Identifier: MIT
 *
 * Offsets in comments are hexadecimal; sizes and counts are decimal.
 */
#include <stdint.h>
#include <stdio.h>

#include "nitro/g2d.h"

{declarations}

#define PUT(value) do {{ \\
    if (fwrite(&(value), sizeof(value), 1, out) != 1) return 1; \\
}} while (0)

int main(int argc, char **argv) {{
    if (argc != 2) return 2;
    FILE *out = fopen(argv[1], "wb");
    if (!out) return 1;
{write_lines}
#undef PUT
    return fclose(out) != 0;
}}
"""


def emit_ncgr(data: bytes) -> str:
    """Emit a C program rebuilding an NCGR (CHAR + optional CPOS)."""
    return _emit(data, b"RGCN", "NCGR", _emit_ncgr_block)


def emit_nclr(data: bytes) -> str:
    """Emit a C program rebuilding an NCLR (PLTT + optional PCMP).

    Both the normal ``RLCN`` magic and the legacy ``RPCN`` alias are accepted.
    """
    return _emit(data, (b"RLCN", b"RPCN"), "NCLR", _emit_nclr_block)


def emit_nscr(data: bytes) -> str:
    """Emit a C program rebuilding an NSCR (SCRN)."""
    return _emit(data, b"RCSN", "NSCR", _emit_nscr_block)


def emit_ncer(data: bytes) -> str:
    """Emit a C program rebuilding an NCER (CEBK + optional LABL/UEXT)."""
    return _emit(data, b"RECN", "NCER", _emit_ncer_block)


def emit_nftr(data: bytes) -> str:
    """Emit a C program rebuilding an NFTR (FINF/CGLP/CWDH/CMAP chains)."""
    return _emit(data, b"RTFN", "NFTR", _emit_nftr_block)


def emit_nanr(data: bytes) -> str:
    """Emit a C program rebuilding an NANR (KNBA + optional LABL/UEXT)."""
    return _emit(data, b"RNAN", "NANR", _emit_nanr_block)


EMITTERS: dict[bytes, Callable[[bytes], str]] = {
    b"RGCN": emit_ncgr,
    b"RLCN": emit_nclr,
    b"RPCN": emit_nclr,
    b"RCSN": emit_nscr,
    b"RECN": emit_ncer,
    b"RTFN": emit_nftr,
    b"RNAN": emit_nanr,
}


def emit_source(data: bytes) -> str:
    """Dispatch on the four-byte resource magic."""
    if len(data) < 16:
        raise ValueError("G2D resource is shorter than its 16-byte header")
    try:
        emitter = EMITTERS[data[:4]]
    except KeyError as exc:
        raise ValueError(f"unknown G2D magic {data[:4]!r}") from exc
    return emitter(data)
