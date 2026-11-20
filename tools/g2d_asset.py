# Mario Kart DS Modding Trove
# tools/g2d_asset.py — unified editable G2D asset projects
# SPDX-License-Identifier: MIT
"""One project folder per G2D asset (NCGR/NCLR/NCER/NSCR).

    python3 tools/g2d_asset.py export --ncgr a.ncgr --palette a.nclr \
        --ncer a.ncer --screen a.nscr -o out/a
    python3 tools/g2d_asset.py rebuild out/a -o rebuilt
    python3 tools/g2d_asset.py describe out/a

The project uses a single `asset.json` with only non-derivable fields, an
indexed `tilesheet.bmp`/`screen.bmp` with the palette embedded, and per-cell
images under `cells/`. Magic, BOM, version, sizes and offsets are generated.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import struct
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from tools import bmp, g2d_project as gp  # noqa: E402

PROJECT_FORMAT = "mkds-g2d-asset"
PROJECT_VERSION = 1


class AssetError(ValueError):
    pass


def _u16(data: bytes, off: int) -> int:
    return struct.unpack_from("<H", data, off)[0]


def _u32(data: bytes, off: int) -> int:
    return struct.unpack_from("<I", data, off)[0]


DEFAULT_BOM = 0xFEFF
DEFAULT_VERSION = 0x0100


def _u16(data: bytes, off: int) -> int:
    return struct.unpack_from("<H", data, off)[0]


def _u32(data: bytes, off: int) -> int:
    return struct.unpack_from("<I", data, off)[0]


def _quirks(data: bytes, magic: bytes, version: int, block_count: int) -> dict:
    """Only header values that differ from the generated defaults."""
    actual = {
        "magic": data[:4].decode("ascii", "replace"),
        "bom": _u16(data, 0x04),
        "version": _u16(data, 0x06),
        "file_size": _u32(data, 0x08),
        "header_size": _u16(data, 0x0C),
        "block_count": _u16(data, 0x0E),
    }
    defaults = {
        "magic": magic.decode("ascii"),
        "bom": DEFAULT_BOM,
        "version": version,
        "file_size": len(data),
        "header_size": 0x10,
        "block_count": block_count,
    }
    return {key: value for key, value in actual.items()
            if value != defaults[key]}


def _pack_header(quirks: dict | None, magic: bytes, version: int,
                 block_count: int, file_size: int) -> bytes:
    q = quirks or {}
    return (str(q.get("magic", magic.decode("ascii"))).encode("ascii") +
            struct.pack("<HHIHH",
                        int(q.get("bom", DEFAULT_BOM)),
                        int(q.get("version", version)),
                        int(q.get("file_size", file_size)),
                        int(q.get("header_size", 0x10)),
                        int(q.get("block_count", block_count))))


_SHAPES = ("square", "wide", "tall")


def _signed(value: int, bits: int) -> int:
    sign = 1 << (bits - 1)
    return value - (1 << bits) if value & sign else value


def _oam_named(raw: list[int]) -> dict:
    attr0, attr1, attr2 = raw
    shape = (attr0 >> 14) & 3
    size = (attr1 >> 14) & 3
    width, height = gp._OBJ_SIZES.get(shape, gp._OBJ_SIZES[0])[size]
    item = {"x": _signed(attr1 & 0x1FF, 9),
            "y": _signed(attr0 & 0xFF, 8),
            "tile": attr2 & 0x3FF}
    if shape:
        item["shape"] = _SHAPES[shape] if shape < 3 else "square"
    if size:
        item["size"] = size
    if attr2 & 0xF000:
        item["palette"] = (attr2 >> 12) & 0x0F
    if attr1 & 0x1000:
        item["hflip"] = True
    if attr1 & 0x2000:
        item["vflip"] = True
    if attr2 & 0x0C00:
        item["priority"] = (attr2 >> 10) & 0x03
    if attr1 & 0x0E00:
        item["affine_index"] = (attr1 >> 9) & 0x07
    if attr0 & 0x2000:
        item["color_depth"] = True
    if attr0 & 0x1000:
        item["mosaic"] = True
    if attr0 & 0x0C00:
        item["mode"] = (attr0 >> 10) & 0x03
    if attr0 & 0x0100:
        item["affine"] = True
    if attr0 & 0x0200:
        item["disable"] = True
    return item


def _oam_raw(oam: dict) -> list[int]:
    raw = list(oam.get("raw", [0, 0, 0]))
    attr0, attr1, attr2 = (raw + [0, 0, 0])[:3]
    shape = _SHAPES.index(oam.get("shape", "square")) if oam.get("shape") in _SHAPES else (attr0 >> 14) & 3
    size = int(oam.get("size", (attr1 >> 14) & 3)) & 3
    x = int(oam.get("x", _signed(attr1 & 0x1FF, 9))) & 0x1FF
    y = int(oam.get("y", _signed(attr0 & 0xFF, 8))) & 0xFF
    tile = int(oam.get("tile", attr2 & 0x3FF)) & 0x3FF
    palette = int(oam.get("palette", (attr2 >> 12) & 0x0F)) & 0x0F
    attr0 = (attr0 & ~(0xFF | (3 << 14))) | y | (shape << 14)
    attr0 &= ~((1 << 8) | (1 << 9) | (3 << 10) | (1 << 12) | (1 << 13))
    attr0 |= int(bool(oam.get("affine", False))) << 8
    attr0 |= int(bool(oam.get("disable", False))) << 9
    attr0 |= (int(oam.get("mode", 0)) & 0x03) << 10
    attr0 |= int(bool(oam.get("mosaic", False))) << 12
    attr0 |= int(bool(oam.get("color_depth", False))) << 13
    attr1 = (attr1 & ~(0x1FF | (0x07 << 9) | (1 << 12) | (1 << 13) | (3 << 14)))
    attr1 |= x | ((int(oam.get("affine_index", 0)) & 0x07) << 9)
    attr1 |= int(bool(oam.get("hflip", False))) << 12
    attr1 |= int(bool(oam.get("vflip", False))) << 13
    attr1 |= size << 14
    attr2 = (attr2 & ~(0x3FF | (0x03 << 10) | (0x0F << 12)))
    attr2 |= tile | ((int(oam.get("priority", 0)) & 0x03) << 10)
    attr2 |= palette << 12
    return [attr0 & 0xFFFF, attr1 & 0xFFFF, attr2 & 0xFFFF]


def _bbox_named(bbox: list[int]) -> dict:
    return {"max_x": bbox[0], "max_y": bbox[1],
            "min_x": bbox[2], "min_y": bbox[3]}


def _bbox_raw(bbox: dict | list[int] | None) -> list[int] | None:
    if bbox is None:
        return None
    if isinstance(bbox, list):
        return bbox
    return [int(bbox["max_x"]), int(bbox["max_y"]),
            int(bbox["min_x"]), int(bbox["min_y"])]


def _cell_attr_named(raw: int) -> dict:
    return {
        "radius": raw & 0x3F,
        "hflip": bool(raw & 0x100),
        "vflip": bool(raw & 0x200),
        "hvflip": bool(raw & 0x400),
        "bbox": bool(raw & 0x800),
        "reserved": (raw >> 12) & 0x0F,
        "reserved_6_7": (raw >> 6) & 0x03,
    }


def _cell_attr_raw(attr: dict | int) -> int:
    if isinstance(attr, int):
        return attr
    raw = 0
    raw |= int(attr.get("radius", 0)) & 0x3F
    raw |= (int(attr.get("reserved_6_7", 0)) & 0x03) << 6
    raw |= int(bool(attr.get("hflip", False))) << 8
    raw |= int(bool(attr.get("vflip", False))) << 9
    raw |= int(bool(attr.get("hvflip", False))) << 10
    raw |= int(bool(attr.get("bbox", False))) << 11
    raw |= (int(attr.get("reserved", 0)) & 0x0F) << 12
    return raw & 0xFFFF


def _cell_named(cell: dict) -> dict:
    raw = int(cell.get("attributes", 0))
    attributes = _cell_attr_named(raw)
    compact = {}
    for key, value in attributes.items():
        if value:
            compact[key] = value
    item = {
        "oam": [_oam_named(entry) for entry in cell.get("oam", [])],
    }
    if compact:
        item["attributes"] = compact
    if cell.get("bbox"):
        item["bbox"] = _bbox_named(cell["bbox"])
    return item


def _cell_raw(cell: dict) -> dict:
    oam = [_oam_raw(entry) if isinstance(entry, dict) else entry
           for entry in cell.get("oam", [])]
    return {
        "oam_count": len(oam),
        "attributes": _cell_attr_raw(cell.get("attributes", 0)),
        "oam": oam,
        "bbox": _bbox_raw(cell.get("bbox")),
    }


def _entry_named(raw: int) -> dict:
    return {
        "tile": raw & 0x3FF,
        "hflip": bool(raw & 0x0400),
        "vflip": bool(raw & 0x0800),
        "palette": (raw >> 12) & 0x0F,
    }


def _entry_raw(entry: dict | int) -> int:
    if isinstance(entry, int):
        return entry
    raw = int(entry.get("raw", 0))
    raw &= ~0xFFF
    raw |= int(entry.get("tile", 0)) & 0x3FF
    raw |= int(bool(entry.get("hflip", False))) << 10
    raw |= int(bool(entry.get("vflip", False))) << 11
    raw |= (int(entry.get("palette", 0)) & 0x0F) << 12
    return raw & 0xFFFF



def _ncgr_named(raw: bytes) -> dict:
    parsed = gp._parse_ncgr(raw)
    data_start = 0x18 + parsed["data_offset"]
    data_end = data_start + parsed["data_size"]
    suffix = raw[data_end:]
    cpos = None
    tail = suffix
    if suffix[:4] == b"SOPC":
        cpos = {
            "x": _u16(suffix, 8),
            "y": _u16(suffix, 10),
            "width": _u16(suffix, 12),
            "height": _u16(suffix, 14),
        }
        tail = suffix[_u32(suffix, 4):]
    width = _u16(raw, 0x18)
    height = _u16(raw, 0x1A)
    mapping_type = _u32(raw, 0x20)
    character_format = _u32(raw, 0x24)
    info = {
        "bpp": parsed["bpp"],
        "tile_count": parsed["tile_count"],
        "per_row": parsed["tiles_per_row"],
    }
    if width != 0xFFFF:
        info["width"] = width
    if height != 0xFFFF:
        info["height"] = height
    if mapping_type != 0:
        info["mapping_type"] = mapping_type
    if character_format != 0:
        info["character_format"] = character_format
    if cpos is not None:
        info["cpos"] = cpos
    if parsed["trailing_hex"]:
        info["trailing_hex"] = parsed["trailing_hex"]
    if tail:
        info["tail_hex"] = tail.hex()
    quirks = _quirks(raw, b"RGCN", 0x0101 if cpos else 0x0100,
                     2 if cpos else 1)
    if quirks:
        info["quirks"] = quirks
    return info


def _nclr_named(raw: bytes) -> dict:
    parsed = gp._parse_nclr(raw)
    block_size = _u32(raw, 0x14)
    payload_size = block_size - 0x18
    suffix = raw[0x10 + block_size:]
    pcmp = None
    tail = suffix
    if suffix[:4] == b"PMCP":
        count = _u16(suffix, 8)
        index_offset = _u32(suffix, 0x0C)
        pcmp = {
            "count": count,
            "indices": [_u16(suffix, 8 + index_offset + 2 * i)
                        for i in range(count)],
        }
        reserved = _u16(suffix, 0x0A)
        if reserved != 0xBEEF:
            pcmp["reserved"] = reserved
        if index_offset != 8:
            pcmp["index_offset"] = index_offset
        tail = suffix[_u32(suffix, 4):]
    info = {
        "bank_size": parsed["bank_size"],
        "bank_count": len(parsed["banks"]),
    }
    colors = sum(len(bank) for bank in parsed["banks"])
    if colors != parsed["bank_size"] * len(parsed["banks"]):
        info["color_count"] = colors
    if _u32(raw, 0x1C):
        info["extended"] = _u32(raw, 0x1C)
    declared = _u32(raw, 0x20)
    if declared != payload_size:
        info["declared_data_size"] = declared
    if pcmp is not None:
        info["pcmp"] = pcmp
    if tail:
        info["tail_hex"] = tail.hex()
    quirks = _quirks(raw, b"RLCN", 0x0100, 2 if pcmp else 1)
    if quirks:
        info["quirks"] = quirks
    return info


def _ncer_named(raw: bytes) -> dict:
    parsed = gp._parse_ncer(raw)
    attr = _u16(raw, 0x1A)
    info = {
        "mapping_mode": parsed["mapping_mode"],
        "bbox": bool(attr & 1),
    }
    if attr >> 1:
        info["attributes_reserved"] = attr >> 1
    for key, off in (("vram_transfer_offset", 0x24),
                     ("string_bank", 0x28),
                     ("extended_data", 0x2C)):
        value = _u32(raw, off)
        if value:
            info[key] = value
    tail = raw[0x10 + _u32(raw, 0x14):]
    if tail:
        info["tail_hex"] = tail.hex()
    quirks = _quirks(raw, b"RECN", 0x0100, 1)
    if quirks:
        info["quirks"] = quirks
    return info


def _nscr_named(raw: bytes) -> dict:
    parsed = gp._parse_nscr(raw)
    info = {
        "width": parsed["width"],
        "height": parsed["height"],
        "color_mode": parsed["color_mode"],
        "screen_format": parsed["screen_format"],
        "entries": [_entry_named(entry) for entry in parsed["entries"]],
    }
    tail = raw[0x24 + parsed["data_size"]:]
    if tail:
        info["tail_hex"] = tail.hex()
    quirks = _quirks(raw, b"RCSN", 0x0100, 1)
    if quirks:
        info["quirks"] = quirks
    return info


def _palette256(nclr_raw: bytes | None, bpp: int) -> tuple[list[int], list[tuple[int, int, int]]]:
    banks = gp._parse_nclr(nclr_raw)["banks"] if nclr_raw is not None else []
    if bpp == 4:
        values = []
        for bank in range(16):
            entries = banks[bank] if bank < len(banks) else []
            values.extend(entries[:16])
            values.extend([0] * (16 - min(16, len(entries))))
    else:
        values = list(banks[0][:256]) if banks else []
        values.extend([0] * (256 - len(values)))
    return values, [gp.rgb555_to_rgb8(value) for value in values]


def _cell_indices(ncer_raw: bytes, ncgr_raw: bytes,
                  nclr_raw: bytes | None) -> tuple[list[dict], list[tuple[int, int, int]]]:
    ncgr = gp._parse_ncgr(ncgr_raw)
    ncer = gp._parse_ncer(ncer_raw)
    bpp = ncgr["bpp"]
    tile_bytes = gp.TILE_BYTES_4BPP if bpp == 4 else gp.TILE_BYTES_8BPP
    start = 0x18 + ncgr["data_offset"]
    raw_tiles = [gp._unpack_tile(
        ncgr_raw[start + i * tile_bytes:start + (i + 1) * tile_bytes], bpp)
        for i in range(ncgr["tile_count"])]
    values, palette = _palette256(nclr_raw, bpp)

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
                wide = gp._OBJ_SIZES.get(shape, gp._OBJ_SIZES[0])[size]
                x = gp._signed(attr1 & 0x1FF, 9)
                y = gp._signed(attr0 & 0xFF, 8)
                min_x = min(min_x, x)
                min_y = min(min_y, y)
                max_x = max(max_x, x + wide[0])
                max_y = max(max_y, y + wide[1])
        width = max(1, max_x - min_x)
        height = max(1, max_y - min_y)
        canvas = [[0] * width for _ in range(height)]
        for oam in cell.get("oam", []):
            attr0, attr1, attr2 = oam
            shape = (attr0 >> 14) & 3
            size = (attr1 >> 14) & 3
            obj_w, obj_h = gp._OBJ_SIZES.get(shape, gp._OBJ_SIZES[0])[size]
            x = gp._signed(attr1 & 0x1FF, 9) - min_x
            y = gp._signed(attr0 & 0xFF, 8) - min_y
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
                            dx = x + tx * 8 + px
                            dy = y + ty * 8 + py
                            if 0 <= dx < width and 0 <= dy < height:
                                canvas[dy][dx] = bank * 16 + color if bpp == 4 else color
        cells.append({
            "image": f"cells/cell_{len(cells):03d}.bmp",
            "width": width,
            "height": height,
            "attributes": cell.get("attributes", 0),
            "bbox": cell.get("bbox"),
            "oam": cell.get("oam", []),
            "canvas": canvas,
        })
    return cells, palette


def _write_cells(project: Path, ncer_raw: bytes, ncgr_raw: bytes,
                 nclr_raw: bytes | None) -> None:
    cells, palette = _cell_indices(ncer_raw, ncgr_raw, nclr_raw)
    cell_dir = project / "cells"
    cell_dir.mkdir(exist_ok=True)
    config_cells = []
    for index, cell in enumerate(cells):
        path = cell_dir / f"cell_{index:03d}.bmp"
        bmp.write_indexed(path, cell["width"], cell["height"],
                          cell["canvas"], palette)
        config_cells.append({
            "image": cell["image"],
            "width": cell["width"],
            "height": cell["height"],
            **_cell_named(cell),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        })
    parsed = gp._parse_ncer(ncer_raw)
    config = {
        "mapping_mode": int(parsed["mapping_mode"]),
        "bbox": bool(int(parsed["attributes"]) & 1),
        "cells": config_cells,
    }
    if int(parsed["attributes"]) >> 1:
        config["attributes_reserved"] = int(parsed["attributes"]) >> 1
    (project / "cells.json").write_text(
        json.dumps(config, indent=2) + "\n", encoding="utf-8")


def _materialize_tilesheet(project: Path, asset: dict) -> Path:
    existing = project / "tilesheet.bmp"
    if existing.exists():
        return existing
    source_names = {key: Path(value).name
                    for key, value in asset.get("sources", {}).items()}
    ncgr_name = source_names.get("ncgr")
    if not ncgr_name:
        raise AssetError("no tilesheet and no source NCGR to rebuild from")
    ncgr_path = project / "source" / ncgr_name
    if not ncgr_path.exists():
        raise AssetError(f"missing source NCGR {ncgr_name}")
    parsed = gp._parse_ncgr(ncgr_path.read_bytes())
    bpp = parsed["bpp"]
    tile_bytes = gp.TILE_BYTES_4BPP if bpp == 4 else gp.TILE_BYTES_8BPP
    start = 0x18 + parsed["data_offset"]
    raw = ncgr_path.read_bytes()
    nclr_name = source_names.get("nclr")
    nclr_path = project / "source" / nclr_name if nclr_name else None
    values = gp._palette_all(nclr_path, bpp)
    palette = [gp.rgb555_to_rgb8(value) for value in values]
    per_row = int(asset["ncgr"]["per_row"])
    count = int(asset["ncgr"]["tile_count"])
    width = per_row * gp.TILE_SIZE
    height = max(1, (count + per_row - 1) // per_row) * gp.TILE_SIZE
    canvas = [[0] * width for _ in range(height)]
    for index in range(count):
        block = gp._unpack_tile(
            raw[start + index * tile_bytes:start + (index + 1) * tile_bytes], bpp)
        tx = (index % per_row) * gp.TILE_SIZE
        ty = (index // per_row) * gp.TILE_SIZE
        for y in range(gp.TILE_SIZE):
            canvas[ty + y][tx:tx + gp.TILE_SIZE] = block[y]
    cache = project / ".cache"
    cache.mkdir(exist_ok=True)
    path = cache / "tilesheet.bmp"
    bmp.write_indexed(path, width, height, canvas, palette)
    return path



def _apply_cells(project: Path, asset: dict) -> None:
    config_path = project / "cells.json"
    if not config_path.exists() or not asset.get("ncgr") or not asset.get("ncer"):
        return
    config = json.loads(config_path.read_text(encoding="utf-8"))
    info = asset["ncgr"]
    bpp = int(info["bpp"])
    tile_count = int(info["tile_count"])
    per_row = int(info["per_row"])
    tilesheet = _materialize_tilesheet(project, asset)
    image = bmp.load_indexed(tilesheet)
    tiles = []
    for index in range(tile_count):
        tx = (index % per_row) * gp.TILE_SIZE
        ty = (index // per_row) * gp.TILE_SIZE
        block = [row[tx:tx + gp.TILE_SIZE]
                 for row in image.pixels[ty:ty + gp.TILE_SIZE]]
        tiles.append([row[:] for row in block])

    changed = False
    for cell in config["cells"]:
        path = project / cell["image"]
        if not path.exists():
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if cell.get("sha256") == digest and not cell.get("new"):
            continue
        changed = True
        cell_image = bmp.load_indexed(path)
        pixels = cell_image.pixels
        bbox = cell.get("bbox") or {"min_x": 0, "min_y": 0}
        min_x = int(bbox["min_x"]) if isinstance(bbox, dict) else bbox[2]
        min_y = int(bbox["min_y"]) if isinstance(bbox, dict) else bbox[3]
        for oam in cell.get("oam", []):
            if isinstance(oam, dict):
                shape_name = oam.get("shape", "square")
                shape = _SHAPES.index(shape_name) if shape_name in _SHAPES else 0
                size = int(oam.get("size", 0)) & 3
                obj_w, obj_h = gp._OBJ_SIZES.get(shape, gp._OBJ_SIZES[0])[size]
                hflip = bool(oam.get("hflip", False))
                vflip = bool(oam.get("vflip", False))
                tile = oam.get("tile")
                step = 1 if bpp == 4 else 2
                needed = max(1, (obj_w // 8) * (obj_h // 8) * step)
                if cell.get("new") or tile is None or int(tile) + needed > len(tiles):
                    tile = len(tiles)
                    oam["tile"] = tile
                    tiles.extend([[[0] * 8 for _ in range(8)]
                                  for _ in range(needed)])
                tile = int(tile)
                ox = int(oam.get("x", 0))
                oy = int(oam.get("y", 0))
            else:
                attr0, attr1, attr2 = oam
                shape = (attr0 >> 14) & 3
                size = (attr1 >> 14) & 3
                obj_w, obj_h = gp._OBJ_SIZES.get(shape, gp._OBJ_SIZES[0])[size]
                hflip = bool(attr1 & 0x1000)
                vflip = bool(attr1 & 0x2000)
                tile = attr2 & 0x3FF
                ox = gp._signed(attr1 & 0x1FF, 9)
                oy = gp._signed(attr0 & 0xFF, 8)
            step = 1 if bpp == 4 else 2
            tiles_x = max(1, obj_w // 8)
            for sy in range(obj_h):
                for sx in range(obj_w):
                    out_x = obj_w - 1 - sx if hflip else sx
                    out_y = obj_h - 1 - sy if vflip else sy
                    px = ox - min_x + out_x
                    py = oy - min_y + out_y
                    if py < 0 or px < 0 or py >= len(pixels) or px >= len(pixels[py]):
                        continue
                    value = pixels[py][px]
                    color = value & 0x0F if bpp == 4 else value & 0xFF
                    index = tile + ((sy // 8) * tiles_x + (sx // 8)) * step
                    if index >= len(tiles):
                        continue
                    tiles[index][sy % 8][sx % 8] = color

    asset["ncgr"]["tile_count"] = len(tiles)
    rows = per_row
    width = rows * gp.TILE_SIZE
    height = max(1, (len(tiles) + rows - 1) // rows) * gp.TILE_SIZE
    canvas = [[0] * width for _ in range(height)]
    for index, block in enumerate(tiles):
        tx = (index % rows) * gp.TILE_SIZE
        ty = (index // rows) * gp.TILE_SIZE
        for y in range(gp.TILE_SIZE):
            canvas[ty + y][tx:tx + gp.TILE_SIZE] = block[y]
    bmp.write_indexed(tilesheet, width, height, canvas, image.palette)
    if changed:
        for cell in config["cells"]:
            cell.pop("new", None)
            path = project / cell["image"]
            if path.exists():
                cell["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
        config_path.write_text(json.dumps(config, indent=2) + "\n",
                               encoding="utf-8")
    return changed



def export_asset(outdir: Path, ncgr: Path | None = None,
                 nclr: Path | None = None, ncer: Path | None = None,
                 nscr: Path | None = None,
                 sources: dict[str, str] | None = None) -> int:
    outdir.mkdir(parents=True, exist_ok=True)
    source = {
        "ncgr": ncgr.name if ncgr else None,
        "nclr": nclr.name if nclr else None,
        "ncer": ncer.name if ncer else None,
        "nscr": nscr.name if nscr else None,
    }
    asset: dict = {
        "sources": sources or {key: value for key, value in source.items()
                               if value},
    }

    if ncgr is not None:
        gp.export_project(ncgr, nclr, outdir)
        # Rename the old intermediate names to the unified project names.
        if (outdir / "tiles.bmp").exists():
            (outdir / "tiles.bmp").replace(outdir / "tilesheet.bmp")
        if (outdir / "tiles_preview.bmp").exists():
            (outdir / "tiles_preview.bmp").unlink()
        if (outdir / "project.json").exists():
            (outdir / "project.json").unlink()
        asset["ncgr"] = _ncgr_named(ncgr.read_bytes())
        if nclr is not None:
            asset["nclr"] = _nclr_named(nclr.read_bytes())

    if nclr is not None and ncgr is None:
        gp.export_nclr(nclr, outdir)
        if (outdir / "nclr.json").exists():
            (outdir / "nclr.json").unlink()
        asset["nclr"] = _nclr_named(nclr.read_bytes())

    if ncer is not None:
        gp.export_ncer(ncer, outdir, ncgr, nclr)
        if (outdir / "cells_preview.bmp").exists():
            (outdir / "cells_preview.bmp").replace(
                outdir / "sprite_sheet.bmp")
        if (outdir / "ncer.json").exists():
            (outdir / "ncer.json").unlink()
        asset["ncer"] = _ncer_named(ncer.read_bytes())
        if ncgr is not None:
            _write_cells(outdir, ncer.read_bytes(), ncgr.read_bytes(),
                         nclr.read_bytes() if nclr is not None else None)

    if nscr is not None:
        gp.export_nscr(nscr, outdir, ncgr, nclr)
        if (outdir / "screen_preview.bmp").exists():
            (outdir / "screen_preview.bmp").unlink()
        if (outdir / "nscr.json").exists():
            (outdir / "nscr.json").unlink()
        asset["nscr"] = _nscr_named(nscr.read_bytes())

    source_dir = outdir / "source"
    source_dir.mkdir(exist_ok=True)
    for path in (ncgr, nclr, ncer, nscr):
        if path is not None:
            shutil.copy2(path, source_dir / path.name)
    if ncgr is not None and (ncer is not None or nscr is not None):
        if (outdir / "tilesheet.bmp").exists():
            (outdir / "tilesheet.bmp").unlink()
    if ncer is not None and (outdir / "cells" / "cell_000.bmp").exists():
        asset["palette_image"] = "cells/cell_000.bmp"
    elif nscr is not None:
        asset["palette_image"] = "screen.bmp"
    elif ncgr is not None:
        asset["palette_image"] = "tilesheet.bmp"
    else:
        asset["palette_image"] = "palette.bmp"
    if nscr is not None and (outdir / "screen.bmp").exists():
        asset["screen_sha256"] = hashlib.sha256(
            (outdir / "screen.bmp").read_bytes()).hexdigest()

    (outdir / "asset.json").write_text(
        json.dumps(asset, indent=2) + "\n", encoding="utf-8")
    print(f"exported {outdir}")
    return 0


def _old_ncgr_manifest(asset: dict, image: str = "tilesheet.bmp") -> dict:
    info = asset["ncgr"]
    bpp = int(info["bpp"])
    tile_bytes = gp.TILE_BYTES_4BPP if bpp == 4 else gp.TILE_BYTES_8BPP
    trailing = bytes.fromhex(info.get("trailing_hex", ""))
    data_size = int(info["tile_count"]) * tile_bytes + len(trailing)
    width = int(info.get("width", 0xFFFF))
    height = int(info.get("height", 0xFFFF))
    mapping = int(info.get("mapping_type", 0))
    character_format = int(info.get("character_format", 0))
    color_format = 3 if bpp == 4 else 4
    cpos = info.get("cpos")
    version = 0x0101 if cpos else 0x0100
    header = _pack_header(info.get("quirks"), b"RGCN", version,
                          2 if cpos else 1, 0)
    char_bytes = (b"RAHC" + struct.pack(
        "<IHHIIIII", 0x20 + data_size, width, height, color_format,
        mapping, character_format, data_size, 0x18))
    suffix = b""
    if cpos:
        suffix += (b"SOPC" + struct.pack(
            "<IHHHH", 0x10, int(cpos["x"]), int(cpos["y"]),
            int(cpos["width"]), int(cpos["height"])))
    suffix += bytes.fromhex(info.get("tail_hex", ""))
    return {
        "image": image,
        "ncgr": {
            "prefix_hex": (header + char_bytes).hex(),
            "suffix_hex": suffix.hex(),
            "bpp": bpp,
            "tile_count": int(info["tile_count"]),
            "trailing_hex": info.get("trailing_hex", ""),
            "tiles_per_row": int(info["per_row"]),
        },
    }


def _old_nclr_manifest(asset: dict) -> dict:
    info = asset["nclr"]
    payload_size = int(info.get("color_count",
                                int(info["bank_size"]) * int(info["bank_count"]))) * 2
    bank_size = int(info["bank_size"])
    palette_format = 3 if bank_size == 16 else 4
    declared = int(info.get("declared_data_size", payload_size))
    extended = int(info.get("extended", 0))
    pcmp = info.get("pcmp")
    header = _pack_header(info.get("quirks"), b"RLCN", 0x0100,
                          2 if pcmp else 1, 0)
    pltt_bytes = (b"TTLP" + struct.pack(
        "<IIIII", 0x18 + payload_size, palette_format, extended,
        declared, 0x10))
    suffix = b""
    if pcmp:
        count = int(pcmp["count"])
        index_offset = int(pcmp.get("index_offset", 8))
        size = 8 + index_offset + 2 * count
        block = bytearray(size)
        block[:4] = b"PMCP"
        struct.pack_into("<I", block, 4, size)
        struct.pack_into("<H", block, 8, count)
        struct.pack_into("<H", block, 0x0A, int(pcmp.get("reserved", 0xBEEF)))
        struct.pack_into("<I", block, 0x0C, index_offset)
        for index, value in enumerate(pcmp["indices"]):
            struct.pack_into("<H", block, 8 + index_offset + 2 * index,
                             int(value))
        suffix += bytes(block)
    suffix += bytes.fromhex(info.get("tail_hex", ""))
    return {
        "nclr": {
            "prefix_hex": (header + pltt_bytes).hex(),
            "suffix_hex": suffix.hex(),
            "format": palette_format,
            "bank_size": bank_size,
            "bank_files": [],
            "palette_image": asset.get("palette_image", "tilesheet.bmp"),
            "colors_rgb555": [],
            "data_size": declared,
            "payload_size": payload_size,
        },
    }


def _old_ncer_manifest(asset: dict) -> dict:
    info = asset["ncer"]
    attr = (int(info.get("attributes_reserved", 0)) << 1) | int(bool(info["bbox"]))
    header = _pack_header(info.get("quirks"), b"RECN", 0x0100, 1, 0)
    cebk_bytes = (b"KBEC" + struct.pack(
        "<IHHIIIII", 0, len(info["cells"]), attr, 0x18,
        int(info["mapping_mode"]), int(info.get("vram_transfer_offset", 0)),
        int(info.get("string_bank", 0)), int(info.get("extended_data", 0))))
    return {
        "ncer": {
            "prefix_hex": (header + cebk_bytes).hex(),
            "suffix_hex": info.get("tail_hex", ""),
            "cells": [_cell_raw(cell) for cell in info.get("cells", [])],
            "block_size": int(info.get("block_size", 0)),
            "file_size": int(info.get("quirks", {}).get("file_size", 0)),
            "cell_offset": 0x18,
            "attributes": attr,
            "mapping_mode": int(info["mapping_mode"]),
        },
    }


def _old_nscr_manifest(asset: dict) -> dict:
    info = asset["nscr"]
    entries = [_entry_raw(entry) for entry in info["entries"]]
    payload_size = 2 * len(entries)
    header = _pack_header(info.get("quirks"), b"RCSN", 0x0100, 1, 0)
    scrn_bytes = (b"NRCS" + struct.pack(
        "<IHHHHI", 0x14 + payload_size, int(info["width"]),
        int(info["height"]), int(info["color_mode"]),
        int(info["screen_format"]), payload_size))
    return {
        "nscr": {
            "prefix_hex": (header + scrn_bytes).hex(),
            "suffix_hex": info.get("tail_hex", ""),
            "width": int(info["width"]),
            "height": int(info["height"]),
            "color_mode": int(info["color_mode"]),
            "screen_format": int(info["screen_format"]),
            "data_size": payload_size,
            "block_size": 0x14 + payload_size,
            "entries": entries,
        },
    }


def _apply_screen(project: Path, asset: dict) -> Path:
    source_names = {key: Path(value).name
                    for key, value in asset.get("sources", {}).items()}
    ncgr_path = project / "source" / source_names["ncgr"]
    parsed = gp._parse_ncgr(ncgr_path.read_bytes())
    raw = ncgr_path.read_bytes()
    bpp = parsed["bpp"]
    tile_bytes = gp.TILE_BYTES_4BPP if bpp == 4 else gp.TILE_BYTES_8BPP
    start = 0x18 + parsed["data_offset"]
    tiles = [gp._unpack_tile(
        raw[start + i * tile_bytes:start + (i + 1) * tile_bytes], bpp)
        for i in range(parsed["tile_count"])]
    screen = bmp.load_indexed(project / "screen.bmp")
    info = asset["nscr"]
    entries = info["entries"]
    width = int(info["width"])
    height = int(info["height"])
    tiles_x = max(1, width // gp.TILE_SIZE)

    # Render the original screen from the source tiles, then write only the
    # pixels that actually changed. Shared tiles are not overwritten by
    # unchanged occurrences later in the tilemap.
    original = [[0] * width for _ in range(height)]
    for index, entry in enumerate(entries):
        tile = int(entry.get("tile", 0))
        if tile >= len(tiles):
            continue
        bank = int(entry.get("palette", 0)) if bpp == 4 else 0
        hflip = bool(entry.get("hflip", False))
        vflip = bool(entry.get("vflip", False))
        tx = (index % tiles_x) * gp.TILE_SIZE
        ty = (index // tiles_x) * gp.TILE_SIZE
        for sy in range(gp.TILE_SIZE):
            for sx in range(gp.TILE_SIZE):
                out_x = gp.TILE_SIZE - 1 - sx if hflip else sx
                out_y = gp.TILE_SIZE - 1 - sy if vflip else sy
                px, py = tx + out_x, ty + out_y
                if py < height and px < width:
                    color = tiles[tile][sy][sx]
                    original[py][px] = bank * 16 + color if bpp == 4 else color

    for index, entry in enumerate(entries):
        tile = int(entry.get("tile", 0))
        if tile >= len(tiles):
            continue
        bank = int(entry.get("palette", 0)) if bpp == 4 else 0
        hflip = bool(entry.get("hflip", False))
        vflip = bool(entry.get("vflip", False))
        tx = (index % tiles_x) * gp.TILE_SIZE
        ty = (index // tiles_x) * gp.TILE_SIZE
        for sy in range(gp.TILE_SIZE):
            for sx in range(gp.TILE_SIZE):
                out_x = gp.TILE_SIZE - 1 - sx if hflip else sx
                out_y = gp.TILE_SIZE - 1 - sy if vflip else sy
                px, py = tx + out_x, ty + out_y
                if py >= height or px >= width:
                    continue
                value = screen.pixels[py][px]
                if value == original[py][px]:
                    continue
                tiles[tile][sy][sx] = value & 0x0F if bpp == 4 else value & 0xFF

    per_row = int(asset["ncgr"]["per_row"])
    canvas_width = per_row * gp.TILE_SIZE
    canvas_height = max(1, (len(tiles) + per_row - 1) // per_row) * gp.TILE_SIZE
    canvas = [[0] * canvas_width for _ in range(canvas_height)]
    for index, block in enumerate(tiles):
        tx = (index % per_row) * gp.TILE_SIZE
        ty = (index // per_row) * gp.TILE_SIZE
        for y in range(gp.TILE_SIZE):
            canvas[ty + y][tx:tx + gp.TILE_SIZE] = block[y]
    cache = project / ".cache"
    cache.mkdir(exist_ok=True)
    path = cache / "tilesheet.bmp"
    bmp.write_indexed(path, canvas_width, canvas_height, canvas, screen.palette)
    return path


def rebuild_asset(project: Path, outdir: Path) -> list[Path]:
    asset = json.loads((project / "asset.json").read_text(encoding="utf-8"))
    outdir.mkdir(parents=True, exist_ok=True)
    written = []
    source = {key: Path(value).name
              for key, value in asset.get("sources", {}).items()}
    source_dir = project / "source"

    def apply_size_quirk(data: bytes, info: dict) -> bytes:
        quirk = info.get("quirks", {}).get("file_size")
        if quirk is None:
            return data
        out = bytearray(data)
        struct.pack_into("<I", out, 0x08, int(quirk))
        return bytes(out)

    # Composed assets keep the original atomic files for the exact baseline.
    # If the composed image was not edited, copying them is the rebuild.
    if asset.get("ncer") or asset.get("nscr"):
        for kind, name in source.items():
            if not name:
                continue
            src = source_dir / name
            if src.exists():
                shutil.copy2(src, outdir / name)
                written.append(outdir / name)

        cells_changed = False
        config_path = project / "cells.json"
        config = None
        if asset.get("ncer") and config_path.exists():
            config = json.loads(config_path.read_text(encoding="utf-8"))
            for cell in config.get("cells", []):
                path = project / cell["image"]
                if path.exists() and cell.get("new"):
                    cells_changed = True
                    break
                if path.exists():
                    digest = hashlib.sha256(path.read_bytes()).hexdigest()
                    if cell.get("sha256") != digest:
                        cells_changed = True
                        break

        screen_changed = False
        if asset.get("nscr") and asset.get("screen_sha256"):
            screen = project / "screen.bmp"
            if screen.exists():
                digest = hashlib.sha256(screen.read_bytes()).hexdigest()
                screen_changed = digest != asset["screen_sha256"]

        if cells_changed and asset.get("ncgr") and config is not None:
            asset["ncer"]["cells"] = config["cells"]
            asset["ncer"]["mapping_mode"] = config["mapping_mode"]
            asset["ncer"]["bbox"] = bool(config.get("bbox", False))
            if config.get("attributes_reserved"):
                asset["ncer"]["attributes_reserved"] = int(
                    config["attributes_reserved"])
            tilesheet = _materialize_tilesheet(project, asset).resolve()
            _apply_cells(project, asset)
            if config_path.exists():
                config = json.loads(config_path.read_text(encoding="utf-8"))
                asset["ncer"]["cells"] = config["cells"]
            name = source.get("ncgr") or "asset.ncgr"
            data = gp._rebuild_ncgr(_old_ncgr_manifest(asset, str(tilesheet)),
                                    project)
            (outdir / name).write_bytes(
                apply_size_quirk(data, asset["ncgr"]))
            written.append(outdir / name)
            if asset.get("nclr"):
                nclr_name = source.get("nclr") or "asset.nclr"
                data = gp._rebuild_nclr(_old_nclr_manifest(asset), project)
                (outdir / nclr_name).write_bytes(
                    apply_size_quirk(data, asset["nclr"]))
                written.append(outdir / nclr_name)
            ncer_name = source.get("ncer") or "asset.ncer"
            data = gp._rebuild_ncer(_old_ncer_manifest(asset))
            (outdir / ncer_name).write_bytes(
                apply_size_quirk(data, asset["ncer"]))
            written.append(outdir / ncer_name)
            cache = project / ".cache"
            if cache.exists():
                shutil.rmtree(cache)
        if screen_changed and asset.get("ncgr"):
            tilesheet = _apply_screen(project, asset).resolve()
            ncgr_name = source.get("ncgr") or "asset.ncgr"
            data = gp._rebuild_ncgr(_old_ncgr_manifest(asset, str(tilesheet)),
                                    project)
            (outdir / ncgr_name).write_bytes(
                apply_size_quirk(data, asset["ncgr"]))
            written.append(outdir / ncgr_name)
            if asset.get("nclr"):
                nclr_name = source.get("nclr") or "asset.nclr"
                asset["palette_image"] = "screen.bmp"
                data = gp._rebuild_nclr(_old_nclr_manifest(asset), project)
                (outdir / nclr_name).write_bytes(
                    apply_size_quirk(data, asset["nclr"]))
                written.append(outdir / nclr_name)
            if asset.get("nscr"):
                nscr_name = source.get("nscr") or "asset.nscr"
                data = gp._rebuild_nscr(_old_nscr_manifest(asset))
                (outdir / nscr_name).write_bytes(
                    apply_size_quirk(data, asset["nscr"]))
                written.append(outdir / nscr_name)
            cache = project / ".cache"
            if cache.exists():
                shutil.rmtree(cache)
        elif screen_changed:
            print("warning: edited screen.bmp is a preview; "
                  "the original NSCR was copied", file=sys.stderr)
        return written

    if asset.get("ncgr"):
        _apply_cells(project, asset)
        name = source.get("ncgr") or "asset.ncgr"
        data = gp._rebuild_ncgr(_old_ncgr_manifest(asset), project)
        (outdir / name).write_bytes(apply_size_quirk(data, asset["ncgr"]))
        written.append(outdir / name)
    if asset.get("nclr"):
        name = source.get("nclr") or "asset.nclr"
        data = gp._rebuild_nclr(_old_nclr_manifest(asset), project)
        (outdir / name).write_bytes(apply_size_quirk(data, asset["nclr"]))
        written.append(outdir / name)
    if asset.get("ncer"):
        name = source.get("ncer") or "asset.ncer"
        data = gp._rebuild_ncer(_old_ncer_manifest(asset))
        (outdir / name).write_bytes(apply_size_quirk(data, asset["ncer"]))
        written.append(outdir / name)
    if asset.get("nscr"):
        name = source.get("nscr") or "asset.nscr"
        data = gp._rebuild_nscr(_old_nscr_manifest(asset))
        (outdir / name).write_bytes(apply_size_quirk(data, asset["nscr"]))
        written.append(outdir / name)
    return written


def describe_asset(project: Path) -> str:
    asset = json.loads((project / "asset.json").read_text(encoding="utf-8"))
    lines = [f"project: {project}", "source:"]
    for kind, name in asset.get("sources", {}).items():
        if name:
            lines.append(f"  {kind}: {name}")
    if asset.get("ncgr"):
        info = asset["ncgr"]
        tile_bytes = gp.TILE_BYTES_4BPP if info["bpp"] == 4 else gp.TILE_BYTES_8BPP
        data_bytes = info["tile_count"] * tile_bytes + len(
            bytes.fromhex(info.get("trailing_hex", "")))
        lines.append(
            f"NCGR: {info['bpp']}bpp, {info['tile_count']} tiles, "
            f"{info['per_row']} per row, mapping {info.get('mapping_type', 0)}, "
            f"{data_bytes} data bytes")
    if asset.get("nclr"):
        info = asset["nclr"]
        lines.append(
            f"NCLR: {info['bank_count']} bank(s), bank size {info['bank_size']}, "
            f"{info['color_count']} colours")
    if asset.get("ncer"):
        info = asset["ncer"]
        cell_count = len(info.get("cells", []))
        config = project / "cells.json"
        if config.exists():
            cell_count = len(json.loads(config.read_text(encoding="utf-8")).get("cells", []))
        lines.append(
            f"NCER: {cell_count} cells, mapping {info['mapping_mode']}, "
            f"bbox {info['bbox']}")
    if asset.get("nscr"):
        info = asset["nscr"]
        lines.append(
            f"NSCR: {info['width']}x{info['height']}, {len(info['entries'])} entries, "
            f"mode {info['color_mode']}, format {info['screen_format']}")
    return "\n".join(lines)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    export = sub.add_parser("export")
    export.add_argument("--ncgr", default=None)
    export.add_argument("--palette", default=None)
    export.add_argument("--ncer", default=None)
    export.add_argument("--screen", default=None)
    export.add_argument("-o", "--output", required=True)

    rebuild = sub.add_parser("rebuild")
    rebuild.add_argument("project")
    rebuild.add_argument("-o", "--output", required=True)

    describe = sub.add_parser("describe")
    describe.add_argument("project")

    args = parser.parse_args(argv)
    try:
        if args.command == "export":
            return export_asset(
                Path(args.output),
                Path(args.ncgr) if args.ncgr else None,
                Path(args.palette) if args.palette else None,
                Path(args.ncer) if args.ncer else None,
                Path(args.screen) if args.screen else None)
        if args.command == "describe":
            print(describe_asset(Path(args.project)))
            return 0
        written = rebuild_asset(Path(args.project), Path(args.output))
        for path in written:
            print(f"rebuilt {path}")
        return 0
    except (OSError, AssetError, gp.ProjectError) as exc:
        parser.error(str(exc))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
