# Mario Kart DS Modding Trove
# tools/arm.py — small ARM/Thumb helpers for patch profiles
# SPDX-License-Identifier: MIT
"""Instruction-level helpers used while locating patch sites."""

from __future__ import annotations


def thumb_bl_target(address: int, data: bytes, offset: int = 0) -> int:
    """Decode the 32-bit Thumb BL at ``data[offset:offset+4]``.

    ``address`` is the runtime address of the BL.  Returns the branch target.
    """
    h1 = data[offset] | data[offset + 1] << 8
    h2 = data[offset + 2] | data[offset + 3] << 8
    sign = (h1 >> 10) & 1
    imm10 = h1 & 0x3FF
    j1 = (h2 >> 13) & 1
    j2 = (h2 >> 11) & 1
    imm11 = h2 & 0x7FF
    i1 = 1 - (j1 ^ sign)
    i2 = 1 - (j2 ^ sign)
    delta = ((sign << 24) | (i1 << 23) | (i2 << 22)
             | (imm10 << 12) | (imm11 << 1))
    if delta & (1 << 24):
        delta -= 1 << 25
    return (address + 4 + delta) & 0xFFFFFFFF
