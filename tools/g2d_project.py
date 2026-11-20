# Mario Kart DS Modding Trove
# tools/g2d_project.py — lossless editable G2D tileset/palette projects
# SPDX-License-Identifier: MIT
"""Convert NCGR/NCLR pairs to an editable project and back.

    python3 tools/g2d_project.py export tiles.ncgr --palette tiles.nclr \
        -o out/tiles
    # edit out/tiles/tiles.bmp and out/tiles/palette_00.pal
    python3 tools/g2d_project.py import out/tiles \
        -o rebuilt.ncgr --palette rebuilt.nclr

The project keeps an 8-bit indexed BMP, one JASC-PAL file per palette bank,
and a JSON manifest with the exact file/block header bytes and any trailing
bytes. The manifest is authoritative for headers and tile order; the BMP and
palette files are the editable surfaces. Unedited projects rebuild the input
bytes exactly.
"""
from __future__ import annotations

import argparse
import json
import math
import struct
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from tools import bmp  # noqa: E402

PROJECT_FORMAT = "mkds-g2d-project"
PROJECT_VERSION = 1

NCGR_MAGIC = b"RGCN"
NCGR_CHAR = b"RAHC"
NCLR_MAGIC = b"RLCN"
NCLR_LEGACY = b"RPCN"
NCLR_PLTT = b"TTLP"
NCLR_PCMP = b"PMCP"

TILE_SIZE = 8
TILE_BYTES_4BPP = 32
TILE_BYTES_8BPP = 64


class ProjectError(ValueError):
    pass


def _u16(data: bytes, off: int) -> int:
    return struct.unpack_from("<H", data, off)[0]


def _u32(data: bytes, off: int) -> int:
    return struct.unpack_from("<I", data, off)[0]


def _s16(data: bytes, off: int) -> int:
    return struct.unpack_from("<h", data, off)[0]


def _p16(data: bytearray, off: int, value: int) -> None:
    struct.pack_into("<H", data, off, value & 0xFFFF)


def _p32(data: bytearray, off: int, value: int) -> None:
    struct.pack_into("<I", data, off, value & 0xFFFFFFFF)


def _hex(data: bytes) -> str:
    return data.hex()


def _unhex(text: str) -> bytes:
    return bytes.fromhex(text or "")


def rgb555_to_rgb8(value: int) -> tuple[int, int, int]:
    red = value & 0x1F
    green = (value >> 5) & 0x1F
    blue = (value >> 10) & 0x1F
    return ((red << 3) | (red >> 2),
            (green << 3) | (green >> 2),
            (blue << 3) | (blue >> 2))


def rgb8_to_rgb555(rgb: tuple[int, int, int]) -> int:
    red, green, blue = rgb
    return ((round(red * 31 / 255) & 0x1F)
            | ((round(green * 31 / 255) & 0x1F) << 5)
            | ((round(blue * 31 / 255) & 0x1F) << 10))


def _parse_ncgr(data: bytes) -> dict:
    if len(data) < 0x30 or data[:4] != NCGR_MAGIC:
        raise ProjectError("not an NCGR (RGCN) file")
    if data[0x10:0x14] != NCGR_CHAR:
        raise ProjectError("NCGR is missing its CHAR block")
    color_format = _u32(data, 0x1C)
    if color_format not in (3, 4):
        raise ProjectError(f"unsupported NCGR colour format {color_format}")
    bpp = 4 if color_format == 3 else 8
    data_size = _u32(data, 0x28)
    data_offset = _u32(data, 0x2C)
    start = 0x18 + data_offset
    end = start + data_size
    if end > len(data):
        raise ProjectError("NCGR character data runs past the file")
    tile_bytes = TILE_BYTES_4BPP if bpp == 4 else TILE_BYTES_8BPP
    full_tiles, trailing = divmod(data_size, tile_bytes)
    width = _u16(data, 0x18)
    height = _u16(data, 0x1A)
    if 1 <= width <= 64:
        tiles_per_row = width
    elif 1 <= height <= 64:
        tiles_per_row = height
    else:
        tiles_per_row = max(1, min(32, math.isqrt(max(1, full_tiles - 1)) + 1))
    tiles_per_row = max(1, min(64, tiles_per_row))
    return {
        "prefix_hex": _hex(data[:start]),
        "suffix_hex": _hex(data[end:]),
        "bpp": bpp,
        "color_format": color_format,
        "tile_count": full_tiles,
        "trailing_hex": _hex(data[start + full_tiles * tile_bytes:end]),
        "tiles_per_row": tiles_per_row,
        "width": width,
        "height": height,
        "mapping_type": _u32(data, 0x20),
        "data_size": data_size,
        "data_offset": data_offset,
        "raw": data,
    }


def _unpack_tile(raw: bytes, bpp: int) -> list[list[int]]:
    pixels = [[0] * TILE_SIZE for _ in range(TILE_SIZE)]
    if bpp == 4:
        for y in range(TILE_SIZE):
            for x in range(TILE_SIZE):
                byte = raw[y * 4 + x // 2]
                pixels[y][x] = (byte & 0x0F) if x % 2 == 0 else (byte >> 4)
    else:
        for y in range(TILE_SIZE):
            for x in range(TILE_SIZE):
                pixels[y][x] = raw[y * TILE_SIZE + x]
    return pixels


def _pack_tile(pixels: list[list[int]], bpp: int) -> bytes:
    if bpp == 4:
        out = bytearray(TILE_BYTES_4BPP)
        for y in range(TILE_SIZE):
            for x in range(TILE_SIZE):
                value = pixels[y][x] & 0x0F
                index = y * 4 + x // 2
                if x % 2 == 0:
                    out[index] = (out[index] & 0xF0) | value
                else:
                    out[index] = (out[index] & 0x0F) | (value << 4)
        return bytes(out)
    out = bytearray(TILE_BYTES_8BPP)
    for y in range(TILE_SIZE):
        for x in range(TILE_SIZE):
            out[y * TILE_SIZE + x] = pixels[y][x] & 0xFF
    return bytes(out)


def _tile_image(parsed: dict, data: bytes) -> tuple[list[list[int]], int, int]:
    bpp = parsed["bpp"]
    tile_bytes = TILE_BYTES_4BPP if bpp == 4 else TILE_BYTES_8BPP
    count = parsed["tile_count"]
    per_row = parsed["tiles_per_row"]
    columns = per_row
    rows = max(1, (count + per_row - 1) // per_row)
    width = columns * TILE_SIZE
    height = rows * TILE_SIZE
    pixels = [[0] * width for _ in range(height)]
    start = 0x18 + parsed["data_offset"]
    for tile in range(count):
        raw = data[start + tile * tile_bytes:start + (tile + 1) * tile_bytes]
        block = _unpack_tile(raw, bpp)
        tx = (tile % per_row) * TILE_SIZE
        ty = (tile // per_row) * TILE_SIZE
        for y in range(TILE_SIZE):
            pixels[ty + y][tx:tx + TILE_SIZE] = block[y]
    return pixels, width, height


def _parse_nclr(data: bytes) -> dict:
    if len(data) < 0x28 or data[:4] not in (NCLR_MAGIC, NCLR_LEGACY):
        raise ProjectError("not an NCLR (RLCN/RPCN) file")
    if data[0x10:0x14] != NCLR_PLTT:
        raise ProjectError("NCLR is missing its PLTT block")
    format_value = _u32(data, 0x18)
    if format_value not in (3, 4):
        raise ProjectError(f"unsupported NCLR palette format {format_value}")
    block_size = _u32(data, 0x14)
    payload_size = max(0, block_size - 0x18)
    start = 0x28
    end = start + payload_size
    if end > len(data):
        raise ProjectError("NCLR palette data runs past the file")
    bank_size = 16 if format_value == 3 else 256
    colors = list(struct.unpack_from("<%dH" % (payload_size // 2), data, start))
    banks = [colors[index:index + bank_size]
             for index in range(0, len(colors), bank_size)]
    if not banks:
        banks = [[]]
    return {
        "prefix_hex": _hex(data[:start]),
        "suffix_hex": _hex(data[end:]),
        "format": format_value,
        "bank_size": bank_size,
        "banks": banks,
        "data_size": _u32(data, 0x20),
        "payload_size": payload_size,
        "raw": data,
    }


def _write_pal(path: Path, colors: list[int]) -> None:
    lines = ["JASC-PAL", "0100", str(len(colors))]
    for value in colors:
        red, green, blue = rgb555_to_rgb8(value)
        lines.append(f"{red} {green} {blue}")
    path.write_text("\n".join(lines) + "\n", encoding="ascii")


def _read_pal(path: Path) -> list[tuple[int, int, int]]:
    lines = [line.strip() for line in path.read_text(encoding="utf-8").splitlines()]
    if not lines:
        raise ProjectError(f"{path}: empty palette")
    if lines[0].upper() == "JASC-PAL":
        if len(lines) < 3:
            raise ProjectError(f"{path}: truncated JASC-PAL header")
        count = int(lines[2])
        lines = lines[3:3 + count]
    colors = []
    for line in lines:
        if not line or line.startswith("#"):
            continue
        parts = line.replace(",", " ").split()
        if len(parts) < 3:
            raise ProjectError(f"{path}: bad palette line {line!r}")
        colors.append(tuple(int(part) for part in parts[:3]))
    return colors


def _merge_palette(colors: list[int], rgb: list[tuple[int, int, int]]) -> list[int]:
    merged = list(colors)
    for index, value in enumerate(merged):
        if index < len(rgb):
            expanded = rgb555_to_rgb8(value)
            if tuple(rgb[index]) != expanded:
                merged[index] = rgb8_to_rgb555(tuple(rgb[index]))
    if len(rgb) > len(merged):
        merged.extend(rgb8_to_rgb555(tuple(item)) for item in rgb[len(merged):])
    return merged


def export_project(ncgr_path: Path, nclr_path: Path | None, outdir: Path) -> int:
    ncgr_raw = ncgr_path.read_bytes()
    ncgr = _parse_ncgr(ncgr_raw)
    outdir.mkdir(parents=True, exist_ok=True)
    pixels, width, height = _tile_image(ncgr, ncgr_raw)
    palette = _palette_all(nclr_path, ncgr["bpp"])
    palette_rgb = [rgb555_to_rgb8(value) for value in palette]
    bmp.write_indexed(outdir / "tiles.bmp", width, height, pixels, palette_rgb)

    manifest = {
        "format": PROJECT_FORMAT,
        "version": PROJECT_VERSION,
        "image": "tiles.bmp",
        "transparent_index": 0,
        "ncgr": {
            "prefix_hex": ncgr["prefix_hex"],
            "suffix_hex": ncgr["suffix_hex"],
            "bpp": ncgr["bpp"],
            "color_format": ncgr["color_format"],
            "tile_count": ncgr["tile_count"],
            "trailing_hex": ncgr["trailing_hex"],
            "tiles_per_row": ncgr["tiles_per_row"],
            "width": ncgr["width"],
            "height": ncgr["height"],
            "mapping_type": ncgr["mapping_type"],
            "data_size": ncgr["data_size"],
            "data_offset": ncgr["data_offset"],
        },
    }

    if nclr_path is not None:
        nclr_raw = nclr_path.read_bytes()
        nclr = _parse_nclr(nclr_raw)
        manifest["nclr"] = {
            "prefix_hex": nclr["prefix_hex"],
            "suffix_hex": nclr["suffix_hex"],
            "format": nclr["format"],
            "bank_size": nclr["bank_size"],
            "bank_files": [],
            "palette_image": "tiles.bmp",
            "colors_rgb555": nclr["banks"],
            "data_size": nclr["data_size"],
            "payload_size": nclr["payload_size"],
        }
    else:
        manifest["nclr"] = None

    (outdir / "project.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"exported {ncgr_path.name} -> {outdir}")
    return 0


def _palette_all(nclr_path: Path | None, bpp: int) -> list[int]:
    """All palette banks concatenated into one 256-entry BMP palette."""
    values: list[int] = []
    if nclr_path is not None:
        nclr = _parse_nclr(nclr_path.read_bytes())
        values = [value for bank in nclr["banks"] for value in bank]
    if not values:
        size = 16 if bpp == 4 else 256
        values = [((index * 8) & 0x1F)
                  | (((index * 3) & 0x1F) << 5)
                  | (((index * 5) & 0x1F) << 10)
                  for index in range(size)]
    return (values + [0] * 256)[:256]


def _rebuild_ncgr(manifest: dict, outdir: Path) -> bytes:
    info = manifest["ncgr"]
    image = bmp.load_indexed(outdir / manifest["image"])
    per_row = int(info["tiles_per_row"])
    bpp = int(info["bpp"])
    tile_bytes = TILE_BYTES_4BPP if bpp == 4 else TILE_BYTES_8BPP
    columns = per_row
    rows = max(1, (int(info["tile_count"]) + per_row - 1) // per_row)
    expected = (columns * TILE_SIZE, rows * TILE_SIZE)
    if (image.width, image.height) != expected:
        raise ProjectError(
            f"tiles.bmp is {image.width}x{image.height}, expected "
            f"{expected[0]}x{expected[1]} for {info['tile_count']} tiles")
    data = bytearray()
    for tile in range(int(info["tile_count"])):
        tx = (tile % per_row) * TILE_SIZE
        ty = (tile // per_row) * TILE_SIZE
        block = [row[tx:tx + TILE_SIZE] for row in image.pixels[ty:ty + TILE_SIZE]]
        data += _pack_tile(block, bpp)
    data += _unhex(info["trailing_hex"])
    prefix = bytearray(_unhex(info["prefix_hex"]))
    _p32(prefix, 0x08, 0)  # file size, filled below
    _p32(prefix, 0x14, 0x20 + len(data))  # CHAR block size
    _p32(prefix, 0x28, len(data))  # CHAR data size
    suffix = _unhex(info["suffix_hex"])
    out = bytes(prefix) + bytes(data) + suffix
    result = bytearray(out)
    _p32(result, 0x08, len(result))
    return bytes(result)


def _rebuild_nclr(manifest: dict, outdir: Path) -> bytes:
    info = manifest["nclr"]
    rgb555_banks = info.get("colors_rgb555") or []
    expected = [value for bank in rgb555_banks for value in bank]
    total = sum(len(bank) for bank in rgb555_banks)
    if not total:
        total = int(info.get("payload_size", 0)) // 2
    colors: list[int] = []
    bank_files = info.get("bank_files") or []
    if bank_files:
        for index, name in enumerate(bank_files):
            original = list(rgb555_banks[index]) if index < len(rgb555_banks) else []
            path = outdir / name
            if path.exists():
                colors.extend(_merge_palette(original, _read_pal(path)))
            else:
                colors.extend(original)
    else:
        image_name = info.get("palette_image") or "tiles.bmp"
        image_path = outdir / image_name
        if image_path.exists():
            image = bmp.load_indexed(image_path)
            palette_rgb = list(image.palette) + [(0, 0, 0)] * 256
            if not expected:
                colors = [rgb8_to_rgb555(tuple(palette_rgb[index]))
                          for index in range(total)]
            else:
                for index in range(max(total, 256)):
                    original = expected[index] if index < len(expected) else 0
                    rgb = palette_rgb[index] if index < len(palette_rgb) else (0, 0, 0)
                    if tuple(rgb) == rgb555_to_rgb8(original):
                        colors.append(original)
                    else:
                        colors.append(rgb8_to_rgb555(tuple(rgb)))
                colors = colors[:total]
        else:
            colors = expected
    data = bytearray()
    for value in colors:
        data += struct.pack("<H", value & 0xFFFF)
    prefix = bytearray(_unhex(info["prefix_hex"]))
    _p32(prefix, 0x08, 0)
    _p32(prefix, 0x14, 0x18 + len(data))
    declared = info.get("data_size", len(data))
    if len(data) != int(info.get("payload_size", len(data))):
        declared = len(data)
    _p32(prefix, 0x20, declared)
    suffix = _unhex(info["suffix_hex"])
    out = bytes(prefix) + bytes(data) + suffix
    result = bytearray(out)
    _p32(result, 0x08, len(result))
    return bytes(result)


def import_project(project_dir: Path, ncgr_path: Path,
                   nclr_path: Path | None) -> int:
    manifest = json.loads((project_dir / "project.json").read_text(encoding="utf-8"))
    if manifest.get("format") != PROJECT_FORMAT:
        raise ProjectError("not an MKDS G2D project")
    ncgr_path.parent.mkdir(parents=True, exist_ok=True)
    ncgr_path.write_bytes(_rebuild_ncgr(manifest, project_dir))
    if nclr_path is not None:
        if not manifest.get("nclr"):
            raise ProjectError("project has no NCLR palette")
        nclr_path.parent.mkdir(parents=True, exist_ok=True)
        nclr_path.write_bytes(_rebuild_nclr(manifest, project_dir))
    print(f"rebuilt {ncgr_path}" + (f" and {nclr_path}" if nclr_path else ""))
    return 0



def _parse_ncer(data: bytes) -> dict:
    if len(data) < 0x30 or data[:4] != b"RECN":
        raise ProjectError("not an NCER (RECN) file")
    if data[0x10:0x14] != b"KBEC":
        raise ProjectError("NCER is missing its CEBK block")
    block_size = _u32(data, 0x14)
    count = _u16(data, 0x18)
    attributes = _u16(data, 0x1A)
    cell_offset = _u32(data, 0x1C)
    stride = 16 if attributes & 1 else 8
    start = 0x18 + cell_offset
    end = start + count * stride
    if end > len(data) or 0x10 + block_size > len(data):
        raise ProjectError("NCER cell data runs past the file")
    oam_start = end
    oam_end = 0x10 + block_size
    oam_area = data[oam_start:oam_end]
    cells = []
    for index in range(count):
        base = start + index * stride
        oam_count = _u16(data, base)
        cell_attributes = _u16(data, base + 2)
        oam_offset = _u32(data, base + 4)
        cell = {
            "oam_count": oam_count,
            "attributes": cell_attributes,
            "oam": [],
        }
        if stride == 16:
            cell["bbox"] = [_s16(data, base + 8), _s16(data, base + 10),
                            _s16(data, base + 12), _s16(data, base + 14)]
        for oam in range(oam_count):
            off = oam_offset + oam * 6
            if off + 6 > len(oam_area):
                raise ProjectError("NCER OAM data runs past the block")
            cell["oam"].append([_u16(oam_area, off),
                                _u16(oam_area, off + 2),
                                _u16(oam_area, off + 4)])
        cells.append(cell)
    return {
        "prefix_hex": _hex(data[:0x30]),
        "suffix_hex": _hex(data[0x10 + block_size:]),
        "cells": cells,
        "oam_area_hex": _hex(oam_area),
        "block_size": block_size,
        "file_size": _u32(data, 0x08),
        "actual_size": len(data),
        "cell_offset": cell_offset,
        "attributes": attributes,
        "mapping_mode": _u32(data, 0x20),
    }


def _rebuild_ncer(manifest: dict) -> bytes:
    info = manifest["ncer"]
    cells = info["cells"]
    stride = 16 if int(info["attributes"]) & 1 else 8
    cell_area = bytearray()
    oam_area = bytearray()
    for cell in cells:
        oam = cell.get("oam", [])
        oam_offset = len(oam_area)
        for entry in oam:
            for value in entry:
                oam_area += struct.pack("<H", int(value) & 0xFFFF)
        cell_area += struct.pack("<HHI", len(oam),
                                 int(cell.get("attributes", 0)) & 0xFFFF,
                                 oam_offset)
        if stride == 16:
            bbox = cell.get("bbox", [0, 0, 0, 0])
            for value in bbox:
                cell_area += struct.pack("<H", int(value) & 0xFFFF)
    payload = bytes(cell_area + oam_area)
    prefix = bytearray(_unhex(info["prefix_hex"]))
    block_size = 0x20 + len(payload)
    file_size = info.get("file_size", len(prefix) + len(payload) + len(_unhex(info["suffix_hex"])))
    if block_size != int(info.get("block_size", block_size)):
        file_size = len(prefix) + len(payload) + len(_unhex(info["suffix_hex"]))
    _p32(prefix, 0x08, file_size)
    _p32(prefix, 0x14, block_size)
    _p16(prefix, 0x18, len(cells))
    _p16(prefix, 0x1A, int(info["attributes"]) & 0xFFFF)
    _p32(prefix, 0x1C, int(info["cell_offset"]))
    _p32(prefix, 0x20, int(info["mapping_mode"]))
    suffix = _unhex(info["suffix_hex"])
    out = bytearray(prefix) + payload + suffix
    return bytes(out)



_OBJ_SIZES = {
    0: ((8, 8), (16, 16), (32, 32), (64, 64)),
    1: ((16, 8), (32, 8), (32, 16), (64, 32)),
    2: ((8, 16), (8, 32), (16, 32), (32, 64)),
}


def _signed(value: int, bits: int) -> int:
    sign = 1 << (bits - 1)
    return value - (1 << bits) if value & sign else value


def _render_ncer(ncgr_raw: bytes, nclr_raw: bytes | None,
                 ncer_raw: bytes) -> tuple[list[list[tuple[int, int, int]]], int, int]:
    ncgr = _parse_ncgr(ncgr_raw)
    ncer = _parse_ncer(ncer_raw)
    bpp = ncgr["bpp"]
    tile_bytes = TILE_BYTES_4BPP if bpp == 4 else TILE_BYTES_8BPP
    start = 0x18 + ncgr["data_offset"]
    raw_tiles = []
    for index in range(ncgr["tile_count"]):
        raw = ncgr_raw[start + index * tile_bytes:
                       start + (index + 1) * tile_bytes]
        raw_tiles.append(_unpack_tile(raw, bpp))
    if nclr_raw is not None:
        banks = _parse_nclr(nclr_raw)["banks"]
    else:
        banks = []
    if bpp == 4:
        colors = []
        for bank in range(16):
            entries = banks[bank] if bank < len(banks) else []
            colors.extend(entries[:16])
            colors.extend([0] * (16 - min(16, len(entries))))
    else:
        colors = list(banks[0][:256]) if banks else []
        colors.extend([0] * (256 - len(colors)))
    palette = [rgb555_to_rgb8(value) for value in colors]

    cells = []
    for cell in ncer["cells"]:
        bbox = cell.get("bbox")
        if bbox:
            max_x, max_y, min_x, min_y = bbox
        else:
            min_x = min_y = 0
            max_x = max_y = 0
            for oam in cell.get("oam", []):
                attr0, attr1, _ = oam
                shape = (attr0 >> 14) & 3
                size = (attr1 >> 14) & 3
                wide = _OBJ_SIZES.get(shape, _OBJ_SIZES[0])[size]
                x = _signed(attr1 & 0x1FF, 9)
                y = _signed(attr0 & 0xFF, 8)
                min_x = min(min_x, x)
                min_y = min(min_y, y)
                max_x = max(max_x, x + wide[0])
                max_y = max(max_y, y + wide[1])
        width = max(1, max_x - min_x)
        height = max(1, max_y - min_y)
        canvas = [[(255, 0, 255)] * width for _ in range(height)]
        for oam in cell.get("oam", []):
            attr0, attr1, attr2 = oam
            shape = (attr0 >> 14) & 3
            size = (attr1 >> 14) & 3
            obj_w, obj_h = _OBJ_SIZES.get(shape, _OBJ_SIZES[0])[size]
            x = _signed(attr1 & 0x1FF, 9) - min_x
            y = _signed(attr0 & 0xFF, 8) - min_y
            hflip = bool(attr1 & 0x1000)
            vflip = bool(attr1 & 0x2000)
            tile = attr2 & 0x3FF
            bank = (attr2 >> 12) & 0x0F if bpp == 4 else 0
            step = 1 if bpp == 4 else 2
            tiles_x = max(1, obj_w // 8)
            for ty in range(obj_h // 8):
                for tx in range(obj_w // 8):
                    index = tile + (ty * tiles_x + tx) * step
                    if index >= len(raw_tiles):
                        continue
                    block = raw_tiles[index]
                    for py in range(8):
                        for px in range(8):
                            sx = 7 - px if hflip else px
                            sy = 7 - py if vflip else py
                            color = block[sy][sx]
                            value = bank * 16 + color if bpp == 4 else color
                            dx = x + tx * 8 + px
                            dy = y + ty * 8 + py
                            if 0 <= dx < width and 0 <= dy < height:
                                canvas[dy][dx] = palette[value % 256]
        cells.append(canvas)

    if not cells:
        return [[(255, 0, 255)]], 1, 1
    max_width = 512
    pad = 2
    positions = []
    x = y = row_height = 0
    sheet_width = 0
    for canvas in cells:
        width = len(canvas[0]) if canvas else 1
        height = len(canvas) if canvas else 1
        if x and x + width > max_width:
            x = 0
            y += row_height + pad
            row_height = 0
        positions.append((x, y))
        x += width + pad
        row_height = max(row_height, height)
        sheet_width = max(sheet_width, x)
    sheet_height = y + row_height
    sheet = [[(32, 32, 32)] * sheet_width for _ in range(sheet_height)]
    for canvas, (px, py) in zip(cells, positions):
        for cy, row in enumerate(canvas):
            sheet[py + cy][px:px + len(row)] = row
    return sheet, sheet_width, sheet_height

def export_ncer(path: Path, outdir: Path, ncgr_path: Path | None = None,
                nclr_path: Path | None = None) -> int:
    raw = path.read_bytes()
    parsed = _parse_ncer(raw)
    outdir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "format": PROJECT_FORMAT,
        "version": PROJECT_VERSION,
        "ncer": parsed,
    }
    if ncgr_path is not None:
        preview, width, height = _render_ncer(
            ncgr_path.read_bytes(),
            nclr_path.read_bytes() if nclr_path is not None else None, raw)
        bmp.write(outdir / "cells_preview.bmp", width, height, preview)
        manifest["cells_preview"] = "cells_preview.bmp"
        manifest["tiles_source"] = ncgr_path.name
        if nclr_path is not None:
            manifest["palette_source"] = nclr_path.name
    (outdir / "ncer.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"exported {path.name} -> {outdir / 'ncer.json'}")
    return 0


def import_ncer(project_dir: Path, output: Path) -> int:
    manifest = json.loads((project_dir / "ncer.json").read_text(encoding="utf-8"))
    output.write_bytes(_rebuild_ncer(manifest))
    print(f"rebuilt {output}")
    return 0



def _render_nscr(ncgr_raw: bytes, nclr_raw: bytes | None,
                 nscr_raw: bytes) -> tuple[list[list[int]], list[tuple[int, int, int]]]:
    ncgr = _parse_ncgr(ncgr_raw)
    screen = _parse_nscr(nscr_raw)
    bpp = ncgr["bpp"]
    tile_bytes = TILE_BYTES_4BPP if bpp == 4 else TILE_BYTES_8BPP
    start = 0x18 + ncgr["data_offset"]
    raw_tiles = []
    for index in range(ncgr["tile_count"]):
        raw = ncgr_raw[start + index * tile_bytes:
                       start + (index + 1) * tile_bytes]
        raw_tiles.append(_unpack_tile(raw, bpp))
    if nclr_raw is not None:
        nclr = _parse_nclr(nclr_raw)
        banks = nclr["banks"]
    else:
        banks = []
    if bpp == 4:
        palette_values = []
        for bank in range(16):
            colors = banks[bank] if bank < len(banks) else []
            palette_values.extend(colors[:16])
            palette_values.extend([0] * (16 - min(16, len(colors))))
    else:
        colors = banks[0] if banks else []
        palette_values = list(colors[:256])
        palette_values.extend([0] * (256 - len(palette_values)))
    palette = [rgb555_to_rgb8(value) for value in palette_values]
    width, height = screen["width"], screen["height"]
    pixels = [[0] * width for _ in range(height)]
    entries = screen["entries"]
    tiles_x = max(1, width // TILE_SIZE)
    for tile_y in range(max(1, height // TILE_SIZE)):
        for tile_x in range(tiles_x):
            index = tile_y * tiles_x + tile_x
            if index >= len(entries):
                break
            entry = entries[index]
            tile_index = entry & 0x3FF
            if tile_index >= len(raw_tiles):
                continue
            bank = (entry >> 12) & 0x0F if bpp == 4 else 0
            hflip = bool(entry & 0x0400)
            vflip = bool(entry & 0x0800)
            block = raw_tiles[tile_index]
            for y in range(TILE_SIZE):
                src_y = TILE_SIZE - 1 - y if vflip else y
                for x in range(TILE_SIZE):
                    src_x = TILE_SIZE - 1 - x if hflip else x
                    color = block[src_y][src_x]
                    if bpp == 4:
                        value = bank * 16 + color
                    else:
                        value = color
                    if 0 <= value < 256:
                        pixels[tile_y * TILE_SIZE + y][tile_x * TILE_SIZE + x] = value
    return pixels, palette

def _parse_nscr(data: bytes) -> dict:
    if len(data) < 0x24 or data[:4] != b"RCSN":
        raise ProjectError("not an NSCR (RCSN) file")
    if data[0x10:0x14] != b"NRCS":
        raise ProjectError("NSCR is missing its SCRN block")
    block_size = _u32(data, 0x14)
    data_size = _u32(data, 0x20)
    start = 0x24
    if start + data_size > len(data):
        raise ProjectError("NSCR screen data runs past the file")
    entries = list(struct.unpack_from("<%dH" % (data_size // 2), data, start))
    return {
        "prefix_hex": _hex(data[:start]),
        "suffix_hex": _hex(data[start + data_size:]),
        "width": _u16(data, 0x18),
        "height": _u16(data, 0x1A),
        "color_mode": _u16(data, 0x1C),
        "screen_format": _u16(data, 0x1E),
        "data_size": data_size,
        "block_size": block_size,
        "entries": entries,
    }


def _rebuild_nscr(manifest: dict) -> bytes:
    info = manifest["nscr"]
    entries = [int(value) & 0xFFFF for value in info["entries"]]
    payload = b"".join(struct.pack("<H", value) for value in entries)
    prefix = bytearray(_unhex(info["prefix_hex"]))
    _p32(prefix, 0x08, 0)
    _p32(prefix, 0x14, 0x14 + len(payload))
    _p16(prefix, 0x18, int(info["width"]))
    _p16(prefix, 0x1A, int(info["height"]))
    _p16(prefix, 0x1C, int(info["color_mode"]))
    _p16(prefix, 0x1E, int(info["screen_format"]))
    _p32(prefix, 0x20, len(payload))
    suffix = _unhex(info["suffix_hex"])
    out = bytearray(prefix) + payload + suffix
    _p32(out, 0x08, len(out))
    return bytes(out)


def export_nscr(path: Path, outdir: Path, ncgr_path: Path | None = None,
                nclr_path: Path | None = None) -> int:
    raw = path.read_bytes()
    parsed = _parse_nscr(raw)
    outdir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "format": PROJECT_FORMAT,
        "version": PROJECT_VERSION,
        "nscr": parsed,
    }
    if ncgr_path is not None:
        pixels, palette = _render_nscr(
            ncgr_path.read_bytes(),
            nclr_path.read_bytes() if nclr_path is not None else None, raw)
        bmp.write_indexed(outdir / "screen.bmp", parsed["width"],
                          parsed["height"], pixels, palette)
        manifest["screen_image"] = "screen.bmp"
        manifest["tiles_source"] = ncgr_path.name
        if nclr_path is not None:
            manifest["palette_source"] = nclr_path.name
    (outdir / "nscr.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"exported {path.name} -> {outdir / 'nscr.json'}")
    return 0


def import_nscr(project_dir: Path, output: Path) -> int:
    manifest = json.loads((project_dir / "nscr.json").read_text(encoding="utf-8"))
    output.write_bytes(_rebuild_nscr(manifest))
    print(f"rebuilt {output}")
    return 0


def new_nclr(output: Path, palette_path: Path, format_value: int | None = None,
             extended: bool = False) -> int:
    rgb = _read_pal(palette_path)
    if format_value is None:
        format_value = 3 if len(rgb) <= 16 else 4
    if format_value not in (3, 4):
        raise ProjectError("palette format must be 3 (4bpp) or 4 (8bpp)")
    colors = [rgb8_to_rgb555(tuple(item)) for item in rgb]
    payload = b"".join(struct.pack("<H", value) for value in colors)
    header = bytearray(0x10)
    header[:4] = NCLR_MAGIC
    struct.pack_into("<H", header, 4, 0xFEFF)
    struct.pack_into("<H", header, 6, 0x0100)
    struct.pack_into("<I", header, 0x08, 0x10 + 0x18 + len(payload))
    struct.pack_into("<H", header, 0x0C, 0x10)
    struct.pack_into("<H", header, 0x0E, 1)
    pltt = bytearray(0x18)
    pltt[:4] = NCLR_PLTT
    struct.pack_into("<I", pltt, 4, 0x18 + len(payload))
    struct.pack_into("<I", pltt, 8, format_value)
    struct.pack_into("<I", pltt, 0x0C, 1 if extended else 0)
    struct.pack_into("<I", pltt, 0x10, len(payload))
    struct.pack_into("<I", pltt, 0x14, 0x10)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(bytes(header + pltt) + payload)
    print(f"created {output} ({len(colors)} colours)")
    return 0


def new_ncer(output: Path, cells: int, oam_per_cell: int = 0,
             bbox: bool = False, mapping_mode: int = 4) -> int:
    if cells < 0 or oam_per_cell < 0:
        raise ProjectError("cell and OAM counts must be non-negative")
    stride = 16 if bbox else 8
    attributes = 1 if bbox else 0
    cell_area = bytearray()
    oam_area = bytearray()
    for index in range(cells):
        cell_area += struct.pack("<HHI", oam_per_cell, 0x0800 if bbox else 0,
                                 index * oam_per_cell * 6)
        if bbox:
            cell_area += struct.pack("<hhhh", 0, 0, 0, 0)
        for _ in range(oam_per_cell):
            oam_area += struct.pack("<HHH", 0, 0, 0)
    payload = bytes(cell_area + oam_area)
    header = bytearray(0x10)
    header[:4] = b"RECN"
    struct.pack_into("<H", header, 4, 0xFEFF)
    struct.pack_into("<H", header, 6, 0x0100)
    struct.pack_into("<I", header, 0x08, 0x10 + 0x20 + len(payload))
    struct.pack_into("<H", header, 0x0C, 0x10)
    struct.pack_into("<H", header, 0x0E, 1)
    cebk = bytearray(0x20)
    cebk[:4] = b"KBEC"
    struct.pack_into("<I", cebk, 4, 0x20 + len(payload))
    struct.pack_into("<HH", cebk, 8, cells, attributes)
    struct.pack_into("<I", cebk, 0x0C, 0x18)
    struct.pack_into("<I", cebk, 0x10, mapping_mode)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(bytes(header + cebk) + payload)
    print(f"created {output} ({cells} cells, {oam_per_cell} OAM each)")
    return 0


def export_nclr(path: Path, outdir: Path) -> int:
    raw = path.read_bytes()
    parsed = _parse_nclr(raw)
    outdir.mkdir(parents=True, exist_ok=True)
    values = [value for bank in parsed["banks"] for value in bank]
    values = (values + [0] * 256)[:256]
    rgb = [rgb555_to_rgb8(value) for value in values]
    bmp.write_indexed(outdir / "palette.bmp", 16, 16,
                      [[row * 16 + column for column in range(16)]
                       for row in range(16)], rgb)
    manifest = {
        "format": PROJECT_FORMAT,
        "version": PROJECT_VERSION,
        "nclr": {
            "prefix_hex": parsed["prefix_hex"],
            "suffix_hex": parsed["suffix_hex"],
            "format": parsed["format"],
            "bank_size": parsed["bank_size"],
            "bank_files": [],
            "palette_image": "palette.bmp",
            "colors_rgb555": parsed["banks"],
            "data_size": parsed["data_size"],
            "payload_size": parsed["payload_size"],
        },
    }
    (outdir / "nclr.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"exported {path.name} -> {outdir / 'nclr.json'}")
    return 0


def import_nclr(project_dir: Path, output: Path) -> int:
    manifest = json.loads((project_dir / "nclr.json").read_text(encoding="utf-8"))
    output.write_bytes(_rebuild_nclr(manifest, project_dir))
    print(f"rebuilt {output}")
    return 0

def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    export = sub.add_parser("export")
    export.add_argument("ncgr")
    export.add_argument("--palette", default=None)
    export.add_argument("-o", "--output", required=True)

    imp = sub.add_parser("import")
    imp.add_argument("project")
    imp.add_argument("-o", "--output", required=True)
    imp.add_argument("--palette", default=None)

    sub_parser = sub.add_parser("export-ncer")
    sub_parser.add_argument("input")
    sub_parser.add_argument("-o", "--output", required=True)
    sub_parser.add_argument("--tiles", default=None)
    sub_parser.add_argument("--palette", default=None)
    sub_parser = sub.add_parser("export-nclr")
    sub_parser.add_argument("input")
    sub_parser.add_argument("-o", "--output", required=True)
    sub_parser = sub.add_parser("export-nscr")
    sub_parser.add_argument("input")
    sub_parser.add_argument("-o", "--output", required=True)
    sub_parser.add_argument("--tiles", default=None)
    sub_parser.add_argument("--palette", default=None)
    for command in ("import-ncer", "import-nscr", "import-nclr"):
        sub_parser = sub.add_parser(command)
        sub_parser.add_argument("project")
        sub_parser.add_argument("-o", "--output", required=True)

    new_pal = sub.add_parser("new-nclr")
    new_pal.add_argument("palette")
    new_pal.add_argument("-o", "--output", required=True)
    new_pal.add_argument("--format", type=int, choices=(3, 4), default=None)
    new_pal.add_argument("--extended", action="store_true")

    new_cell = sub.add_parser("new-ncer")
    new_cell.add_argument("-o", "--output", required=True)
    new_cell.add_argument("--cells", type=int, default=1)
    new_cell.add_argument("--oam-per-cell", type=int, default=0)
    new_cell.add_argument("--bbox", action="store_true")
    new_cell.add_argument("--mapping-mode", type=int, default=4)

    args = parser.parse_args(argv)
    try:
        if args.command == "export":
            return export_project(Path(args.ncgr),
                                  Path(args.palette) if args.palette else None,
                                  Path(args.output))
        if args.command == "export-ncer":
            return export_ncer(Path(args.input), Path(args.output),
                               Path(args.tiles) if args.tiles else None,
                               Path(args.palette) if args.palette else None)
        if args.command == "export-nscr":
            return export_nscr(Path(args.input), Path(args.output),
                               Path(args.tiles) if args.tiles else None,
                               Path(args.palette) if args.palette else None)
        if args.command == "export-nclr":
            return export_nclr(Path(args.input), Path(args.output))
        if args.command == "import-ncer":
            return import_ncer(Path(args.project), Path(args.output))
        if args.command == "import-nscr":
            return import_nscr(Path(args.project), Path(args.output))
        if args.command == "import-nclr":
            return import_nclr(Path(args.project), Path(args.output))
        if args.command == "new-nclr":
            return new_nclr(Path(args.output), Path(args.palette),
                            args.format, args.extended)
        if args.command == "new-ncer":
            return new_ncer(Path(args.output), args.cells, args.oam_per_cell,
                            args.bbox, args.mapping_mode)
        return import_project(Path(args.project), Path(args.output),
                              Path(args.palette) if args.palette else None)
    except (OSError, ProjectError) as exc:
        parser.error(str(exc))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
