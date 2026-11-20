# Mario Kart DS Modding Trove
# tests/test_arm.py — Thumb BL decoder
# SPDX-License-Identifier: MIT
import unittest

from tools.arm import thumb_bl_target


class ArmTests(unittest.TestCase):
    def test_thumb_bl_forward(self):
        # EU class-select render: bl 0x021A11C4 from 0x021855D0
        self.assertEqual(
            thumb_bl_target(0x021855D0, bytes.fromhex("1bf0f8fd")),
            0x021A11C4)

    def test_thumb_bl_backward(self):
        # EU class-select confirm branch: bl 0x020CCC74 from 0x021855E2
        self.assertEqual(
            thumb_bl_target(0x021855E2, bytes.fromhex("47f747fb")),
            0x020CCC74)


if __name__ == "__main__":
    unittest.main()
