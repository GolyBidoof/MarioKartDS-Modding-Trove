# Mario Kart DS Modding Trove
# tests/test_ctables_fx.py — FX32/FX16 text is lossless in both directions
# SPDX-License-Identifier: MIT
"""The C tables print fixed-point values as short decimals.

``FX32(v)`` is ``(int32_t)((double)v * 4096.0)`` and ``FX16(v)`` narrows to
16 bits.  The formatter must choose a decimal that the same macro maps back to
the original raw word, otherwise an edited table would not rebuild the file.
"""
import random
import unittest

from tools.ctables.common.cformat import fx_decimal


def macro_fx32(text: str) -> int:
    """Model the C FX32 macro: double multiply, truncate toward zero."""
    return int(float(text) * 4096.0)


def macro_fx16(text: str) -> int:
    """Model the C FX16 macro: double multiply, truncate, then narrow."""
    value = int(float(text) * 4096.0)
    value &= 0xFFFF
    return value - 0x10000 if value >= 0x8000 else value


class FixedPointTextTests(unittest.TestCase):
    def test_every_fx16_raw_word(self):
        for raw in range(-0x8000, 0x8000):
            text = fx_decimal(raw, 12)
            self.assertEqual(macro_fx16(text), raw, text)

    def test_fx32_boundaries_and_samples(self):
        values = {
            0, 1, -1, 2, -2, 4095, 4096, -4096, 4097,
            0x7FFFFFFF, -0x80000000, 0x7FFFFFFE, -0x7FFFFFFF,
        }
        rng = random.Random(0x4B44)
        values.update(rng.randint(-0x80000000, 0x7FFFFFFF)
                      for _ in range(20000))
        for raw in values:
            text = fx_decimal(raw, 12)
            self.assertEqual(macro_fx32(text), raw,
                             f"{raw} -> {text}")

    def test_short_forms_are_used(self):
        self.assertEqual(fx_decimal(3809), "0.93")
        self.assertEqual(fx_decimal(2662), "0.65")
        self.assertEqual(fx_decimal(4055), "0.99")
        self.assertEqual(fx_decimal(4096), "1.0")
        self.assertEqual(fx_decimal(-4096), "-1.0")


if __name__ == "__main__":
    unittest.main()
