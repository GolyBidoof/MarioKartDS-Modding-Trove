# Mario Kart DS Modding Trove
# tools/ctables/mkds/course_tables.py — typed C tables for MKDS course files
# SPDX-License-Identifier: MIT
"""Emit complete C programs that rebuild NKM, KCL and SPA files byte-for-byte.

Each emitter returns a self-contained C translation unit that includes the
format header from ``include/nitro/mkds`` and writes the rebuilt file to
``argv[1]``.  Records use the header structs and C11 designated initializers;
section tables, record strides and payload blocks stay explicit so the output
can be compiled and compared with :mod:`tools.ctables.common.harness`.

Byte order is little-endian, matching the Nitro file ABI.  Offsets are printed
in hexadecimal; sizes and counts are decimal.
"""
from __future__ import annotations

import struct
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

from tools.ctables.common.cformat import fx_literal
from tools.ctables.common.cnames import enum_name

# ------------------------------------------------------------------ C helpers


def _c_char(value: int) -> str:
    """Return a C character constant for one byte."""
    if value == 0x5C:
        return "'\\\\'"
    if value == 0x27:
        return "'\\''"
    if 0x20 <= value <= 0x7E:
        return "'" + chr(value) + "'"
    return "0x%02x" % value


def _c_bytes(name: str, blob: bytes, per_line: int = 12) -> str:
    if not blob:
        return ""
    lines = ["static const uint8_t %s[] = {" % name]
    for start in range(0, len(blob), per_line):
        chunk = blob[start:start + per_line]
        lines.append("    " + ", ".join("0x%02x" % b for b in chunk) + ",")
    lines.append("};")
    return "\n".join(lines)


def _c_u32_array(name: str, values: Sequence[int]) -> str:
    lines = ["static const uint32_t %s[] = {" % name]
    for value in values:
        lines.append("    0x%08xu," % (value & 0xFFFFFFFF))
    lines.append("};")
    return "\n".join(lines)


_C_PROLOGUE = """\
#include <stdint.h>
#include <stdio.h>

static int write_bytes(FILE *out, const void *data, size_t size)
{
    return size == 0 || fwrite(data, 1, size, out) == size;
}

/* Legacy NKM records are shorter than the typed struct; copy the on-disk prefix. */
static int write_prefix_records(FILE *out, const void *base, size_t element_size,
                                size_t write_size, size_t count)
{
    const uint8_t *p = (const uint8_t *)base;
    size_t i;

    for (i = 0; i < count; i++) {
        if (fwrite(p + i * element_size, 1, write_size, out) != write_size)
            return 0;
    }
    return 1;
}
"""

_C_MAIN_HEAD = """\

int main(int argc, char **argv)
{
    FILE *out;
    int ok = 1;

    if (argc != 2)
        return 2;
    out = fopen(argv[1], "wb");
    if (out == NULL)
        return 3;
"""

_C_MAIN_TAIL = """\
    if (fclose(out) != 0)
        ok = 0;
    return ok ? 0 : 4;
}
"""


def _program(header: str, declarations: Sequence[str],
             body: Sequence[str]) -> str:
    parts = [_C_PROLOGUE, '#include "%s"\n' % header]
    parts.extend(declarations)
    parts.append(_C_MAIN_HEAD)
    parts.extend(body)
    parts.append(_C_MAIN_TAIL)
    return "\n".join(part for part in parts if part) + "\n"


# ------------------------------------------------------------------ fields

# Each field kind records the struct format, its size in bytes, and how the
# value is written in C.  Fixed-point and signed values are printed as their
# two's-complement bit pattern so the source is independent of host sign
# behaviour.
_KIND_FORMAT = {
    "u8": "B",
    "u16": "H",
    "i16": "h",
    "u32": "I",
    "i32": "i",
    "fx16": "h",
    "fx32": "i",
    "stage_id": "H",
    "object_id": "H",
    "visibility": "H",
    "area_shape": "B",
    "area_type": "B",
    "camera_type": "H",
    "intro_camera": "B",
    "fog_color": "I",
    "magic": "B",
}

_KIND_SIZE = {
    "u8": 1,
    "u16": 2,
    "i16": 2,
    "u32": 4,
    "i32": 4,
    "fx16": 2,
    "fx32": 4,
    "stage_id": 2,
    "object_id": 2,
    "visibility": 2,
    "area_shape": 1,
    "area_type": 1,
    "camera_type": 2,
    "intro_camera": 1,
    "fog_color": 4,
    "magic": 1,
}


def _c_scalar(kind: str, value: int) -> str:
    if kind == "u8":
        return "0x%02xu" % (value & 0xFF)
    if kind == "u16":
        return "0x%04xu" % (value & 0xFFFF)
    if kind == "i16":
        return str(value if value < 0x8000 else value - 0x10000)
    if kind == "fx16":
        return fx_literal(value if value < 0x8000 else value - 0x10000, 12)
    if kind == "u32":
        return "0x%08xu" % (value & 0xFFFFFFFF)
    if kind == "i32":
        return str(value if value < 0x80000000 else value - 0x100000000)
    if kind == "fx32":
        return fx_literal(value if value < 0x80000000 else value - 0x100000000, 12)
    if kind == "stage_id":
        name = enum_name("MkdsStageCourse", value)
        return name or "(MkdsStageCourseId)0x%04xu" % (value & 0xFFFF)
    if kind == "object_id":
        name = enum_name("MkdsMapObject", value & 0xFFFF)
        if name:
            return name
        return "(MkdsMapObjectId)0x%04xu" % (value & 0xFFFF)
    if kind == "visibility":
        value &= 0xFFFF
        c0, c1, c2, c3 = (value % 10, (value // 10) % 10,
                         (value // 100) % 10, (value // 1000) % 10)
        inactive = value // 10000
        rebuilt = (c0 + c1 * 10 + c2 * 100 + c3 * 1000
                   + (inactive == 1) * 10000)
        if rebuilt == value and inactive in (0, 1):
            return "NKM_OBJI_VISIBILITY(%d, %d, %d, %d, %d)" % (
                c0, c1, c2, c3, inactive)
        return "0x%04xu" % value
    if kind == "fog_color":
        if value & 0xFFF00000:
            return "{ .raw = 0x%08xu }" % (value & 0xFFFFFFFF)
        red = value & 0x1F
        green = (value >> 5) & 0x1F
        blue = (value >> 10) & 0x1F
        alpha = (value >> 15) & 0x1F
        return ("{ .bits = { .red = %d, .green = %d, .blue = %d, "
                ".alpha = %d } }" % (red, green, blue, alpha))
    if kind in ("area_shape", "area_type", "camera_type", "intro_camera"):
        type_name = {
            "area_shape": "NkmAreaShape",
            "area_type": "NkmAreaType",
            "camera_type": "NkmCameraType",
            "intro_camera": "NkmIntroCamera",
        }[kind]
        name = enum_name(type_name, value)
        return name or str(value)
    raise ValueError("unknown field kind %r" % (kind,))


@dataclass(frozen=True)
class _Field:
    name: str
    kind: str
    count: int = 1


def _f(name: str, kind: str, count: int = 1) -> _Field:
    return _Field(name, kind, count)


def _field_size(field: _Field) -> int:
    return _KIND_SIZE[field.kind] * field.count


def _parse_fields(record: bytes, fields: Sequence[_Field],
                  limit: int) -> List[Tuple[_Field, Tuple[int, ...]]]:
    """Unpack as many leading fields as fit in ``limit`` bytes."""
    parsed: List[Tuple[_Field, Tuple[int, ...]]] = []
    offset = 0
    for field in fields:
        size = _field_size(field)
        if offset + size > limit:
            break
        fmt = "<" + _KIND_FORMAT[field.kind] * field.count
        values = struct.unpack_from(fmt, record, offset)
        parsed.append((field, values))
        offset += size
    return parsed


def _c_field(field: _Field, values: Sequence[int]) -> str:
    if field.kind == "magic":
        items = ", ".join(_c_char(value) for value in values)
        return ".%s = { %s }," % (field.name, items)
    if field.count == 1:
        return ".%s = %s," % (field.name, _c_scalar(field.kind, values[0]))
    items = ", ".join(_c_scalar(field.kind, value) for value in values)
    return ".%s = { %s }," % (field.name, items)


def _c_record(struct_name: str, name: str,
              records: Sequence[Sequence[Tuple[_Field, Tuple[int, ...]]]]) -> str:
    lines = ["static const %s %s[] = {" % (struct_name, name)]
    for record in records:
        lines.append("    {")
        for field, values in record:
            lines.append("        " + _c_field(field, values))
        lines.append("    },")
    lines.append("};")
    return "\n".join(lines)


# ------------------------------------------------------------------ NKM

_NKM_CANONICAL = {
    b"OBJI": 60,
    b"PATH": 4,
    b"POIT": 20,
    b"KTPS": 28,
    b"KTPJ": 32,
    b"KTP2": 28,
    b"KTPC": 28,
    b"KTPM": 28,
    b"CPOI": 36,
    b"CPAT": 12,
    b"IPOI": 20,
    b"IPAT": 12,
    b"EPOI": 24,
    b"EPAT": 12,
    b"MEPO": 24,
    b"MEPA": 20,
    b"AREA": 72,
    b"CAME": 76,
}

_NKM_SCHEMA: Dict[bytes, Tuple[str, Tuple[_Field, ...]]] = {
    b"STAG": ("NkmStage", (
        _f("magic", "magic", 4),
        _f("course_id", "stage_id"),
        _f("lap_count", "i16"),
        _f("pole_position", "u8"),
        _f("fog_enabled", "u8"),
        _f("fog_table_mode", "u8"),
        _f("fog_shift", "u8"),
        _f("unidentified_0C", "u8", 8),
        _f("fog_offset", "fx32"),
        _f("fog_color", "fog_color"),
        _f("kcl_light_color", "u16", 4),
        _f("object_far_clip", "fx32"),
        _f("frustum_far", "fx32"),
    )),
    b"OBJI": ("NkmObjectEntry", (
        _f("position", "fx32", 3),
        _f("rotation", "fx32", 3),
        _f("scale", "fx32", 3),
        _f("object_id", "object_id"),
        _f("path_id", "i16"),
        _f("settings", "i16", 7),
        _f("visibility", "visibility"),
        _f("time_trial_visible", "u32"),
    )),
    b"PATH": ("NkmPathEntry", (
        _f("index", "u8"),
        _f("loop", "u8"),
        _f("point_count", "i16"),
    )),
    b"POIT": ("NkmPointEntry", (
        _f("position", "fx32", 3),
        _f("index", "u8"),
        _f("translucency_flags", "u8"),
        _f("duration", "i16"),
        _f("path_parameter", "i16"),
        _f("traffic_cosine", "i16"),
    )),
    b"KTPS": ("NkmKtpsEntry", (
        _f("position", "fx32", 3),
        _f("rotation", "fx32", 3),
        _f("marker", "u16"),
        _f("index", "i16"),
    )),
    b"KTPJ": ("NkmKtpjEntry", (
        _f("position", "fx32", 3),
        _f("rotation", "fx32", 3),
        _f("enemy_point_id", "i16"),
        _f("item_point_id", "i16"),
        _f("index", "i32"),
    )),
    b"KTP2": ("NkmKtp2Entry", (
        _f("position", "fx32", 3),
        _f("rotation", "fx32", 3),
        _f("marker", "u32"),
    )),
    b"KTPC": ("NkmKtpcEntry", (
        _f("position", "fx32", 3),
        _f("rotation", "fx32", 3),
        _f("next_mepo", "i16"),
        _f("index", "i16"),
    )),
    b"KTPM": ("NkmKtpmEntry", (
        _f("position", "fx32", 3),
        _f("rotation", "fx32", 3),
        _f("marker", "u16"),
        _f("index", "i16"),
    )),
    b"CPOI": ("NkmCpoiEntry", (
        _f("point1", "fx32", 2),
        _f("point2", "fx32", 2),
        _f("sine", "fx32"),
        _f("cosine", "fx32"),
        _f("distance", "fx32"),
        _f("goto_section", "i16"),
        _f("start_section", "i16"),
        _f("key_point_id", "i16"),
        _f("respawn_id", "u8"),
        _f("flags", "u8"),
    )),
    b"CPAT": ("NkmCpatEntry", (
        _f("start_index", "u16"),
        _f("length", "u16"),
        _f("next", "u8", 3),
        _f("previous", "u8", 3),
        _f("section_order", "u8"),
        _f("padding", "u8"),
    )),
    b"IPOI": ("NkmItemPointEntry", (
        _f("position", "fx32", 3),
        _f("radius", "fx32"),
        _f("recalculation_index", "u8"),
        _f("padding", "u8", 3),
    )),
    b"IPAT": ("NkmPathLinkEntry", (
        _f("start_index", "i16"),
        _f("length", "i16"),
        _f("next", "u8", 3),
        _f("previous", "u8", 3),
        _f("section_order", "i16"),
    )),
    b"EPOI": ("NkmEnemyPointEntry", (
        _f("position", "fx32", 3),
        _f("radius", "fx32"),
        _f("drifting", "i16"),
        _f("parameter_1", "i16"),
        _f("parameter_2", "i16"),
        _f("parameter_3", "i16"),
    )),
    b"EPAT": ("NkmPathLinkEntry", (
        _f("start_index", "i16"),
        _f("length", "i16"),
        _f("next", "u8", 3),
        _f("previous", "u8", 3),
        _f("section_order", "i16"),
    )),
    b"MEPO": ("NkmMissionEnemyPointEntry", (
        _f("position", "fx32", 3),
        _f("radius", "fx32"),
        _f("drifting", "i16"),
        _f("padding_12", "u8", 2),
        _f("settings_word", "u32"),
    )),
    b"MEPA": ("NkmMissionPathEntry", (
        _f("start_index", "i16"),
        _f("length", "i16"),
        _f("next", "u8", 8),
        _f("previous", "u8", 8),
    )),
    b"AREA": ("NkmAreaEntry", (
        _f("position", "fx32", 3),
        _f("length", "fx32", 3),
        _f("x_axis", "fx32", 3),
        _f("y_axis", "fx32", 3),
        _f("z_axis", "fx32", 3),
        _f("parameter_0", "i16"),
        _f("parameter_1", "i16"),
        _f("enemy_point_id", "i16"),
        _f("shape", "area_shape"),
        _f("linked_camera", "u8"),
        _f("area_type", "area_type"),
        _f("reserved_45", "u8", 3),
    )),
    b"CAME": ("NkmCameEntry", (
        _f("position", "fx32", 3),
        _f("rotation", "fx32", 3),
        _f("target_1", "fx32", 3),
        _f("target_2", "fx32", 3),
        _f("fov_begin", "u16"),
        _f("fov_begin_sine", "fx16"),
        _f("fov_begin_cosine", "fx16"),
        _f("fov_end", "u16"),
        _f("fov_end_sine", "fx16"),
        _f("fov_end_cosine", "fx16"),
        _f("fov_speed", "fx16"),
        _f("type", "camera_type"),
        _f("linked_route", "i16"),
        _f("path_speed", "fx16"),
        _f("target_speed", "fx16"),
        _f("duration", "i16"),
        _f("next_camera", "i16"),
        _f("first_intro_camera", "intro_camera"),
        _f("show_award_trail", "u8"),
    )),
}


def _nkm_stride(tag: bytes, version: int) -> int:
    if tag == b"KTPJ" and version < 32:
        return 28
    if tag == b"IPOI" and version < 34:
        return 16
    return _NKM_CANONICAL[tag]


@dataclass
class _NkmSection:
    tag: bytes
    offset: int
    length: int
    count: Optional[int]
    stride: int
    struct_name: str
    records: List[List[Tuple[_Field, Tuple[int, ...]]]]
    tail: bytes


def _parse_nkm(data: bytes) -> Tuple[int, int, List[_NkmSection]]:
    if len(data) < 8 or data[:4] != b"NKMD":
        raise ValueError("not an NKM file")
    version, header_size = struct.unpack_from("<HH", data, 4)
    if header_size < 8 or (header_size - 8) % 4:
        raise ValueError("invalid NKM header size")
    count = (header_size - 8) // 4
    if header_size > len(data):
        raise ValueError("truncated NKM header table")
    offsets = struct.unpack_from("<%dI" % count, data, 8)

    sections: List[_NkmSection] = []
    cursor = 0
    for index, offset in enumerate(offsets):
        if offset != cursor:
            raise ValueError("NKM section offsets are not contiguous")
        end = offsets[index + 1] if index + 1 < len(offsets) else len(data) - header_size
        if end < offset:
            raise ValueError("NKM section offsets are not ordered")
        start = header_size + offset
        length = end - offset
        if length < 4:
            raise ValueError("truncated NKM section")
        tag = data[start:start + 4]
        if tag not in _NKM_SCHEMA:
            raise ValueError("unsupported NKM section %r" % (tag,))

        struct_name, fields = _NKM_SCHEMA[tag]
        if tag == b"STAG":
            if length < 44:
                raise ValueError("truncated NKM STAG section")
            record_count = None
            stride = 44
            body = data[start:start + stride]
            records = [_parse_fields(body, fields, stride)]
            tail = data[start + stride:start + length]
        else:
            if length < 8:
                raise ValueError("truncated NKM section header")
            record_count = struct.unpack_from("<I", data, start + 4)[0]
            stride = _nkm_stride(tag, version)
            body_size = record_count * stride
            if 8 + body_size > length:
                raise ValueError("truncated NKM %r records" % (tag,))
            records = []
            for record_index in range(record_count):
                body = data[start + 8 + record_index * stride:
                            start + 8 + (record_index + 1) * stride]
                records.append(_parse_fields(body, fields, stride))
            tail = data[start + 8 + body_size:start + length]

        sections.append(_NkmSection(
            tag=tag,
            offset=offset,
            length=length,
            count=record_count,
            stride=stride,
            struct_name=struct_name,
            records=records,
            tail=tail,
        ))
        cursor += length

    if cursor != len(data) - header_size:
        raise ValueError("NKM section layout does not cover the file")
    if header_size != 8 + 4 * len(sections):
        raise ValueError("NKM header size does not match its section table")
    return version, header_size, sections


def emit_nkm_source(data: bytes) -> str:
    """Return a C program that writes ``data`` as an NKM file."""
    version, header_size, sections = _parse_nkm(data)
    declarations: List[str] = []
    body: List[str] = []

    declarations.append(
        "static const NkmHeader nkm_header = {\n"
        "    .magic = { 'N', 'K', 'M', 'D' },\n"
        "    .version = %du,\n"
        "    .header_size = %du,\n"
        "};" % (version, header_size))
    declarations.append(_c_u32_array(
        "nkm_section_offsets", [section.offset for section in sections]))

    used: Dict[str, int] = {}
    for section in sections:
        base = "nkm_" + section.tag.decode("ascii").lower()
        seen = used.get(base, 0)
        used[base] = seen + 1
        if seen:
            base = "%s_%d" % (base, seen)

        declarations.append(
            "/* %s at 0x%08x: %s, %d bytes */" % (
                section.tag.decode("ascii"),
                section.offset,
                "1 record" if section.count is None else "%d records" % section.count,
                section.length))

        if section.count is None:
            declarations.append(_c_record(section.struct_name, base, section.records))
        else:
            declarations.append(
                "static const NkmSectionHeader %s_header = {\n"
                "    .magic = { %s },\n"
                "    .entry_count = %du,\n"
                "};" % (
                    base,
                    ", ".join(_c_char(value) for value in section.tag),
                    section.count))
            if section.records:
                declarations.append(_c_record(
                    section.struct_name, base + "_records", section.records))

        if section.tail:
            declarations.append(_c_bytes(base + "_tail", section.tail))

        if section.count is not None:
            body.append("    ok = ok && write_bytes(out, &%s_header, sizeof %s_header);"
                        % (base, base))
            if section.records:
                body.append(
                    "    ok = ok && write_prefix_records(out, %s_records, "
                    "sizeof %s_records[0], %d, %d);" % (
                        base, base, section.stride, section.count))
        else:
            body.append("    ok = ok && write_bytes(out, &%s, sizeof %s);" % (base, base))
        if section.tail:
            body.append("    ok = ok && write_bytes(out, %s_tail, sizeof %s_tail);"
                        % (base, base))

    body.insert(0, "    ok = ok && write_bytes(out, &nkm_header, sizeof nkm_header);")
    body.insert(1, "    ok = ok && write_bytes(out, nkm_section_offsets, "
                   "sizeof nkm_section_offsets);")
    return _program("nitro/mkds/course/nkm.h", declarations, body)


# ------------------------------------------------------------------ KCL

@dataclass
class _KclPlan:
    header: Tuple[int, ...]
    prefix: bytes
    positions: List[Tuple[int, int, int]]
    position_tail: bytes
    normals: List[Tuple[int, int, int]]
    normal_padding: bytes
    prisms: List[Tuple[int, int, int, int, int, int, int]]
    prism_tail: bytes
    octree: bytes


def _parse_kcl(data: bytes) -> _KclPlan:
    if len(data) < 60:
        raise ValueError("truncated KCL file")
    header = struct.unpack_from("<15I", data)
    position_table, normal_table, prism_table_stored, block_table = header[:4]
    prism_table = prism_table_stored + 0x10
    if position_table < 60 or not (position_table <= normal_table <= prism_table <= block_table):
        raise ValueError("invalid KCL table offsets")
    if block_table > len(data):
        raise ValueError("truncated KCL octree")

    prefix = data[60:position_table]

    position_bytes = data[position_table:normal_table]
    position_count = len(position_bytes) // 12
    position_tail = position_bytes[position_count * 12:]
    positions = [
        struct.unpack_from("<3i", position_bytes, index * 12)
        for index in range(position_count)
    ]

    normal_bytes = data[normal_table:prism_table]
    padding = None
    for candidate in range(4):
        if (len(normal_bytes) - candidate) % 6 == 0:
            padding = candidate
            break
    if padding is None:
        raise ValueError("KCL normal table is not a run of FX16 triples")
    normal_count = (len(normal_bytes) - padding) // 6
    normal_padding = normal_bytes[normal_count * 6:]
    normals = [
        struct.unpack_from("<3h", normal_bytes, index * 6)
        for index in range(normal_count)
    ]

    prism_bytes = data[prism_table:block_table]
    prism_count = len(prism_bytes) // 16
    prism_tail = prism_bytes[prism_count * 16:]
    prisms = [
        struct.unpack_from("<i6H", prism_bytes, index * 16)
        for index in range(prism_count)
    ]

    return _KclPlan(
        header=header,
        prefix=prefix,
        positions=positions,
        position_tail=position_tail,
        normals=normals,
        normal_padding=normal_padding,
        prisms=prisms,
        prism_tail=prism_tail,
        octree=data[block_table:],
    )


def _c_kcl_header(header: Sequence[int]) -> str:
    return (
        "static const KclHeader kcl_header = {\n"
        "    .position_table = 0x%08xu,\n"
        "    .normal_table = 0x%08xu,\n"
        "    .prism_table_stored = 0x%08xu,\n"
        "    .block_table = 0x%08xu,\n"
        "    .prism_thickness = (Fx32)0x%08xu,\n"
        "    .area_min = { .x = (Fx32)0x%08xu, .y = (Fx32)0x%08xu, "
        ".z = (Fx32)0x%08xu },\n"
        "    .area_x_mask = 0x%08xu,\n"
        "    .area_y_mask = 0x%08xu,\n"
        "    .area_z_mask = 0x%08xu,\n"
        "    .block_width_shift = 0x%08xu,\n"
        "    .area_x_blocks_shift = 0x%08xu,\n"
        "    .area_xy_blocks_shift = 0x%08xu,\n"
        "    .sphere_radius = (Fx32)0x%08xu,\n"
        "};" % (
            header[0], header[1], header[2],
            header[3], header[4], header[5], header[6], header[7],
            header[8], header[9], header[10], header[11], header[12],
            header[13], header[14]))


def emit_kcl_source(data: bytes) -> str:
    """Return a C program that writes ``data`` as a KCL file."""
    plan = _parse_kcl(data)
    declarations: List[str] = [_c_kcl_header(plan.header)]
    body: List[str] = []

    if plan.prefix:
        declarations.append(_c_bytes("kcl_prefix", plan.prefix))

    if plan.positions:
        lines = ["static const KclVecFx32 kcl_positions[] = {"]
        for x, y, z in plan.positions:
            lines.append("    { .x = (Fx32)0x%08xu, .y = (Fx32)0x%08xu, "
                         ".z = (Fx32)0x%08xu }," % (x & 0xFFFFFFFF,
                                                    y & 0xFFFFFFFF,
                                                    z & 0xFFFFFFFF))
        lines.append("};")
        declarations.append("\n".join(lines))
    if plan.position_tail:
        declarations.append(_c_bytes("kcl_position_tail", plan.position_tail))

    if plan.normals:
        lines = ["static const KclVecFx16 kcl_normals[] = {"]
        for x, y, z in plan.normals:
            lines.append("    { .x = (Fx16)0x%04xu, .y = (Fx16)0x%04xu, "
                         ".z = (Fx16)0x%04xu }," % (x & 0xFFFF,
                                                    y & 0xFFFF,
                                                    z & 0xFFFF))
        lines.append("};")
        declarations.append("\n".join(lines))
    if plan.normal_padding:
        declarations.append(_c_bytes("kcl_normal_padding", plan.normal_padding))

    if plan.prisms:
        lines = ["static const KclPrism kcl_prisms[] = {"]
        for prism in plan.prisms:
            height, position, face, edge0, edge1, edge2, attribute = prism
            lines.append(
                "    {\n"
                "        .height = (Fx32)0x%08xu,\n"
                "        .position_index = 0x%04xu,\n"
                "        .face_normal_index = 0x%04xu,\n"
                "        .edge_normal_index = { 0x%04xu, 0x%04xu, 0x%04xu },\n"
                "        .attribute = 0x%04xu,\n"
                "    }," % (
                    height & 0xFFFFFFFF, position, face, edge0, edge1,
                    edge2, attribute))
        lines.append("};")
        declarations.append("\n".join(lines))
    if plan.prism_tail:
        declarations.append(_c_bytes("kcl_prism_tail", plan.prism_tail))
    if plan.octree:
        declarations.append(_c_bytes("kcl_octree", plan.octree))

    body.append("    ok = ok && write_bytes(out, &kcl_header, sizeof kcl_header);")
    if plan.prefix:
        body.append("    ok = ok && write_bytes(out, kcl_prefix, sizeof kcl_prefix);")
    if plan.positions:
        body.append("    ok = ok && write_bytes(out, kcl_positions, sizeof kcl_positions);")
    if plan.position_tail:
        body.append("    ok = ok && write_bytes(out, kcl_position_tail, "
                    "sizeof kcl_position_tail);")
    if plan.normals:
        body.append("    ok = ok && write_bytes(out, kcl_normals, sizeof kcl_normals);")
    if plan.normal_padding:
        body.append("    ok = ok && write_bytes(out, kcl_normal_padding, "
                    "sizeof kcl_normal_padding);")
    if plan.prisms:
        body.append("    ok = ok && write_bytes(out, kcl_prisms, sizeof kcl_prisms);")
    if plan.prism_tail:
        body.append("    ok = ok && write_bytes(out, kcl_prism_tail, "
                    "sizeof kcl_prism_tail);")
    if plan.octree:
        body.append("    ok = ok && write_bytes(out, kcl_octree, sizeof kcl_octree);")

    return _program("nitro/mkds/course/kcl.h", declarations, body)


# ------------------------------------------------------------------ SPA

@dataclass
class _SpaPiece:
    name: str
    blob: bytes
    comment: str


@dataclass
class _SpaTexture:
    header: Tuple[bytes, int, int, int, int, int, int, int]
    pieces: List[_SpaPiece]


@dataclass
class _SpaPlan:
    header: Tuple[bytes, int, int, int, int, int, int, int, int]
    emitter_block: bytes
    emitter_gap: bytes
    textures: List[_SpaTexture]
    texture_block_tail: bytes
    trailing: bytes


def _spa_regions(texture: bytes) -> List[Tuple[int, int, str]]:
    """Return non-empty payload regions inside one texture record."""
    _, _, texture_size, palette_offset, palette_size, index_offset, index_size, block_size = (
        struct.unpack_from("<4sIIIIIII", texture))
    if block_size < 32:
        raise ValueError("SPA texture block is smaller than its descriptor")
    regions = [
        (32, 32 + texture_size, "texture data"),
        (palette_offset, palette_offset + palette_size, "palette"),
        (index_offset, index_offset + index_size, "palette index"),
    ]
    active = []
    for start, end, label in regions:
        if end <= start:
            continue
        if start < 32 or end > block_size:
            raise ValueError("SPA texture payload region is outside its block")
        active.append((start, end, label))
    active.sort()
    for previous, current in zip(active, active[1:]):
        if previous[1] > current[0]:
            raise ValueError("overlapping SPA texture payload regions")
    return active


def _parse_spa(data: bytes) -> _SpaPlan:
    if len(data) < 32:
        raise ValueError("truncated SPA file")
    header = struct.unpack_from("<4sIHHIIIII", data)
    magic, version, emitter_count, texture_count, reserved_0c = header[:5]
    emitter_length, texture_length, texture_offset, reserved_20 = header[5:]
    if magic not in (b" APS", b"SPA "):
        raise ValueError("not a SPA file")
    if texture_offset < 32 or texture_offset + texture_length > len(data):
        raise ValueError("invalid SPA texture block range")
    if 32 + emitter_length > texture_offset:
        raise ValueError("SPA emitter block overlaps the texture block")

    emitter_block = data[32:32 + emitter_length]
    emitter_gap = data[32 + emitter_length:texture_offset]
    texture_end = texture_offset + texture_length
    trailing = data[texture_end:]

    textures: List[_SpaTexture] = []
    cursor = texture_offset
    for index in range(texture_count):
        if cursor + 32 > texture_end:
            raise ValueError("truncated SPA texture descriptor")
        values = struct.unpack_from("<4sIIIIIII", data, cursor)
        block_size = values[7]
        if block_size < 32 or cursor + block_size > texture_end:
            raise ValueError("invalid SPA texture block size")
        record = data[cursor:cursor + block_size]
        regions = _spa_regions(record)

        pieces: List[_SpaPiece] = []
        payload_cursor = 32
        piece_index = 0
        for start, end, label in regions:
            if start > payload_cursor:
                pieces.append(_SpaPiece(
                    "spa_texture_%d_gap_%d" % (index, piece_index),
                    record[payload_cursor:start],
                    "gap before %s" % label))
                piece_index += 1
            name = {
                "texture data": "spa_texture_%d_data" % index,
                "palette": "spa_texture_%d_palette" % index,
                "palette index": "spa_texture_%d_palette_index" % index,
            }[label]
            pieces.append(_SpaPiece(
                name, record[start:end],
                "%s, %d bytes at +0x%04x" % (label, end - start, start)))
            payload_cursor = end
        if payload_cursor < block_size:
            pieces.append(_SpaPiece(
                "spa_texture_%d_gap_%d" % (index, piece_index),
                record[payload_cursor:block_size],
                "trailing gap, %d bytes" % (block_size - payload_cursor)))

        textures.append(_SpaTexture(header=values, pieces=pieces))
        cursor += block_size

    if cursor > texture_end:
        raise ValueError("SPA texture records exceed the texture block")
    texture_block_tail = data[cursor:texture_end]
    return _SpaPlan(
        header=header,
        emitter_block=emitter_block,
        emitter_gap=emitter_gap,
        textures=textures,
        texture_block_tail=texture_block_tail,
        trailing=trailing,
    )


def _c_spa_header(values: Sequence[object]) -> str:
    return (
        "static const SpaHeader spa_header = {\n"
        "    .magic = { %s },\n"
        "    .version = 0x%08xu,\n"
        "    .emitter_count = %du,\n"
        "    .texture_count = %du,\n"
        "    .reserved_0C = 0x%08xu,\n"
        "    .emitter_block_length = %du,\n"
        "    .texture_block_length = %du,\n"
        "    .texture_block_offset = 0x%08xu,\n"
        "    .reserved_20 = 0x%08xu,\n"
        "};" % (
            ", ".join(_c_char(value) for value in values[0]),
            values[1], values[2], values[3], values[4], values[5],
            values[6], values[7], values[8]))


def _c_spa_textures(textures: Sequence[_SpaTexture]) -> str:
    lines = ["static const SpaTextureHeader spa_textures[] = {"]
    for texture in textures:
        magic, params, texture_size, palette_offset, palette_size, index_offset, index_size, block_size = texture.header
        lines.append(
            "    {\n"
            "        .magic = { %s },\n"
            "        .params = { .raw = 0x%08xu },\n"
            "        .texture_size = %du,\n"
            "        .palette_offset = 0x%08xu,\n"
            "        .palette_size = %du,\n"
            "        .palette_index_offset = 0x%08xu,\n"
            "        .palette_index_size = %du,\n"
            "        .block_size = %du,\n"
            "    }," % (
                ", ".join(_c_char(value) for value in magic), params,
                texture_size, palette_offset, palette_size, index_offset,
                index_size, block_size))
    lines.append("};")
    return "\n".join(lines)


def emit_spa_source(data: bytes) -> str:
    """Return a C program that writes ``data`` as a SPA file.

    The emitter block is preserved as one opaque blob: its per-emitter record
    layout is not part of the typed headers yet.  The header, texture
    descriptors and texture payload regions are typed and split into named
    arrays.
    """
    plan = _parse_spa(data)
    declarations: List[str] = []
    if plan.header[0] == b" APS":
        declarations.append(
            '/* Stock files store the magic as " APS" (0x53504120), not the\n'
            ' * SPA_MAGIC spelling, so the bytes are kept verbatim here. */')
    declarations.append(_c_spa_header(plan.header))
    body: List[str] = []

    if plan.emitter_block:
        declarations.append(_c_bytes("spa_emitter_block", plan.emitter_block))
    if plan.emitter_gap:
        declarations.append(_c_bytes("spa_emitter_gap", plan.emitter_gap))

    if plan.textures:
        declarations.append(_c_spa_textures(plan.textures))
        for texture in plan.textures:
            for piece in texture.pieces:
                if piece.blob:
                    declarations.append(_c_bytes(piece.name, piece.blob))
    if plan.texture_block_tail:
        declarations.append(_c_bytes("spa_texture_block_tail",
                                     plan.texture_block_tail))
    if plan.trailing:
        declarations.append(_c_bytes("spa_trailing", plan.trailing))

    body.append("    ok = ok && write_bytes(out, &spa_header, sizeof spa_header);")
    if plan.emitter_block:
        body.append("    ok = ok && write_bytes(out, spa_emitter_block, "
                    "sizeof spa_emitter_block);")
    if plan.emitter_gap:
        body.append("    ok = ok && write_bytes(out, spa_emitter_gap, "
                    "sizeof spa_emitter_gap);")
    for index, texture in enumerate(plan.textures):
        body.append("    ok = ok && write_bytes(out, &spa_textures[%d], "
                    "sizeof spa_textures[%d]);" % (index, index))
        for piece in texture.pieces:
            body.append("    ok = ok && write_bytes(out, %s, sizeof %s);" % (
                piece.name, piece.name))
    if plan.texture_block_tail:
        body.append("    ok = ok && write_bytes(out, spa_texture_block_tail, "
                    "sizeof spa_texture_block_tail);")
    if plan.trailing:
        body.append("    ok = ok && write_bytes(out, spa_trailing, "
                    "sizeof spa_trailing);")

    return _program("nitro/mkds/course/spa.h", declarations, body)


# ------------------------------------------------------------------ dispatch


def emit_source(data: bytes) -> str:
    """Emit a C program for any supported course file.

    NKM and SPA have magic values; KCL has no magic, so it is the fallback
    after the other two are ruled out.
    """
    if data[:4] == b"NKMD":
        return emit_nkm_source(data)
    if data[:4] in (b" APS", b"SPA "):
        return emit_spa_source(data)
    return emit_kcl_source(data)
