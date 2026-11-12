# Mario Kart DS Modding Trove
# tools/nds.py — NDS/Nitro readers (BLZ, ARM9, FNT/FAT, NARC)
# SPDX-License-Identifier: MIT
# Format notes: docs/nitro.md, docs/arm9-autoloads.md
"""Minimal NDS/Nitro readers: BLZ, ARM9, ROM file table, NARC."""
from __future__ import annotations

import struct


def u16(data: bytes, off: int) -> int:
    return struct.unpack_from("<H", data, off)[0]


def u32(data: bytes, off: int) -> int:
    return struct.unpack_from("<I", data, off)[0]


def blz_decompress(data: bytes) -> bytes:
    if len(data) < 8:
        return bytes(data)
    inc_len = u32(data, len(data) - 4)
    if inc_len == 0:
        return bytes(data)
    header = u32(data, len(data) - 8)
    header_len = header >> 24
    enc_len = header & 0xFFFFFF
    raw_end = len(data) - enc_len
    out = bytearray(len(data) + inc_len)
    out[:raw_end] = data[:raw_end]
    src = len(data) - header_len
    dst = len(out)
    while dst > raw_end and src > raw_end:
        src -= 1
        flags = data[src]
        for _ in range(8):
            if dst <= raw_end or src <= raw_end:
                break
            if flags & 0x80:
                b1 = data[src - 1]
                b2 = data[src - 2]
                src -= 2
                length = (b1 >> 4) + 3
                disp = (((b1 & 0xF) << 8) | b2) + 3
                for _ in range(length):
                    dst -= 1
                    out[dst] = out[dst + disp]
            else:
                src -= 1
                dst -= 1
                out[dst] = data[src]
            flags = (flags << 1) & 0xFF
    return bytes(out)


MODULE_MAGIC = struct.pack("<II", 0xDEC00621, 0x2106C0DE)


class Arm9Image:
    """Address-aware ARM9 view.

    The main image lives at ``addr - base``; autoload payloads live from
    ``autoload_start - base`` onwards.  Patch pointers are runtime addresses,
    so tables must be read through the autoload list.
    """

    def __init__(self, data: bytes, base: int):
        self.data = data
        self.base = base
        pos = data.find(MODULE_MAGIC)
        if pos < 0x1C:
            raise ValueError("module params magic not found")
        mp = pos - 0x1C
        self.autoload_start = u32(data, mp + 8)
        list_start = u32(data, mp + 0)
        list_end = u32(data, mp + 4)
        self.autoloads: list[tuple[int, int, int]] = []
        payload = self.autoload_start - base
        p = list_start - base
        while p < list_end - base:
            address = u32(data, p)
            size = u32(data, p + 4)
            self.autoloads.append((address, size, payload))
            payload += size
            p += 12

    def offset(self, address: int) -> int:
        if self.base <= address < self.autoload_start:
            return address - self.base
        for start, size, payload in self.autoloads:
            if start <= address < start + size:
                return payload + (address - start)
        raise KeyError(f"address {address:#x} is not stored in this image")

    def u16(self, address: int) -> int:
        return u16(self.data, self.offset(address))

    def u32(self, address: int) -> int:
        return u32(self.data, self.offset(address))


def _maybe_decompress(raw: bytes, base: int) -> bytes:
    """Use ``compressed_static_end``; the magic also exists in compressed data."""
    pos = raw.find(MODULE_MAGIC)
    if pos >= 0x1C:
        mp = pos - 0x1C
        if mp + 0x18 <= len(raw):
            compressed_end = u32(raw, mp + 0x14)
            if compressed_end:
                cut = compressed_end - base
                if not 0 < cut <= len(raw):
                    raise ValueError(
                        f"compressed_static_end {compressed_end:#x} is outside "
                        f"the ARM9 image")
                out = bytearray(blz_decompress(raw[:cut]) + raw[cut:])
                struct.pack_into("<I", out, mp + 0x14, 0)
                return bytes(out)
            return raw
    out = blz_decompress(raw)
    if MODULE_MAGIC not in out:
        raise ValueError("ARM9 is neither plain nor a BLZ image with module params")
    return out


def arm9_from_nds(path: str) -> tuple[bytes, int]:
    with open(path, "rb") as handle:
        data = handle.read()
    arm9_off = u32(data, 0x20)
    arm9_size = u32(data, 0x2C)
    base = u32(data, 0x28) or 0x02000000
    return _maybe_decompress(data[arm9_off:arm9_off + arm9_size], base), base


def read_fnt(data: bytes, fnt_off: int) -> dict[str, int]:
    root = struct.unpack_from("<IHH", data, fnt_off)
    dirs = [struct.unpack_from("<IHH", data, fnt_off + i * 8)
            for i in range(root[2])]
    files: dict[str, int] = {}

    def walk(idx: int, prefix: str) -> None:
        entry_start, fid, _ = dirs[idx]
        p = fnt_off + entry_start
        while True:
            kind = data[p]
            p += 1
            if kind == 0:
                break
            n = kind & 0x7F
            name = data[p:p + n].decode("ascii", "replace")
            p += n
            if kind & 0x80:
                child = struct.unpack_from("<H", data, p)[0]
                p += 2
                walk(child - 0xF000, prefix + name + "/")
            else:
                files[prefix + name] = fid
                fid += 1

    walk(0, "")
    return files


def fat_entries(data: bytes, fat_off: int, fat_size: int) -> list[tuple[int, int]]:
    return [struct.unpack_from("<II", data, fat_off + i * 8)
            for i in range(fat_size // 8)]


def nds_member(data: bytes, path: str) -> bytes:
    fnt_off, _, fat_off, fat_size = struct.unpack_from("<IIII", data, 0x40)
    files = read_fnt(data, fnt_off)
    fid = files[path]
    start, end = fat_entries(data, fat_off, fat_size)[fid]
    return data[start:end + 1]


def lz77_decompress(data: bytes) -> bytes:
    size = data[1] | data[2] << 8 | data[3] << 16
    out = bytearray(size)
    p = 4
    o = 0
    while o < size:
        header = data[p]
        p += 1
        for _ in range(8):
            if o >= size:
                break
            if header & 0x80:
                a = data[p]
                b = data[p + 1]
                p += 2
                off = (((a & 0xF) << 8) | b) + 1
                n = (a >> 4) + 3
                for _ in range(n):
                    if o >= size:
                        break
                    out[o] = out[o - off]
                    o += 1
            else:
                out[o] = data[p]
                p += 1
                o += 1
            header = (header << 1) & 0xFF
    return bytes(out)


def unpack_narc(data: bytes) -> dict[str, bytes]:
    if data[:1] == b"\x10":
        data = lz77_decompress(data)
    if data[:4] != b"NARC":
        raise ValueError("not a NARC")
    btaf = 0x10
    btaf_size = u32(data, btaf + 4)
    count = u16(data, btaf + 8)
    btnf = btaf + btaf_size
    btnf_size = u32(data, btnf + 4)
    gmif = btnf + btnf_size
    if data[gmif:gmif + 4] != b"GMIF":
        raise ValueError("NARC has no GMIF")
    data_base = gmif + 8
    entries = [struct.unpack_from("<II", data, btaf + 0xC + i * 8)
               for i in range(count)]

    base = btnf + 8
    root = struct.unpack_from("<IHH", data, base)
    dirs = [struct.unpack_from("<IHH", data, base + i * 8)
            for i in range(root[2])]
    names: dict[int, str] = {}

    def walk(idx: int, prefix: str) -> None:
        entry_start, fid, _ = dirs[idx]
        p = base + entry_start
        while True:
            kind = data[p]
            p += 1
            if kind == 0:
                break
            n = kind & 0x7F
            name = data[p:p + n].decode("ascii", "replace")
            p += n
            if kind & 0x80:
                child = struct.unpack_from("<H", data, p)[0]
                p += 2
                walk(child - 0xF000, prefix + name + "/")
            else:
                names[fid] = prefix + name
                fid += 1

    walk(0, "")
    out = {}
    for i, (start, end) in enumerate(entries):
        out[names[i]] = data[data_base + start:data_base + end]
    return out
