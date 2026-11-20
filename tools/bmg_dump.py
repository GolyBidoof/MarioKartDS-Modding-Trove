# Mario Kart DS Modding Trove
# tools/bmg_dump.py — unpack every BMG bank to readable per-language text
# SPDX-License-Identifier: MIT
"""Dump MESG/bmg1 message banks without storing game data in the repository.

    python3 tools/bmg_dump.py path/to/extracted/root -o out/bmg

Each input ``.bmg`` becomes a UTF-8 text file with one message per line:

    000<TAB>"YES"
    001<TAB>"NO"

The quoted form is JSON string escaping, so newlines and control codes stay on
one line while Japanese and other non-ASCII text remains readable.  A JSON
copy and an index are written next to the text files.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from tools.bmg import Bmg, BmgError, render_message  # noqa: E402


def dump_one(source: Path, relative: Path, outdir: Path) -> dict:
    raw = source.read_bytes()
    bank = Bmg(raw)
    line_dir = outdir / relative.parent
    line_dir.mkdir(parents=True, exist_ok=True)
    stem = relative.name[:-4] if relative.name.lower().endswith(".bmg") else relative.name

    lines_path = line_dir / f"{stem}.txt"
    with lines_path.open("w", encoding="utf-8") as handle:
        handle.write(f"# {relative.as_posix()}\n")
        handle.write(f"# encoding={bank.encoding} messages={len(bank.strings)}\n")
        for index, text in enumerate(bank.strings):
            handle.write(
                f"{index:03d}\t{json.dumps(render_message(text), ensure_ascii=False)}\n")

    json_path = line_dir / f"{stem}.json"
    json_path.write_text(
        json.dumps({"source": relative.as_posix(),
                    "encoding": bank.encoding,
                    "messages": [render_message(text) for text in bank.strings]},
                   ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    return {
        "source": relative.as_posix(),
        "encoding": bank.encoding,
        "messages": len(bank.strings),
        "text": str(lines_path.relative_to(outdir)),
        "json": str(json_path.relative_to(outdir)),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", help="directory tree containing .bmg files")
    parser.add_argument("-o", "--output", required=True,
                        help="output directory, for example out/bmg")
    args = parser.parse_args(argv)

    root = Path(args.root)
    outdir = Path(args.output)
    if not root.is_dir():
        parser.error(f"{root} is not a directory")

    files = sorted(root.rglob("*.bmg"))
    if not files:
        parser.error(f"no .bmg files under {root}")

    entries = []
    errors = []
    for source in files:
        relative = source.relative_to(root)
        try:
            entries.append(dump_one(source, relative, outdir))
        except (OSError, BmgError) as exc:
            errors.append({"source": relative.as_posix(), "error": str(exc)})

    (outdir / "index.json").write_text(
        json.dumps({"root": str(root), "files": entries, "errors": errors},
                   indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"{len(entries)} BMG banks -> {outdir}")
    for entry in errors:
        print(f"error: {entry['source']}: {entry['error']}", file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
