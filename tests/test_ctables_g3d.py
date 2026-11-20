# Mario Kart DS Modding Trove
# tests/test_ctables_g3d.py — synthetic typed G3D C-table rebuild tests
# SPDX-License-Identifier: MIT
"""Synthetic G3D fixtures for the typed C-table emitters; no game data."""
import struct
import unittest

from tools.ctables.generic import g3d_tables
from tools.ctables.common import harness

# Each fixture is assembled from typed records plus dictionary scaffolding and
# then rebuilt through the generated C program.  The checks are byte-exact, so
# any offset, padding or bitfield change is caught even when the result still
# parses as a G3D resource.


def _dict(entries, names):
    """Build one Nitro dictionary with Patricia nodes and 16-byte names."""
    count = len(entries)
    entry_size = len(entries[0])
    entry_header_offset = 8 + 4 * (count + 1)
    name_offset = 4 + count * entry_size
    names_offset = entry_header_offset + name_offset
    size = names_offset + 16 * count
    nodes = b"".join(bytes((0x7F, 1, 0, 0)) for _ in range(count + 1))
    body = b"".join(entries)
    name_table = b"".join(name.encode("ascii").ljust(16, b"\0")
                          for name in names)
    header = struct.pack("<BBHHH", 0, count, size, 8, entry_header_offset)
    entry_header = struct.pack("<HH", entry_size, name_offset)
    result = header + nodes + entry_header + body + name_table
    assert len(result) == size
    return result


def _file(magic, version, blocks):
    """Assemble a G3D envelope around already-built blocks."""
    header_size = 16 + 4 * len(blocks)
    out = bytearray(header_size)
    offsets = []
    for block in blocks:
        while len(out) & 3:
            out.append(0)
        offsets.append(len(out))
        out += block
    out[0:4] = magic
    struct.pack_into("<HHIHH", out, 4, 0xFEFF, version, len(out), 16,
                     len(blocks))
    for index, offset in enumerate(offsets):
        struct.pack_into("<I", out, 16 + 4 * index, offset)
    return bytes(out)


def _model():
    """One node, one material and one shape, with a small display list."""
    model = bytearray(0x10C)
    struct.pack_into("<IIIII", model, 0x00,
                     0x10C, 0x104, 0x6C, 0xC4, 0x10C)
    info = bytearray(0x2C)
    info[0:8] = bytes((0, 1, 0, 1, 1, 1, 0, 0))
    struct.pack_into("<iiHHHH", info, 0x08,
                     0x1000, 0x1000, 24, 6, 4, 2)
    struct.pack_into("<hhhhhh", info, 0x18,
                     -0x100, 0x100, -0x80, 0x200, 0x200, 0x200)
    struct.pack_into("<ii", info, 0x24, 0x1000, 0x1000)
    model[0x14:0x40] = info

    node_dict = _dict([struct.pack("<I", 0x28)], ["world_root"])
    model[0x40:0x40 + len(node_dict)] = node_dict
    struct.pack_into("<Hh", model, 0x68, 0x0007, 0x1000)

    material = struct.pack(
        "<HHIIIIIIHHHHii",
        0, 0x2C,
        0x00008000, 0x80800000, 0x001F00FF, 0xFFFFFFFF,
        0x08000000, 0xFFFFFFFF,
        0, 0x1FCE, 32, 32, 0x1000, 0x1000)
    material_dict = _dict([struct.pack("<I", 0x2C)], ["body_mat"])
    material_set = struct.pack("<HH", 0, 0) + material_dict + material
    assert len(material_set) == 0x58
    model[0x6C:0xC4] = material_set

    shape_dict = _dict([struct.pack("<I", 0x28)], ["polygon0"])
    model[0xC4:0xC4 + len(shape_dict)] = shape_dict
    struct.pack_into("<HHIII", model, 0xEC,
                     0, 16, 0x06, 0x10, 8)
    model[0xFC:0x104] = bytes.fromhex("4024262703000000")
    model[0x104:0x10C] = bytes.fromhex("c0fe40010001c0fe")
    return bytes(model)


def _tex0_block():
    """Two textures and two palettes, with image and palette payloads."""
    texture_entries = [
        struct.pack("<II", 0x08000000, 0x80004008),
        struct.pack("<II", 0x10004210, 0x00004010),
    ]
    palette_entries = [
        struct.pack("<HH", 0, 0x0001),
        struct.pack("<HH", 8, 0x0000),
    ]
    texture_dict = _dict(texture_entries, ["bodyA", "bodyB"])
    palette_dict = _dict(palette_entries, ["bodyA_pl", "bodyB_pl"])
    texture_data = bytes(range(16))
    palette_data = bytes.fromhex("ff7fff7fff7f00000000000000000000")

    out = bytearray(0x3C)
    out[0:4] = b"TEX0"
    struct.pack_into("<IHHHHI", out, 0x08,
                     0, 2, 0x3C, 0, 0, 0xC4)
    struct.pack_into("<IHHHHII", out, 0x18,
                     0, 0, 0x3C, 0, 0, 0xC4, 0xC4)
    struct.pack_into("<IHHHHI", out, 0x2C,
                     0, 2, 0x8000, 0x84, 0, 0xD4)
    out += texture_dict
    out += palette_dict
    out += texture_data
    out += palette_data
    struct.pack_into("<I", out, 0x04, len(out))
    return bytes(out)


def _bmd0(with_tex=False):
    model_block = bytearray(8 + 0x28 + 0x10C)
    model_block[0:4] = b"MDL0"
    model_block[8:8 + 0x28] = _dict([struct.pack("<I", 0x30)], ["model0"])
    model_block[0x30:] = _model()
    struct.pack_into("<I", model_block, 4, len(model_block))
    blocks = [bytes(model_block)]
    if with_tex:
        blocks.append(_tex0_block())
    return _file(b"BMD0", 2, blocks)


def _nsbtx():
    return _file(b"BTX0", 1, [_tex0_block()])


def _nsbca():
    record = bytearray(0x2C)
    record[0:4] = b"J\0AC"
    struct.pack_into("<HHII", record, 0x04, 10, 2, 0, 0x20)
    struct.pack_into("<I", record, 0x10, 0x20)
    struct.pack_into("<HH", record, 0x14, 0x18, 0x1C)
    struct.pack_into("<Hh", record, 0x18, 0x0007, 0x1000)
    struct.pack_into("<Hh", record, 0x1C, 0x0003, 0x0000)
    struct.pack_into("<HhhHhh", record, 0x20,
                     0x0001, 0x1000, 0, 0x0002, 0, -0x1000)
    block = bytearray(8 + 0x28 + len(record))
    block[0:4] = b"JNT0"
    block[8:8 + 0x28] = _dict([struct.pack("<I", 0x30)], ["walk"])
    block[0x30:] = record
    struct.pack_into("<I", block, 4, len(block))
    return _file(b"BCA0", 1, [bytes(block)])


def _nsbtp():
    record = bytearray(0x84)
    record[0:4] = b"M\0PT"
    struct.pack_into("<HBBHH", record, 0x04, 8, 2, 2, 0x44, 0x64)
    inner = _dict([struct.pack("<HhH", 3, 0, 0x38)], ["mat0"])
    record[0x0C:0x0C + len(inner)] = inner
    struct.pack_into("<HBBHBBHBB", record, 0x38,
                     0, 1, 0, 2, 1, 1, 4, 0, 1)
    record[0x44:0x54] = b"bodyA".ljust(16, b"\0")
    record[0x54:0x64] = b"bodyB".ljust(16, b"\0")
    record[0x64:0x74] = b"bodyA_pl".ljust(16, b"\0")
    record[0x74:0x84] = b"bodyB_pl".ljust(16, b"\0")
    block = bytearray(8 + 0x28 + len(record))
    block[0:4] = b"PAT0"
    block[8:8 + 0x28] = _dict([struct.pack("<I", 0x30)], ["paint"])
    block[0x30:] = record
    struct.pack_into("<I", block, 4, len(block))
    return _file(b"BTP0", 1, [bytes(block)])


def _nsbta():
    entry = struct.pack(
        "<10I",
        0x20000014, 0x1000,
        0x20000014, 0x1000,
        0x20000014, 0x10000000,
        0x00000014, 0x54,
        0x00000014, 0x58)
    record = bytearray(0x5C)
    record[0:4] = b"M\0AT"
    struct.pack_into("<HBB", record, 0x04, 20, 3, 0x10)
    inner = _dict([entry], ["mat0"])
    record[0x08:0x08 + len(inner)] = inner
    struct.pack_into("<II", record, 0x54, 0x1000, 0x2000)
    block = bytearray(8 + 0x28 + len(record))
    block[0:4] = b"SRT0"
    block[8:8 + 0x28] = _dict([struct.pack("<I", 0x30)], ["scroll"])
    block[0x30:] = record
    struct.pack_into("<I", block, 4, len(block))
    return _file(b"BTA0", 1, [bytes(block)])


def _nsbma():
    entry = struct.pack(
        "<5I",
        0x00007FFF, 0x00004210, 0x00002108, 0x00001084, 0x0000001F)
    record = bytearray(0x40)
    record[0:4] = b"M\0AM"
    struct.pack_into("<HH", record, 0x04, 12, 1)
    inner = _dict([entry], ["mat0"])
    record[0x08:0x08 + len(inner)] = inner
    block = bytearray(8 + 0x28 + len(record))
    block[0:4] = b"MAT0"
    block[8:8 + 0x28] = _dict([struct.pack("<I", 0x30)], ["fade"])
    block[0x30:] = record
    struct.pack_into("<I", block, 4, len(block))
    return _file(b"BMA0", 1, [bytes(block)])


FIXTURES = {
    "nsbmd": (_bmd0(), "nitro/g3d/nsbmd.h", "G3dModelHeader"),
    "nsbmd_tex": (_bmd0(with_tex=True), "nitro/g3d/nsbtx.h",
                  "G3dTextureSetHeader"),
    "nsbtx": (_nsbtx(), "nitro/g3d/nsbtx.h", "G3dTextureSetHeader"),
    "nsbca": (_nsbca(), "nitro/g3d/nsbca.h", "G3dJointAnimationHeader"),
    "nsbtp": (_nsbtp(), "nitro/g3d/nsbtp.h", "G3dTexturePatternHeader"),
    "nsbta": (_nsbta(), "nitro/g3d/nsbta.h", "G3dTextureSrtHeader"),
    "nsbma": (_nsbma(), "nitro/g3d/nsbma.h", "G3dMaterialAnimationHeader"),
}


@unittest.skipUnless(harness.CC, "no host C compiler")
class G3dTableTests(unittest.TestCase):
    def test_fixtures_are_well_formed(self):
        for name, (data, _, _) in FIXTURES.items():
            with self.subTest(name=name):
                self.assertGreaterEqual(len(data), 16)
                self.assertEqual(data[4:6], b"\xff\xfe")

    def test_emit_source_is_exact(self):
        for name, (data, _, _) in FIXTURES.items():
            with self.subTest(name=name):
                source = g3d_tables.emit_source(data)
                ok, produced, error = harness.compile_and_compare(
                    source, data)
                self.assertTrue(ok, error or produced.hex())

    def test_typed_records_and_headers_are_visible(self):
        for name, (data, header, type_name) in FIXTURES.items():
            with self.subTest(name=name):
                source = g3d_tables.emit_source(data)
                self.assertIn(f'#include "{header}"', source)
                self.assertIn(f"static const {type_name} ", source)
                self.assertIn("s_block_offset_", source)
                self.assertIn("memcpy(out + 0x", source)

    def test_union_bitfield_style(self):
        checks = {
            "nsbtx": ("G3dTextureEntry", "G3dPaletteEntry"),
            "nsbta": ("G3dTextureSrtEntry",),
            "nsbma": ("G3dMaterialAnimationEntry",),
        }
        for name, types in checks.items():
            with self.subTest(name=name):
                source = g3d_tables.emit_source(FIXTURES[name][0])
                self.assertIn(".raw =", source)
                for type_name in types:
                    self.assertIn(f"static const {type_name} ", source)
                self.assertNotIn("_SHIFT =", source)

    def test_offsets_are_hexadecimal(self):
        source = g3d_tables.emit_source(FIXTURES["nsbmd"][0])
        self.assertIn(".sbc_offset = 0x", source)
        self.assertIn(".material_offset = 0x", source)
        self.assertIn(".display_list_offset = 0x", source)
        source = g3d_tables.emit_source(FIXTURES["nsbtx"][0])
        self.assertIn(".dictionary_offset = 0x", source)
        self.assertIn(".texture_data_offset = 0x", source)

    def test_rejects_non_g3d_data(self):
        with self.assertRaises(ValueError):
            g3d_tables.emit_source(b"NOPE" + b"\0" * 32)
        with self.assertRaises(ValueError):
            g3d_tables.emit_source(b"MDL0" + b"\0" * 32)


if __name__ == "__main__":
    unittest.main()
