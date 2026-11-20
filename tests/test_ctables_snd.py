# Mario Kart DS Modding Trove
# tests/test_ctables_snd.py — typed C emitters round-trip Nitro sound files
# SPDX-License-Identifier: MIT
"""Build synthetic Nitro sound files and rebuild them from generated C."""
from __future__ import annotations

import struct
import subprocess
import unittest

from tools.ctables.generic import snd_tables
from tools.ctables.common.harness import CC, REPO, compile_and_compare


def u16(value: int) -> bytes:
    return struct.pack("<H", value)


def u32(value: int) -> bytes:
    return struct.pack("<I", value)


def snd_file(magic: bytes, body: bytes) -> bytes:
    total = 0x10 + len(body)
    return (magic + u16(0xFEFF) + u16(0x0100) + u32(total)
            + u16(0x10) + u16(1) + body)


def sseq_fixture() -> bytes:
    stream = bytes([0xFF, 0x00, 0x10, 0x01, 0x7F, 0x80, 0xFE, 0x00, 0x42])
    body = b"DATA" + u32(12 + len(stream)) + u32(0x1C) + stream
    return snd_file(b"SSEQ", body)


def ssar_fixture() -> bytes:
    payload = bytes([0xFF, 0x00, 0x2A, 0x00, 0xFE, 0x7F, 0x00])
    count = 3
    gap = bytes([0xDE, 0xAD, 0xBE, 0xEF])
    data_offset = 0x20 + count * 12 + len(gap)
    entries = b"".join([
        u32(0) + u16(0x0010) + bytes([127, 64, 64, 8]) + u16(0),
        u32(4) + u16(0x0011) + bytes([100, 64, 64, 9]) + u16(0),
        u32(1) + u16(0xFFFF) + bytes([0, 0, 0, 0]) + u16(0x1234),
    ])
    body = (b"DATA" + u32(16 + count * 12 + len(gap) + len(payload))
            + u32(data_offset) + u32(count) + entries + gap + payload)
    return snd_file(b"SSAR", body)


def sbnk_note(wave: int, archive: int, pitch: int, attack: int = 127,
              decay: int = 64, sustain: int = 32, release: int = 16,
              pan: int = 64) -> bytes:
    return struct.pack("<HHBBBBBB", wave, archive, pitch, attack,
                       decay, sustain, release, pan)


def sbnk_fixture() -> bytes:
    count = 5
    table_end = 0x3C + count * 4
    first = sbnk_note(1, 0, 60)
    second = sbnk_note(2, 1, 62, 100, 50, 20, 10, 32)
    range_notes = b"".join(bytes([1, 0]) + note for note in (first, second))
    region_one = bytes([60, 0, 0, 0, 0, 0, 0, 0]) + bytes([1, 0]) + first
    region_two = bytes([62, 0, 0, 0, 0, 0, 0, 0]) + bytes([2, 0]) + second
    payload = (first + second + bytes([60, 61]) + range_notes
               + region_one + region_two + b"\x00\x00")
    reserved = bytes([0xA5]) + bytes(31)
    offsets = [0, table_end, table_end + 10, table_end + 20, table_end + 46]
    types = [0, 1, 2, 0x10, 0x11]
    entries = b"".join(
        bytes([kind]) + u16(offset) + bytes([index & 0x0F])
        for index, (kind, offset) in enumerate(zip(types, offsets)))
    body = (b"DATA" + u32(44 + count * 4 + len(payload))
            + reserved + u32(count) + entries + payload)
    return snd_file(b"SBNK", body)


def sbnk_raw_fallback_fixture() -> bytes:
    count = 1
    table_end = 0x3C + count * 4
    payload = bytes([0x10, 0x20, 0x30, 0x40])
    entries = bytes([1]) + u16(table_end) + bytes([0])
    body = (b"DATA" + u32(44 + count * 4 + len(payload))
            + bytes(32) + u32(count) + entries + payload)
    return snd_file(b"SBNK", body)


def swar_fixture() -> bytes:
    count = 3
    table_end = 0x3C + count * 4
    first = struct.pack("<BBHHHI", 2, 1, 8000, 2094, 1, 1)
    first_samples = bytes([0x00, 0x11, 0x22, 0x33, 0x44, 0x55, 0x66, 0x77])
    second = struct.pack("<BBHHHI", 0, 0, 22050, 759, 0, 2)
    second_samples = bytes([0x80, 0x81, 0x82, 0x83, 0x84, 0x85, 0x86, 0x87])
    payload = first + first_samples + bytes(4) + second + second_samples
    offsets = [table_end, table_end, table_end + 24]
    body = (b"DATA" + u32(44 + count * 4 + len(payload))
            + bytes(32) + u32(count)
            + b"".join(u32(offset) for offset in offsets) + payload)
    return snd_file(b"SWAR", body)


def swar_empty_fixture() -> bytes:
    body = b"DATA" + u32(44) + bytes(32) + u32(0)
    return snd_file(b"SWAR", body)


def swav_fixture(kind: int) -> bytes:
    if kind == 0:
        param = struct.pack("<BBHHHI", 0, 0, 22050, 759, 0, 4)
        samples = bytes([0x00, 0x12, 0x34, 0x56, 0x78, 0x9A,
                         0xBC, 0xDE, 0xF0, 0x11, 0x22, 0x33, 0x44, 0x55,
                         0x66, 0x77])
    else:
        param = struct.pack("<BBHHHI", 2, 1, 32000, 523, 3, 5)
        samples = bytes([0x01, 0x23, 0x45, 0x67, 0x89, 0xAB,
                         0xCD, 0xEF] * 4)
    body = b"DATA" + u32(0x14 + len(samples)) + param + samples
    return snd_file(b"SWAV", body)


# ---------------------------------------------------------------- SDAT fixture

def build_symb() -> bytes:
    block = bytearray(0x40)
    block[0:4] = b"SYMB"
    record_offsets = [0] * 8
    string_slots: list[tuple[int, str]] = []

    def record(index: int, count: int) -> int:
        record_offsets[index] = len(block)
        block.extend(b"\x00\x00\x00\x00")
        struct.pack_into("<I", block, record_offsets[index], count)
        return record_offsets[index] + 4

    def name_slot(text: str) -> None:
        string_slots.append((len(block), text))
        block.extend(b"\x00\x00\x00\x00")

    # 0 SEQ: two named entries.
    record(0, 2)
    name_slot("seq_menu")
    name_slot("seq_alt")

    # 1 SEQARC: one named archive pointing at a nested record.
    record(1, 1)
    name_slot("arc_jingle")
    sub_slot = len(block)
    block.extend(b"\x00\x00\x00\x00")

    # 2 BANK, 3 WAVEARC, 4 PLAYER, 5 GROUP, 6/7 STREAM tables.
    record(2, 1)
    name_slot("bank_menu")
    record(3, 0)
    record(4, 1)
    name_slot("player_menu")
    record(5, 1)
    name_slot("group_menu")
    record(6, 0)
    record(7, 0)

    # Nested SEQARC record: two named sequences.
    sub_offset = len(block)
    struct.pack_into("<I", block, sub_slot, sub_offset)
    block.extend(u32(2))
    name_slot("arc_seq_0")
    name_slot("arc_seq_1")

    strings_start = len(block)
    for slot, text in string_slots:
        struct.pack_into("<I", block, slot, len(block))
        block.extend(text.encode("ascii") + b"\x00")
    if strings_start == len(block):
        raise AssertionError("fixture has no strings")

    struct.pack_into("<I", block, 4, len(block))
    for index, offset in enumerate(record_offsets):
        struct.pack_into("<I", block, 0x08 + index * 4, offset)
    return bytes(block)


def build_info() -> bytes:
    block = bytearray(0x40)
    block[0:4] = b"INFO"
    counts = [3, 1, 1, 2, 1, 2, 1, 1]
    section_offsets = []
    position = 0x40
    for count in counts:
        section_offsets.append(position)
        position += 4 + count * 4
    record_start = position
    block.extend(bytes(record_start - len(block)))

    records: dict[int, list[int]] = {index: [0] * count
                                     for index, count in enumerate(counts)}
    cursor = record_start

    def place(section: int, index: int, payload: bytes) -> None:
        nonlocal cursor
        if len(block) != cursor:
            raise AssertionError("INFO records must be appended in order")
        records[section][index] = cursor
        block.extend(payload)
        cursor += len(payload)

    # Section 0 SEQ: middle entry is absent.
    seq0 = (u32(0x00000005) + u16(50) + bytes([98, 64, 64, 8]) + u16(0))
    seq2 = (u32(0x00000007) + u16(51) + bytes([127, 64, 64, 9]) + u16(0))
    place(0, 0, seq0)
    place(0, 2, seq2)

    # Section 1 SEQARC.
    place(1, 0, u32(76))

    # Section 2 BANK: one live slot, three unused.
    place(2, 0, u32(81) + struct.pack("<hhhh", 0, 1, -1, -1))

    # Section 3 WAVEARC: one flagged record.
    place(3, 0, u32(180))
    place(3, 1, u32(181 | (1 << 24)))

    # Section 4 PLAYER.
    place(4, 0, u16(2) + u16(0x00FF) + u32(0x1000))

    # Section 5 GROUP: 2 and 1 items.
    place(5, 0, u32(2)
          + bytes([3, 8]) + u16(0) + u32(2)
          + bytes([0, 7]) + u16(0) + u32(73))
    place(5, 1, u32(1) + bytes([1, 6]) + u16(0) + u32(45))

    # Section 6 STREAM PLAYER: 17-byte body, then 7 bytes of writer spacing.
    channels = bytes(range(16))
    place(6, 0, bytes([1]) + channels)
    block.extend(bytes(7))
    cursor += 7

    # Section 7 STREAM.
    place(7, 0, u32(284) + bytes([100, 64, 8, 0x01]) + bytes(4))

    block.extend(bytes(4))
    struct.pack_into("<I", block, 4, len(block))
    for index, offset in enumerate(section_offsets):
        struct.pack_into("<I", block, 0x08 + index * 4, offset)

    # Write section tables (count + record offsets) at their reserved slots.
    for section, count in enumerate(counts):
        base = section_offsets[section]
        struct.pack_into("<I", block, base, count)
        for index, offset in enumerate(records[section]):
            struct.pack_into("<I", block, base + 4 + index * 4, offset)
    return bytes(block)


def build_sdat() -> bytes:
    symb = build_symb()
    info = build_info()
    contents = [
        bytes([0x53, 0x53, 0x45, 0x51, 0xFF, 0x00]),
        bytes(range(0x20)),
        bytes([0xA5] * 33),
        b"BANK\x00\x01\x02\x03\x04",
        bytes([0x00, 0xFF, 0x7F, 0x80, 0x01]),
    ]

    out = bytearray(0x40)
    out[0:4] = b"SDAT"
    out[0x35] = 0x5A  # reserved byte, preserved by the typed header

    symb_offset = len(out)
    out.extend(symb)
    out.extend(bytes([0xDE, 0xAD, 0xBE, 0xEF, 0x01, 0x02, 0x03, 0x04]))

    info_offset = len(out)
    out.extend(info)
    out.extend(bytes([0xAA, 0xBB, 0xCC, 0xDD]))

    fat_offset = len(out)
    fat_size = 12 + len(contents) * 16
    file_offset = fat_offset + fat_size

    file_block = bytearray(12)
    file_block[0:4] = b"FILE"
    pad = (file_offset + len(file_block) + 31) // 32 * 32 - (
        file_offset + len(file_block))
    file_block.extend(bytes(pad))

    fat_entries = []
    for index, content in enumerate(contents):
        absolute = file_offset + len(file_block)
        fat_entries.append((absolute, len(content)))
        file_block.extend(content)
        if index + 1 < len(contents):
            next_offset = (file_offset + len(file_block) + 31) // 32 * 32
            file_block.extend(bytes(next_offset - (file_offset + len(file_block))))
    file_block.extend(bytes(7))
    struct.pack_into("<I", file_block, 4, len(file_block))
    struct.pack_into("<I", file_block, 8, len(contents))

    fat = bytearray(fat_size)
    fat[0:4] = b"FAT "
    struct.pack_into("<I", fat, 4, fat_size)
    struct.pack_into("<I", fat, 8, len(contents))
    for index, (offset, size) in enumerate(fat_entries):
        entry = 12 + index * 16
        struct.pack_into("<II", fat, entry, offset, size)
        fat[entry + 8] = 0xA5 if index == 0 else 0x00
    out.extend(fat)
    out.extend(file_block)

    struct.pack_into("<4sHHIHH", out, 0, b"SDAT", 0xFEFF, 0x0100,
                     len(out), 0x40, 4)
    refs = [(symb_offset, len(symb)), (info_offset, len(info)),
            (fat_offset, fat_size), (file_offset, len(file_block))]
    for index, (offset, size) in enumerate(refs):
        struct.pack_into("<II", out, 0x10 + index * 8, offset, size)
    return bytes(out)


class SndCTableTests(unittest.TestCase):
    def assert_round_trip(self, source: str, data: bytes) -> None:
        ok, produced, error = compile_and_compare(source, data)
        if not ok:
            diff = next((index for index, (left, right)
                         in enumerate(zip(produced, data)) if left != right),
                        None)
            where = "length" if diff is None else f"0x{diff:X}"
            self.fail(f"mismatch at {where} "
                      f"(produced {len(produced)} bytes, expected {len(data)})"
                      f"\n{error}")

    @unittest.skipUnless(CC, "no host C compiler")
    def test_sseq_exact(self):
        data = sseq_fixture()
        source = snd_tables.emit_sseq_source(data)
        self.assertIn('#include "nitro/snd/sseq.h"', source)
        self.assertIn("SndFileHeader", source)
        self.assertIn("SseqDataBlock", source)
        self.assertIn(".data_offset = 0x1C", source)
        self.assertIn("fwrite(", source)
        self.assert_round_trip(source, data)

    @unittest.skipUnless(CC, "no host C compiler")
    def test_ssar_exact(self):
        data = ssar_fixture()
        source = snd_tables.emit_ssar_source(data)
        self.assertIn('#include "nitro/snd/ssar.h"', source)
        self.assertIn("SsarEntry", source)
        self.assertIn("ssar_entries[3]", source)
        self.assertIn(".offset = 0x4", source)
        self.assert_round_trip(source, data)

    @unittest.skipUnless(CC, "no host C compiler")
    def test_sbnk_exact(self):
        data = sbnk_fixture()
        source = snd_tables.emit_sbnk_source(data)
        self.assertIn('#include "nitro/snd/sbnk.h"', source)
        self.assertIn("SbnkDataBlock", source)
        self.assertIn("SbnkInstrumentEntry", source)
        self.assertIn(".offset = { 0x50, 0x0 }", source)
        self.assertIn("SbnkNote", source)
        self.assertIn("SbnkRangeHeader", source)
        self.assertIn("SbnkRegionalHeader", source)
        self.assertIn("SbnkTypedNote", source)
        self.assertIn("sbnk_instrument_0001_note", source)
        self.assertIn("sbnk_instrument_0004_region_0", source)
        self.assertIn("sbnk_instrument_0004_region_1", source)
        self.assertNotIn("sbnk_payload", source)
        self.assert_round_trip(source, data)

    @unittest.skipUnless(CC, "no host C compiler")
    def test_sbnk_raw_payload_fallback(self):
        data = sbnk_raw_fallback_fixture()
        source = snd_tables.emit_sbnk_source(data)
        self.assertIn("sbnk_payload", source)
        self.assert_round_trip(source, data)

    @unittest.skipUnless(CC, "no host C compiler")
    def test_swar_exact(self):
        data = swar_fixture()
        source = snd_tables.emit_swar_source(data)
        self.assertIn('#include "nitro/snd/swar.h"', source)
        self.assertIn('#include "nitro/snd/swav.h"', source)
        self.assertIn("SwarDataBlock", source)
        self.assertIn("SwavParam", source)
        self.assertIn("swar_wave_offsets[3]", source)
        self.assertIn("swar_wave_0000_param", source)
        self.assertIn("swar_wave_0001_param", source)
        self.assertNotIn("swar_wave_0002_param", source)
        self.assert_round_trip(source, data)

    @unittest.skipUnless(CC, "no host C compiler")
    def test_swar_empty(self):
        data = swar_empty_fixture()
        source = snd_tables.emit_swar_source(data)
        self.assertNotIn("swar_wave_offsets[0]", source)
        self.assert_round_trip(source, data)

    @unittest.skipUnless(CC, "no host C compiler")
    def test_swav_exact(self):
        for kind in (0, 1):
            with self.subTest(kind=kind):
                data = swav_fixture(kind)
                source = snd_tables.emit_swav_source(data)
                self.assertIn('#include "nitro/snd/swav.h"', source)
                self.assertIn("SwavDataBlock", source)
                self.assertIn(".param = {", source)
                self.assert_round_trip(source, data)

    @unittest.skipUnless(CC, "no host C compiler")
    def test_sdat_exact(self):
        data = build_sdat()
        source = snd_tables.emit_sdat_source(data)
        for symbol in ("SdatHeader", "SdatSymbHeader", "SdatSymbRecord",
                       "SdatSymbArchiveEntry", "SdatInfoHeader",
                       "SdatInfoTable", "SdatSeqInfo", "SdatSeqArcInfo",
                       "SdatBankInfo", "SdatWaveArcInfo", "SdatPlayerInfo",
                       "SdatGroupItem", "SdatStreamPlayerInfo",
                       "SdatStreamInfo", "SdatFatHeader", "SdatFatEntry",
                       "SdatFileHeader"):
            self.assertIn(symbol, source)
        self.assertIn("sdat_file_0000", source)
        self.assertIn(".block_count = 4", source)
        self.assert_round_trip(source, data)

    @unittest.skipUnless(CC, "no host C compiler")
    def test_generated_source_is_warning_clean(self):
        sources = {
            "sseq": snd_tables.emit_sseq_source(sseq_fixture()),
            "ssar": snd_tables.emit_ssar_source(ssar_fixture()),
            "sbnk": snd_tables.emit_sbnk_source(sbnk_fixture()),
            "swar": snd_tables.emit_swar_source(swar_fixture()),
            "swav": snd_tables.emit_swav_source(swav_fixture(1)),
            "sdat": snd_tables.emit_sdat_source(build_sdat()),
        }
        for name, source in sources.items():
            with self.subTest(format=name):
                result = subprocess.run(
                    [CC, "-std=c11", "-Wall", "-Wextra", "-Werror",
                     "-I", str(REPO / "include"), "-x", "c", "-",
                     "-fsyntax-only"],
                    input=source, text=True, capture_output=True)
                self.assertEqual(result.returncode, 0, result.stderr)

    def test_dispatch_by_magic(self):
        fixtures = [
            (sseq_fixture(), snd_tables.emit_sseq_source),
            (ssar_fixture(), snd_tables.emit_ssar_source),
            (sbnk_fixture(), snd_tables.emit_sbnk_source),
            (swar_fixture(), snd_tables.emit_swar_source),
            (swav_fixture(0), snd_tables.emit_swav_source),
            (build_sdat(), snd_tables.emit_sdat_source),
        ]
        for data, emitter in fixtures:
            with self.subTest(magic=data[:4]):
                self.assertEqual(snd_tables.emit_source(data), emitter(data))
        with self.assertRaises(ValueError):
            snd_tables.emit_source(b"XXXX" + bytes(0x40))
        with self.assertRaises(ValueError):
            snd_tables.emit_source(b"SD")

    def test_rejects_wrong_magic(self):
        for emitter in (snd_tables.emit_sseq_source,
                        snd_tables.emit_ssar_source,
                        snd_tables.emit_sbnk_source,
                        snd_tables.emit_swar_source,
                        snd_tables.emit_swav_source,
                        snd_tables.emit_sdat_source):
            with self.subTest(emitter=emitter.__name__):
                data = b"XXXX" + bytes(0x80)
                with self.assertRaises(ValueError):
                    emitter(data)

    def test_rejects_truncated_file(self):
        with self.assertRaises(ValueError):
            snd_tables.emit_sseq_source(b"SSEQ" + bytes(8))
        with self.assertRaises(ValueError):
            snd_tables.emit_sdat_source(b"SDAT" + bytes(0x20))


if __name__ == "__main__":
    unittest.main()
