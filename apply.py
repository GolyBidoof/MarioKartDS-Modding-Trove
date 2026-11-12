#!/usr/bin/env python3
# Mario Kart DS Modding Trove
# apply.py — one-command modding entry point
# SPDX-License-Identifier: MIT
"""Apply one or more independent mods to Mario Kart DS ROMs.

Quick start:
    python3 apply.py /path/to/game.nds

The first run sets up the public tools automatically if they are missing.
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

from tools import bmgset, mods as modlib, patch
from tools.nds import arm9_from_nds


def resolve_tools() -> patch.Tools:
    try:
        return patch.locate()
    except patch.ToolError as exc:
        print(f"   {exc}")
        print("   first run: setting up the public tools (one time) ...")
        import bootstrap
        bootstrap.ensure_tools()
        return patch.locate()


def run_one(rom: Path, out_dir: Path, work_dir: Path, keep_work: bool,
            dry_run: bool, selected: list[modlib.Mod]) -> None:
    stem = rom.stem
    work = work_dir / stem
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)

    ids = [mod.id for mod in selected]
    print(f"\n== {rom.name}")
    print(f"   mods: {', '.join(ids)}")

    arm9, base = arm9_from_nds(str(rom))
    profiles = {mod.id: patch.load_profile(mod, arm9, base)
                for mod in selected}
    print(f"   ARM9 {base:#010x}")
    for mod in selected:
        profile = profiles[mod.id]
        summary = getattr(profile, "summary", None)
        print(f"   {mod.id} profile:")
        if callable(summary):
            for line in summary():
                print(f"     {line}")
        else:
            print(f"     {profile}")

    plan = bmgset.plan_rom(rom, work, selected)
    rendered_by_mod: dict[str, list[str]] = {}
    sources: list[tuple[str, str]] = []
    for mod in selected:
        rendered = patch.render_mod_sources(mod, profiles[mod.id],
                                           plan.ids[mod.id])
        rendered_by_mod[mod.id] = [text for _, text in rendered]
        sources.extend(rendered)
        print(f"   {mod.id}: {len(rendered)} source(s), "
              f"BMG ids {plan.ids[mod.id]}")
    patch.check_conflicts(rendered_by_mod)

    for dest, _ in plan.files:
        print(f"   BMG {dest}")

    if dry_run:
        print("   dry run: no ROM written")
        if not keep_work:
            shutil.rmtree(work)
        return

    tools = resolve_tools()
    output = work / "patched.nds"
    ncp = patch.write_ncp_project(tools, work, rom, output, sources, plan.files)
    print("   NCPatcher: compiling and patching ...")
    patch.run_ncp(tools, ncp, output)

    print("   verifying ...")
    image = patch.verify_global(output, base, plan.files)
    for mod in selected:
        context = patch.ModContext(profile=profiles[mod.id], image=image,
                                   base=base, new_ids=plan.ids[mod.id],
                                   tools=tools)
        patch.verify_mod(mod, context)

    out_dir.mkdir(parents=True, exist_ok=True)
    final = out_dir / f"{stem}_{'+'.join(ids)}.nds"
    shutil.copy2(output, final)
    print(f"   wrote {final}")

    if not keep_work:
        shutil.rmtree(work)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("roms", nargs="*", metavar="ROM",
                    help="ROM(s) to patch")
    ap.add_argument("--rom", action="append", default=[],
                    help="additional ROM (repeatable)")
    ap.add_argument("--rom-dir", help="directory to scan for *.nds")
    ap.add_argument("--mod", action="append", default=[],
                    help="mod id to apply (repeatable; default: all)")
    ap.add_argument("--all-mods", action="store_true", help="apply every mod")
    ap.add_argument("--list-mods", action="store_true", help="list mods and exit")
    ap.add_argument("--out-dir", default="out", help="where patched ROMs go")
    ap.add_argument("--work-dir", help="scratch directory (default: OUT/.work)")
    ap.add_argument("--keep-work", action="store_true",
                    help="keep generated sources and intermediates")
    ap.add_argument("--dry-run", action="store_true",
                    help="print the plan without writing a ROM")
    a = ap.parse_args(argv)

    all_mods = modlib.discover()
    if a.list_mods:
        print(modlib.describe(all_mods))
        return 0

    if not a.mod and not a.all_mods:
        a.all_mods = True

    try:
        selected = modlib.select(all_mods, a.mod, a.all_mods)
    except modlib.ModError as exc:
        print(f"error: {exc}", file=sys.stderr)
        print("\n" + modlib.describe(all_mods), file=sys.stderr)
        return 2
    if not selected:
        ap.error("no mods found under mods/")
    selected.sort(key=lambda mod: mod.id)

    roms = [Path(p).expanduser().resolve() for p in a.roms + a.rom]
    if a.rom_dir:
        roms += sorted(p.resolve() for p in Path(a.rom_dir).expanduser().glob("*")
                       if p.suffix.lower() == ".nds")
    if not roms:
        ap.error("give a ROM: python3 apply.py /path/to/game.nds")
    for rom in roms:
        if not rom.is_file():
            ap.error(f"not a file: {rom}")

    out_dir = Path(a.out_dir).expanduser().resolve()
    work_dir = Path(a.work_dir).expanduser().resolve() if a.work_dir else out_dir / ".work"

    failures = 0
    for rom in roms:
        try:
            run_one(rom, out_dir, work_dir, a.keep_work, a.dry_run, selected)
        except Exception as exc:
            failures += 1
            print(f"   ERROR: {exc}", file=sys.stderr)
    if failures:
        print(f"\n{failures} ROM(s) failed", file=sys.stderr)
        return 1
    print("\nall ROMs patched and verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
