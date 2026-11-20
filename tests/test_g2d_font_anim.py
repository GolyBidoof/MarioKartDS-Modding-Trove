# Mario Kart DS Modding Trove
# tests/test_g2d_font_anim.py — NFTR glyph bitstream decoding
# SPDX-License-Identifier: MIT
import unittest

from tools.g2d_font_anim import _decode_glyph, _encode_glyph


class GlyphCodecTests(unittest.TestCase):
    def test_2bpp_rows(self):
        # 2bpp, 4x2: rows 2,1,3,0 and 0,3,1,2
        pixels = [[2, 1, 3, 0], [0, 3, 1, 2]]
        raw = _encode_glyph(pixels, 4, 2, 2, 2)
        self.assertEqual(_decode_glyph(raw, 4, 2, 2), pixels)

    def test_3bpp_rows(self):
        pixels = [[0, 1, 2, 3], [4, 5, 6, 7]]
        raw = _encode_glyph(pixels, 4, 2, 3, 3)
        self.assertEqual(_decode_glyph(raw, 4, 2, 3), pixels)

    def test_1bpp_unchanged(self):
        pixels = [[0, 1, 1, 0], [1, 0, 1, 0]]
        raw = _encode_glyph(pixels, 4, 2, 1, 1)
        self.assertEqual(_decode_glyph(raw, 4, 2, 1), pixels)


if __name__ == "__main__":
    unittest.main()
