# Mario Kart DS Modding Trove
# tests/test_g2d_project.py — editable NCGR/NCLR project round-trips
# SPDX-License-Identifier: MIT
import struct
import tempfile
import unittest
from pathlib import Path

from tools import bmp
from tools.g2d_project import (export_ncer, export_nscr, export_project,
                               import_ncer, import_nscr, import_project,
                               new_ncer, new_nclr)


def ncgr(width, height, bpp, data, cpos=None):
    char = bytearray(0x20)
    char[:4] = b"RAHC"
    struct.pack_into("<I", char, 4, 0x20 + len(data))
    struct.pack_into("<HH", char, 8, height, width)
    struct.pack_into("<I", char, 0x0C, 3 if bpp == 4 else 4)
    struct.pack_into("<I", char, 0x10, 0x10)
    struct.pack_into("<I", char, 0x14, 0)
    struct.pack_into("<I", char, 0x18, len(data))
    struct.pack_into("<I", char, 0x1C, 0x18)
    blocks = 2 if cpos else 1
    header = bytearray(0x10)
    header[:4] = b"RGCN"
    struct.pack_into("<H", header, 4, 0xFEFF)
    struct.pack_into("<H", header, 6, 0x0101 if cpos else 0x0100)
    struct.pack_into("<I", header, 0x08, 0)
    struct.pack_into("<H", header, 0x0C, 0x10)
    struct.pack_into("<H", header, 0x0E, blocks)
    out = header + char + data
    if cpos:
        block = bytearray(0x10)
        block[:4] = b"SOPC"
        struct.pack_into("<I", block, 4, 0x10)
        struct.pack_into("<HHHH", block, 8, 0, 0, width, height)
        out += block
    struct.pack_into("<I", out, 0x08, len(out))
    return bytes(out)


def nclr(colors, format_value=3, data_size=None, pcmp=None):
    payload = b"".join(struct.pack("<H", color) for color in colors)
    pltt = bytearray(0x18)
    pltt[:4] = b"TTLP"
    struct.pack_into("<I", pltt, 4, 0x18 + len(payload))
    struct.pack_into("<I", pltt, 8, format_value)
    struct.pack_into("<I", pltt, 0x0C, 0)
    struct.pack_into("<I", pltt, 0x10,
                     len(payload) if data_size is None else data_size)
    struct.pack_into("<I", pltt, 0x14, 0x10)
    block_count = 2 if pcmp is not None else 1
    header = bytearray(0x10)
    header[:4] = b"RLCN"
    struct.pack_into("<H", header, 4, 0xFEFF)
    struct.pack_into("<H", header, 6, 0x0100)
    struct.pack_into("<I", header, 0x08, 0)
    struct.pack_into("<H", header, 0x0C, 0x10)
    struct.pack_into("<H", header, 0x0E, block_count)
    out = header + pltt + payload
    if pcmp is not None:
        block = bytearray(0x10 + 2 * len(pcmp))
        block[:4] = b"PMCP"
        struct.pack_into("<I", block, 4, len(block))
        struct.pack_into("<H", block, 8, len(pcmp))
        struct.pack_into("<H", block, 0x0A, 0xBEEF)
        struct.pack_into("<I", block, 0x0C, 8)
        for index, value in enumerate(pcmp):
            struct.pack_into("<H", block, 0x10 + 2 * index, value)
        out += block
    struct.pack_into("<I", out, 0x08, len(out))
    return bytes(out)


def ncer_file(cell_count=1, bbox=True, oam=((1, 2, 3),)):
    attributes = 1 if bbox else 0
    stride = 16 if bbox else 8
    cell_area = bytearray()
    oam_area = bytearray()
    for index in range(cell_count):
        cell_area += struct.pack("<HHI", len(oam), 0x0800 if bbox else 0,
                                 len(oam_area))
        if bbox:
            cell_area += struct.pack("<hhhh", 8, 8, -8, -8)
        for entry in oam:
            oam_area += struct.pack("<HHH", *entry)
    payload = bytes(cell_area + oam_area)
    header = bytearray(0x10)
    header[:4] = b"RECN"
    struct.pack_into("<H", header, 4, 0xFEFF)
    struct.pack_into("<H", header, 6, 0x0100)
    struct.pack_into("<I", header, 0x08, 0x10 + 0x20 + len(payload))
    struct.pack_into("<H", header, 0x0C, 0x10)
    struct.pack_into("<H", header, 0x0E, 1)
    cebk = bytearray(0x20)
    cebk[:4] = b"KBEC"
    struct.pack_into("<I", cebk, 4, 0x20 + len(payload))
    struct.pack_into("<HH", cebk, 8, cell_count, attributes)
    struct.pack_into("<I", cebk, 0x0C, 0x18)
    struct.pack_into("<I", cebk, 0x10, 4)
    return bytes(header + cebk + payload)


def nscr_file(width=16, height=8, entries=(1, 2)):
    payload = b"".join(struct.pack("<H", value) for value in entries)
    header = bytearray(0x10)
    header[:4] = b"RCSN"
    struct.pack_into("<H", header, 4, 0xFEFF)
    struct.pack_into("<H", header, 6, 0x0100)
    struct.pack_into("<I", header, 0x08, 0x10 + 0x14 + len(payload))
    struct.pack_into("<H", header, 0x0C, 0x10)
    struct.pack_into("<H", header, 0x0E, 1)
    scrn = bytearray(0x14)
    scrn[:4] = b"NRCS"
    struct.pack_into("<I", scrn, 4, 0x14 + len(payload))
    struct.pack_into("<HHHH", scrn, 8, width, height, 0, 0)
    struct.pack_into("<I", scrn, 0x10, len(payload))
    return bytes(header + scrn + payload)


class G2dProjectTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_4bpp_roundtrip_and_edit(self):
        data = bytes(range(64))
        source = self.root / "a.ncgr"
        palette = self.root / "a.nclr"
        source.write_bytes(ncgr(2, 1, 4, data, cpos=True))
        palette.write_bytes(nclr(list(range(16)), pcmp=[0]))
        project = self.root / "project"
        export_project(source, palette, project)
        out_ncgr = self.root / "out.ncgr"
        out_nclr = self.root / "out.nclr"
        import_project(project, out_ncgr, out_nclr)
        self.assertEqual(out_ncgr.read_bytes(), source.read_bytes())
        self.assertEqual(out_nclr.read_bytes(), palette.read_bytes())
        image = bmp.load_indexed(project / "tiles.bmp")
        image.pixels[0][0] = 5
        bmp.write_indexed(project / "tiles.bmp", image.width, image.height,
                          image.pixels, image.palette)
        import_project(project, out_ncgr, out_nclr)
        rebuilt = out_ncgr.read_bytes()
        self.assertEqual(rebuilt[0x30] & 0x0F, 5)

    def test_8bpp_roundtrip_and_palette_edit(self):
        data = bytes((index * 3) & 0xFF for index in range(128))
        source = self.root / "b.ncgr"
        palette = self.root / "b.nclr"
        source.write_bytes(ncgr(2, 1, 8, data))
        colors = [(index * 7) & 0x7FFF for index in range(256)]
        palette.write_bytes(nclr(colors, format_value=4,
                                 data_size=0x1E00, pcmp=[0]))
        project = self.root / "project"
        export_project(source, palette, project)
        out_ncgr = self.root / "out.ncgr"
        out_nclr = self.root / "out.nclr"
        import_project(project, out_ncgr, out_nclr)
        self.assertEqual(out_ncgr.read_bytes(), source.read_bytes())
        self.assertEqual(out_nclr.read_bytes(), palette.read_bytes())

        image = bmp.load_indexed(project / "tiles.bmp")
        image.palette[1] = (255, 0, 0)
        bmp.write_indexed(project / "tiles.bmp", image.width, image.height,
                          image.pixels, image.palette)
        import_project(project, out_ncgr, out_nclr)
        changed = out_nclr.read_bytes()
        self.assertEqual(struct.unpack_from("<H", changed, 0x2A)[0], 0x001F)

    def test_ncer_roundtrip_and_edit(self):
        source = self.root / "a.ncer"
        source.write_bytes(ncer_file())
        tiles = self.root / "a.ncgr"
        pal = self.root / "a.nclr"
        tiles.write_bytes(ncgr(1, 1, 4, bytes(32)))
        pal.write_bytes(nclr(list(range(16))))
        project = self.root / "cell"
        export_ncer(source, project, tiles, pal)
        self.assertTrue((project / "cells_preview.bmp").exists())
        out = self.root / "out.ncer"
        import_ncer(project, out)
        self.assertEqual(out.read_bytes(), source.read_bytes())

        import json
        data = json.loads((project / "ncer.json").read_text(encoding="utf-8"))
        data["ncer"]["cells"][0]["attributes"] = 3
        data["ncer"]["cells"][0]["oam"][0][0] = 9
        (project / "ncer.json").write_text(json.dumps(data), encoding="utf-8")
        import_ncer(project, out)
        rebuilt = out.read_bytes()
        self.assertEqual(struct.unpack_from("<H", rebuilt, 0x32)[0], 3)
        self.assertEqual(struct.unpack_from("<H", rebuilt, 0x40)[0], 9)

    def test_nscr_roundtrip_and_edit(self):
        source = self.root / "a.nscr"
        source.write_bytes(nscr_file())
        tiles = self.root / "a.ncgr"
        pal = self.root / "a.nclr"
        tiles.write_bytes(ncgr(1, 1, 4, bytes(32)))
        pal.write_bytes(nclr(list(range(16))))
        project = self.root / "screen"
        export_nscr(source, project, tiles, pal)
        self.assertTrue((project / "screen.bmp").exists())
        out = self.root / "out.nscr"
        import_nscr(project, out)
        self.assertEqual(out.read_bytes(), source.read_bytes())

        import json
        data = json.loads((project / "nscr.json").read_text(encoding="utf-8"))
        data["nscr"]["entries"][0] = 0x2ABC
        (project / "nscr.json").write_text(json.dumps(data), encoding="utf-8")
        import_nscr(project, out)
        self.assertEqual(struct.unpack_from("<H", out.read_bytes(), 0x24)[0],
                         0x2ABC)

    def test_new_nclr_and_new_ncer(self):
        pal = self.root / "p.pal"
        pal.write_text("JASC-PAL\n0100\n2\n0 0 0\n255 0 0\n",
                       encoding="ascii")
        nclr_path = self.root / "new.nclr"
        new_nclr(nclr_path, pal, 3)
        data = nclr_path.read_bytes()
        self.assertEqual(data[:4], b"RLCN")
        self.assertEqual(data[0x10:0x14], b"TTLP")

        ncer_path = self.root / "new.ncer"
        new_ncer(ncer_path, 2, 1, bbox=True)
        project = self.root / "cell"
        export_ncer(ncer_path, project)
        out = self.root / "out.ncer"
        import_ncer(project, out)
        self.assertEqual(out.read_bytes(), ncer_path.read_bytes())

    def test_import_rejects_wrong_size(self):
        source = self.root / "c.ncgr"
        source.write_bytes(ncgr(1, 1, 4, bytes(32)))
        project = self.root / "project"
        export_project(source, None, project)
        image = bmp.load_indexed(project / "tiles.bmp")
        bmp.write_indexed(project / "tiles.bmp", image.width + 8,
                          image.height, [row + [0] * 8 for row in image.pixels],
                          image.palette)
        with self.assertRaises(Exception):
            import_project(project, self.root / "bad.ncgr", None)


if __name__ == "__main__":
    unittest.main()
