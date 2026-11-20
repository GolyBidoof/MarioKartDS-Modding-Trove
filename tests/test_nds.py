# Mario Kart DS Modding Trove
# tests/test_nds.py — generic NDS overlay reader
# SPDX-License-Identifier: MIT
import struct
import tempfile
import unittest
from pathlib import Path

from tools.nds import overlay_from_nds


def make_rom(overlay_id=3, ram=0x02180000, payload=b"ABCDEFGH",
             compressed=False):
    data = bytearray(0x400)
    struct.pack_into("<I", data, 0x48, 0x100)   # FAT offset
    struct.pack_into("<I", data, 0x50, 0x200)   # overlay table offset
    struct.pack_into("<I", data, 0x54, 32)      # one entry
    struct.pack_into("<II", data, 0x100, 0x300, 0x300 + len(payload))
    flags = 0x01000000 if compressed else 0
    struct.pack_into("<IIIIIIII", data, 0x200,
                     overlay_id, ram, len(payload), 0, 0, 0, 0, flags)
    data[0x300:0x300 + len(payload)] = payload
    return bytes(data)


class NdsTests(unittest.TestCase):
    def test_overlay_from_nds(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "test.nds"
            path.write_bytes(make_rom())
            ram, data = overlay_from_nds(str(path), 3)
            self.assertEqual(ram, 0x02180000)
            self.assertEqual(data, b"ABCDEFGH")

    def test_missing_overlay_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "test.nds"
            path.write_bytes(make_rom())
            with self.assertRaises(ValueError):
                overlay_from_nds(str(path), 4)


if __name__ == "__main__":
    unittest.main()
