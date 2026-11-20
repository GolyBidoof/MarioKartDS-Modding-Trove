# Mario Kart DS Modding Trove
# tools/g2d_bulk.py — unpack G2D assets into unified editable projects
# SPDX-License-Identifier: MIT
"""Bulk-export G2D assets with cross-archive palette/tiles bridging.

    python3 tools/g2d_bulk.py path/to/extracted/root/data -o out/g2d

Each asset gets one folder containing `asset.json`, `README.txt`, an indexed
`tilesheet.bmp`, composed previews (`sprite_sheet.bmp`, `screen.bmp`), palette
files and per-cell images. Palettes and shared graphics missing from a language
archive are matched against the base archive and other siblings.
"""
from __future__ import annotations

import argparse
import contextlib
import html
import io
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from tools import g2d_asset  # noqa: E402

_LANGS = ("us", "fr", "ge", "it", "es", "ja")


def base_stem(path: Path) -> str:
    name = path.name
    lower = name.lower()
    for suffix in (".ncgr", ".nclr", ".ncer", ".nscr"):
        if lower.endswith(suffix):
            name = name[:-len(suffix)]
            break
    if name.lower().endswith(".nce"):
        name = name[:-4]
    return name


def normalize(stem: str) -> str:
    text = stem.lower().replace("-", "_")
    while True:
        for suffix in ("_o", "_s", "_m", "_b", "_c"):
            if text.endswith(suffix):
                text = text[:-2]
                break
        else:
            return text


def family(path: Path) -> tuple[Path, str]:
    name = path.parent.name
    for language in _LANGS:
        suffix = "_" + language + "_arc"
        if name.endswith(suffix):
            name = name[:-len(suffix)] + "_arc"
            break
    return path.parent.parent, name


def family_path(path: Path, root: Path) -> Path:
    parts = list(path.parent.relative_to(root).parts)
    for index, part in enumerate(parts):
        match = re.match(r"^(.*?)(?:_(us|fr|ge|it|es|ja))?_arc$", part)
        if match:
            parts[index] = match.group(1)
    return Path(*parts) if parts else Path(".")


def language(path: Path) -> str:
    name = path.parent.name
    for language_name in _LANGS:
        if name.endswith("_" + language_name + "_arc"):
            return language_name
    return "base"


def context(stem: str, has_ncer: bool, has_nscr: bool) -> str:
    low = stem.lower()
    if has_ncer or any(word in low for word in ("character", "gp", "title", "name")):
        return "object"
    if has_nscr or any(word in low for word in ("bg", "map", "stage")):
        return "background"
    return "neutral"


def score(source: Path, candidate: Path, ctx: str) -> int:
    source_norm = normalize(base_stem(source))
    candidate_norm = normalize(base_stem(candidate))
    value = 0
    if source_norm == candidate_norm:
        value += 10000
    elif candidate_norm.startswith(source_norm) or source_norm.startswith(candidate_norm):
        value += 1000 + min(len(source_norm), len(candidate_norm))
    else:
        prefix = 0
        for left, right in zip(source_norm, candidate_norm):
            if left != right:
                break
            prefix += 1
        value += prefix
        if prefix < 4:
            return value
    source_tokens = set(source_norm.split("_"))
    candidate_tokens = set(candidate_norm.split("_"))
    value += 40 * len(source_tokens & candidate_tokens)
    if source.parent == candidate.parent:
        value += 500
    if family(source) == family(candidate):
        value += 200
    candidate_name = candidate.stem.lower()
    if candidate_name.endswith("_o"):
        value += 200 if ctx == "object" else -100
    if candidate_name.endswith("_b"):
        value += 200 if ctx == "background" else -100
    if any(candidate.parent.name.endswith("_" + language + "_arc")
           for language in _LANGS):
        value -= 10
    return value


def best_match(source: Path, candidates: list[Path], ctx: str) -> Path | None:
    scored = [(score(source, candidate, ctx), candidate) for candidate in candidates]
    if not scored:
        return None
    scored.sort(key=lambda item: (-item[0], len(item[1].name), item[1].name))
    best_score, best = scored[0]
    return best if best_score >= 20 else None


def collect(root: Path) -> list[Path]:
    return [path for path in root.rglob("*") if path.is_file()]


def group_assets(files: list[Path], root: Path) -> dict[tuple[Path, str], dict[str, dict[str, Path]]]:
    groups: dict[tuple[Path, str], dict[str, dict[str, Path]]] = {}
    for path in files:
        suffix = path.suffix.lower()
        if suffix not in (".ncgr", ".nclr", ".ncer", ".nscr"):
            continue
        key = (family_path(path, root), base_stem(path))
        groups.setdefault(key, {}).setdefault(language(path), {})[suffix[1:]] = path
    return groups


def write_gallery(outdir: Path, index: dict) -> None:
    rows = []
    for entry in index["entries"]:
        project = outdir / entry["project"]
        preview = None
        for name in ("sprite_sheet.bmp", "screen.bmp", "tilesheet.bmp"):
            candidate = project / name
            if candidate.exists():
                preview = candidate.relative_to(outdir).as_posix()
                break
        image = (f'<a href="{html.escape(preview)}">'
                 f'<img loading="lazy" src="{html.escape(preview)}"></a>'
                 if preview else '<span class="none">no preview</span>')
        kinds = ",".join(kind for kind in ("ncgr", "nclr", "ncer", "nscr")
                         if entry.get(kind))
        rows.append(
            f'<tr><td>{html.escape(kinds)}</td>'
            f'<td>{html.escape(entry["project"])}</td>'
            f'<td>{image}</td></tr>')
    document = ("<!doctype html>\n<meta charset=\"utf-8\">\n"
                "<title>MKDS G2D assets</title>\n"
                "<style>body{font:13px sans-serif;background:#222;color:#ddd}"
                "table{border-collapse:collapse}td,th{border:1px solid #444;"
                "padding:4px;vertical-align:top}img{max-width:256px;"
                "max-height:256px;image-rendering:pixelated}"
                ".none{color:#888}</style>\n"
                "<h1>MKDS G2D assets</h1>\n"
                f"<p>{len(index['entries'])} projects; "
                f"{index['counts']['errors']} errors.</p>\n"
                "<table><tr><th>contains</th><th>project</th><th>preview</th>"
                "</tr>\n" + "\n".join(rows) + "\n</table>\n")
    (outdir / "index.html").write_text(document, encoding="utf-8")


def bulk_export(root: Path, outdir: Path, limit: int | None = None) -> int:
    files = collect(root)
    all_ncgr = [path for path in files if path.suffix.lower() == ".ncgr"]
    all_nclr = [path for path in files if path.suffix.lower() == ".nclr"]
    all_ncer = [path for path in files if path.suffix.lower() == ".ncer"]
    all_nscr = [path for path in files if path.suffix.lower() == ".nscr"]
    groups = group_assets(files, root)
    items = sorted(
        groups.items(),
        key=lambda item: (
            0 if any(group.get("ncer") or group.get("nscr")
                     for group in item[1].values()) else 1,
            item[0]))
    if limit is not None:
        items = items[:limit]

    outdir.mkdir(parents=True, exist_ok=True)
    entries = []
    errors = []
    used_ncgr: set[Path] = set()
    used_nclr: set[Path] = set()

    def export_one(project: Path, ncgr, nclr, ncer, nscr, kind: str,
                   lang: str, bridged_ncgr: bool = False,
                   bridged_nclr: bool = False) -> None:
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                g2d_asset.export_asset(
                    project, ncgr, nclr, ncer, nscr,
                    sources={
                        name: value.relative_to(root).as_posix()
                        for name, value in (
                            ("ncgr", ncgr), ("nclr", nclr),
                            ("ncer", ncer), ("nscr", nscr))
                        if value is not None
                    })
            entry = {
                "project": project.relative_to(outdir).as_posix(),
                "language": lang,
                "kind": kind,
                "ncgr": ncgr.relative_to(root).as_posix() if ncgr else None,
                "nclr": nclr.relative_to(root).as_posix() if nclr else None,
                "ncer": ncer.relative_to(root).as_posix() if ncer else None,
                "nscr": nscr.relative_to(root).as_posix() if nscr else None,
            }
            if bridged_ncgr:
                entry["bridged_ncgr"] = True
            if bridged_nclr:
                entry["bridged_nclr"] = True
            entries.append(entry)
            if ncgr is not None:
                used_ncgr.add(ncgr)
            if nclr is not None:
                used_nclr.add(nclr)
        except Exception as exc:  # noqa: BLE001 - report and continue
            errors.append({"project": project.as_posix(), "error": str(exc)})

    for (family, stem), languages in items:
        for lang, group in sorted(languages.items()):
            ncgr = group.get("ncgr")
            nclr = group.get("nclr")
            ncer = group.get("ncer")
            nscr = group.get("nscr")
            if ncgr is None and nclr is None and ncer is None and nscr is None:
                continue

            if nscr is not None:
                screen_ncgr = best_match(nscr, all_ncgr, "background")
                screen_nclr = best_match(
                    screen_ncgr or nscr, all_nclr, "background")
                export_one(outdir / family / stem / "screen" / lang,
                           screen_ncgr, screen_nclr, None, nscr, "screen",
                           lang, screen_ncgr is not None,
                           screen_nclr is not None)

            if ncer is not None:
                cell_ncgr = ncgr or best_match(ncer, all_ncgr, "object")
                cell_nclr = best_match(
                    cell_ncgr or ncer, all_nclr, "object")
                export_one(outdir / family / stem / "cells" / lang,
                           cell_ncgr, cell_nclr, ncer, None, "cells",
                           lang, cell_ncgr is not None,
                           cell_nclr is not None)

            if nscr is None and ncer is None and ncgr is not None:
                if ncgr in used_ncgr:
                    continue
                tile_nclr = nclr or best_match(ncgr, all_nclr, "neutral")
                export_one(outdir / family / stem / "tiles" / lang,
                           ncgr, tile_nclr, None, None, "tiles", lang,
                           False, tile_nclr is not None)

    index = {
        "root": str(root),
        "counts": {
            "ncgr": len(all_ncgr),
            "nclr": len(all_nclr),
            "ncer": len(all_ncer),
            "nscr": len(all_nscr),
            "projects": len(entries),
            "errors": len(errors),
        },
        "entries": entries,
        "errors": errors,
    }
    (outdir / "index.json").write_text(
        json.dumps(index, indent=2) + "\n", encoding="utf-8")
    write_gallery(outdir, index)
    print(f"{len(entries)} projects -> {outdir}")
    for error in errors[:20]:
        print(f"error: {error['project']}: {error['error']}", file=sys.stderr)
    return 1 if errors else 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", help="extracted data directory")
    parser.add_argument("-o", "--output", required=True,
                        help="output directory, for example out/g2d")
    parser.add_argument("--limit", type=int, default=None,
                        help="limit the number of asset groups")
    args = parser.parse_args(argv)
    root = Path(args.root)
    if not root.is_dir():
        parser.error(f"{root} is not a directory")
    return bulk_export(root, Path(args.output), args.limit)


if __name__ == "__main__":
    raise SystemExit(main())
