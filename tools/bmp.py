# Mario Kart DS Modding Trove
# tools/bmp.py — dependency-free BMP reader, writer and differ
# SPDX-License-Identifier: MIT
"""Small BMP helpers for screenshot verification."""

from __future__ import annotations

import struct


class Bmp:
    def __init__(self, width, height, pixels, top_down=True):
        self.width = width
        self.height = height
        self.pixels = pixels  # rows top-to-bottom, each row list[(r, g, b)]
        self.top_down = top_down

    def pixel(self, x, y):
        return self.pixels[y][x]


class IndexedBmp:
    """An 8-bit indexed BMP: one palette index per pixel."""

    def __init__(self, width, height, pixels, palette, top_down=True):
        self.width = width
        self.height = height
        self.pixels = pixels  # rows top-to-bottom, each row list[int]
        self.palette = palette  # list[(r, g, b)]
        self.top_down = top_down

    def pixel(self, x, y):
        return self.pixels[y][x]


def load(path):
    with open(path, "rb") as f:
        data = f.read()
    if data[:2] != b"BM":
        raise ValueError("not a BMP")
    offset = struct.unpack_from("<I", data, 10)[0]
    header = struct.unpack_from("<IiiHHIIiiII", data, 14)
    _, width, height, planes, bpp, compression, _, _, _, _, _ = header
    if planes != 1 or compression not in (0, 3):
        raise ValueError("unsupported BMP compression")
    top_down = height < 0
    height = abs(height)
    row_size = ((width * bpp + 31) // 32) * 4
    rows = []
    for y in range(height):
        src_y = y if top_down else height - 1 - y
        base = offset + src_y * row_size
        row = []
        for x in range(width):
            p = base + (x * bpp) // 8
            if bpp == 32:
                b, g, r = data[p], data[p + 1], data[p + 2]
            elif bpp == 24:
                b, g, r = data[p], data[p + 1], data[p + 2]
            else:
                raise ValueError(f"unsupported bpp {bpp}")
            row.append((r, g, b))
        rows.append(row)
    return Bmp(width, height, rows, top_down)


def load_indexed(path):
    with open(path, "rb") as f:
        data = f.read()
    if data[:2] != b"BM":
        raise ValueError("not a BMP")
    offset = struct.unpack_from("<I", data, 10)[0]
    (header_size, width, height, planes, bpp, compression, image_size,
     _, _, colors_used, _) = struct.unpack_from("<IiiHHIIiiII", data, 14)
    if planes != 1 or compression != 0 or bpp != 8:
        raise ValueError("expected an uncompressed 8-bit indexed BMP")
    if header_size < 40:
        raise ValueError("unsupported BMP header")
    top_down = height < 0
    height = abs(height)
    palette_bytes = data[14 + header_size:offset]
    count = colors_used or len(palette_bytes) // 4
    palette = []
    for index in range(count):
        b, g, r = palette_bytes[index * 4:index * 4 + 3]
        palette.append((r, g, b))
    row_size = ((width * 8 + 31) // 32) * 4
    rows = []
    for y in range(height):
        src_y = y if top_down else height - 1 - y
        base = offset + src_y * row_size
        rows.append(list(data[base:base + width]))
    return IndexedBmp(width, height, rows, palette, top_down)


def write_indexed(path, width, height, pixels, palette):
    """Write an 8-bit indexed BMP. ``pixels`` is rows of palette indices."""
    if len(palette) > 256:
        raise ValueError("BMP supports at most 256 palette entries")
    row_size = ((width * 8 + 31) // 32) * 4
    body = bytearray(row_size * height)
    for y in range(height):
        for x in range(width):
            value = int(pixels[y][x])
            if not 0 <= value <= 255:
                raise ValueError("palette index is outside 0..255")
            body[y * row_size + x] = value
    palette_bytes = bytearray(1024)
    for index, (r, g, b) in enumerate(palette):
        palette_bytes[index * 4:index * 4 + 4] = bytes([b, g, r, 0])
    offset = 14 + 40 + len(palette_bytes)
    size = offset + len(body)
    header = b"BM" + struct.pack("<IHHI", size, 0, 0, offset)
    info = struct.pack("<IiiHHIIiiII", 40, width, -height, 1, 8, 0,
                       len(body), 2835, 2835, len(palette), 0)
    with open(path, "wb") as f:
        f.write(header + info + palette_bytes + body)


def write(path, width, height, pixels):
    """Write a 24-bit top-down BMP. ``pixels`` is rows of ``(r, g, b)``."""
    row_size = ((width * 24 + 31) // 32) * 4
    body = bytearray(row_size * height)
    for y in range(height):
        for x in range(width):
            r, g, b = pixels[y][x]
            p = y * row_size + x * 3
            body[p:p + 3] = bytes([b, g, r])
    size = 54 + len(body)
    header = b"BM" + struct.pack("<IHHI", size, 0, 0, 54)
    info = struct.pack("<IiiHHIIiiII", 40, width, -height, 1, 24, 0,
                       len(body), 2835, 2835, 0, 0)
    with open(path, "wb") as f:
        f.write(header + info + body)


def compare(a_path, b_path, threshold=0):
    a = load(a_path)
    b = load(b_path)
    if (a.width, a.height) != (b.width, b.height):
        return {
            "same_size": False,
            "a": [a.width, a.height],
            "b": [b.width, b.height],
            "equal": False,
        }
    changed = 0
    max_delta = 0
    total_delta = 0
    x0, y0, x1, y1 = a.width, a.height, -1, -1
    for y in range(a.height):
        ra, rb = a.pixels[y], b.pixels[y]
        for x in range(a.width):
            pa, pb = ra[x], rb[x]
            d = max(abs(pa[0] - pb[0]), abs(pa[1] - pb[1]), abs(pa[2] - pb[2]))
            total_delta += d
            if d > max_delta:
                max_delta = d
            if d > threshold:
                changed += 1
                x0, y0 = min(x0, x), min(y0, y)
                x1, y1 = max(x1, x), max(y1, y)
    total = a.width * a.height
    return {
        "same_size": True,
        "width": a.width,
        "height": a.height,
        "total_pixels": total,
        "changed_pixels": changed,
        "changed_ratio": round(changed / total, 6) if total else 0.0,
        "max_delta": max_delta,
        "mean_delta": round(total_delta / total, 4) if total else 0.0,
        "bbox": [x0, y0, x1, y1] if changed else None,
        "equal": changed == 0,
    }


def save_diff(a_path, b_path, out_path, threshold=0):
    """Write a 24-bit BMP: identical pixels grey, changed pixels red."""
    a = load(a_path)
    b = load(b_path)
    if (a.width, a.height) != (b.width, b.height):
        raise ValueError("size mismatch")
    pixels = []
    for y in range(a.height):
        row = []
        for x in range(a.width):
            pa, pb = a.pixels[y][x], b.pixels[y][x]
            d = max(abs(pa[0] - pb[0]), abs(pa[1] - pb[1]), abs(pa[2] - pb[2]))
            row.append((255, 0, 0) if d > threshold else (32, 32, 32))
        pixels.append(row)
    write(out_path, a.width, a.height, pixels)
