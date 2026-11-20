# Mario Kart DS Modding Trove
# tests/test_ctables_g2d.py — exact C table rebuilds for Nitro G2D resources
# SPDX-License-Identifier: MIT
"""Round-trip synthetic G2D resources through typed C emitters.

Each fixture is built in memory, emitted as a complete C program, compiled by
the host compiler and compared byte-for-byte with harness.compile_and_compare.
No stock game data is read here.
"""
from __future__ import annotations

import struct
import unittest

from tools.ctables.generic import g2d_tables
from tools.ctables.common import harness


def _u16(value: int) -> bytes:
    return struct.pack("<H", value)


def _u32(value: int) -> bytes:
    return struct.pack("<I", value)


def _block(magic: bytes, payload: bytes, size: int | None = None) -> bytes:
    declared = 8 + len(payload) if size is None else size
    return magic + _u32(declared) + payload


def _g2d(magic: bytes, version: int, blocks: list[bytes], *,
         bom: int = 0xFEFF, size: int | None = None,
         count: int | None = None, header_extra: bytes = b"",
         trailer: bytes = b"") -> bytes:
    header_size = 16 + len(header_extra)
    body = header_extra + b"".join(blocks)
    declared_size = 16 + len(body) + len(trailer) if size is None else size
    declared_count = len(blocks) if count is None else count
    header = magic + struct.pack(
        "<HHIHH", bom, version, declared_size, header_size, declared_count)
    return header + body + trailer


def _ncgr_char(payload: bytes, *, height: int = 0xFFFF, width: int = 0xFFFF,
               color_format: int = 3, mapping: int = 0x10,
               char_format: int = 0, data_size: int | None = None,
               data_offset: int = 0x18) -> bytes:
    if data_size is None:
        data_size = len(payload)
    fields = struct.pack("<HHIIIII", height, width, color_format, mapping,
                         char_format, data_size, data_offset)
    return _block(b"RAHC", fields + payload)


def _ncgr_cpos(x: int = 0, y: int = 0, width: int = 32,
               height: int = 8) -> bytes:
    return _block(b"SOPC", struct.pack("<HHHH", x, y, width, height))


def _nclr_pltt(palette: bytes, *, palette_format: int = 3,
               extended: int = 0, data_size: int | None = None,
               data_offset: int = 0x10) -> bytes:
    if data_size is None:
        data_size = len(palette)
    fields = struct.pack("<IIII", palette_format, extended, data_size,
                         data_offset)
    return _block(b"TTLP", fields + palette)


def _nclr_pcmp(indices: list[int], *, count: int | None = None,
               reserved: int = 0xBEEF, index_offset: int = 8) -> bytes:
    declared = len(indices) if count is None else count
    payload = struct.pack("<HHI", declared, reserved, index_offset)
    payload += b"".join(_u16(index) for index in indices)
    return _block(b"PMCP", payload)


def _nscr(width: int, height: int, color_mode: int, screen_format: int,
          payload: bytes, *, data_size: int | None = None) -> bytes:
    if data_size is None:
        data_size = len(payload)
    fields = struct.pack("<HHHHI", width, height, color_mode,
                         screen_format, data_size)
    return _block(b"NRCS", fields + payload)


def _ncer_cebk(cells: bytes, *, cell_count: int, attributes: int,
               mapping: int = 0, cell_data_offset: int = 0x18,
               oam: bytes = b"") -> bytes:
    fields = struct.pack("<HHIIIII", cell_count, attributes,
                         cell_data_offset, mapping, 0, 0, 0)
    return _block(b"KBEC", fields + cells + oam)


def _ncer_cell(oam_count: int, attributes: int, oam_offset: int) -> bytes:
    return struct.pack("<HHI", oam_count, attributes, oam_offset)


def _ncer_cell_bbox(oam_count: int, attributes: int, oam_offset: int,
                    max_x: int, max_y: int, min_x: int,
                    min_y: int) -> bytes:
    return struct.pack("<HHIhhhh", oam_count, attributes, oam_offset,
                       max_x, max_y, min_x, min_y)


def _nanr_knba(animations: bytes, frames: bytes, frame_data: bytes, *,
               animation_count: int, frame_count: int,
               animation_offset: int, frame_offset: int,
               frame_data_offset: int, padding: bytes = b"\x00" * 8) -> bytes:
    fields = struct.pack("<HHIII", animation_count, frame_count,
                         animation_offset, frame_offset, frame_data_offset)
    return _block(b"KNBA", fields + padding + animations + frames + frame_data)


def _nanr_animation(frame_count: int, loop_start: int, animation_type: int,
                    play_mode: int, first_frame_offset: int) -> bytes:
    return struct.pack("<HHIII", frame_count, loop_start, animation_type,
                       play_mode, first_frame_offset)


def _nanr_frame(data_offset: int, duration: int, reserved: int) -> bytes:
    return struct.pack("<IHH", data_offset, duration, reserved)


def _nftr_finf(version: int, glyph_offset: int, width_offset: int,
               code_map_offset: int, *, encoding: int = 1) -> bytes:
    if version == 0x0001:
        fields = struct.pack("<BBHbbBB", 0, 13, 0, 0, 8, encoding, 0xA5)
    else:
        fields = struct.pack("<BBHbbBB", 0, 11, 0, 0, 8, 8, encoding)
    return _block(b"FNIF", fields + struct.pack(
        "<III", glyph_offset, width_offset, code_map_offset))


def _nftr_cglp(glyphs: bytes, *, cell_width: int = 8, cell_height: int = 9,
               cell_size: int = 9, baseline: int = 8, max_width: int = 8,
               bpp: int = 1) -> bytes:
    fields = struct.pack("<BBHbbBB", cell_width, cell_height, cell_size,
                         baseline, max_width, bpp, 0)
    return _block(b"PLGC", fields + glyphs)


def _nftr_cwdh(first: int, last: int, entries: bytes, *,
               next_offset: int = 0) -> bytes:
    return _block(b"HDWC", struct.pack("<HHI", first, last, next_offset)
                  + entries)


def _nftr_cmap(code_begin: int, code_end: int, method: int, payload: bytes, *,
               reserved: int = 0, next_offset: int = 0) -> bytes:
    fields = struct.pack("<HHHHI", code_begin, code_end, method, reserved,
                         next_offset)
    return _block(b"PAMC", fields + payload)


def _first_difference(expected: bytes, produced: bytes) -> str:
    if len(expected) != len(produced):
        return f"length {len(produced)} != {len(expected)}"
    for offset, (want, got) in enumerate(zip(expected, produced)):
        if want != got:
            return f"first difference at 0x{offset:04X}: {got:02X} != {want:02X}"
    return "no difference"


class G2dTableTests(unittest.TestCase):
    @unittest.skipUnless(harness.CC, "no host C compiler")
    def _round_trip(self, data: bytes, emitter, type_names=()):
        source = emitter(data)
        self.assertIn('#include "nitro/g2d.h"', source)
        self.assertIn("static const", source)
        for name in type_names:
            self.assertIn(name, source)
        ok, produced, error = harness.compile_and_compare(source, data)
        self.assertTrue(
            ok, f"{error}\n{_first_difference(data, produced)}"
            if not ok else "")
        return source

    def test_unknown_magic_is_rejected(self):
        with self.assertRaises(ValueError):
            g2d_tables.emit_source(b"XXXX" + b"\x00" * 12)
        with self.assertRaises(ValueError):
            g2d_tables.emit_source(b"RGCN")

    @unittest.skipUnless(harness.CC, "no host C compiler")
    def test_malformed_envelope_is_preserved(self):
        # header_size below 16 and a block size past EOF: keep every byte.
        header = b"RGCN" + struct.pack("<HHIHH", 0xFEFF, 0x0100, 0x20, 12, 1)
        data = header + bytes(range(16))
        self._round_trip(data, g2d_tables.emit_source, ("trailer",))

    @unittest.skipUnless(harness.CC, "no host C compiler")
    def test_ncgr_char(self):
        char_data = bytes((index * 7) & 0xFF for index in range(96))
        data = _g2d(b"RGCN", 0x0100, [
            _ncgr_char(char_data, height=4, width=12, mapping=0),
        ])
        source = self._round_trip(
            data, g2d_tables.emit_ncgr, ("NcgrCharBlock",))
        self.assertIn(".character_format = { .raw = 0x00000000u }", source)
        self.assertIn(".data_offset = 0x00000018u", source)

    @unittest.skipUnless(harness.CC, "no host C compiler")
    def test_ncgr_cpos_and_legacy_envelope(self):
        char_data = bytes(range(32))
        char = _ncgr_char(char_data, data_size=len(char_data) + 8)
        blocks = [char, _ncgr_cpos(width=10, height=3)]
        data = _g2d(b"RGCN", 0x0101, blocks, bom=0,
                    size=sum(len(block) for block in blocks) + 16,
                    trailer=b"\xDE\xAD\xBE\xEF\x00\x00\x00\x00")
        source = self._round_trip(
            data, g2d_tables.emit_ncgr,
            ("NcgrCharBlock", "NcgrCposBlock", "trailer"))

    @unittest.skipUnless(harness.CC, "no host C compiler")
    def test_nclr_pltt_and_pcmp(self):
        palette = b"".join(_u16(0x001F + index) for index in range(4))
        blocks = [
            _nclr_pltt(palette, data_size=0x1E00),
            _nclr_pcmp([3, 7]),
        ]
        data = _g2d(b"RLCN", 0x0100, blocks)
        self.assertEqual(len(blocks[1]), 20)  # PCMP size is 0x10 + 2*n
        source = self._round_trip(
            data, g2d_tables.emit_nclr,
            ("NclrPlttBlock", "NclrPcmpBlock", "blk1_pcmp_indices"))
        self.assertIn("0x0003u, 0x0007u", source)

    @unittest.skipUnless(harness.CC, "no host C compiler")
    def test_nclr_legacy_magic_and_truncated_pcmp(self):
        palette = b"".join(_u16(index) for index in range(3))
        # Declared count (4) exceeds the two stored indices; keep it verbatim.
        blocks = [_nclr_pltt(palette), _nclr_pcmp([1, 2], count=4)]
        data = _g2d(b"RPCN", 0x0001, blocks, bom=0,
                    trailer=b"\x01\x02\x03\x04\x05\x06\x07\x08")
        self._round_trip(data, g2d_tables.emit_nclr,
                         ("NclrPlttBlock", "NclrPcmpBlock"))
        self._round_trip(data, g2d_tables.emit_source,
                         ("NclrPlttBlock", "trailer"))

    @unittest.skipUnless(harness.CC, "no host C compiler")
    def test_nscr_screen_map(self):
        entries = b"".join(_u16(value) for value in
                           (0x0001, 0x0402, 0x0803, 0x0C04))
        data = _g2d(b"RCSN", 0x0100, [
            _nscr(16, 16, 0, 0, entries + b"\xAA"),
        ])
        source = self._round_trip(
            data, g2d_tables.emit_nscr,
            ("NscrScreenBlock", "blk0_entries", "blk0_entries_tail"))
        self.assertIn("0x0402u", source)

    @unittest.skipUnless(harness.CC, "no host C compiler")
    def test_ncer_bbox_cells_and_oam(self):
        cells = b"".join((
            _ncer_cell_bbox(2, 0x0803, 0, 16, 16, -16, -16),
            _ncer_cell_bbox(1, 0x0806, 12, 8, 4, -8, -4),
        ))
        oam = b"".join(_u16(0x1000 + index) for index in range(9))
        data = _g2d(b"RECN", 0x0100, [
            _ncer_cebk(cells, cell_count=2, attributes=1, oam=oam),
        ])
        source = self._round_trip(
            data, g2d_tables.emit_ncer,
            ("NcerCebkHeader", "NcerCellBbox", "blk0_oam"))
        self.assertIn(".max_x = 16", source)

    @unittest.skipUnless(harness.CC, "no host C compiler")
    def test_ncer_labels_and_unaligned_uext(self):
        cell = _ncer_cell(0, 0x0002, 0)
        labels = struct.pack("<II", 0, 3) + b"aa\x00bb\x00"
        data = _g2d(b"RECN", 0x0100, [
            _ncer_cebk(cell, cell_count=1, attributes=0, mapping=4),
            _block(b"LBAL", labels),
            _block(b"TXEU", _u32(1)),
        ])
        self.assertEqual(len(_block(b"LBAL", labels)) % 4, 2)
        self._round_trip(data, g2d_tables.emit_ncer,
                         ("NcerCebkHeader", "NcerCell", "G2dUextBlock"))

    @unittest.skipUnless(harness.CC, "no host C compiler")
    def test_nftr_version_0100_chain(self):
        glyphs = bytes((index * 5) & 0xFF for index in range(36))
        cglp = _nftr_cglp(glyphs)
        widths = bytes((
            0, 8, 0,
            1, 7, 1,
            0xFF, 6, 0,
            0, 5, 0xFE,
        ))
        cwdh = _nftr_cwdh(0, 3, widths + b"\x00\x00")
        direct = _nftr_cmap(0x20, 0x20, 0, _u16(4) + b"\x00\x00")
        table = _nftr_cmap(0x41, 0x44, 1,
                           b"".join(_u16(value) for value in (4, 5, 6, 7)))
        scan = _nftr_cmap(0, 0xFFFF, 2,
                          _u16(3) + b"".join((
                              _u16(0x20) + _u16(4),
                              _u16(0x41) + _u16(5),
                              _u16(0x44) + _u16(7),
                          )) + b"\x00\x00")
        # FINF sits at 0x10 and is 28 bytes; each offset is from file+8.
        position_finf = 0x10
        position_cglp = position_finf + 28
        position_cwdh = position_cglp + len(cglp)
        position_direct = position_cwdh + len(cwdh)
        position_table = position_direct + len(direct)
        position_scan = position_table + len(table)
        direct = _nftr_cmap(0x20, 0x20, 0, _u16(4) + b"\x00\x00",
                            next_offset=position_table - 8)
        table = _nftr_cmap(0x41, 0x44, 1,
                           b"".join(_u16(value) for value in (4, 5, 6, 7)),
                           next_offset=position_scan - 8)
        finf = _nftr_finf(0x0100, position_cglp - 8,
                          position_cwdh - 8, position_direct - 8)
        data = _g2d(b"RTFN", 0x0100, [finf, cglp, cwdh, direct, table, scan])
        source = self._round_trip(
            data, g2d_tables.emit_nftr,
            ("NftrInfoBlock", "NftrGlyphBlock", "NftrWidthBlock",
             "NftrCodeMapBlock", "NftrScanEntry"))
        self.assertIn(".left = -1", source)

    @unittest.skipUnless(harness.CC, "no host C compiler")
    def test_nftr_version_0001_old_structures(self):
        glyphs = bytes(range(16))
        cglp = _nftr_cglp(glyphs, cell_width=4, cell_height=4, cell_size=2,
                          baseline=3, max_width=4, bpp=1)
        widths = bytes((0, 8, 1, 6, 2, 4, 3, 2))
        cwdh = _nftr_cwdh(0, 3, widths)
        table = _nftr_cmap(0x20, 0x23, 1,
                           b"".join(_u16(value) for value in (0, 1, 2, 3)),
                           reserved=0x1234)
        scan = _nftr_cmap(0, 0xFFFF, 2,
                          _u16(2) + _u16(0x20) + _u16(0)
                          + _u16(0x23) + _u16(3) + b"\x00\x00")
        position_finf = 0x10
        position_cglp = position_finf + 28
        position_cwdh = position_cglp + len(cglp)
        position_table = position_cwdh + len(cwdh)
        position_scan = position_table + len(table)
        table = _nftr_cmap(0x20, 0x23, 1,
                           b"".join(_u16(value) for value in (0, 1, 2, 3)),
                           reserved=0x1234,
                           next_offset=position_scan - 8)
        finf = _nftr_finf(0x0001, position_cglp - 8,
                          position_cwdh - 8, position_table - 8,
                          encoding=0)
        data = _g2d(b"RTFN", 0x0001, [finf, cglp, cwdh, table, scan])
        source = self._round_trip(
            data, g2d_tables.emit_nftr,
            ("NftrInfoBlockOld", "NftrCharWidthOld", "NftrScanEntry"))
        self.assertIn(".reserved = 0x1234u", source)

    @unittest.skipUnless(harness.CC, "no host C compiler")
    def test_nanr_knba_labels_and_uext(self):
        animations = b"".join((
            _nanr_animation(2, 0, 0x00010000, 2, 0),
            _nanr_animation(1, 0, 0x00010000, 2, 16),
        ))
        frames = b"".join((
            _nanr_frame(0, 4, 0xBEEF),
            _nanr_frame(4, 4, 0xBEEF),
            _nanr_frame(8, 6, 0xBEEF),
        ))
        frame_data = b"".join((
            _u16(5), b"\xCC\xCC",
            _u16(6), b"\xCC\xCC",
            _u16(7), b"\xCC\xCC",
        ))
        # KNBA header is 24 bytes, then 8 padding bytes, then 0x20/0x40/0x58.
        knba = _nanr_knba(animations, frames, frame_data,
                          animation_count=2, frame_count=3,
                          animation_offset=0x18, frame_offset=0x38,
                          frame_data_offset=0x50)
        labels = struct.pack("<II", 0, 3) + b"aa\x00bb\x00"
        blocks = [knba, _block(b"LBAL", labels), _block(b"TXEU", _u32(1))]
        data = _g2d(b"RNAN", 0x0100, blocks)
        self.assertEqual(len(blocks[1]) % 4, 2)
        source = self._round_trip(
            data, g2d_tables.emit_nanr,
            ("NanrKnbaHeader", "NanrAnimation", "NanrFrame", "G2dUextBlock"))
        self.assertIn(".animation_type = { .raw = 0x00010000u }", source)
        self.assertIn(".reserved = 0xBEEFu", source)

    @unittest.skipUnless(harness.CC, "no host C compiler")
    def test_nanr_knba_only(self):
        animations = _nanr_animation(1, 0, 0x00020000, 2, 0)
        frames = _nanr_frame(0, 10, 0xCCCC)
        frame_data = _u16(9) + b"\xCC\xCC"
        knba = _nanr_knba(animations, frames, frame_data,
                          animation_count=1, frame_count=1,
                          animation_offset=0x18, frame_offset=0x28,
                          frame_data_offset=0x30)
        data = _g2d(b"RNAN", 0x0100, [knba])
        self._round_trip(data, g2d_tables.emit_nanr,
                         ("NanrKnbaHeader", "NanrAnimation", "NanrFrame"))


if __name__ == "__main__":
    unittest.main()
