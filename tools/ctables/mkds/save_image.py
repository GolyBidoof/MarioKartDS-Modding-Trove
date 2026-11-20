# Mario Kart DS Modding Trove
# tools/ctables/mkds/save_image.py — editable .sav image extractor/rebuilder
# SPDX-License-Identifier: MIT
"""Split an MKDS .sav into editable typed C blocks and rebuild the card image.

    python3 tools/ctables/mkds/save_image.py extract partida.sav -o out/save
    # edit out/save/NKSY_primary.c and friends
    python3 tools/ctables/mkds/save_image.py build out/save -o rebuilt.sav

The small layout.json records block offsets, encryption seeds and whether the
block has an 8-byte plaintext prefix. It contains no save data.
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

from tools.ctables.common import harness  # noqa: E402
from tools.ctables.mkds import save_crypto, save_tables  # noqa: E402
from tools.ctables.common.cformat import pretty_c  # noqa: E402

SAV_FILE_SIZE = 0x40000
ERASED = 0xFF

# (kind, primary offset, backup offset or None, size, count, header block)
REGIONS = [
    ("NKSY", 0x00000, 0x30F00, 0x100, 1, True),
    ("NKEM", 0x00100, 0x31000, 0x300, 1, False),
    ("NKGP", 0x00400, 0x31300, 0x400, 1, False),
    ("NKTA", 0x00800, 0x31700, 0x1600, 1, False),
    ("NKMR", 0x01E00, 0x32D00, 0x100, 1, False),
    ("NKFL", 0x01F00, 0x32E00, 0xC00, 1, False),
    ("NKFE", 0x02B00, 0x33A00, 0xB00, 5, False),
    ("NKPG", 0x0AF00, None, 0xE00, 32, False),
    ("NKDG", 0x26F00, None, 0x1000, 10, False),
]


def _iter_blocks():
    for kind, primary, backup, size, count, header in REGIONS:
        for index in range(count):
            suffix = f"_{index:02d}" if count > 1 else ""
            yield kind, f"{kind}{suffix}_primary", primary + index * size, size, header
            if backup is not None:
                yield kind, f"{kind}{suffix}_backup", backup + index * size, size, header


def _is_erased(block: bytes) -> bool:
    return all(b == ERASED for b in block)


def extract(sav_path: Path, outdir: Path) -> int:
    image = sav_path.read_bytes()
    if len(image) != SAV_FILE_SIZE:
        raise SystemExit(f"{sav_path}: expected {SAV_FILE_SIZE} bytes, got {len(image)}")
    outdir.mkdir(parents=True, exist_ok=True)
    blocks = []
    warnings = []
    for kind, label, offset, size, header in _iter_blocks():
        block = image[offset:offset + size]
        if _is_erased(block):
            continue
        try:
            plain, seed = save_crypto.decrypt_block(block, kind, header)
        except ValueError as exc:
            warnings.append(f"{label} @ 0x{offset:X}: {exc}")
            continue
        source = save_tables.emit_sav_block(plain, kind)
        path = outdir / f"{label}.c"
        path.write_text(pretty_c(source), encoding="utf-8")
        blocks.append({
            "label": label,
            "kind": kind,
            "offset": offset,
            "size": size,
            "header": header,
            "seed": seed,
            "file": path.name,
        })

    (outdir / "layout.json").write_text(json.dumps({
        "file_size": SAV_FILE_SIZE,
        "blocks": blocks,
    }, indent=2) + "\n", encoding="utf-8")

    print(f"{len(blocks)} editable blocks -> {outdir}")
    for warning in warnings:
        print("warning:", warning)
    return 0


def build(outdir: Path, output: Path) -> int:
    layout = json.loads((outdir / "layout.json").read_text(encoding="utf-8"))
    image = bytearray([ERASED] * int(layout.get("file_size", SAV_FILE_SIZE)))
    for block in layout["blocks"]:
        source = (outdir / block["file"]).read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as tmp:
            raw_path = Path(tmp) / "block.bin"
            error = harness.compile_and_write(source, raw_path)
            if error:
                sys.stderr.write(error)
                return 1
            plain = raw_path.read_bytes()
        size = int(block["size"])
        if len(plain) != size:
            raise SystemExit(
                f"{block['label']}: expected {size} bytes, generated {len(plain)}")
        plain = save_crypto.refresh_footer(plain)
        encrypted = save_crypto.encrypt_block(
            plain, block["kind"], int(block["seed"]), bool(block["header"]))
        offset = int(block["offset"])
        image[offset:offset + size] = encrypted

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(bytes(image))
    print(f"wrote {output} ({len(image)} bytes)")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p_extract = sub.add_parser("extract")
    p_extract.add_argument("input")
    p_extract.add_argument("-o", "--output", required=True)

    p_build = sub.add_parser("build")
    p_build.add_argument("input")
    p_build.add_argument("-o", "--output", required=True)

    args = parser.parse_args(argv)
    if args.command == "extract":
        return extract(Path(args.input), Path(args.output))
    return build(Path(args.input), Path(args.output))


if __name__ == "__main__":
    raise SystemExit(main())
