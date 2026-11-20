# Mario Kart DS Modding Trove
# tools/g2d_font_anim.py — editable NFTR fonts and NANR cell animations
# SPDX-License-Identifier: MIT
"""Visualise and edit Nitro NFTR fonts and NANR cell animations.

    python3 tools/g2d_font_anim.py nftr-export font.NFTR -o out/font
    python3 tools/g2d_font_anim.py nftr-rebuild out/font -o rebuilt.NFTR

    python3 tools/g2d_font_anim.py nanr-export anim.NANR \
        --ncer anim.NCER --ncgr anim.NCGR --palette anim.NCLR -o out/anim
    python3 tools/g2d_font_anim.py nanr-rebuild out/anim -o rebuilt.NANR

NFTR projects contain `font.bmp`, `glyphs/glyph_XXX.bmp`, `font.json` and a
`source/` copy. NANR projects contain `frames/frame_XXX.bmp`, `sheet.bmp`,
`preview.html`, `anim.json` and a `source/` copy.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import shutil
import struct
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from tools import bmp, g2d_asset, g2d_project as gp  # noqa: E402


class FontAnimError(ValueError):
    pass


def _u16(data: bytes, off: int) -> int:
    return struct.unpack_from("<H", data, off)[0]


def _u32(data: bytes, off: int) -> int:
    return struct.unpack_from("<I", data, off)[0]


def _blocks(data: bytes) -> list[tuple[int, bytes]]:
    if len(data) < 16:
        raise FontAnimError("file is shorter than its 16-byte header")
    result = []
    offset = 16
    while offset + 8 <= len(data):
        size = _u32(data, offset + 4)
        if size < 8 or offset + size > len(data):
            break
        result.append((offset, data[offset:offset + size]))
        offset += size
    return result


def _glyph_palette(bpp: int) -> list[tuple[int, int, int]]:
    count = 1 << bpp
    return [(index * 255 // (count - 1),) * 3 for index in range(count)]


def _decode_glyph(raw: bytes, width: int, height: int, bpp: int) -> list[list[int]]:
    bits = width * height * bpp
    index = 0
    pixels = []
    for _y in range(height):
        row = []
        for _x in range(width):
            value = 0
            for _bit in range(bpp):
                if index >= bits:
                    value <<= 1
                else:
                    byte = raw[index // 8] if index // 8 < len(raw) else 0
                    value = (value << 1) | ((byte >> (7 - (index % 8))) & 1)
                    index += 1
            row.append(value)
        pixels.append(row)
    return pixels


def _encode_glyph(pixels: list[list[int]], width: int, height: int,
                  bpp: int, cell_size: int) -> bytes:
    out = bytearray(cell_size)
    bit_index = 0
    for y in range(height):
        for x in range(width):
            value = int(pixels[y][x]) & ((1 << bpp) - 1)
            for shift in range(bpp - 1, -1, -1):
                if (value >> shift) & 1:
                    out[bit_index // 8] |= 0x80 >> (bit_index % 8)
                bit_index += 1
    return bytes(out)


def _atlas(glyphs: list[list[list[int]]], width: int, height: int,
           palette: list[tuple[int, int, int]], path: Path) -> None:
    cols = 16
    rows = max(1, (len(glyphs) + cols - 1) // cols)
    cell_w = width + 1
    cell_h = height + 1
    pixels = [[0] * (cols * cell_w) for _ in range(rows * cell_h)]
    for index, glyph in enumerate(glyphs):
        ox = (index % cols) * cell_w
        oy = (index // cols) * cell_h
        for y in range(height):
            pixels[oy + y][ox:ox + width] = glyph[y]
    bmp.write_indexed(path, cols * cell_w, rows * cell_h, pixels, palette)


def nftr_export(path: Path, outdir: Path) -> int:
    raw = path.read_bytes()
    if raw[:4] != b"RTFN":
        raise FontAnimError("not an NFTR (RTFN) file")
    version = _u16(raw, 6)
    blocks = _blocks(raw)
    finf = glyph = None
    width_blocks = []
    cmap_blocks = []
    for _offset, block in blocks:
        magic = block[:4]
        if magic == b"FNIF":
            finf = block
        elif magic == b"PLGC":
            glyph = block
        elif magic == b"HDWC":
            width_blocks.append(block)
        elif magic == b"PAMC":
            cmap_blocks.append(block)
    if finf is None or glyph is None:
        raise FontAnimError("NFTR is missing FINF or CGLP")
    width = glyph[8]
    height = glyph[9]
    cell_size = _u16(glyph, 0x0A)
    bpp = glyph[0x0E]
    if bpp not in (1, 2, 3):
        raise FontAnimError(f"unsupported NFTR bpp {bpp}")
    payload = glyph[16:]
    glyph_count = len(payload) // cell_size if cell_size else 0
    glyphs = []
    palette = _glyph_palette(bpp)
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / "glyphs").mkdir(exist_ok=True)
    for index in range(glyph_count):
        pixels = _decode_glyph(payload[index * cell_size:(index + 1) * cell_size],
                               width, height, bpp)
        glyphs.append(pixels)
        bmp.write_indexed(outdir / "glyphs" / f"glyph_{index:03d}.bmp",
                          width, height, pixels, palette)
    _atlas(glyphs, width, height, palette, outdir / "font.bmp")

    widths = {}
    for block in width_blocks:
        first, last = _u16(block, 8), _u16(block, 0x0A)
        entry_size = 2 if version == 0x0001 else 3
        for index in range(max(0, last - first + 1)):
            base = 16 + index * entry_size
            if base + entry_size > len(block):
                break
            if entry_size == 3:
                widths[str(first + index)] = [struct.unpack_from("<b", block, base)[0],
                                              block[base + 1],
                                              struct.unpack_from("<b", block, base + 2)[0]]
            else:
                widths[str(first + index)] = [struct.unpack_from("<b", block, base)[0],
                                              block[base + 1], 0]
    cmaps = []
    for block in cmap_blocks:
        first, last = _u16(block, 8), _u16(block, 0x0A)
        method = _u16(block, 0x0C)
        payload = block[20:]
        mapping = {}
        if method == 0 and len(payload) >= 2:
            mapping = {str(first): _u16(payload, 0)}
        elif method == 1:
            for index in range(max(0, last - first + 1)):
                if 2 * index + 2 > len(payload):
                    break
                mapping[str(first + index)] = _u16(payload, 2 * index)
        elif method == 2 and len(payload) >= 2:
            scan_count = _u16(payload, 0)
            for index in range(scan_count):
                base = 2 + index * 4
                if base + 4 > len(payload):
                    break
                mapping[str(_u16(payload, base))] = _u16(payload, base + 2)
        cmaps.append({"first": first, "last": last, "method": method,
                      "mapping": mapping})

    json_data = {
        "source": path.name,
        "header": {"version": version, "bom": _u16(raw, 4),
                   "encoding": finf[0x0F] if version != 0x0001 else finf[0x0E]},
        "finf_hex": finf.hex(),
        "cglp": {"cell_width": width, "cell_height": height,
                 "cell_size": cell_size, "baseline": glyph[0x0C],
                 "max_char_width": glyph[0x0D], "bpp": bpp,
                 "glyph_count": glyph_count},
        "widths": widths,
        "cmaps": cmaps,
        "glyphs": [f"glyphs/glyph_{index:03d}.bmp"
                   for index in range(glyph_count)],
        "trailer_hex": raw[16 + sum(len(block) for _, block in blocks):].hex(),
    }
    (outdir / "font.json").write_text(
        json.dumps(json_data, indent=2) + "\n", encoding="utf-8")
    source_dir = outdir / "source"
    source_dir.mkdir(exist_ok=True)
    shutil.copy2(path, source_dir / path.name)
    print(f"exported {path.name} -> {outdir}")
    return 0


def nftr_rebuild(project: Path, output: Path) -> int:
    data = json.loads((project / "font.json").read_text(encoding="utf-8"))
    cells = data["cglp"]
    width, height = cells["cell_width"], cells["cell_height"]
    bpp, cell_size = cells["bpp"], cells["cell_size"]
    glyphs = []
    for name in data["glyphs"]:
        image = bmp.load_indexed(project / name)
        glyphs.append(_encode_glyph(image.pixels, width, height, bpp, cell_size))
    payload = b"".join(glyphs)
    finf = bytes.fromhex(data["finf_hex"])
    cglp = (b"PLGC" + struct.pack("<I", 16 + len(payload)) +
            struct.pack("<BBHBBBB", width, height, cell_size,
                        int(cells["baseline"]) & 0xFF,
                        int(cells["max_char_width"]) & 0xFF,
                        bpp, 0) + payload)
    width_items = sorted((int(k), v) for k, v in data["widths"].items())
    if width_items:
        first, last = width_items[0][0], width_items[-1][0]
        entry_size = 2 if data["header"]["version"] == 0x0001 else 3
        entries = bytearray()
        by_index = {index: value for index, value in width_items}
        for index in range(first, last + 1):
            item = by_index.get(index, [0, 0, 0])
            entries += struct.pack("<bB", int(item[0]), int(item[1]) & 0xFF)
            if entry_size == 3:
                entries += struct.pack("<b", int(item[2]))
        cwdh = b"HDWC" + struct.pack("<IHHII", 16 + len(entries), first, last,
                                      0, 0) + bytes(entries)
    else:
        cwdh = b""
    cmaps = []
    for cmap in data["cmaps"]:
        mapping = sorted((int(k), v) for k, v in cmap["mapping"].items())
        if not mapping:
            continue
        first, last = mapping[0][0], mapping[-1][0]
        method = 2
        table = bytearray(struct.pack("<H", len(mapping)))
        for code, glyph in mapping:
            table += struct.pack("<HH", code, glyph)
        cmaps.append(b"PAMC" + struct.pack("<IHHHHI", 20 + len(table), first,
                                           last, method, 0, 0) + bytes(table))
    blocks = [finf, cglp, cwdh] + cmaps
    header = bytearray(16)
    header[:4] = b"RTFN"
    struct.pack_into("<H", header, 4, data["header"]["bom"])
    struct.pack_into("<H", header, 6, data["header"]["version"])
    struct.pack_into("<H", header, 0x0C, 0x10)
    struct.pack_into("<H", header, 0x0E, len(blocks))
    out = bytearray(header)
    for block in blocks:
        if block:
            out += block
    out += bytes.fromhex(data.get("trailer_hex", ""))
    struct.pack_into("<I", out, 8, len(out))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(bytes(out))
    print(f"rebuilt {output}")
    return 0


def _frame_canvas(cells: list[dict], index: int, max_w: int, max_h: int,
                  palette: list[tuple[int, int, int]]) -> list[list[int]]:
    canvas = [[0] * max_w for _ in range(max_h)]
    if index >= len(cells):
        return canvas
    cell = cells[index]["canvas"]
    ox = (max_w - len(cell[0])) // 2
    oy = (max_h - len(cell)) // 2
    for y, row in enumerate(cell):
        canvas[oy + y][ox:ox + len(row)] = row
    return canvas


def nanr_export(path: Path, outdir: Path, ncer: Path, ncgr: Path,
                nclr: Path | None) -> int:
    raw = path.read_bytes()
    if raw[:4] != b"RNAN":
        raise FontAnimError("not an NANR (RNAN) file")
    knba = None
    tail = b""
    for _offset, block in _blocks(raw):
        if block[:4] == b"KNBA":
            knba = block
            tail = raw[_offset + len(block):]
            break
    if knba is None:
        raise FontAnimError("NANR is missing its KNBA block")
    anim_count, frame_count = _u16(knba, 8), _u16(knba, 0x0A)
    anim_base = 8 + _u32(knba, 0x0C)
    frame_base = 8 + _u32(knba, 0x10)
    data_base = 8 + _u32(knba, 0x14)
    animations = []
    for index in range(anim_count):
        base = anim_base + index * 16
        animations.append({
            "frame_count": _u16(knba, base),
            "loop_start": _u16(knba, base + 2),
            "animation_type": _u32(knba, base + 4),
            "play_mode": _u32(knba, base + 8),
            "first_frame_offset": _u32(knba, base + 0x0C),
        })
    frames = []
    cells_used = []
    for index in range(frame_count):
        base = frame_base + index * 8
        offset, duration, reserved = struct.unpack_from("<IHH", knba, base)
        cell = _u16(knba, data_base + offset) if data_base + offset + 2 <= len(knba) else 0
        frames.append({"data_offset": offset, "duration": duration,
                       "reserved": reserved, "cell": cell})
        cells_used.append(cell)
    cells, palette = g2d_asset._cell_indices(ncer.read_bytes(),
                                             ncgr.read_bytes(),
                                             nclr.read_bytes() if nclr else None)
    max_w = max((len(cell["canvas"][0]) for cell in cells), default=1)
    max_h = max((len(cell["canvas"]) for cell in cells), default=1)
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / "frames").mkdir(exist_ok=True)
    frame_paths = []
    canvases = []
    for index, frame in enumerate(frames):
        canvas = _frame_canvas(cells, frame["cell"], max_w, max_h, palette)
        canvases.append(canvas)
        name = f"frames/frame_{index:03d}.bmp"
        bmp.write_indexed(outdir / name, max_w, max_h, canvas, palette)
        frame_paths.append(name)
    cols = min(8, max(1, len(canvases)))
    rows = max(1, (len(canvases) + cols - 1) // cols)
    sheet = [[0] * (cols * (max_w + 2)) for _ in range(rows * (max_h + 2))]
    for index, canvas in enumerate(canvases):
        ox = (index % cols) * (max_w + 2)
        oy = (index // cols) * (max_h + 2)
        for y, row in enumerate(canvas):
            sheet[oy + y][ox:ox + max_w] = row
    bmp.write_indexed(outdir / "sheet.bmp", cols * (max_w + 2),
                      rows * (max_h + 2), sheet, palette)
    html_doc = ("<!doctype html><meta charset='utf-8'><title>NANR</title>"
                "<style>body{background:#222;color:#ddd;font:13px sans-serif}"
                "img{image-rendering:pixelated;max-width:512px}</style>"
                "<h1>NANR preview</h1><img id='f'>"
                "<p id='a'></p><script>const frames="
                + json.dumps(frame_paths) + ";const delays="
                + json.dumps([frame["duration"] for frame in frames])
                + ";let i=0;function show(){document.getElementById('f').src=frames[i];"
                  "document.getElementById('a').textContent='frame '+i+' / '+(frames.length-1)+'  duration '+delays[i];"
                  "i=(i+1)%frames.length;setTimeout(show,Math.max(20,delays[i-1]*1000/60));}show();</script>")
    (outdir / "preview.html").write_text(html_doc, encoding="utf-8")

    # Keep the paired cell project next to the animation so cells can be
    # edited and rebuilt without hunting for the original NCER/NCGR.
    g2d_asset.export_asset(outdir / "cells", ncgr, nclr, ncer, None)

    data = {
        "source": path.name,
        "header": {"version": _u16(raw, 6), "bom": _u16(raw, 4)},
        "knba": {"animation_count": anim_count, "frame_count": frame_count,
                 "animation_offset": _u32(knba, 0x0C),
                 "frame_offset": _u32(knba, 0x10),
                 "frame_data_offset": _u32(knba, 0x14)},
        "animations": animations,
        "frames": frames,
        "sources": {"ncer": ncer.name,
                    "ncgr": ncgr.name,
                    "nclr": nclr.name if nclr else None},
        "tail_hex": tail.hex(),
    }
    (outdir / "anim.json").write_text(
        json.dumps(data, indent=2) + "\n", encoding="utf-8")
    source_dir = outdir / "source"
    source_dir.mkdir(exist_ok=True)
    for item in (path, ncer, ncgr, nclr):
        if item is not None:
            shutil.copy2(item, source_dir / item.name)
    print(f"exported {path.name} -> {outdir}")
    return 0


def nanr_rebuild(project: Path, output: Path) -> int:
    data = json.loads((project / "anim.json").read_text(encoding="utf-8"))
    animations = data["animations"]
    frames = data["frames"]
    frame_data = bytearray()
    for frame in frames:
        frame["data_offset"] = len(frame_data)
        frame_data += struct.pack("<H", int(frame["cell"]) & 0xFFFF)
        if len(frame_data) & 3:
            frame_data += b"\0" * (4 - (len(frame_data) & 3))
    animation_data = bytearray()
    for animation in animations:
        animation_data += struct.pack("<HHIII",
                                      int(animation["frame_count"]),
                                      int(animation["loop_start"]),
                                      int(animation["animation_type"]),
                                      int(animation["play_mode"]),
                                      int(animation["first_frame_offset"]))
    frame_block = bytearray()
    for frame in frames:
        frame_block += struct.pack("<IHH", int(frame["data_offset"]),
                                   int(frame["duration"]),
                                   int(frame.get("reserved", 0)))
    header = bytearray(24)
    header[:4] = b"KNBA"
    struct.pack_into("<HH", header, 8, len(animations), len(frames))
    struct.pack_into("<III", header, 0x0C, 24,
                    24 + len(animation_data),
                    24 + len(animation_data) + len(frame_block))
    block = bytes(header) + bytes(animation_data) + bytes(frame_block) + bytes(frame_data)
    block = bytearray(block)
    struct.pack_into("<I", block, 4, len(block))
    file_header = bytearray(16)
    file_header[:4] = b"RNAN"
    struct.pack_into("<H", file_header, 4, data["header"]["bom"])
    struct.pack_into("<H", file_header, 6, data["header"]["version"])
    struct.pack_into("<H", file_header, 0x0C, 0x10)
    struct.pack_into("<H", file_header, 0x0E, 1)
    out = bytearray(file_header) + block + bytes.fromhex(data.get("tail_hex", ""))
    struct.pack_into("<I", out, 8, len(out))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(bytes(out))
    print(f"rebuilt {output}")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for command in ("nftr-export", "nanr-export"):
        p = sub.add_parser(command)
        p.add_argument("input")
        p.add_argument("-o", "--output", required=True)
        if command == "nanr-export":
            p.add_argument("--ncer", required=True)
            p.add_argument("--ncgr", required=True)
            p.add_argument("--palette", default=None)
    for command in ("nftr-rebuild", "nanr-rebuild"):
        p = sub.add_parser(command)
        p.add_argument("project")
        p.add_argument("-o", "--output", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "nftr-export":
            return nftr_export(Path(args.input), Path(args.output))
        if args.command == "nanr-export":
            return nanr_export(Path(args.input), Path(args.output),
                               Path(args.ncer), Path(args.ncgr),
                               Path(args.palette) if args.palette else None)
        if args.command == "nftr-rebuild":
            return nftr_rebuild(Path(args.project), Path(args.output))
        return nanr_rebuild(Path(args.project), Path(args.output))
    except (OSError, FontAnimError, gp.ProjectError) as exc:
        parser.error(str(exc))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
