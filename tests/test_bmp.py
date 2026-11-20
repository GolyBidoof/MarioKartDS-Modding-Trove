# Mario Kart DS Modding Trove
# tests/test_bmp.py — screenshot differ
# SPDX-License-Identifier: MIT
import tempfile
import unittest
from pathlib import Path

from tools import bmp


class BmpTests(unittest.TestCase):
    def test_compare_and_diff(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            a = root / "a.bmp"
            b = root / "b.bmp"
            d = root / "diff.bmp"
            bmp.write(str(a), 2, 1, [[(255, 0, 0), (0, 255, 0)]])
            bmp.write(str(b), 2, 1, [[(255, 0, 0), (0, 0, 255)]])
            result = bmp.compare(str(a), str(b))
            self.assertTrue(result["same_size"])
            self.assertEqual(result["changed_pixels"], 1)
            self.assertEqual(result["bbox"], [1, 0, 1, 0])
            self.assertFalse(result["equal"])
            bmp.save_diff(str(a), str(b), str(d))
            self.assertEqual(bmp.load(str(d)).pixel(1, 0), (255, 0, 0))

    def test_size_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            a = root / "a.bmp"
            b = root / "b.bmp"
            bmp.write(str(a), 1, 1, [[(0, 0, 0)]])
            bmp.write(str(b), 2, 1, [[(0, 0, 0), (0, 0, 0)]])
            self.assertFalse(bmp.compare(str(a), str(b))["same_size"])


if __name__ == "__main__":
    unittest.main()
