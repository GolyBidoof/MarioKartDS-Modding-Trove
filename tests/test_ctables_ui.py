# Mario Kart DS Modding Trove
# tests/test_ctables_ui.py — typed UI C tables rebuild exact bytes
# SPDX-License-Identifier: MIT
"""Synthetic round-trip tests for tools/ctables/ui_*.py."""
import struct
import unittest

from tools.ctables.mkds import ui_tables
from tools.ctables.common.harness import CC, compile_and_compare

HEADER = "<4sHH"


def coord(value, origin=0, param=0):
    return ((value & 0x0FFF) | ((origin & 0x3) << 12)
            | ((param & 0x3) << 14))


def make_bncl(cells, reserved=0):
    data = bytearray(struct.pack(HEADER, b"JNCL", reserved, len(cells)))
    for x, y, cell_id in cells:
        data += struct.pack("<HHI", x, y, cell_id)
    return bytes(data)


def pack_bnll(records, pool, reserved=0):
    data = bytearray(struct.pack(HEADER, b"JNLL", reserved, len(records)))
    for record in records:
        data += struct.pack("<HHbbHI", *record)
    data += pool
    return bytes(data)


def make_bnll(entries, reserved=0):
    """entries: (x, y, h_space, v_space, style, text)."""
    count = len(entries)
    pool = bytearray()
    records = []
    for x, y, h_space, v_space, style, text in entries:
        string_offset = 8 + 12 * count + len(pool)
        pool += text.encode("utf-16-le") + b"\x00\x00"
        records.append((x, y, h_space, v_space, style, string_offset))
    return pack_bnll(records, bytes(pool), reserved)


def make_bnbl(boxes, reserved=0):
    data = bytearray(struct.pack(HEADER, b"JNBL", reserved, len(boxes)))
    for x, y, width, height in boxes:
        data += struct.pack("<HHBB", x, y, width, height)
    return bytes(data)


def make_kbd(keys):
    data = bytearray()
    for x, y, width, height, chain_step, key_id in keys:
        data += struct.pack("<BBBBhH", x, y, width, height, chain_step, key_id)
    return bytes(data)


def make_kbdmap(characters):
    return b"\xFF\xFE" + struct.pack("<%dH" % len(characters), *characters)


def make_lld(entries, trailer=b"\x00" * 8):
    data = bytearray(struct.pack("<H", len(entries)))
    for element_id, x, y, flags in entries:
        data += struct.pack("<HHHH", element_id, x, y, flags)
    data += trailer
    return bytes(data)


def make_nbfp(colors):
    return struct.pack("<16H", *colors)


def make_nbfc(pattern=None):
    if pattern is None:
        pattern = bytes((index * 7 + 3) & 0xFF for index in range(512))
    return pattern


class UiTableRoundTripTests(unittest.TestCase):
    @unittest.skipUnless(CC, "no host C compiler")
    def assertRoundTrip(self, source, expected):
        ok, produced, error = compile_and_compare(source, expected)
        if ok:
            return
        if error:
            self.fail(error)
        limit = min(len(produced), len(expected))
        mismatch = next(
            (index for index in range(limit)
             if produced[index] != expected[index]), limit)
        self.fail(
            "byte mismatch at 0x%X (produced %d bytes, expected %d)\n"
            "produced: %s\nexpected: %s"
            % (mismatch, len(produced), len(expected),
               produced[mismatch:mismatch + 16].hex(" "),
               expected[mismatch:mismatch + 16].hex(" ")))

    @unittest.skipUnless(CC, "no host C compiler")
    def test_bncl_round_trip(self):
        data = make_bncl([
            (coord(-16, 1), coord(32, 1), 15),
            (coord(42, 1), coord(300, 2, 1), 0),
            (coord(343, 3), coord(0, 0), 57),
        ], reserved=0xABCD)
        source = ui_tables.bncl.emit_source(data)
        self.assertIn('#include "nitro/mkds/ui/bncl.h"', source)
        self.assertIn(".reserved = 43981,", source)
        self.assertIn("MkdsUiCellElement", source)
        self.assertIn(".bits = { .value = -16", source)
        self.assertIn("MKDS_UI_ORIGIN_CENTER", source)
        self.assertIn(".cell_id = 57", source)
        self.assertRoundTrip(source, data)

    @unittest.skipUnless(CC, "no host C compiler")
    def test_bncl_empty(self):
        data = make_bncl([])
        self.assertRoundTrip(ui_tables.bncl.emit_source(data), data)

    @unittest.skipUnless(CC, "no host C compiler")
    def test_bnll_round_trip_strings(self):
        data = make_bnll([
            (coord(7, 0), coord(133, 2), 1, 0, 0x000D, "OK"),
            (coord(128, 1, 1), coord(173, 1), -1, 2, 0x200E,
             "\u30a2\u30a4\u30c6\u30e0"),
            (coord(0, 0, 3), coord(0, 0), 127, -128, 0xF0FF, ""),
        ], reserved=0x1234)
        source = ui_tables.bnll.emit_source(data)
        self.assertIn('#include "nitro/mkds/ui/bnll.h"', source)
        self.assertIn(".reserved = 4660,", source)
        self.assertIn("MkdsUiLabelElement", source)
        self.assertIn("MKDS_UI_LINE_ALIGN_CENTER", source)
        self.assertIn(".h_space = -1", source)
        self.assertIn(".style = { .bits = { .color = 14", source)
        self.assertIn(".string_offset = 0x0000002C", source)
        self.assertIn("label_string_2", source)
        self.assertIn("0x30A2", source)
        self.assertRoundTrip(source, data)

    @unittest.skipUnless(CC, "no host C compiler")
    def test_bnll_shared_string(self):
        count = 2
        pool_base = 8 + 12 * count
        pool = "OK\x00".encode("utf-16-le")
        data = pack_bnll([
            (coord(1), coord(2), 0, 0, 0x0001, pool_base),
            (coord(3), coord(4), 0, 0, 0x0002, pool_base),
        ], pool)
        source = ui_tables.bnll.emit_source(data)
        self.assertEqual(source.count("static const uint16_t label_string_"), 1)
        self.assertRoundTrip(source, data)

    @unittest.skipUnless(CC, "no host C compiler")
    def test_bnll_raw_pool_fallback(self):
        count = 2
        pool_base = 8 + 12 * count
        pool = b"\x00\x00" + b"A\x00\x00\x00" + b"\x00\x00"
        data = pack_bnll([
            (coord(1), coord(2), 0, 0, 0x0001, pool_base + 2),
            (coord(3), coord(4), 0, 0, 0x0002, pool_base + 4),
        ], pool)
        source = ui_tables.bnll.emit_source(data)
        self.assertIn("static const uint8_t string_pool[]", source)
        self.assertRoundTrip(source, data)

    @unittest.skipUnless(CC, "no host C compiler")
    def test_bnbl_round_trip(self):
        data = make_bnbl([
            (coord(39, 1), coord(29, 1), 40, 40),
            (coord(219, 1), coord(133, 1), 200, 200),
            (coord(-1, 1), coord(0, 2), 1, 1),
        ], reserved=0x4321)
        source = ui_tables.bnbl.emit_source(data)
        self.assertIn('#include "nitro/mkds/ui/bnbl.h"', source)
        self.assertIn(".reserved = 17185,", source)
        self.assertIn("MkdsUiBoxElement", source)
        self.assertIn(".width = 200", source)
        self.assertRoundTrip(source, data)

    @unittest.skipUnless(CC, "no host C compiler")
    def test_bnbl_empty(self):
        data = make_bnbl([])
        self.assertRoundTrip(ui_tables.bnbl.emit_source(data), data)

    @unittest.skipUnless(CC, "no host C compiler")
    def test_kbd_round_trip(self):
        data = make_kbd([
            (218, 33, 31, 20, 0, 1),
            (255, 52, 1, 1, -2, 2),
            (88, 96, 99, 20, 3, 3),
        ])
        source = ui_tables.kbd.emit_source(data)
        self.assertIn('#include "nitro/mkds/ui/kbd.h"', source)
        self.assertIn("MkdsUiKeyEntry", source)
        self.assertIn(".chain_step = -2", source)
        self.assertIn(".key_id = 3", source)
        self.assertRoundTrip(source, data)

    @unittest.skipUnless(CC, "no host C compiler")
    def test_kbd_empty(self):
        self.assertRoundTrip(ui_tables.kbd.emit_source(b""), b"")

    @unittest.skipUnless(CC, "no host C compiler")
    def test_kbdmap_round_trip(self):
        data = make_kbdmap([
            0x0031, 0x0032, 0x3042, 0x30A2, 0xE000, 0x20AC, 0x0000,
        ])
        source = ui_tables.kbdmap.emit_source(data)
        self.assertIn('#include "nitro/mkds/ui/kbdmap.h"', source)
        self.assertIn("MKDS_UI_KBDMAP_PREFIX_SIZE", source)
        self.assertIn("0xFF, 0xFE", source)
        self.assertIn("0xE000", source)
        self.assertRoundTrip(source, data)

    @unittest.skipUnless(CC, "no host C compiler")
    def test_kbdmap_bom_only(self):
        data = b"\xFF\xFE"
        self.assertRoundTrip(ui_tables.kbdmap.emit_source(data), data)

    @unittest.skipUnless(CC, "no host C compiler")
    def test_lld_round_trip(self):
        data = make_lld([
            (0, 128, 96, 1),
            (1, 200, 172, 0),
            (42, 0, 65535, 2),
        ], trailer=b"\x00\x00\x00\x00\x00\x00\x00\x00")
        source = ui_tables.lld.emit_source(data)
        self.assertIn('#include "nitro/mkds/ui/lld.h"', source)
        self.assertIn("MkdsUiEmblemEntry", source)
        self.assertIn(".flags = 2", source)
        self.assertIn("lld_trailer", source)
        self.assertRoundTrip(source, data)

    @unittest.skipUnless(CC, "no host C compiler")
    def test_lld_preserves_trailer(self):
        trailer = b"\xDE\xAD\xBE\xEF\x01\x02\x03\x04"
        data = make_lld([(7, 1, 2, 1)], trailer=trailer)
        source = ui_tables.lld.emit_source(data)
        self.assertRoundTrip(source, data)

    @unittest.skipUnless(CC, "no host C compiler")
    def test_lld_empty(self):
        data = make_lld([])
        self.assertRoundTrip(ui_tables.lld.emit_source(data), data)

    @unittest.skipUnless(CC, "no host C compiler")
    def test_nbfp_round_trip(self):
        colors = [
            0x7E00, 0x7FFF, 0x001F, 0x03E0, 0x7C00, 0xFFFF,
            0x0000, 0x1234, 0x5678, 0x7FFF, 0x4000, 0x0200,
            0x0010, 0x2108, 0x4210, 0x6318,
        ]
        data = make_nbfp(colors)
        source = ui_tables.nbfp.emit_source(data)
        self.assertIn('#include "nitro/mkds/ui/nbfp.h"', source)
        self.assertIn("MkdsUiBannerColor", source)
        self.assertIn(".bits = { .red = 0, .green = 16, .blue = 31", source)
        self.assertIn(".reserved = 1", source)
        self.assertIn("MKDS_UI_NBFP_COLOR_COUNT", source)
        self.assertRoundTrip(source, data)

    @unittest.skipUnless(CC, "no host C compiler")
    def test_nbfc_round_trip(self):
        data = make_nbfc()
        source = ui_tables.nbfc.emit_source(data)
        self.assertIn('#include "nitro/mkds/ui/nbfc.h"', source)
        self.assertIn("MKDS_UI_NBFC_TILES", source)
        self.assertIn("MKDS_UI_NBFC_TILE_HEIGHT", source)
        self.assertIn("MkdsUiBannerTileRow", source)
        self.assertRoundTrip(source, data)


class UiTableDispatchTests(unittest.TestCase):
    def test_aliases_select_the_same_emitter(self):
        data = make_bncl([(coord(1), coord(2), 3)])
        expected = ui_tables.bncl.emit_source(data)
        self.assertEqual(ui_tables.emit_source("bncl", data), expected)
        self.assertEqual(ui_tables.emit_source(".JNCL", data), expected)
        self.assertEqual(ui_tables.emit_source("JNCL", data), expected)
        self.assertEqual(ui_tables.emit_bncl(data), expected)

    def test_format_map_covers_all_ui_containers(self):
        self.assertEqual(
            set(ui_tables.FORMATS),
            {"bncl", "bnll", "bnbl", "kbd", "kbdmap", "lld",
             "nbfp", "nbfc"},
        )

    def test_unknown_format_is_rejected(self):
        with self.assertRaises(ValueError):
            ui_tables.emit_source("ncer", b"")

    def test_bad_sizes_and_magics_are_rejected(self):
        with self.assertRaises(ValueError):
            ui_tables.bncl.emit_source(b"JNCL")
        with self.assertRaises(ValueError):
            ui_tables.bncl.emit_source(
                struct.pack(HEADER, b"JNLL", 0, 0))
        with self.assertRaises(ValueError):
            ui_tables.bncl.emit_source(
                struct.pack(HEADER, b"JNCL", 0, 2) + b"\x00" * 8)
        with self.assertRaises(ValueError):
            ui_tables.bnbl.emit_source(
                struct.pack(HEADER, b"JNBL", 0, 1))
        with self.assertRaises(ValueError):
            ui_tables.kbd.emit_source(b"\x00" * 7)
        with self.assertRaises(ValueError):
            ui_tables.kbdmap.emit_source(b"\xFF")
        with self.assertRaises(ValueError):
            ui_tables.kbdmap.emit_source(b"\xFE\xFF\x00\x00")
        with self.assertRaises(ValueError):
            ui_tables.kbdmap.emit_source(b"\xFF\xFE\x00")
        with self.assertRaises(ValueError):
            ui_tables.lld.emit_source(struct.pack("<H", 2) + b"\x00" * 8)
        with self.assertRaises(ValueError):
            ui_tables.nbfp.emit_source(b"\x00" * 31)
        with self.assertRaises(ValueError):
            ui_tables.nbfc.emit_source(b"\x00" * 511)

    def test_bnll_rejects_bad_string_offsets(self):
        base = 8 + 12
        with self.assertRaises(ValueError):
            ui_tables.bnll.emit_source(pack_bnll(
                [(0, 0, 0, 0, 0, 0x1000)], b"\x00\x00"))
        with self.assertRaises(ValueError):
            ui_tables.bnll.emit_source(pack_bnll(
                [(0, 0, 0, 0, 0, base + 1)], b"\x00\x00\x00\x00"))
        with self.assertRaises(ValueError):
            ui_tables.bnll.emit_source(pack_bnll(
                [(0, 0, 0, 0, 0, base)], b"A\x00"))
        with self.assertRaises(ValueError):
            ui_tables.bnll.emit_source(
                struct.pack(HEADER, b"JNLL", 0, 2) + b"\x00" * 12)


if __name__ == "__main__":
    unittest.main()
