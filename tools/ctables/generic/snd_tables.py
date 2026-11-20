# Mario Kart DS Modding Trove
# tools/ctables/generic/snd_tables.py — typed C emitters for Nitro sound files
# SPDX-License-Identifier: MIT
# Format notes: docs/generic/formats-audio.md
"""Emit C programs that rebuild Nitro sound files byte-for-byte.

Each ``emit_*_source`` parses one file into typed header/record tables plus
static payload arrays and returns a complete C program.  The program includes
the real headers from ``include/nitro/snd/`` and writes the binary to argv[1].
``emit_source`` dispatches on the four-byte magic.

Formats: SDAT (SYMB/INFO/FAT/FILE), SSEQ, SSAR, SBNK, SWAR and SWAV.
Byte offsets are hexadecimal; sizes and counts are decimal.
"""
from __future__ import annotations

import struct
from typing import Iterable, Sequence

from tools.ctables.common.cnames import enum_name

# ---------------------------------------------------------------- parsing

def _u8(data: bytes, off: int) -> int:
    return data[off]


def _u16(data: bytes, off: int) -> int:
    return struct.unpack_from("<H", data, off)[0]


def _u32(data: bytes, off: int) -> int:
    return struct.unpack_from("<I", data, off)[0]


def _need(data: bytes, off: int, size: int, what: str) -> None:
    if off < 0 or size < 0 or off + size > len(data):
        raise ValueError(
            f"{what}: need {size} bytes at 0x{off:X}, file is {len(data)} bytes")


def _slice(data: bytes, off: int, size: int, what: str) -> bytes:
    _need(data, off, size, what)
    return data[off:off + size]


def _magic(data: bytes, off: int, expected: bytes, what: str) -> None:
    got = _slice(data, off, 4, what)
    if got != expected:
        raise ValueError(
            f"{what}: expected {expected!r} at 0x{off:X}, got {got!r}")

# ---------------------------------------------------------------- literals

def _hex(value: int) -> str:
    return f"0x{value:X}"


def _dec(value: int) -> str:
    return str(value)


def _swav_format(value: int) -> str:
    return enum_name("SwavFormat", value) or str(value)


def _player(value: int) -> str:
    if value == 8:
        return "MKDS_SND_PLAYER_RACE"
    if value == 9:
        return "MKDS_SND_PLAYER_JINGLE"
    return str(value)


def _c_magic(raw: bytes) -> str:
    """A char[4] initializer that never relies on a terminating NUL."""
    parts = []
    for byte in raw:
        if 0x20 <= byte <= 0x7E and byte not in (ord("'"), ord("\\")):
            parts.append(f"'{chr(byte)}'")
        else:
            parts.append(f"0x{byte:02X}")
    return "{ " + ", ".join(parts) + " }"


def _c_array(raw: bytes) -> str:
    """A byte-array initializer, abbreviated when every byte is zero."""
    if not raw or not any(raw):
        return "{ 0 }"
    return "{ " + ", ".join(f"0x{byte:02X}" for byte in raw) + " }"


def _is_zero(raw: bytes) -> bool:
    return not any(raw)

# ---------------------------------------------------------------- layout

class _Layout:
    """Collect typed declarations and place them at their exact offsets.

    Every segment is emitted once, in ascending file order.  Gaps between
    segments and the trailing bytes to ``total`` come from the source file when
    one is supplied, so unmodelled alignment padding still round-trips.
    """

    def __init__(self, total: int, source: bytes | None = None):
        self.total = total
        self.source = source
        self._decls: list[str] = []
        self._segments: list[tuple[int, int, str, bool, str]] = []
        self._names: set[str] = set()
        self._pads = 0

    def _claim(self, name: str) -> None:
        if name in self._names:
            raise ValueError(f"duplicate C symbol {name}")
        self._names.add(name)

    def _add(self, offset: int, size: int, name: str, struct_like: bool,
             comment: str) -> None:
        if offset < 0 or size < 0:
            raise ValueError(f"{name}: bad offset/size {offset}/{size}")
        if offset + size > self.total:
            raise ValueError(
                f"{name}: ends at 0x{offset + size:X}, file is {self.total} bytes")
        self._segments.append((offset, size, name, struct_like, comment))

    def add_struct(self, offset: int, ctype: str, fields: Sequence[tuple[str, str]],
                   comment: str = "", name: str | None = None) -> str:
        if name is None:
            name = _ident(comment or ctype).lower()
        self._claim(name)
        lines = []
        lines.append(f"static const {ctype} {name} = {{")
        for field, value in fields:
            lines.append(f"    .{field} = {value},")
        lines.append("};")
        self._decls.append("\n".join(lines))
        self._add(offset, struct_size(ctype), name, True, comment)
        return name

    def add_struct_array(self, offset: int, ctype: str, name: str,
                         rows: Sequence[str], comment: str = "",
                         count: int | None = None) -> str:
        self._claim(name)
        n = len(rows) if count is None else count
        if n == 0:
            raise ValueError(f"{name}: empty struct array")
        lines = []
        lines.append(f"static const {ctype} {name}[{n}] = {{")
        lines.extend(f"    {row}," for row in rows)
        lines.append("};")
        self._decls.append("\n".join(lines))
        self._add(offset, struct_size(ctype) * n, name, True, comment)
        return name

    def add_array(self, offset: int, ctype: str, name: str,
                  values: Iterable[str], comment: str = "") -> str:
        values = list(values)
        self._claim(name)
        if not values:
            raise ValueError(f"{name}: empty array")
        lines = []
        lines.append(f"static const {ctype} {name}[{len(values)}] = {{")
        lines.extend(f"    {value}," for value in values)
        lines.append("};")
        self._decls.append("\n".join(lines))
        size = type_size(ctype) * len(values)
        self._add(offset, size, name, False, comment)
        return name

    def add_raw(self, offset: int, payload: bytes, name: str,
                comment: str = "") -> str | None:
        if not payload:
            return None
        self._claim(name)
        lines = []
        lines.append(f"static const uint8_t {name}[{len(payload)}] = {{")
        for start in range(0, len(payload), 16):
            chunk = payload[start:start + 16]
            lines.append("    " + ", ".join(f"0x{byte:02X}" for byte in chunk) + ",")
        lines.append("};")
        self._decls.append("\n".join(lines))
        self._add(offset, len(payload), name, False, comment)
        return name

    def build(self, include: str | Sequence[str], title: str) -> str:
        segments = sorted(self._segments, key=lambda item: item[0])
        pads: list[str] = []
        writes: list[str] = []
        cursor = 0

        def pad_to(offset: int) -> None:
            nonlocal cursor
            if offset < cursor:
                raise ValueError(
                    f"segments overlap at 0x{cursor:X}: next starts at 0x{offset:X}")
            if offset > cursor:
                name = f"pad_bytes_{self._pads}"
                self._pads += 1
                raw = (self.source[cursor:offset]
                       if self.source is not None else b"")
                pads.append(
                    f"static const uint8_t {name}[{offset - cursor}] = {_c_array(raw)};")
                writes.append(f"fwrite({name}, 1, sizeof {name}, out);")
            cursor = offset

        for offset, _size, name, struct_like, _comment in segments:
            pad_to(offset)
            if struct_like:
                writes.append(f"fwrite(&{name}, 1, sizeof {name}, out);")
            else:
                writes.append(f"fwrite({name}, 1, sizeof {name}, out);")
            cursor = offset + _size

        pad_to(self.total)
        if cursor != self.total:
            raise ValueError(
                f"{title}: layout ends at 0x{cursor:X}, expected 0x{self.total:X}")

        includes = [include] if isinstance(include, str) else list(include)
        include_lines = "\n".join(f'#include "{name}"' for name in includes)
        declarations = "\n\n".join(self._decls + pads)
        body = "\n".join(f"    {line}" for line in writes)
        return f"""\
/* Mario Kart DS Modding Trove
 * Generated by tools/ctables/generic/snd_tables.py — {title}
 * SPDX-License-Identifier: MIT
 * Build: cc -std=c11 -I include FILE.c -o FILE && ./FILE OUT.bin
 */
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>

{include_lines}

{declarations}

int main(int argc, char **argv)
{{
    if (argc != 2) {{
        fprintf(stderr, "usage: %s OUT.bin\\n", argv[0]);
        return 2;
    }}
    FILE *out = fopen(argv[1], "wb");
    if (out == NULL) {{
        perror(argv[1]);
        return 1;
    }}
{body}
    if (fclose(out) != 0) {{
        perror(argv[1]);
        return 1;
    }}
    return 0;
}}
"""


_STRUCT_SIZES = {
    "SndFileHeader": 16,
    "SndDataBlockHeader": 8,
    "SseqDataBlock": 12,
    "SsarDataBlock": 16,
    "SsarEntry": 12,
    "SbnkDataBlock": 44,
    "SbnkInstrumentEntry": 4,
    "SbnkNote": 10,
    "SbnkTypedNote": 12,
    "SbnkRangeHeader": 2,
    "SbnkRegionalHeader": 8,
    "SwarDataBlock": 44,
    "SwavParam": 12,
    "SwavDataBlock": 20,
    "SdatBlockRef": 8,
    "SdatHeader": 64,
    "SdatSymbHeader": 64,
    "SdatSymbRecord": 4,
    "SdatSymbArchiveEntry": 8,
    "SdatInfoHeader": 64,
    "SdatInfoTable": 4,
    "SdatSeqInfo": 12,
    "SdatSeqArcInfo": 4,
    "SdatBankInfo": 12,
    "SdatWaveArcInfo": 4,
    "SdatPlayerInfo": 8,
    "SdatGroupItem": 8,
    "SdatGroupInfo": 4,
    "SdatStreamPlayerInfo": 17,
    "SdatStreamInfo": 12,
    "SdatFatHeader": 12,
    "SdatFatEntry": 16,
    "SdatFileHeader": 12,
}

_TYPE_SIZES = {"uint8_t": 1, "uint16_t": 2, "uint32_t": 4, "int16_t": 2}


def struct_size(ctype: str) -> int:
    try:
        return _STRUCT_SIZES[ctype]
    except KeyError as exc:
        raise ValueError(f"unknown struct type {ctype}") from exc


def type_size(ctype: str) -> int:
    try:
        return _TYPE_SIZES[ctype]
    except KeyError as exc:
        raise ValueError(f"unknown scalar type {ctype}") from exc


def _ident(text: str) -> str:
    out = []
    for char in text:
        out.append(char.lower() if char.isalnum() else "_")
    name = "".join(out).strip("_")
    while "__" in name:
        name = name.replace("__", "_")
    return name or "item"

# ---------------------------------------------------------------- common

def _emit_file_header(layout: _Layout, data: bytes) -> None:
    layout.add_struct(0, "SndFileHeader", [
        ("magic", _c_magic(data[0:4])),
        ("bom", _hex(_u16(data, 4))),
        ("version", _hex(_u16(data, 6))),
        ("file_size", _dec(_u32(data, 8))),
        ("header_size", _dec(_u16(data, 12))),
        ("block_count", _dec(_u16(data, 14))),
    ], "Nitro sound file header", name="snd_file_header")


def _block_literal(data: bytes, off: int) -> str:
    return "{ %s, %d }" % (_c_magic(data[off:off + 4]), _u32(data, off + 4))


def _check_file_header(data: bytes, magic: bytes, what: str) -> None:
    _need(data, 0, 16, what)
    _magic(data, 0, magic, what)

# ---------------------------------------------------------------- SSEQ

def emit_sseq_source(data: bytes) -> str:
    """SSEQ: file header, DATA block and the SMFT stream."""
    _check_file_header(data, b"SSEQ", "SSEQ")
    _need(data, 0x10, 12, "SSEQ DATA block")
    data_offset = _u32(data, 0x18)
    if data_offset < 0x1C:
        raise ValueError(f"SSEQ data offset 0x{data_offset:X} overlaps the block header")
    _need(data, data_offset, 0, "SSEQ stream")

    layout = _Layout(len(data), data)
    _emit_file_header(layout, data)
    layout.add_struct(0x10, "SseqDataBlock", [
        ("block", _block_literal(data, 0x10)),
        ("data_offset", _hex(data_offset)),
    ], "SSEQ DATA block", name="sseq_data_block")
    layout.add_raw(data_offset, data[data_offset:], "sseq_smft_stream",
                   "SMFT command stream")
    return layout.build("nitro/snd/sseq.h", "SSEQ")

# ---------------------------------------------------------------- SSAR

def emit_ssar_source(data: bytes) -> str:
    """SSAR: file header, DATA block, entry table and archived SMFT streams."""
    _check_file_header(data, b"SSAR", "SSAR")
    _need(data, 0x10, 16, "SSAR DATA block")
    data_offset = _u32(data, 0x18)
    count = _u32(data, 0x1C)
    table_end = 0x20 + count * 12
    _need(data, 0x20, count * 12, "SSAR entries")
    if table_end > data_offset:
        raise ValueError(
            f"SSAR entry table ends at 0x{table_end:X}, past data offset 0x{data_offset:X}")

    layout = _Layout(len(data), data)
    _emit_file_header(layout, data)
    layout.add_struct(0x10, "SsarDataBlock", [
        ("block", _block_literal(data, 0x10)),
        ("data_offset", _hex(data_offset)),
        ("count", _dec(count)),
    ], "SSAR DATA block", name="ssar_data_block")

    rows = []
    for index in range(count):
        off = 0x20 + index * 12
        rows.append(
            "{ .offset = %s, .bank = %d, .volume = %d, "
            ".channel_priority = %d, .player_priority = %d, "
            ".player = %d, .reserved = %d }" % (
                _hex(_u32(data, off)), _u16(data, off + 4),
                _u8(data, off + 6), _u8(data, off + 7),
                _u8(data, off + 8), _u8(data, off + 9),
                _u16(data, off + 10)))
    if count:
        layout.add_struct_array(
            0x20, "SsarEntry", "ssar_entries", rows,
            "entry: offset (relative), bank, volume, channel priority, "
            "player priority, player, reserved")

    layout.add_raw(data_offset, data[data_offset:], "ssar_streams",
                   "archived SMFT streams")
    return layout.build("nitro/snd/ssar.h", "SSAR")

# ---------------------------------------------------------------- SBNK

def _sbnk_note_fields(data: bytes, off: int) -> list[tuple[str, str]]:
    return [
        ("wave", _dec(_u16(data, off))),
        ("wave_archive", _dec(_u16(data, off + 2))),
        ("pitch", _dec(_u8(data, off + 4))),
        ("attack", _dec(_u8(data, off + 5))),
        ("decay", _dec(_u8(data, off + 6))),
        ("sustain", _dec(_u8(data, off + 7))),
        ("release", _dec(_u8(data, off + 8))),
        ("pan", _dec(_u8(data, off + 9))),
    ]


def _sbnk_note_literal(data: bytes, off: int) -> str:
    return "{ " + ", ".join(f".{field} = {value}"
                            for field, value in _sbnk_note_fields(data, off)) + " }"


def _sbnk_typed_note_row(data: bytes, off: int) -> str:
    return "{ .type = %d, .reserved = %d, .note = %s }" % (
        _u8(data, off), _u8(data, off + 1), _sbnk_note_literal(data, off + 2))


def _sbnk_payload_plan(data: bytes, table_end: int, count: int):
    """Describe typed payloads, or return None when the area is not tiled.

    Instrument payloads can repeat variable-length regional sets, so the plan
    is only used when every byte from ``table_end`` onwards is accounted for by
    a known type or by zero padding.
    """
    by_offset: dict[int, tuple[int, int]] = {}
    for index in range(count):
        off = 0x3C + index * 4
        kind = _u8(data, off)
        payload = _u16(data, off + 1)
        if payload == 0:
            continue
        if payload in by_offset and by_offset[payload][0] != kind:
            return None
        by_offset.setdefault(payload, (kind, index))

    plan = []
    offsets = sorted(by_offset)
    cursor = table_end
    for position, offset in enumerate(offsets):
        if offset < cursor or not _is_zero(data[cursor:offset]):
            return None
        kind, entry = by_offset[offset]
        end = offsets[position + 1] if position + 1 < len(offsets) else len(data)
        if offset >= end:
            return None
        span = data[offset:end]
        if 1 <= kind <= 15:
            if len(span) < 10 or not _is_zero(span[10:]):
                return None
            plan.append(("note", offset, entry, None))
            cursor = offset + 10
        elif kind == 0x10:
            if len(span) < 2:
                return None
            first, last = span[0], span[1]
            if first > last:
                return None
            need = 2 + (last - first + 1) * 12
            if len(span) < need or not _is_zero(span[need:]):
                return None
            plan.append(("range", offset, entry, (first, last)))
            cursor = offset + need
        elif kind == 0x11:
            sets = []
            inner = 0
            while inner + 8 <= len(span):
                if _is_zero(span[inner:]):
                    break
                keys = span[inner:inner + 8]
                notes = sum(1 for key in keys if key)
                need = 8 + notes * 12
                if inner + need > len(span):
                    return None
                sets.append((inner, keys, notes))
                inner += need
            if not sets or not _is_zero(span[inner:]):
                return None
            plan.append(("regional", offset, entry, sets))
            cursor = offset + inner
        else:
            return None
    if not _is_zero(data[cursor:]):
        return None
    return plan


def _emit_sbnk_payload(layout: _Layout, data: bytes, plan) -> None:
    for kind, offset, entry, extra in plan:
        stem = f"sbnk_instrument_{entry:04d}"
        if kind == "note":
            layout.add_struct(offset, "SbnkNote", _sbnk_note_fields(data, offset),
                              f"entry {entry} note", name=f"{stem}_note")
        elif kind == "range":
            first, last = extra
            layout.add_struct(offset, "SbnkRangeHeader", [
                ("first_key", _dec(first)),
                ("last_key", _dec(last)),
            ], f"entry {entry} key range", name=f"{stem}_range")
            rows = [_sbnk_typed_note_row(data, offset + 2 + index * 12)
                    for index in range(last - first + 1)]
            layout.add_struct_array(
                offset + 2, "SbnkTypedNote", f"{stem}_range_notes", rows,
                "range notes")
        else:
            for index, (inner, keys, notes) in enumerate(extra):
                set_offset = offset + inner
                layout.add_struct(set_offset, "SbnkRegionalHeader", [
                    ("last_key", _c_array(keys)),
                ], f"entry {entry} region {index}", name=f"{stem}_region_{index}")
                if notes:
                    rows = [_sbnk_typed_note_row(data, set_offset + 8 + note * 12)
                            for note in range(notes)]
                    layout.add_struct_array(
                        set_offset + 8, "SbnkTypedNote",
                        f"{stem}_region_{index}_notes", rows,
                        "regional notes")


def emit_sbnk_source(data: bytes) -> str:
    """SBNK: file header, DATA block, instrument entries and payloads."""
    _check_file_header(data, b"SBNK", "SBNK")
    _need(data, 0x10, 44, "SBNK DATA block")
    count = _u32(data, 0x38)
    table_end = 0x3C + count * 4
    _need(data, 0x3C, count * 4, "SBNK instrument entries")

    layout = _Layout(len(data), data)
    _emit_file_header(layout, data)
    layout.add_struct(0x10, "SbnkDataBlock", [
        ("block", _block_literal(data, 0x10)),
        ("reserved", _c_array(data[0x18:0x38])),
        ("instrument_count", _dec(count)),
    ], "SBNK DATA block", name="sbnk_data_block")

    rows = []
    for index in range(count):
        off = 0x3C + index * 4
        rows.append(
            "{ .type = %d, .offset = { %s, %s }, .reserved = %d }" % (
                _u8(data, off), _hex(_u8(data, off + 1)),
                _hex(_u8(data, off + 2)), _u8(data, off + 3)))
    if count:
        layout.add_struct_array(
            0x3C, "SbnkInstrumentEntry", "sbnk_instruments", rows,
            "type, little-endian payload offset, reserved")

    plan = _sbnk_payload_plan(data, table_end, count)
    if plan is None:
        layout.add_raw(table_end, data[table_end:], "sbnk_payload",
                       "instrument payloads (notes, ranges, regions)")
    else:
        _emit_sbnk_payload(layout, data, plan)
    return layout.build("nitro/snd/sbnk.h", "SBNK")

# ---------------------------------------------------------------- SWAR

def _swar_waves(data: bytes, table_end: int) -> list[tuple[int, int, int]]:
    """Return (file offset, sample offset, sample bytes) per unique wave."""
    count = _u32(data, 0x38)
    offsets = [_u32(data, 0x3C + index * 4) for index in range(count)]
    seen: set[int] = set()
    waves = []
    for offset in offsets:
        if offset == 0 or offset in seen:
            continue
        seen.add(offset)
        _need(data, offset, 12, "SWAR wave parameter")
        loop_start = _u16(data, offset + 6)
        loop_length = _u32(data, offset + 8)
        sample_bytes = (loop_start + loop_length) * 4
        _need(data, offset + 12, sample_bytes, "SWAR wave samples")
        waves.append((offset, offset + 12, sample_bytes))
    waves.sort()
    return waves


def _swar_typed_ok(data: bytes, table_end: int,
                   waves: Sequence[tuple[int, int, int]]) -> bool:
    cursor = table_end
    for offset, _sample_off, sample_bytes in waves:
        if offset < cursor or not _is_zero(data[cursor:offset]):
            return False
        cursor = offset + 12 + sample_bytes
    return cursor <= len(data) and _is_zero(data[cursor:])


def emit_swar_source(data: bytes) -> str:
    """SWAR: file header, DATA block, offset table, SWAV params and samples."""
    _check_file_header(data, b"SWAR", "SWAR")
    _need(data, 0x10, 44, "SWAR DATA block")
    count = _u32(data, 0x38)
    table_end = 0x3C + count * 4
    _need(data, 0x3C, count * 4, "SWAR wave offsets")
    waves = _swar_waves(data, table_end)

    layout = _Layout(len(data), data)
    _emit_file_header(layout, data)
    layout.add_struct(0x10, "SwarDataBlock", [
        ("block", _block_literal(data, 0x10)),
        ("reserved", _c_array(data[0x18:0x38])),
        ("wave_count", _dec(count)),
    ], "SWAR DATA block", name="swar_data_block")

    if count:
        layout.add_array(
            0x3C, "uint32_t", "swar_wave_offsets",
            (_hex(_u32(data, 0x3C + index * 4)) for index in range(count)),
            "absolute wave offsets")

    if waves and _swar_typed_ok(data, table_end, waves):
        for index, (offset, sample_off, sample_bytes) in enumerate(waves):
            layout.add_struct(offset, "SwavParam", [
                ("format", _swav_format(_u8(data, offset))),
                ("loop", _dec(_u8(data, offset + 1))),
                ("sample_rate", _dec(_u16(data, offset + 2))),
                ("time", _dec(_u16(data, offset + 4))),
                ("loop_start", _dec(_u16(data, offset + 6))),
                ("loop_length", _dec(_u32(data, offset + 8))),
            ], f"wave {index} parameter", name=f"swar_wave_{index:04d}_param")
            layout.add_raw(sample_off, data[sample_off:sample_off + sample_bytes],
                           f"swar_wave_{index:04d}_samples",
                           f"wave {index} samples")
    else:
        layout.add_raw(table_end, data[table_end:], "swar_payload",
                       "wave parameters and samples")

    return layout.build(["nitro/snd/swar.h", "nitro/snd/swav.h"], "SWAR")

# ---------------------------------------------------------------- SWAV

def emit_swav_source(data: bytes) -> str:
    """Standalone SWAV: file header, DATA block, parameter and samples."""
    _check_file_header(data, b"SWAV", "SWAV")
    _need(data, 0x10, 20, "SWAV DATA block")
    layout = _Layout(len(data), data)
    _emit_file_header(layout, data)
    param = 0x18
    layout.add_struct(0x10, "SwavDataBlock", [
        ("block", _block_literal(data, 0x10)),
        ("param", "{ .format = %s, .loop = %d, .sample_rate = %d, "
                  ".time = %d, .loop_start = %d, .loop_length = %d }" % (
                      _u8(data, param), _u8(data, param + 1),
                      _u16(data, param + 2), _u16(data, param + 4),
                      _u16(data, param + 6), _u32(data, param + 8))),
    ], "SWAV DATA block and parameter", name="swav_data_block")
    layout.add_raw(0x24, data[0x24:], "swav_samples", "wave samples")
    return layout.build("nitro/snd/swav.h", "SWAV")

# ---------------------------------------------------------------- SDAT

_INFO_SECTIONS = (
    ("seq", "SEQ", 12),
    ("seqarc", "SEQARC", 4),
    ("bank", "BANK", 12),
    ("wavearc", "WAVEARC", 4),
    ("player", "PLAYER", 8),
    ("group", "GROUP", None),
    ("stream_player", "STREAM PLAYER", 17),
    ("stream", "STREAM", 12),
)


def _sdat_blocks(data: bytes) -> list[tuple[int, int, int]]:
    refs = []
    for index in range(4):
        off = 0x10 + index * 8
        refs.append((_u32(data, off), _u32(data, off + 4), index))
    return refs


def _emit_symb(layout: _Layout, data: bytes, base: int, size: int) -> None:
    _need(data, base, size, "SDAT SYMB block")
    _magic(data, base, b"SYMB", "SDAT SYMB block")
    record_offsets = [_u32(data, base + 0x08 + index * 4) for index in range(8)]
    layout.add_struct(base, "SdatSymbHeader", [
        ("magic", _c_magic(data[base:base + 4])),
        ("size", _dec(_u32(data, base + 4))),
        ("record_offset", "{ " + ", ".join(_hex(off) for off in record_offsets) + " }"),
        ("reserved", _c_array(data[base + 0x28:base + 0x40])),
    ], "SYMB header", name="sdat_symb_header")

    pending: list[tuple[int, str, int]] = []
    for index, rel in enumerate(record_offsets):
        if rel:
            pending.append((rel, f"sdat_symb_{_INFO_SECTIONS[index][0]}", index))

    seen: set[int] = set()
    strings: set[int] = set()
    while pending:
        rel, name, index = pending.pop(0)
        if rel in seen:
            continue
        seen.add(rel)
        _need(data, base + rel, 4, "SYMB record")
        count = _u32(data, base + rel)
        body = base + rel + 4
        layout.add_struct(base + rel, "SdatSymbRecord", [
            ("count", _dec(count)),
        ], "SYMB record count", name=f"{name}_count")
        if index == 1:
            _need(data, body, count * 8, "SYMB archive record")
            rows = []
            for entry in range(count):
                off = body + entry * 8
                name_off = _u32(data, off)
                sub_off = _u32(data, off + 4)
                rows.append("{ .name_offset = %s, .sub_record_offset = %s }" % (
                    _hex(name_off), _hex(sub_off)))
                if name_off:
                    strings.add(name_off)
                if sub_off:
                    pending.append((sub_off, f"{name}_{entry:04d}", 0))
            if count:
                layout.add_struct_array(
                    body, "SdatSymbArchiveEntry", f"{name}_entries", rows,
                    "archive name offset, sub-record offset")
        else:
            _need(data, body, count * 4, "SYMB string table")
            offsets = [_u32(data, body + entry * 4) for entry in range(count)]
            for string_off in offsets:
                if string_off:
                    strings.add(string_off)
            if count:
                layout.add_array(
                    body, "uint32_t", f"{name}_names",
                    (_hex(off) for off in offsets), "string offsets")

    if strings:
        start = min(strings)
        if start >= size:
            raise ValueError(f"SYMB string offset 0x{start:X} is outside the block")
        layout.add_raw(base + start, data[base + start:base + size],
                       "sdat_symb_strings", "name strings")


def _emit_info_record(layout: _Layout, data: bytes, base: int, section: int,
                      rel: int, index: int) -> int:
    offset = base + rel
    name = f"sdat_info_{_INFO_SECTIONS[section][0]}_{index:03d}"
    if section == 0:
        _need(data, offset, 12, "INFO SEQ record")
        layout.add_struct(offset, "SdatSeqInfo", [
            ("file_id", _dec(_u32(data, offset))),
            ("bank", _dec(_u16(data, offset + 4))),
            ("volume", _dec(_u8(data, offset + 6))),
            ("channel_priority", _dec(_u8(data, offset + 7))),
            ("player_priority", _dec(_u8(data, offset + 8))),
            ("player", _player(_u8(data, offset + 9))),
            ("reserved", _dec(_u16(data, offset + 10))),
        ], f"SEQ {index}", name=name)
        return 12
    if section == 1:
        _need(data, offset, 4, "INFO SEQARC record")
        layout.add_struct(offset, "SdatSeqArcInfo", [
            ("file_id", _dec(_u32(data, offset))),
        ], f"SEQARC {index}", name=name)
        return 4
    if section == 2:
        _need(data, offset, 12, "INFO BANK record")
        slots = [_u16(data, offset + 4 + slot * 2) for slot in range(4)]
        layout.add_struct(offset, "SdatBankInfo", [
            ("file_id", _dec(_u32(data, offset))),
            ("wave_archive", "{ " + ", ".join(
                str(value if value < 0x8000 else value - 0x10000)
                for value in slots) + " }"),
        ], f"BANK {index}", name=name)
        return 12
    if section == 3:
        _need(data, offset, 4, "INFO WAVEARC record")
        raw = _u32(data, offset)
        layout.add_struct(offset, "SdatWaveArcInfo", [
            ("bits", "{ .file_id = %d, .load_individually = %d, .reserved = %d }" % (
                raw & 0xFFFFFF, (raw >> 24) & 1, (raw >> 25) & 0x7F)),
        ], f"WAVEARC {index}", name=name)
        return 4
    if section == 4:
        _need(data, offset, 8, "INFO PLAYER record")
        layout.add_struct(offset, "SdatPlayerInfo", [
            ("max_sequences", _dec(_u16(data, offset))),
            ("channel_mask", _hex(_u16(data, offset + 2))),
            ("heap_size", _dec(_u32(data, offset + 4))),
        ], f"PLAYER {index}", name=name)
        return 8
    if section == 5:
        _need(data, offset, 4, "INFO GROUP record")
        count = _u32(data, offset)
        _need(data, offset + 4, count * 8, "INFO GROUP items")
        layout.add_struct(offset, "SdatGroupInfo", [
            ("count", _dec(count)),
        ], f"GROUP {index} count", name=name)
        rows = []
        for item in range(count):
            item_off = offset + 4 + item * 8
            flags = _u8(data, item_off + 1)
            rows.append(
                "{ .type = %d, .load_flags = { .bits = { .sequence = %d, "
                ".bank = %d, .wave_archive = %d, .sequence_archive = %d, "
                ".reserved = %d } }, .reserved = %d, .index = %d }" % (
                    _u8(data, item_off), flags & 1, (flags >> 1) & 1,
                    (flags >> 2) & 1, (flags >> 3) & 1, (flags >> 4) & 0xF,
                    _u16(data, item_off + 2), _u32(data, item_off + 4)))
        if count:
            layout.add_struct_array(
                offset + 4, "SdatGroupItem", f"{name}_items", rows,
                "type, load flags, reserved, index")
        return 4 + count * 8
    if section == 6:
        _need(data, offset, 17, "INFO STREAM PLAYER record")
        layout.add_struct(offset, "SdatStreamPlayerInfo", [
            ("channel_count", _dec(_u8(data, offset))),
            ("channel", "{ " + ", ".join(
                _dec(_u8(data, offset + 1 + ch)) for ch in range(16)) + " }"),
        ], f"STREAM PLAYER {index}", name=name)
        return 17
    if section == 7:
        _need(data, offset, 12, "INFO STREAM record")
        layout.add_struct(offset, "SdatStreamInfo", [
            ("file_id", _dec(_u32(data, offset))),
            ("volume", _dec(_u8(data, offset + 4))),
            ("player_priority", _dec(_u8(data, offset + 5))),
            ("player", _dec(_u8(data, offset + 6))),
            ("flags", _dec(_u8(data, offset + 7))),
            ("reserved", _c_array(data[offset + 8:offset + 12])),
        ], f"STREAM {index}", name=name)
        return 12
    raise ValueError(f"unknown INFO section {section}")


def _emit_info(layout: _Layout, data: bytes, base: int, size: int) -> None:
    _need(data, base, size, "SDAT INFO block")
    _magic(data, base, b"INFO", "SDAT INFO block")
    section_offsets = [_u32(data, base + 0x08 + index * 4) for index in range(8)]
    layout.add_struct(base, "SdatInfoHeader", [
        ("magic", _c_magic(data[base:base + 4])),
        ("size", _dec(_u32(data, base + 4))),
        ("section_offset", "{ " + ", ".join(_hex(off) for off in section_offsets) + " }"),
        ("reserved", _c_array(data[base + 0x28:base + 0x40])),
    ], "INFO header", name="sdat_info_header")

    for section, (stem, _label, _fixed) in enumerate(_INFO_SECTIONS):
        rel = section_offsets[section]
        if not rel:
            continue
        _need(data, base + rel, 4, f"INFO {stem} section")
        count = _u32(data, base + rel)
        if rel + 4 + count * 4 > size:
            raise ValueError(f"INFO {stem} section runs past the block")
        layout.add_struct(base + rel, "SdatInfoTable", [
            ("count", _dec(count)),
        ], f"INFO {stem} count", name=f"sdat_info_{stem}_count")
        if count:
            offsets = [_u32(data, base + rel + 4 + index * 4)
                       for index in range(count)]
            layout.add_array(base + rel + 4, "uint32_t", f"sdat_info_{stem}_offsets",
                             (_hex(off) for off in offsets),
                             "record offsets (relative to INFO)")

    for section, (stem, _label, _fixed) in enumerate(_INFO_SECTIONS):
        rel = section_offsets[section]
        if not rel:
            continue
        count = _u32(data, base + rel)
        for index in range(count):
            record = _u32(data, base + rel + 4 + index * 4)
            if not record:
                continue
            if record >= size:
                raise ValueError(
                    f"INFO {stem} record {index} offset 0x{record:X} is outside the block")
            written = _emit_info_record(layout, data, base, section, record, index)
            fixed = _INFO_SECTIONS[section][2]
            if fixed is not None and written != fixed:
                raise ValueError(
                    f"INFO {stem} record {index} has a {written}-byte layout")


def _emit_fat(layout: _Layout, data: bytes, base: int,
              size: int) -> list[tuple[int, int]]:
    _need(data, base, size, "SDAT FAT block")
    _magic(data, base, b"FAT ", "SDAT FAT block")
    count = _u32(data, base + 8)
    layout.add_struct(base, "SdatFatHeader", [
        ("magic", _c_magic(data[base:base + 4])),
        ("size", _dec(_u32(data, base + 4))),
        ("count", _dec(count)),
    ], "FAT header", name="sdat_fat_header")
    _need(data, base + 12, count * 16, "SDAT FAT entries")
    rows = []
    entries = []
    for index in range(count):
        off = base + 12 + index * 16
        entries.append((_u32(data, off), _u32(data, off + 4)))
        rows.append("{ .offset = %s, .size = %d, .reserved = %s }" % (
            _hex(_u32(data, off)), _u32(data, off + 4),
            _c_array(data[off + 8:off + 16])))
    if count:
        layout.add_struct_array(
            base + 12, "SdatFatEntry", "sdat_fat_entries", rows,
            "FAT: absolute offset, unpadded size, reserved")
    return entries


def _emit_file(layout: _Layout, data: bytes, base: int, size: int,
               fat: Sequence[tuple[int, int]]) -> None:
    _need(data, base, size, "SDAT FILE block")
    _magic(data, base, b"FILE", "SDAT FILE block")
    count = _u32(data, base + 8)
    layout.add_struct(base, "SdatFileHeader", [
        ("magic", _c_magic(data[base:base + 4])),
        ("size", _dec(_u32(data, base + 4))),
        ("count", _dec(count)),
    ], "FILE header", name="sdat_file_header")

    placed: dict[int, int] = {}
    for index, (offset, file_size) in enumerate(fat):
        _need(data, offset, file_size, f"SDAT file {index}")
        if offset in placed:
            if placed[offset] != file_size:
                raise ValueError(
                    f"SDAT file {index} aliases offset 0x{offset:X} with a different size")
            continue
        placed[offset] = file_size
        layout.add_raw(offset, data[offset:offset + file_size],
                       f"sdat_file_{index:04d}",
                       f"FAT {index}: offset 0x{offset:X}, size {file_size}")


def emit_sdat_source(data: bytes) -> str:
    """SDAT: 0x40 header and the SYMB/INFO/FAT/FILE blocks."""
    _need(data, 0, 64, "SDAT header")
    _magic(data, 0, b"SDAT", "SDAT header")
    blocks = _sdat_blocks(data)
    layout = _Layout(len(data), data)
    layout.add_struct(0, "SdatHeader", [
        ("magic", _c_magic(data[0:4])),
        ("bom", _hex(_u16(data, 4))),
        ("version", _hex(_u16(data, 6))),
        ("file_size", _dec(_u32(data, 8))),
        ("header_size", _dec(_u16(data, 12))),
        ("block_count", _dec(_u16(data, 14))),
        ("block", "{ " + ", ".join(
            "{ %s, %d }" % (_hex(off), size) for off, size, _index in blocks) + " }"),
        ("reserved", _c_array(data[0x30:0x40])),
    ], "SDAT header", name="sdat_header")

    sym = blocks[0]
    info = blocks[1]
    fat = blocks[2]
    file_block = blocks[3]

    if sym[0] and sym[1]:
        _emit_symb(layout, data, sym[0], sym[1])
    if info[0] and info[1]:
        _emit_info(layout, data, info[0], info[1])

    fat_entries: list[tuple[int, int]] = []
    if fat[0] and fat[1]:
        fat_entries = _emit_fat(layout, data, fat[0], fat[1])

    if file_block[0] and file_block[1]:
        _emit_file(layout, data, file_block[0], file_block[1], fat_entries)

    return layout.build(["nitro/mkds/common/ids.h", "nitro/snd/sdat.h"], "SDAT")

# ---------------------------------------------------------------- dispatch

FORMATS = {
    "sdat": emit_sdat_source,
    "sseq": emit_sseq_source,
    "ssar": emit_ssar_source,
    "sbnk": emit_sbnk_source,
    "swar": emit_swar_source,
    "swav": emit_swav_source,
}

_EMITTERS = {
    b"SDAT": emit_sdat_source,
    b"SSEQ": emit_sseq_source,
    b"SSAR": emit_ssar_source,
    b"SBNK": emit_sbnk_source,
    b"SWAR": emit_swar_source,
    b"SWAV": emit_swav_source,
}


def emit_source(data: bytes) -> str:
    """Emit a C program for any Nitro sound file, selected by its magic."""
    if len(data) < 4:
        raise ValueError("sound file is shorter than its magic")
    try:
        emitter = _EMITTERS[data[:4]]
    except KeyError:
        raise ValueError(
            "unknown sound format %r; choose one of %s"
            % (data[:4], ", ".join(sorted(name.decode() for name in _EMITTERS)))
        ) from None
    return emitter(data)
