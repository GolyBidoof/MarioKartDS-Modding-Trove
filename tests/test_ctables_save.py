# Mario Kart DS Modding Trove
# tests/test_ctables_save.py — exact typed-C rebuilds for save, ghost and kart tables
# SPDX-License-Identifier: MIT
"""Synthetic round-trips for tools/ctables/mkds/save_tables.py.

Every fixture is generated in memory; no stock game data is read.  Each test
compiles a complete C program with harness.compile_and_compare and requires the
produced bytes to match the fixture exactly.

The save tests use *decrypted* blocks.  Flash encryption is intentionally not
implemented here (the tables are not part of the shared headers), so the tests
check the payload, the NKSY plaintext tag and the typed footer, not the
encrypted on-card image.
"""
from __future__ import annotations

import random
import unittest

from tools.ctables.mkds import save_tables as st
from tools.ctables.common.harness import compile_and_compare


RNG = random.Random(0x4D4B4453)


def random_bytes(length: int) -> bytes:
    return bytes(RNG.randrange(256) for _ in range(length))


def sparse_input_area(length: int = st.SAV_INPUT_RECORDING_SIZE) -> bytes:
    """A recording with a plausible used count and a few non-zero runs."""
    area = bytearray(length)
    runs = 19
    area[0:4] = (runs * 2).to_bytes(4, "little")
    for index in range(runs):
        area[4 + index * 2] = RNG.choice((0x00, 0x01, 0x09, 0x21, 0x29, 0x81))
        area[5 + index * 2] = RNG.randrange(1, 0xF0)
    return bytes(area)


def make_sav_block(kind: str, timestamp: int = 0x1234) -> bytes:
    size = st.SAV_BLOCK_SIZES[kind]
    body = bytearray(random_bytes(size - 4))
    if kind == "NKSY":
        body[0x00:0x08] = b"MKDSSV10"
        body[0x08:0x0C] = st.SAV_MAGICS[kind].to_bytes(4, "little")
        body[0x33] = 0xA5  # unnamed padding between reserved_32 and field_34
    else:
        body[0x00:0x04] = st.SAV_MAGICS[kind].to_bytes(4, "little")
    if kind in ("NKPG", "NKDG"):
        input_offset = (st.SAV_GHOST_RUN_LENGTH_OFFSET if kind == "NKPG"
                        else st.SAV_GHOST_RUN_DATA_OFFSET)
        area = sparse_input_area()
        body[input_offset:input_offset + len(area)] = area
    return bytes(body) + st.sav_make_footer(bytes(body), timestamp)


def make_ghost_file(kind: str) -> bytes:
    size = {"NKDG": st.GHOST_SIZE_NKDG, "NKPG": st.GHOST_SIZE_NKPG}[kind]
    data = bytearray(random_bytes(size))
    data[0x00:0x04] = kind.encode("ascii")
    input_offset = (st.SAV_GHOST_RUN_LENGTH_OFFSET if kind == "NKPG"
                    else st.SAV_GHOST_RUN_DATA_OFFSET)
    data[input_offset:input_offset + st.SAV_INPUT_RECORDING_SIZE] = sparse_input_area()
    return bytes(data)


def make_kart_physical(width: int) -> bytes:
    rows = 37 if width == st.KART_PHYS_ROW_144 else 50
    return random_bytes(rows * width)


class CTableSaveTests(unittest.TestCase):
    def assert_roundtrip(self, label: str, source: str, expected: bytes) -> None:
        ok, produced, error = compile_and_compare(source, expected)
        if ok:
            return
        if error:
            self.fail(f"{label}: compile/run failed:\n{error}")
        limit = min(len(produced), len(expected))
        offset = next((i for i in range(limit) if produced[i] != expected[i]), limit)
        self.fail(
            f"{label}: byte mismatch at 0x{offset:X} "
            f"(expected {len(expected)} bytes, produced {len(produced)})")

    # -- save blocks -------------------------------------------------------

    def test_save_blocks_roundtrip(self) -> None:
        for kind in ("NKSY", "NKEM", "NKGP", "NKTA", "NKMR", "NKFL", "NKFE"):
            with self.subTest(kind=kind):
                data = make_sav_block(kind, timestamp=0x1000 + len(kind))
                self.assert_roundtrip(f"sav {kind}", st.emit_sav_block(data, kind), data)

    def test_identity_padding_is_preserved(self) -> None:
        data = make_sav_block("NKSY")
        self.assertEqual(data[0x33], 0xA5)
        source = st.emit_sav_block(data, "NKSY")
        self.assertIn("image[0x033] = 0xA5u;", source)
        self.assert_roundtrip("sav NKSY padding", source, data)

    def test_ghost_blocks_roundtrip(self) -> None:
        for kind in ("NKPG", "NKDG"):
            with self.subTest(kind=kind):
                data = make_sav_block(kind, timestamp=0x2222)
                self.assert_roundtrip(f"sav {kind}", st.emit_sav_block(data, kind), data)

    # -- standalone ghost files and input runs -----------------------------

    def test_ghost_files_roundtrip(self) -> None:
        for kind in ("NKDG", "NKPG"):
            with self.subTest(kind=kind):
                data = make_ghost_file(kind)
                self.assert_roundtrip(
                    f"ghost file {kind}", st.emit_ghost_file(data, kind), data)

    def test_input_recording_roundtrip(self) -> None:
        data = sparse_input_area()
        self.assert_roundtrip("input recording",
                              st.emit_input_recording(data), data)

    # -- kart parameter tables --------------------------------------------

    def test_kart_physical_widths(self) -> None:
        for width in (st.KART_PHYS_ROW_152, st.KART_PHYS_ROW_148,
                      st.KART_PHYS_ROW_144):
            with self.subTest(width=width):
                data = make_kart_physical(width)
                self.assert_roundtrip(
                    f"kartphysicalparam {width}",
                    st.emit_kart_physical(data, width), data)

    def test_kart_ai(self) -> None:
        data = random_bytes(480 * st.KART_AI_ROW)
        self.assert_roundtrip("kartAIparam", st.emit_kart_ai(data), data)

    def test_kart_colors(self) -> None:
        for rows in (50, 54):
            with self.subTest(rows=rows):
                data = random_bytes(rows * st.KART_COLOR_ROW)
                self.assert_roundtrip(
                    f"kartcrsmat {rows}", st.emit_kart_colors(data), data)

    def test_kart_offsets(self) -> None:
        data = bytearray(random_bytes(37 * st.KART_OFFSET_ROW))
        data[0x00:0x0C] = b"kart_tire_M\x00"
        self.assert_roundtrip("kartoffsetdata", st.emit_kart_offsets(bytes(data)),
                              bytes(data))

    def test_kart_menu(self) -> None:
        data = random_bytes(50 * st.KART_MENU_ROW)
        self.assert_roundtrip("kartmenuparam", st.emit_kart_menu(data), data)

    def test_character_tables(self) -> None:
        physical_104 = random_bytes(13 * st.CHAR_PHYS_ROW)
        self.assert_roundtrip("charphysicalparam 104",
                              st.emit_char_physical(physical_104), physical_104)
        for label in ("charphysicalparam 26", "charmenuparam 26"):
            with self.subTest(label=label):
                table = random_bytes(13 * st.CHAR_U16_ROW)
                self.assert_roundtrip(label, st.emit_char_u16(table), table)

    def test_staff_ghost_times_owned_by_small_tables(self) -> None:
        # staff_ghost_time.bin is covered by tools/ctables/mkds/small_tables.py;
        # keep this file free of a duplicate emitter.
        self.assertFalse(hasattr(st, "emit_staff_ghost_times"))

    # -- footer helpers and generated style --------------------------------

    def test_footer_crc_contract(self) -> None:
        self.assertEqual(st.sav_crc16(b"123456789"), 0x31C3)
        for kind in ("NKSY", "NKGP", "NKDG"):
            with self.subTest(kind=kind):
                block = make_sav_block(kind, timestamp=0xBEEF)
                self.assertTrue(st.sav_footer_valid(block))
                self.assertEqual(block[-4:-2], b"\xBE\xEF")

    def test_generated_source_is_typed(self) -> None:
        nksy = st.emit_sav_block(make_sav_block("NKSY"), "NKSY")
        self.assertIn("static const SavIdentityBlock block", nksy)
        self.assertIn(".file_magic =", nksy)
        self.assertIn(".flags_31 = { .bits = {", nksy)

        nkgp = st.emit_sav_block(make_sav_block("NKGP"), "NKGP")
        self.assertIn(".info_0 = { .bits = {", nkgp)

        ghost = st.emit_ghost_file(make_ghost_file("NKDG"), "NKDG")
        self.assertIn("static const MkdsGhostHeader header", ghost)
        self.assertIn("static const SavInputRecording input", ghost)
        self.assertIn(".keys = { .bits = {", ghost)

        physical = st.emit_kart_physical(make_kart_physical(152), 152)
        self.assertIn("static const MkdsKartPhysRow152 table[50]", physical)
        self.assertIn(
            ".collision_velocity_multiplier = { [MKDS_SURFACE_ROAD] =",
            physical)

        offset_table = st.emit_kart_offsets(bytes(37 * st.KART_OFFSET_ROW))
        self.assertIn("static const MkdsKartOffsetRow table[37]", offset_table)

        menu = st.emit_kart_menu(bytes(50 * st.KART_MENU_ROW))
        self.assertIn(".speed = 0,", menu)
        self.assertIn(".items = 0", menu)

    def test_rejects_bad_shapes(self) -> None:
        with self.assertRaises(st.TableError):
            st.emit_sav_block(b"\x00" * 10, "NKGP")
        with self.assertRaises(st.TableError):
            st.emit_kart_physical(b"\x00" * 151, 152)
        with self.assertRaises(st.TableError):
            st.emit_ghost_file(b"\x00" * 3584, "NKDG")
        with self.assertRaises(st.TableError):
            st.emit_input_recording(b"\x00" * 4)


if __name__ == "__main__":
    unittest.main()
