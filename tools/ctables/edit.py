# Mario Kart DS Modding Trove
# tools/ctables/edit.py — extract a binary into an editable typed C table and rebuild it
# SPDX-License-Identifier: MIT
"""Editable C-table workflow.

    python3 tools/ctables/edit.py extract path/to/ranktimeGP.rtt -o ranktimeGP.c
    # edit ranktimeGP.c
    python3 tools/ctables/edit.py build ranktimeGP.c -o ranktimeGP.rtt

The generated .c file is a complete, compilable table program: typed static
tables followed by a small writer main(). Edit the initializers, then build.
Generated files and rebuilt binaries should stay outside the repository.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tools.ctables.common import harness  # noqa: E402
from tools.ctables.generic import g2d_tables, g3d_tables, snd_tables  # noqa: E402
from tools.ctables.mkds import (  # noqa: E402
    course_tables, save_tables, small_tables, ui_tables,
)

G2D_MAGICS = {b"RGCN", b"RLCN", b"RPCN", b"RCSN", b"RECN", b"RTFN", b"RNAN"}
G3D_MAGICS = {b"BMD0", b"BTX0", b"BCA0", b"BTP0", b"BTA0", b"BMA0"}
SND_MAGICS = {b"SDAT", b"SSEQ", b"SSAR", b"SBNK", b"SWAR", b"SWAV"}

KART_TABLES = {
    "kartAIparam.bin": save_tables.emit_kart_ai,
    "kartcrsmat.bin": save_tables.emit_kart_colors,
    "kartoffsetdata.bin": save_tables.emit_kart_offsets,
    "kartmenuparam.bin": save_tables.emit_kart_menu,
    "charphysicalparam.bin": None,  # chosen by size
    "charmenuparam.bin": save_tables.emit_char_menu,
}


def detect_emitter(path: Path, data: bytes):
    name = path.name
    suffix = path.suffix.lower().lstrip(".")

    if name in small_tables.EMITTERS:
        return lambda d: small_tables.emit_source(name, d)

    if suffix in ui_tables.FORMATS:
        return lambda d: ui_tables.emit_source(suffix, d)

    if data[:4] in G2D_MAGICS:
        return g2d_tables.emit_source
    if data[:4] in G3D_MAGICS:
        return g3d_tables.emit_source
    if data[:4] in SND_MAGICS:
        return _snd_emitter(data[:4])
    if suffix in ("nkm", "kcl", "spa") or data[:4] in (b"NKMD", b" APS", b"SPA "):
        return course_tables.emit_source

    if data[:4] == b"NKDG":
        return lambda d: save_tables.emit_ghost_file(d, "NKDG")
    if data[:4] == b"NKPG":
        return lambda d: save_tables.emit_ghost_file(d, "NKPG")

    if name == "charphysicalparam.bin":
        if len(data) == 104:
            return save_tables.emit_char_physical
        return save_tables.emit_char_u16
    if name == "kartphysicalparam.bin":
        widths = {5328: 144, 7400: 148, 7600: 152}
        if len(data) in widths:
            width = widths[len(data)]
            return lambda d: save_tables.emit_kart_physical(d, width)
    if name in KART_TABLES and KART_TABLES[name] is not None:
        return KART_TABLES[name]

    raise ValueError(
        f"no C-table emitter for {name!r} ({len(data)} bytes); "
        "use --format to name a known small/UI format")


def _snd_emitter(magic: bytes):
    return {
        b"SDAT": snd_tables.emit_sdat_source,
        b"SSEQ": snd_tables.emit_sseq_source,
        b"SSAR": snd_tables.emit_ssar_source,
        b"SBNK": snd_tables.emit_sbnk_source,
        b"SWAR": snd_tables.emit_swar_source,
        b"SWAV": snd_tables.emit_swav_source,
    }[magic]



from tools.ctables.common.cformat import pretty_c

def cmd_extract(args) -> int:
    path = Path(args.input)
    data = path.read_bytes()
    if args.format:
        key = args.format.lower().lstrip(".")
        if key in ui_tables.FORMATS:
            source = ui_tables.emit_source(key, data)
        elif args.format in small_tables.EMITTERS:
            source = small_tables.emit_source(args.format, data)
        else:
            raise SystemExit(f"unknown --format {args.format!r}")
    else:
        source = detect_emitter(path, data)(data)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    banner = "/* editable typed table; rebuild with tools/ctables/edit.py. */\n"
    out.write_text(banner + pretty_c(source), encoding="utf-8")
    print(f"wrote {out} ({len(data)} source bytes -> {len(source)} C chars)")
    return 0


def cmd_build(args) -> int:
    source = Path(args.input).read_text(encoding="utf-8")
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    error = harness.compile_and_write(source, out)
    if error:
        sys.stderr.write(error)
        return 1
    print(f"wrote {out} ({out.stat().st_size} bytes)")
    return 0


def cmd_list(_args) -> int:
    print("small tables:")
    for name in sorted(small_tables.EMITTERS):
        print(f"  {name}")
    print("UI lists:")
    for name in sorted(ui_tables.FORMATS):
        print(f"  .{name}")
    print("G2D:", " ".join(sorted(m.decode() for m in G2D_MAGICS)))
    print("G3D:", " ".join(sorted(m.decode() for m in G3D_MAGICS)))
    print("audio:", " ".join(sorted(m.decode() for m in SND_MAGICS)))
    print("course: .nkm .kcl .spa")
    print("save/ghost/kart: NKDG, NKPG, kart*.bin, char*.bin, staff_ghost_time.bin")
    print("DWC utility archive: tools/dwc_utility.py (not a C table)")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p_list = sub.add_parser("list", help="list detectable formats")
    p_list.set_defaults(func=cmd_list)

    p_extract = sub.add_parser("extract", help="binary -> editable typed C table")
    p_extract.add_argument("input")
    p_extract.add_argument("-o", "--output", required=True)
    p_extract.add_argument("--format", help="override format name/.extension")
    p_extract.set_defaults(func=cmd_extract)

    p_build = sub.add_parser("build", help="edited typed C table -> binary")
    p_build.add_argument("input")
    p_build.add_argument("-o", "--output", required=True)
    p_build.set_defaults(func=cmd_build)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
