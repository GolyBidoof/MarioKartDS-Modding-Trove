# Mario Kart DS Modding Trove
# tools/bmg.py — BMG (MESG/bmg1) reader, repair and append
# SPDX-License-Identifier: MIT
# Format notes: docs/bmg.md
"""Read and rewrite MESG/bmg1 message banks without storing game data.

Repairs the four-byte-short INF1 layout left by older appenders.  Labels are
supplied by the caller; this module has no mod-specific strings.
"""
from __future__ import annotations

import struct

MAGIC = b"MESG"
VERSION = b"bmg1"
HEADER_SIZE = 0x20
INF1 = b"INF1"
DAT1 = b"DAT1"
MID1 = b"MID1"


class BmgError(ValueError):
    pass


def _u16(data: bytes, off: int) -> int:
    return struct.unpack_from("<H", data, off)[0]


def _u32(data: bytes, off: int) -> int:
    return struct.unpack_from("<I", data, off)[0]


def _p32(value: int) -> bytes:
    return struct.pack("<I", value)


def _decode(data: bytes, off: int, encoding: int) -> str:
    if encoding == 2:
        end = off
        while end + 1 < len(data) and data[end:end + 2] != b"\0\0":
            end += 2
        return data[off:end].decode("utf-16-le", "replace")
    end = data.find(b"\0", off)
    if end < 0:
        end = len(data)
    return data[off:end].decode("latin-1")


def _encode(text: str, encoding: int) -> bytes:
    if encoding == 2:
        return text.encode("utf-16-le") + b"\0\0"
    return text.encode("latin-1") + b"\0"


class Bmg:
    def __init__(self, raw: bytes):
        if len(raw) < HEADER_SIZE or raw[:4] != MAGIC or raw[4:8] != VERSION:
            raise BmgError("not a MESG/bmg1 file")

        self.header = bytes(raw[:HEADER_SIZE])
        self.encoding = _u32(raw, 0x10)
        if self.encoding not in (0, 1, 2):
            raise BmgError(f"unsupported text encoding {self.encoding}")

        inf = raw.find(INF1, HEADER_SIZE)
        dat = raw.find(DAT1, HEADER_SIZE)
        mid = raw.find(MID1, HEADER_SIZE)
        if inf < 0 or dat < 0 or dat < inf:
            raise BmgError("missing INF1 or DAT1")
        if 0 <= mid < dat:
            raise BmgError("MID1 message-id tables are not supported")

        # Old appends wrote an INF1 size four bytes short, so the last
        # declared offset overlapped DAT1.  Trust the space before DAT1.
        count = _u16(raw, inf + 8)
        slots = (dat - (inf + 16)) // 4
        count = min(count, slots)

        dat_data = dat + 8
        dat_size = _u32(raw, dat + 4)
        data_len = max(0, dat_size - 8)
        if dat_data + data_len > len(raw):
            raise BmgError("DAT1 runs past the end of the file")

        self.strings: list[str] = []
        previous = -1
        for i in range(count):
            off = _u32(raw, inf + 16 + i * 4)
            # Stop at the zero an old append left in the INF1 padding.
            if off >= data_len or (i and off < previous):
                break
            previous = off
            self.strings.append(_decode(raw[dat_data:dat_data + data_len], off,
                                        self.encoding))

        end = dat + dat_size
        self.trailing = bytes(raw[end:]) if end <= len(raw) else b""

    def rebuilt(self, strings: list[str]) -> bytes:
        offsets: list[int] = []
        dat = bytearray()
        for text in strings:
            offsets.append(len(dat))
            dat += _encode(text, self.encoding)
            if len(dat) & 1:
                dat += b"\0"

        inf = bytearray()
        inf += INF1 + _p32(0) + struct.pack("<HH", len(strings), 4) + b"\0" * 4
        for off in offsets:
            inf += _p32(off)
        # DAT1 starts on a 0x20 boundary in every retail rule.bmg.
        while (HEADER_SIZE + len(inf)) % 0x20:
            inf += b"\0"
        struct.pack_into("<I", inf, 4, len(inf))

        dat_sec = bytearray(DAT1 + _p32(8 + len(dat)) + dat)
        while len(dat_sec) % 4:
            dat_sec += b"\0"
        struct.pack_into("<I", dat_sec, 4, len(dat_sec))

        out = bytearray(self.header)
        out += inf + dat_sec + self.trailing
        struct.pack_into("<I", out, 0x08, len(out))
        return bytes(out)


def strip_labels(strings: list[str], labels) -> list[str]:
    want = {label.strip().lower() for label in labels}
    return [s for s in strings if s.strip().lower() not in want]


def append_labels(raw: bytes, common_base: int, labels) -> bytes:
    bmg = Bmg(raw)
    base = strip_labels(bmg.strings, labels)
    if len(base) > common_base:
        raise BmgError(
            f"this file already has {len(base)} messages, more than the "
            f"common base {common_base}")
    strings = base + [""] * (common_base - len(base)) + list(labels)
    return bmg.rebuilt(strings)


def base_string_count(raw: bytes, labels) -> int:
    return len(strip_labels(Bmg(raw).strings, labels))
