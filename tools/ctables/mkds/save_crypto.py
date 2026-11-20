# Mario Kart DS Modding Trove
# tools/ctables/mkds/save_crypto.py — MKDS flash-save block encryption
# SPDX-License-Identifier: MIT
"""Encrypt/decrypt MKDS 0x100-aligned save blocks.

The four XOR tables are the stock flash-block cipher parameters. They live in
the tool, not in the public headers: they are implementation data, while the
headers describe the decrypted on-card records.
"""
from __future__ import annotations

import struct

MASK = 0xFFFFFFFF

T0 = [
    0xB6F2BA0C, 0x1A88BEF7, 0x0DDC276B, 0xB000F810, 0x6D254A35, 0x4C69572C,
    0x0E49CFC2, 0xA4391D94, 0x98E199E1, 0x10F88349, 0xA7CCE380, 0xF4287C11,
    0x93857987, 0xF1F1171F, 0x3487B1FA, 0x65B88727, 0xA1711A9C, 0x2338B1FE,
    0xF742B4DF, 0xA33235EC, 0x5350D303, 0xC9C1BE55, 0xC4FD2E1D, 0x8039E1DB,
    0xB6386F71, 0x34CBB389, 0x1224001A, 0x59CDEA11, 0x5371F238,
]
T1 = [
    0x83F3E485, 0x1F854511, 0x33FAE87B, 0xA6949A1E, 0xDB1DA3C5, 0xD5986A2F,
    0xAF6CC662, 0xFB04BD0F, 0x573F3084, 0xDFB9A74F, 0xF60A05B6, 0xDF57E7C7,
    0x11723659, 0x8EAE9859, 0xE08EB664, 0xD310802A, 0x498B2FA5, 0x555452F1,
    0xE5575C26,
]
T2 = [
    0xC0A2CFB9, 0xFCA4F59A, 0xD87E2588, 0xB615DD30, 0xEACC91EE, 0xB6A8F95D,
    0x7BD8B080, 0xCEC11555, 0x59CEF8CE, 0xFFF88DB3, 0xA867F2A3,
]
T3 = [
    0x54E85EA2, 0xDE7CE656, 0xD25261B4, 0x401D1EC4, 0x220DECE2, 0x1F0CF6F4,
    0x7176B2A6, 0x58D602EC, 0x859D5B49, 0xE5258B0C, 0xB31A2910, 0x2DDE04B1,
    0xEEEFA031, 0x5B852490, 0x44AD6965, 0x8E3206A5, 0x5E22B868,
]


def _xor(data: bytes, seed: int) -> bytes:
    if len(data) % 4:
        raise ValueError("save block body must be 32-bit aligned")
    words = list(struct.unpack("<%dI" % (len(data) // 4), data))
    i0, i1, i2, i3 = seed, 0, 0, 0
    out = []
    for word in words:
        key = (T2[i2] + T3[i3] + T1[i1] + T0[i0]) & MASK
        out.append(word ^ key)
        i2 += 1
        if i2 >= 0xB:
            i2 = 0
            i3 += 1
            if i3 >= 0x11:
                i3 = 0
                i1 += 1
                if i1 >= 0x13:
                    i1 = 0
                    i0 = (i0 + 1) % 0x1D
    return struct.pack("<%dI" % len(out), *out)


def find_seed(plain_first: int, signature: int) -> int:
    """Return the seed whose key stream maps signature to plain_first."""
    for seed in range(0x1D):
        key = (T0[seed] + T2[0] + T3[0] + T1[0]) & MASK
        if (signature ^ key) == plain_first:
            return seed
    raise ValueError("no save-block encryption seed matches this first word")


def decrypt_block(block: bytes, kind: str, is_header: bool = False) -> tuple[bytes, int]:
    """Decrypt one full block. Returns (decrypted_block, seed)."""
    signature = int.from_bytes(kind.encode("ascii"), "little")
    if is_header:
        prefix, body = block[:8], block[8:]
    else:
        prefix, body = b"", block
    first = struct.unpack_from("<I", body, 0)[0]
    seed = find_seed(first, signature)
    plain = _xor(body, seed)
    if struct.unpack_from("<I", plain, 0)[0] != signature:
        raise ValueError("decrypted block magic does not match")
    return prefix + plain, seed


def encrypt_block(plain: bytes, kind: str, seed: int, is_header: bool = False) -> bytes:
    """Encrypt one full decrypted block with a known seed."""
    signature = int.from_bytes(kind.encode("ascii"), "little")
    if is_header:
        prefix, body = plain[:8], plain[8:]
    else:
        prefix, body = b"", plain
    if struct.unpack_from("<I", body, 0)[0] != signature:
        raise ValueError("plaintext block magic does not match")
    return prefix + _xor(body, seed)


def crc16(data: bytes) -> int:
    crc = 0
    for byte in data:
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ 0x1021) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
            if byte & 0x80:
                crc ^= 1
            byte = (byte << 1) & 0xFF
    return crc


def refresh_footer(block: bytes) -> bytes:
    """Recompute the block CRC, preserving the two timestamp bytes."""
    out = bytearray(block)
    timestamp = bytes(out[-4:-2])
    out[-4:] = b"\0\0\0\0"
    crc = crc16(out)
    out[-4:-2] = timestamp
    out[-2] = (crc >> 8) & 0xFF
    out[-1] = crc & 0xFF
    return bytes(out)
