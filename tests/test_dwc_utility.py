# Mario Kart DS Modding Trove
# tests/test_dwc_utility.py — NARC-less DWC archive parser
# SPDX-License-Identifier: MIT
import struct
import tempfile
import unittest
from pathlib import Path

from tools import dwc_utility


def _dir(name: str, directory_id: int) -> bytes:
    raw = name.encode("ascii")
    return bytes([0x80 | len(raw)]) + raw + struct.pack("<H", directory_id)


def _file(name: str) -> bytes:
    raw = name.encode("ascii")
    return bytes([len(raw)]) + raw


def build_archive(readme: bytes = b"hello", a_bin: bytes = b"abc") -> bytes:
    root_subtable = _dir("data", 0xF001) + _file("readme.bin") + b"\x00"
    data_subtable = _file("a.bin") + b"\x00"
    main_size = 2 * 8
    root_offset = main_size
    data_offset = root_offset + len(root_subtable)
    fnt = (
        struct.pack("<IHH", root_offset, 0, 2)
        + struct.pack("<IHH", data_offset, 1, 0xF000)
        + root_subtable
        + data_subtable
    )
    fat_offset = 16 + len(fnt)
    data_start = fat_offset + 16
    readme_start = data_start
    a_start = readme_start + len(readme)
    end = a_start + len(a_bin)
    fat = struct.pack("<II", readme_start, a_start) + struct.pack("<II", a_start, end)
    header = struct.pack("<IIII", 16, len(fnt), fat_offset, len(fat))
    return header + fnt + fat + readme + a_bin


class DwcArchiveTests(unittest.TestCase):
    def test_list_tree(self):
        data = build_archive()
        files = dwc_utility.parse_tree(data)
        self.assertEqual(sorted(file.path for file in files),
                         ["data/a.bin", "readme.bin"])
        self.assertEqual(sorted(file.file_id for file in files), [0, 1])

    def test_verify_accepts_stock_shape(self):
        data = build_archive()
        self.assertEqual(len(dwc_utility.verify(data)), 2)

    def test_extract(self):
        data = build_archive(readme=b"one", a_bin=b"two")
        with tempfile.TemporaryDirectory() as directory:
            written = dwc_utility.extract(data, Path(directory))
            self.assertEqual(len(written), 2)
            self.assertEqual((Path(directory) / "readme.bin").read_bytes(), b"one")
            self.assertEqual((Path(directory) / "data" / "a.bin").read_bytes(), b"two")

    def test_rejects_bad_header(self):
        with self.assertRaises(dwc_utility.ArchiveError):
            dwc_utility.parse_header(b"\0" * 15)
        broken = bytearray(build_archive())
        struct.pack_into("<I", broken, 4, 0xFFFFFF)
        with self.assertRaises(dwc_utility.ArchiveError):
            dwc_utility.parse_header(bytes(broken))

    def test_rejects_overlapping_ranges(self):
        data = bytearray(build_archive())
        _, _, fat_offset, _ = dwc_utility.parse_header(bytes(data))
        # Make the second file start inside the first.
        first_start = struct.unpack_from("<I", data, fat_offset)[0]
        struct.pack_into("<I", data, fat_offset + 8, first_start)
        with self.assertRaises(dwc_utility.ArchiveError):
            dwc_utility.verify(bytes(data))


if __name__ == "__main__":
    unittest.main()
