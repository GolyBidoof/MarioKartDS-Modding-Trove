# Mario Kart DS Modding Trove
# tools/ctables/generic/g3d_tables.py — typed C-table emitters for Nitro G3D resources
# SPDX-License-Identifier: MIT
"""Emit a byte-exact C rebuild program for a Nitro G3D resource.

The emitters parse the visible records of one container (NSBMD, NSBTX, NSBCA,
NSBTP, NSBTA or NSBMA) and turn them into typed initialisers that use the
headers in ``include/nitro/g3d*``. Patricia nodes, dictionary name tables and
unstructured payloads (display lists, texture images, key-frame tables) are
emitted as explicit byte arrays, which is the documented fallback for data the
headers do not model.

Every generated program writes the rebuilt file to ``argv[1]`` so that
``tools.ctables.common.harness.compile_and_compare`` can verify it byte-for-byte.

Offsets are emitted in hexadecimal; sizes, counts and strides are decimal.
Packed bitfield words are initialised through their ``raw`` union member.
"""
from __future__ import annotations

import struct
from dataclasses import dataclass

__all__ = [
    "emit_source",
    "emit_nsbmd_source",
    "emit_nsbtx_source",
    "emit_nsbca_source",
    "emit_nsbtp_source",
    "emit_nsbta_source",
    "emit_nsbma_source",
]

_MAGIC_NSBMD = b"BMD0"
_MAGIC_NSBTX = b"BTX0"
_MAGIC_NSBCA = b"BCA0"
_MAGIC_NSBTP = b"BTP0"
_MAGIC_NSBTA = b"BTA0"
_MAGIC_NSBMA = b"BMA0"

_BLOCK_MDL0 = b"MDL0"
_BLOCK_TEX0 = b"TEX0"
_BLOCK_JNT0 = b"JNT0"
_BLOCK_PAT0 = b"PAT0"
_BLOCK_SRT0 = b"SRT0"
_BLOCK_MAT0 = b"MAT0"

# Plausibility limits for dictionaries parsed out of untrusted bytes.
_MAX_ENTRIES = 4096
_MAX_ENTRY_SIZE = 4096


def _u16(data: bytes, offset: int) -> int:
    return struct.unpack_from("<H", data, offset)[0]


def _u32(data: bytes, offset: int) -> int:
    return struct.unpack_from("<I", data, offset)[0]


def _chars(text: bytes) -> str:
    return "{ " + ", ".join(repr(chr(byte)) for byte in text) + " }"


def _hex(value: int, width: int) -> str:
    return f"0x{value:0{width}X}u"


def _fx32(value: int) -> str:
    return f"(int32_t)0x{value:08X}u"


def _fx16(value: int) -> str:
    return f"(int16_t)0x{value:04X}u"


def _obj(fields: list[tuple[str, str]]) -> str:
    """Render a compact nested C aggregate initialiser."""
    return "{ " + ", ".join(f".{name} = {value}"
                            for name, value in fields) + " }"


@dataclass
class _Dict:
    offset: int
    revision: int
    count: int
    size: int
    reserved: int
    entry_header_offset: int
    entry_size: int
    name_offset: int

    @property
    def entry_header(self) -> int:
        return self.offset + self.entry_header_offset

    @property
    def entry_data(self) -> int:
        return self.entry_header + 4


class _Builder:
    """Collect typed overlays and raw gaps for one on-disk file."""

    def __init__(self, data: bytes, includes: list[str]):
        self.data = data
        self.includes = includes
        self.cover = bytearray(len(data))
        self.decls: list[str] = []
        self.copies: list[tuple[int, str, str]] = []
        self.serial = 0

    # -- typed objects ---------------------------------------------------
    def typed(self, offset: int, size: int, type_name: str,
              fields: list[tuple[str, str]], label: str) -> bool:
        if offset < 0 or size <= 0 or offset + size > len(self.data):
            return False
        if any(self.cover[offset:offset + size]):
            return False
        name = f"s_{label}_{self.serial}"
        self.serial += 1
        body = "".join(f"    .{field} = {value},\n"
                       for field, value in fields)
        self.decls.append(
            f"static const {type_name} {name} = {{\n{body}}};\n")
        self.copies.append((offset, f"&{name}", f"sizeof({name})"))
        self.cover[offset:offset + size] = b"\x01" * size
        return True

    def typed_array(self, offset: int, values: list[int], c_type: str,
                    label: str) -> bool:
        width = {"uint8_t": 1, "uint16_t": 2, "uint32_t": 4}[c_type]
        size = width * len(values)
        if not values or offset < 0 or offset + size > len(self.data):
            return False
        if any(self.cover[offset:offset + size]):
            return False
        name = f"s_{label}_{self.serial}"
        self.serial += 1
        rendered = ", ".join(_hex(value, width * 2) for value in values)
        self.decls.append(
            f"static const {c_type} {name}[{len(values)}] = "
            f"{{ {rendered} }};\n")
        self.copies.append((offset, name, f"sizeof({name})"))
        self.cover[offset:offset + size] = b"\x01" * size
        return True

    # -- file envelope ---------------------------------------------------
    def file_header(self) -> None:
        data = self.data
        if len(data) < 16:
            return
        self.typed(0x00, 16, "G3dFileHeader", [
            ("signature", _chars(data[0x00:0x04])),
            ("byte_order", _hex(_u16(data, 0x04), 4)),
            ("version", str(_u16(data, 0x06))),
            ("file_size", str(_u32(data, 0x08))),
            ("header_size", str(_u16(data, 0x0C))),
            ("block_count", str(_u16(data, 0x0E))),
        ], "file_header")
        count = min(_u16(data, 0x0E), 2)
        if count:
            offsets = [_u32(data, 0x10 + 4 * index)
                       for index in range(count)]
            self.typed_array(0x10, offsets, "uint32_t", "block_offset")

    def block_header(self, offset: int, label: str) -> None:
        data = self.data
        if offset < 0 or offset + 8 > len(data):
            return
        self.typed(offset, 8, "G3dBlockHeader", [
            ("magic", _chars(data[offset:offset + 4])),
            ("size", str(_u32(data, offset + 4))),
        ], label)

    # -- dictionaries ----------------------------------------------------
    def dictionary(self, offset: int, label: str) -> _Dict | None:
        data = self.data
        if offset < 0 or offset + 8 > len(data):
            return None
        revision, count, size, reserved, entry_header_offset = \
            struct.unpack_from("<BBHHH", data, offset)
        if count > _MAX_ENTRIES:
            return None
        if entry_header_offset < 8 or entry_header_offset + 4 > size:
            return None
        if offset + entry_header_offset + 4 > len(data):
            return None
        entry_size, name_offset = struct.unpack_from(
            "<HH", data, offset + entry_header_offset)
        if not 0 < entry_size <= _MAX_ENTRY_SIZE:
            return None
        self.typed(offset, 8, "G3dDictHeader", [
            ("revision", str(revision)),
            ("entry_count", str(count)),
            ("size", str(size)),
            ("reserved", str(reserved)),
            ("entry_header_offset", _hex(entry_header_offset, 4)),
        ], f"{label}_dict")
        self.typed(offset + entry_header_offset, 4, "G3dDictEntryHeader", [
            ("entry_size", str(entry_size)),
            ("name_offset", _hex(name_offset, 4)),
        ], f"{label}_entry_header")
        return _Dict(offset, revision, count, size, reserved,
                     entry_header_offset, entry_size, name_offset)

    def dict_offsets(self, dictionary: _Dict) -> list[int]:
        """Return the uint32 payload offsets stored in a dictionary."""
        data = self.data
        if dictionary.entry_size != 4:
            return []
        base = dictionary.entry_data
        if base + dictionary.count * 4 > len(data):
            return []
        return [_u32(data, base + 4 * index)
                for index in range(dictionary.count)]

    def dict_records(self, dictionary: _Dict) -> list[int]:
        """Return the start offset of every fixed-size record in a dict."""
        data = self.data
        step = dictionary.entry_size
        base = dictionary.entry_data
        if base + dictionary.count * step > len(data):
            return []
        return [base + index * step
                for index in range(dictionary.count)]

    # -- output ----------------------------------------------------------
    def raw_gaps(self) -> None:
        data = self.data
        index = 0
        while index < len(data):
            if self.cover[index]:
                index += 1
                continue
            start = index
            while index < len(data) and not self.cover[index]:
                index += 1
            chunk = data[start:index]
            name = f"s_raw_{start:04x}"
            values = ", ".join(f"0x{byte:02X}" for byte in chunk)
            self.decls.append(
                f"static const uint8_t {name}[{len(chunk)}] = "
                f"{{ {values} }};\n")
            self.copies.append((start, name, f"sizeof({name})"))

    def source(self) -> str:
        self.raw_gaps()
        includes = "".join(f'#include "{header}"\n'
                           for header in self.includes)
        lines = [
            "/* Generated typed table."
            " Do not commit. */\n",
            "#include <stdint.h>\n",
            "#include <stdio.h>\n",
            "#include <string.h>\n",
            includes,
            "\n",
        ]
        lines.extend(self.decls)
        lines.append("\nint main(int argc, char **argv)\n{\n")
        lines.append("    if (argc != 2) {\n")
        lines.append('        fprintf(stderr, "usage: %s out.bin\\n",'
                     " argv[0]);\n")
        lines.append("        return 2;\n    }\n")
        lines.append(f"    uint8_t out[{len(self.data)}];\n")
        lines.append("    memset(out, 0, sizeof out);\n")
        for offset, name, size in sorted(self.copies):
            lines.append(f"    memcpy(out + {_hex(offset, 4)}, {name},"
                         f" {size});\n")
        lines.append('    FILE *file = fopen(argv[1], "wb");\n')
        lines.append("    if (!file) {\n")
        lines.append("        perror(argv[1]);\n"
                     "        return 1;\n    }\n")
        lines.append("    if (fwrite(out, 1, sizeof out, file) != sizeof out)"
                     " {\n")
        lines.append("        fclose(file);\n        return 1;\n    }\n")
        lines.append("    return fclose(file) == 0 ? 0 : 1;\n}\n")
        return "".join(lines)


# ---------------------------------------------------------------------------
# NSBMD (BMD0) and MDL0
# ---------------------------------------------------------------------------

def _emit_model(data: bytes, builder: _Builder, base: int) -> None:
    builder.block_header(base, "mdl0_block")
    set_dict = builder.dictionary(base + 0x08, "mdl0_set")
    if set_dict is None:
        return
    for model_offset in builder.dict_offsets(set_dict):
        model = base + model_offset
        if model + 0x40 > len(data):
            continue
        size = _u32(data, model)
        if size < 0x40 or model + size > len(data):
            continue
        builder.typed(model, 20, "G3dModelHeader", [
            ("size", str(size)),
            ("sbc_offset", _hex(_u32(data, model + 0x04), 8)),
            ("material_offset", _hex(_u32(data, model + 0x08), 8)),
            ("shape_offset", _hex(_u32(data, model + 0x0C), 8)),
            ("envelope_offset", _hex(_u32(data, model + 0x10), 8)),
        ], "model")
        info = model + 0x14
        builder.typed(info, 44, "G3dModelInfo", [
            ("sbc_type", str(data[info + 0x00])),
            ("scaling_rule", str(data[info + 0x01])),
            ("texture_matrix_mode", str(data[info + 0x02])),
            ("node_count", str(data[info + 0x03])),
            ("material_count", str(data[info + 0x04])),
            ("shape_count", str(data[info + 0x05])),
            ("first_unused_matrix_stack", str(data[info + 0x06])),
            ("reserved", str(data[info + 0x07])),
            ("position_scale", _fx32(_u32(data, info + 0x08))),
            ("inverse_position_scale", _fx32(_u32(data, info + 0x0C))),
            ("vertex_count", str(_u16(data, info + 0x10))),
            ("polygon_count", str(_u16(data, info + 0x12))),
            ("triangle_count", str(_u16(data, info + 0x14))),
            ("quad_count", str(_u16(data, info + 0x16))),
            ("box_x", _fx16(_u16(data, info + 0x18))),
            ("box_y", _fx16(_u16(data, info + 0x1A))),
            ("box_z", _fx16(_u16(data, info + 0x1C))),
            ("box_w", _fx16(_u16(data, info + 0x1E))),
            ("box_h", _fx16(_u16(data, info + 0x20))),
            ("box_d", _fx16(_u16(data, info + 0x22))),
            ("box_position_scale", _fx32(_u32(data, info + 0x24))),
            ("box_inverse_position_scale",
             _fx32(_u32(data, info + 0x28))),
        ], "model_info")
        _emit_node_dict(data, builder, model, model + 0x40)
        _emit_material_set(data, builder, model,
                           model + _u32(data, model + 0x08))
        _emit_shape_set(data, builder, model,
                        model + _u32(data, model + 0x0C))


def _emit_node_dict(data: bytes, builder: _Builder, model: int,
                    offset: int) -> None:
    dictionary = builder.dictionary(offset, "node")
    if dictionary is None:
        return
    model_size = _u32(data, model)
    for node_offset in builder.dict_offsets(dictionary):
        node = offset + node_offset
        if not (model <= node < model + model_size):
            continue
        builder.typed(node, 4, "G3dNodeDataHeader", [
            ("flags", _hex(_u16(data, node), 4)),
            ("rotation_m00", _fx16(_u16(data, node + 2))),
        ], "node")


def _emit_material_set(data: bytes, builder: _Builder, model: int,
                       offset: int) -> None:
    model_size = _u32(data, model)
    if not (model <= offset < model + model_size):
        return
    builder.typed(offset, 4, "G3dMaterialSetHeader", [
        ("texture_to_material_offset", _hex(_u16(data, offset), 4)),
        ("palette_to_material_offset", _hex(_u16(data, offset + 2), 4)),
    ], "material_set")
    dictionary = builder.dictionary(offset + 4, "material")
    if dictionary is None:
        return
    for material_offset in builder.dict_offsets(dictionary):
        material = offset + material_offset
        if not (model <= material < model + model_size):
            continue
        builder.typed(material, 44, "G3dMaterialData", [
            ("item_tag", str(_u16(data, material + 0x00))),
            ("size", str(_u16(data, material + 0x02))),
            ("diffuse_ambient", _hex(_u32(data, material + 0x04), 8)),
            ("specular_emission", _hex(_u32(data, material + 0x08), 8)),
            ("polygon_attribute", _hex(_u32(data, material + 0x0C), 8)),
            ("polygon_attribute_mask",
             _hex(_u32(data, material + 0x10), 8)),
            ("texture_image_param", _hex(_u32(data, material + 0x14), 8)),
            ("texture_image_param_mask",
             _hex(_u32(data, material + 0x18), 8)),
            ("texture_palette_base", str(_u16(data, material + 0x1C))),
            ("flags", _hex(_u16(data, material + 0x1E), 4)),
            ("original_width", str(_u16(data, material + 0x20))),
            ("original_height", str(_u16(data, material + 0x22))),
            ("magnitude_s", _fx32(_u32(data, material + 0x24))),
            ("magnitude_t", _fx32(_u32(data, material + 0x28))),
        ], "material")


def _emit_shape_set(data: bytes, builder: _Builder, model: int,
                    offset: int) -> None:
    dictionary = builder.dictionary(offset, "shape")
    if dictionary is None:
        return
    model_size = _u32(data, model)
    for shape_offset in builder.dict_offsets(dictionary):
        shape = offset + shape_offset
        if not (model <= shape < model + model_size):
            continue
        builder.typed(shape, 16, "G3dShapeData", [
            ("item_tag", str(_u16(data, shape + 0x00))),
            ("size", str(_u16(data, shape + 0x02))),
            ("flags", _hex(_u32(data, shape + 0x04), 8)),
            ("display_list_offset", _hex(_u32(data, shape + 0x08), 8)),
            ("display_list_size", str(_u32(data, shape + 0x0C))),
        ], "shape")


# ---------------------------------------------------------------------------
# NSBTX (BTX0) and TEX0
# ---------------------------------------------------------------------------

def _tex_info_fields(data: bytes, offset: int) -> list[tuple[str, str]]:
    return [
        ("vram_key", _hex(_u32(data, offset + 0x00), 8)),
        ("texture_data_size", str(_u16(data, offset + 0x04))),
        ("dictionary_offset", _hex(_u16(data, offset + 0x06), 4)),
        ("flag", _obj([("raw", _hex(_u16(data, offset + 0x08), 4))])),
        ("reserved", str(_u16(data, offset + 0x0A))),
        ("texture_data_offset", _hex(_u32(data, offset + 0x0C), 8)),
    ]


def _emit_tex0(data: bytes, builder: _Builder, base: int) -> None:
    if base < 0 or base + 0x3C > len(data):
        return
    if data[base:base + 4] != _BLOCK_TEX0:
        return
    block = _obj([
        ("magic", _chars(data[base:base + 4])),
        ("size", str(_u32(data, base + 0x04))),
    ])
    info = _obj(_tex_info_fields(data, base + 0x08))
    info4x4_fields = _tex_info_fields(data, base + 0x18)
    info4x4_fields.append(
        ("palette_index_offset", _hex(_u32(data, base + 0x28), 8)))
    info4x4 = _obj(info4x4_fields)
    palette = _obj([
        ("vram_key", _hex(_u32(data, base + 0x2C), 8)),
        ("palette_data_size", str(_u16(data, base + 0x30))),
        ("flag", _obj([("raw", _hex(_u16(data, base + 0x32), 4))])),
        ("dictionary_offset", _hex(_u16(data, base + 0x34), 4)),
        ("reserved", str(_u16(data, base + 0x36))),
        ("palette_data_offset", _hex(_u32(data, base + 0x38), 8)),
    ])
    builder.typed(base, 60, "G3dTextureSetHeader", [
        ("block", block),
        ("texture_info", info),
        ("texture4x4_info", info4x4),
        ("palette_info", palette),
    ], "tex0_header")

    texture_dict = builder.dictionary(
        base + _u16(data, base + 0x0E), "texture")
    if texture_dict is not None and texture_dict.entry_size == 8:
        for offset in builder.dict_records(texture_dict):
            builder.typed(offset, 8, "G3dTextureEntry", [
                ("texture_image_param", _obj([
                    ("raw", _hex(_u32(data, offset), 8))])),
                ("extra_param", _obj([
                    ("raw", _hex(_u32(data, offset + 4), 8))])),
            ], "texture_entry")

    palette_dict = builder.dictionary(
        base + _u16(data, base + 0x34), "palette")
    if palette_dict is not None and palette_dict.entry_size == 4:
        for offset in builder.dict_records(palette_dict):
            builder.typed(offset, 4, "G3dPaletteEntry", [
                ("palette_offset", _hex(_u16(data, offset), 4)),
                ("flag", _obj([
                    ("raw", _hex(_u16(data, offset + 2), 4))])),
            ], "palette_entry")


# ---------------------------------------------------------------------------
# NSBCA (BCA0) and JNT0
# ---------------------------------------------------------------------------

def _emit_joint_set(data: bytes, builder: _Builder, base: int) -> None:
    builder.block_header(base, "jnt0_block")
    set_dict = builder.dictionary(base + 0x08, "jnt0_set")
    if set_dict is None:
        return
    for record_offset in builder.dict_offsets(set_dict):
        record = base + record_offset
        if record + 0x14 > len(data):
            continue
        node_count = _u16(data, record + 0x06)
        builder.typed(record, 20, "G3dJointAnimationHeader", [
            ("header", _obj(_animation_header(data, record))),
            ("frame_count", str(_u16(data, record + 0x04))),
            ("node_count", str(node_count)),
            ("flags", _hex(_u32(data, record + 0x08), 8)),
            ("pivot_rotation_offset",
             _hex(_u32(data, record + 0x0C), 8)),
            ("matrix_rotation_offset",
             _hex(_u32(data, record + 0x10), 8)),
        ], "joint_animation")
        table = record + 0x14
        if table + node_count * 2 > len(data):
            continue
        for index in range(node_count):
            node = record + _u16(data, table + index * 2)
            if node + 4 > len(data):
                continue
            builder.typed(node, 4, "G3dNodeDataHeader", [
                ("flags", _hex(_u16(data, node), 4)),
                ("rotation_m00", _fx16(_u16(data, node + 2))),
            ], "bca_node")


# ---------------------------------------------------------------------------
# NSBTP (BTP0) and PAT0
# ---------------------------------------------------------------------------

def _emit_pattern_set(data: bytes, builder: _Builder, base: int) -> None:
    builder.block_header(base, "pat0_block")
    set_dict = builder.dictionary(base + 0x08, "pat0_set")
    if set_dict is None:
        return
    for record_offset in builder.dict_offsets(set_dict):
        record = base + record_offset
        if record + 0x0C > len(data):
            continue
        builder.typed(record, 12, "G3dTexturePatternHeader", [
            ("header", _obj(_animation_header(data, record))),
            ("frame_count", str(_u16(data, record + 0x04))),
            ("texture_count", str(data[record + 0x06])),
            ("palette_count", str(data[record + 0x07])),
            ("texture_names_offset",
             _hex(_u16(data, record + 0x08), 4)),
            ("palette_names_offset",
             _hex(_u16(data, record + 0x0A), 4)),
        ], "pattern_animation")
        dictionary = builder.dictionary(record + 0x0C, "pattern")
        if dictionary is None or dictionary.entry_size != 8:
            continue
        for offset in builder.dict_records(dictionary):
            builder.typed(offset, 8, "G3dTexturePatternEntry", [
                ("frame_value_count", str(_u16(data, offset))),
                ("flags", _hex(_u16(data, offset + 2), 4)),
                ("frame_ratio", _fx16(_u16(data, offset + 4))),
                ("frame_value_offset", _hex(_u16(data, offset + 6), 4)),
            ], "pattern_entry")


# ---------------------------------------------------------------------------
# NSBTA (BTA0) and SRT0
# ---------------------------------------------------------------------------

def _srt_entry_fields(data: bytes, offset: int) -> list[tuple[str, str]]:
    names = ("scale_s", "scale_t", "rotation",
             "translation_s", "translation_t")
    fields: list[tuple[str, str]] = []
    for index, name in enumerate(names):
        info = offset + index * 8
        fields.append((name, _obj([
            ("raw", _hex(_u32(data, info), 8))])))
        fields.append((f"{name}_offset",
                       _hex(_u32(data, info + 4), 8)))
    return fields


def _emit_texture_srt_set(data: bytes, builder: _Builder,
                          base: int) -> None:
    builder.block_header(base, "srt0_block")
    set_dict = builder.dictionary(base + 0x08, "srt0_set")
    if set_dict is None:
        return
    for record_offset in builder.dict_offsets(set_dict):
        record = base + record_offset
        if record + 0x08 > len(data):
            continue
        builder.typed(record, 8, "G3dTextureSrtHeader", [
            ("header", _obj(_animation_header(data, record))),
            ("frame_count", str(_u16(data, record + 0x04))),
            ("flags", _obj([
                ("raw", _hex(data[record + 0x06], 2))])),
            ("texture_matrix_mode", str(data[record + 0x07])),
        ], "srt_animation")
        dictionary = builder.dictionary(record + 0x08, "srt")
        if dictionary is None or dictionary.entry_size != 40:
            continue
        for offset in builder.dict_records(dictionary):
            builder.typed(offset, 40, "G3dTextureSrtEntry",
                          _srt_entry_fields(data, offset), "srt_entry")


# ---------------------------------------------------------------------------
# NSBMA (BMA0) and MAT0
# ---------------------------------------------------------------------------

def _emit_material_animation_set(data: bytes, builder: _Builder,
                                 base: int) -> None:
    builder.block_header(base, "mat0_block")
    set_dict = builder.dictionary(base + 0x08, "mat0_set")
    if set_dict is None:
        return
    for record_offset in builder.dict_offsets(set_dict):
        record = base + record_offset
        if record + 0x08 > len(data):
            continue
        builder.typed(record, 8, "G3dMaterialAnimationHeader", [
            ("header", _obj(_animation_header(data, record))),
            ("frame_count", str(_u16(data, record + 0x04))),
            ("flags", _obj([
                ("raw", _hex(_u16(data, record + 0x06), 4))])),
        ], "material_animation")
        dictionary = builder.dictionary(record + 0x08, "material_animation")
        if dictionary is None or dictionary.entry_size != 20:
            continue
        for offset in builder.dict_records(dictionary):
            builder.typed(offset, 20, "G3dMaterialAnimationEntry", [
                ("diffuse", _obj([
                    ("raw", _hex(_u32(data, offset + 0x00), 8))])),
                ("ambient", _obj([
                    ("raw", _hex(_u32(data, offset + 0x04), 8))])),
                ("specular", _obj([
                    ("raw", _hex(_u32(data, offset + 0x08), 8))])),
                ("emission", _obj([
                    ("raw", _hex(_u32(data, offset + 0x0C), 8))])),
                ("polygon_alpha", _obj([
                    ("raw", _hex(_u32(data, offset + 0x10), 8))])),
            ], "material_animation_entry")


# ---------------------------------------------------------------------------
# Public entry points
# ---------------------------------------------------------------------------

def _animation_header(data: bytes, offset: int) -> list[tuple[str, str]]:
    return [
        ("category0", repr(chr(data[offset]))),
        ("revision", str(data[offset + 1])),
        ("category1", _chars(data[offset + 2:offset + 4])),
    ]


def _emit(data: bytes, includes: list[str],
          block_emitters: list[tuple[int, str]]) -> str:
    builder = _Builder(data, includes)
    builder.file_header()
    for offset, label in block_emitters:
        if label == "mdl0":
            _emit_model(data, builder, offset)
        elif label == "tex0":
            _emit_tex0(data, builder, offset)
        elif label == "jnt0":
            _emit_joint_set(data, builder, offset)
        elif label == "pat0":
            _emit_pattern_set(data, builder, offset)
        elif label == "srt0":
            _emit_texture_srt_set(data, builder, offset)
        elif label == "mat0":
            _emit_material_animation_set(data, builder, offset)
    return builder.source()


def _block_offsets(data: bytes) -> list[int]:
    if len(data) < 0x10:
        return []
    count = min(_u16(data, 0x0E), 2)
    offsets = []
    for index in range(count):
        offset = _u32(data, 0x10 + 4 * index)
        if 0 <= offset < len(data):
            offsets.append(offset)
    return offsets


def emit_nsbmd_source(data: bytes) -> str:
    blocks = []
    for offset in _block_offsets(data):
        magic = data[offset:offset + 4]
        if magic == _BLOCK_MDL0:
            blocks.append((offset, "mdl0"))
        elif magic == _BLOCK_TEX0:
            blocks.append((offset, "tex0"))
    return _emit(data, ["nitro/g3d/nsbmd.h", "nitro/g3d/nsbtx.h"], blocks)


def emit_nsbtx_source(data: bytes) -> str:
    blocks = [(offset, "tex0") for offset in _block_offsets(data)
              if data[offset:offset + 4] == _BLOCK_TEX0]
    return _emit(data, ["nitro/g3d/nsbtx.h"], blocks)


def emit_nsbca_source(data: bytes) -> str:
    blocks = [(offset, "jnt0") for offset in _block_offsets(data)
              if data[offset:offset + 4] == _BLOCK_JNT0]
    return _emit(data, ["nitro/g3d/nsbmd.h", "nitro/g3d/nsbca.h"], blocks)


def emit_nsbtp_source(data: bytes) -> str:
    blocks = [(offset, "pat0") for offset in _block_offsets(data)
              if data[offset:offset + 4] == _BLOCK_PAT0]
    return _emit(data, ["nitro/g3d/nsbtp.h"], blocks)


def emit_nsbta_source(data: bytes) -> str:
    blocks = [(offset, "srt0") for offset in _block_offsets(data)
              if data[offset:offset + 4] == _BLOCK_SRT0]
    return _emit(data, ["nitro/g3d/nsbta.h"], blocks)


def emit_nsbma_source(data: bytes) -> str:
    blocks = [(offset, "mat0") for offset in _block_offsets(data)
              if data[offset:offset + 4] == _BLOCK_MAT0]
    return _emit(data, ["nitro/g3d/nsbma.h"], blocks)


_EMITTERS = {
    _MAGIC_NSBMD: emit_nsbmd_source,
    _MAGIC_NSBTX: emit_nsbtx_source,
    _MAGIC_NSBCA: emit_nsbca_source,
    _MAGIC_NSBTP: emit_nsbtp_source,
    _MAGIC_NSBTA: emit_nsbta_source,
    _MAGIC_NSBMA: emit_nsbma_source,
}


def emit_source(data: bytes) -> str:
    """Return a complete C program that rebuilds ``data`` byte-for-byte."""
    if len(data) < 4:
        raise ValueError("not a Nitro G3D resource: file is too short")
    emitter = _EMITTERS.get(data[:4])
    if emitter is None:
        raise ValueError(f"unsupported G3D signature {data[:4]!r}")
    return emitter(data)
