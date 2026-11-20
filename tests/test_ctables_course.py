# Mario Kart DS Modding Trove
# tests/test_ctables_course.py — exact NKM/KCL/SPA C table rebuilds
# SPDX-License-Identifier: MIT
"""Synthetic fixtures for the typed course-file C table emitters.

The fixtures live entirely in this file; no stock game data is read.  Each
test compiles the generated C program with the real headers through
``tools.ctables.common.harness.compile_and_compare``.
"""
import random
import struct
import unittest

from tools.ctables.mkds import course_tables
from tools.ctables.common.harness import CC, compile_and_compare


def _noise(rng, size):
    return bytes(rng.randrange(256) for _ in range(size))


# ---------------------------------------------------------------- NKM


_NKM_SIZES = {
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


def _make_nkm(version, order, counts, tails, strides=None):
    """Build an NKM file from tags, counts, per-section tails and strides."""
    rng = random.Random(0xC0FFEE + version)
    strides = strides or {}
    bodies = []
    for tag in order:
        if tag == b"STAG":
            body = b"STAG" + _noise(rng, 40)
        else:
            stride = strides.get(tag, _NKM_SIZES[tag])
            count = counts.get(tag, 2)
            records = _noise(rng, count * stride)
            body = tag + struct.pack("<I", count) + records + tails.get(tag, b"")
        bodies.append(body)

    header_size = 8 + 4 * len(order)
    offsets = []
    cursor = 0
    for body in bodies:
        offsets.append(cursor)
        cursor += len(body)

    header = struct.pack("<4sHH", b"NKMD", version, header_size)
    table = struct.pack("<%dI" % len(offsets), *offsets)
    return header + table + b"".join(bodies)


class CourseTableTests(unittest.TestCase):
    @unittest.skipUnless(CC, "no host C compiler")
    def test_nkm_all_sections_exact(self):
        order = [
            b"STAG", b"AREA", b"OBJI", b"CAME", b"PATH", b"POIT", b"KTPS",
            b"KTPJ", b"KTP2", b"KTPC", b"KTPM", b"CPOI", b"CPAT", b"IPOI",
            b"IPAT", b"EPOI", b"EPAT", b"MEPO", b"MEPA",
        ]
        tails = {
            b"KTPC": b"\x00\x00\x00\x00",
            b"IPAT": b"\x00\x00\x00\x00",
            b"CAME": b"\xaa\xbb\xcc",
        }
        data = _make_nkm(37, order, {}, tails)

        source = course_tables.emit_nkm_source(data)
        ok, produced, error = compile_and_compare(source, data)
        self.assertTrue(ok, error or "NKM rebuild differs")
        self.assertEqual(produced, data)

        # Every stock section tag is represented by its typed struct.
        for tag, struct_name in (
                (b"OBJI", "NkmObjectEntry"),
                (b"PATH", "NkmPathEntry"),
                (b"POIT", "NkmPointEntry"),
                (b"STAG", "NkmStage"),
                (b"KTPS", "NkmKtpsEntry"),
                (b"KTPJ", "NkmKtpjEntry"),
                (b"KTP2", "NkmKtp2Entry"),
                (b"KTPC", "NkmKtpcEntry"),
                (b"KTPM", "NkmKtpmEntry"),
                (b"CPOI", "NkmCpoiEntry"),
                (b"CPAT", "NkmCpatEntry"),
                (b"IPOI", "NkmItemPointEntry"),
                (b"IPAT", "NkmPathLinkEntry"),
                (b"EPOI", "NkmEnemyPointEntry"),
                (b"EPAT", "NkmPathLinkEntry"),
                (b"MEPO", "NkmMissionEnemyPointEntry"),
                (b"MEPA", "NkmMissionPathEntry"),
                (b"AREA", "NkmAreaEntry"),
                (b"CAME", "NkmCameEntry"),
        ):
            self.assertIn("static const %s " % struct_name, source, tag)

        self.assertIn("static const NkmHeader nkm_header", source)
        self.assertIn("static const uint32_t nkm_section_offsets[]", source)
        self.assertIn("0x00000000u", source)
        self.assertEqual(
            course_tables.emit_source(data), source)

    @unittest.skipUnless(CC, "no host C compiler")
    def test_nkm_legacy_record_strides_exact(self):
        order = [b"STAG", b"OBJI", b"PATH", b"KTPJ", b"IPOI", b"AREA"]
        counts = {b"PATH": 0, b"AREA": 0, b"KTPJ": 2, b"IPOI": 2}
        tails = {b"PATH": b"\x00\x00\x00\x00", b"AREA": b"\x00\x00\x00\x00"}
        data = _make_nkm(
            30, order, counts, tails,
            strides={b"KTPJ": 28, b"IPOI": 16})

        source = course_tables.emit_nkm_source(data)
        ok, produced, error = compile_and_compare(source, data)
        self.assertTrue(ok, error or "legacy NKM rebuild differs")
        self.assertEqual(produced, data)

        # The typed structs are larger than the on-disk pre-v32/pre-v34
        # records, so the generated writer must copy only the prefix.
        self.assertIn(", 28, 2);", source)
        self.assertIn(", 16, 2);", source)
        self.assertIn("static const NkmKtpjEntry nkm_ktpj_records[]", source)
        self.assertIn("static const NkmItemPointEntry nkm_ipoi_records[]", source)

    @unittest.skipUnless(CC, "no host C compiler")
    def test_kcl_tables_exact(self):
        positions = [
            (0x00001000, -0x00002000, 0x00003000),
            (-0x00000001, 0x00000002, 0x7FFFFFFF),
        ]
        normals = [
            (0x1000, -0x0800, 0x0400),
            (-0x0001, 0x7FFF, -0x8000),
        ]
        normal_padding = b"\x00\x00"
        prisms = [
            (0x00002000, 1, 0, 0, 0, 0, 0x0004),
            (-0x00002000, 0, 1, 1, 0, 1, 0xFFF8),
        ]
        octree = bytes(range(16))

        position_table = 0x3C
        position_bytes = b"".join(struct.pack("<3i", *p) for p in positions)
        normal_table = position_table + len(position_bytes)
        normal_bytes = b"".join(struct.pack("<3h", *n) for n in normals)
        prism_table = normal_table + len(normal_bytes) + len(normal_padding)
        prism_bytes = b"".join(struct.pack("<i6H", *p) for p in prisms)
        block_table = prism_table + len(prism_bytes)

        header = struct.pack(
            "<15I",
            position_table, normal_table, prism_table - 0x10, block_table,
            0x00001000, 0xFFF00000, 0x00001000, 0xFFFFF000,
            0xFFFFE000, 0xFFFFFC00, 0xFFFFE000,
            10, 3, 9, 0x00019000)
        data = (header + position_bytes + normal_bytes + normal_padding
                + prism_bytes + octree)

        source = course_tables.emit_kcl_source(data)
        ok, produced, error = compile_and_compare(source, data)
        self.assertTrue(ok, error or "KCL rebuild differs")
        self.assertEqual(produced, data)

        self.assertIn("static const KclHeader kcl_header", source)
        self.assertIn("static const KclVecFx32 kcl_positions[]", source)
        self.assertIn("static const KclVecFx16 kcl_normals[]", source)
        self.assertIn("static const KclPrism kcl_prisms[]", source)
        self.assertIn("static const uint8_t kcl_normal_padding[]", source)
        self.assertIn("static const uint8_t kcl_octree[]", source)
        self.assertIn("0x0000003cu", source)
        self.assertEqual(course_tables.emit_source(data), source)

    @unittest.skipUnless(CC, "no host C compiler")
    def test_spa_header_descriptors_and_payloads_exact(self):
        rng = random.Random(0x5A5A)
        emitter_block = _noise(rng, 20)

        textures = [
            # texture data 6 bytes, palette 4, palette index 2
            (32 + 6 + 4 + 2, 6, 32 + 6, 4, 32 + 6 + 4, 2),
            # texture data only
            (32 + 3, 3, 32 + 3, 0, 32 + 3, 0),
        ]
        records = []
        for block_size, tsize, po, ps, pio, pis in textures:
            params = rng.randrange(0x100000000)
            record = struct.pack(
                "<4sIIIIIII", b" TPS", params, tsize, po, ps, pio, pis,
                block_size)
            record += _noise(rng, block_size - 32)
            records.append(record)
        texture_block = b"".join(records) + b"\xde\xad\xbe"
        texture_offset = 32 + len(emitter_block)

        header = struct.pack(
            "<4sIHHIIIII", b" APS", 0x315F3231, 2, len(textures), 0,
            len(emitter_block), len(texture_block), texture_offset, 0)
        data = header + emitter_block + texture_block

        source = course_tables.emit_spa_source(data)
        ok, produced, error = compile_and_compare(source, data)
        self.assertTrue(ok, error or "SPA rebuild differs")
        self.assertEqual(produced, data)

        self.assertIn("static const SpaHeader spa_header", source)
        self.assertIn("static const SpaTextureHeader spa_textures[]", source)
        self.assertIn(".params = { .raw = 0x", source)
        self.assertIn("static const uint8_t spa_emitter_block[]", source)
        self.assertIn("static const uint8_t spa_texture_0_data[]", source)
        self.assertIn("static const uint8_t spa_texture_0_palette[]", source)
        self.assertIn("static const uint8_t spa_texture_0_palette_index[]", source)
        self.assertIn("static const uint8_t spa_texture_block_tail[]", source)
        self.assertEqual(course_tables.emit_source(data), source)


if __name__ == "__main__":
    unittest.main()
