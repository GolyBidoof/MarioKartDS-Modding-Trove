# Mario Kart DS Modding Trove
# tools/bmgset.py — multi-mod BMG label planning (per-language)
# SPDX-License-Identifier: MIT
# BMG notes: docs/bmg.md
"""Combine the BMG edits of several independent mods.

Each mod owns a default label set and optional per-language overrides.  The
plan strips every selected variant from the ROM's own BMG, appends the labels
for that archive's language, and gives each mod the ids its labels ended up at.
"""
from __future__ import annotations

from dataclasses import dataclass
from fnmatch import fnmatch
from pathlib import Path

from . import nds
from .bmg import Bmg, strip_labels
from .mods import Mod


class BmgPlanError(RuntimeError):
    pass


@dataclass
class BmgPlan:
    files: list[tuple[str, Path]]
    ids: dict[str, list[int]]


def _variants(mods: list[Mod]) -> set[str]:
    variants: set[str] = set()
    owner: dict[str, str] = {}
    for mod in mods:
        labels = set(mod.bmg_append)
        for values in mod.bmg_messages.values():
            labels.update(values)
        for label in sorted(labels, key=str.lower):
            key = label.strip().lower()
            if key in owner and owner[key] != mod.id:
                raise BmgPlanError(
                    f"mods {owner[key]!r} and {mod.id!r} both use {label!r}")
            owner[key] = mod.id
            variants.add(label)
    return variants


def _counts(mods: list[Mod]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for mod in mods:
        count = len(mod.bmg_append)
        for lang, labels in mod.bmg_messages.items():
            if len(labels) != count:
                raise BmgPlanError(
                    f"mod {mod.id!r} language {lang!r} has {len(labels)} "
                    f"labels, expected {count}")
        counts[mod.id] = count
    return counts


def language_for_archive(archive: str, prefixes: tuple[str, ...]) -> str:
    stem = Path(archive).stem
    for prefix in prefixes:
        if stem.startswith(prefix):
            return stem[len(prefix):] or "default"
    return "default"


def _labels_for(mod: Mod, dest: str) -> tuple[str, ...]:
    lang = language_for_archive(dest.split("!", 1)[0],
                                mod.bmg_language_prefixes)
    return mod.bmg_messages.get(lang,
                                mod.bmg_messages.get("default", mod.bmg_append))


def plan_items(items: list[tuple[str, bytes]], work: Path, mods: list[Mod],
               labels_for=_labels_for) -> BmgPlan:
    variants = _variants(mods)
    counts = _counts(mods)
    ids = {mod.id: [] for mod in mods}
    if not variants:
        return BmgPlan([], ids)

    bases = [(dest, raw, strip_labels(Bmg(raw).strings, variants))
             for dest, raw in items]
    common = max(len(base) for _, _, base in bases)

    cursor = common
    for mod in mods:
        count = counts[mod.id]
        ids[mod.id] = list(range(cursor, cursor + count))
        cursor += count

    entries: list[tuple[str, Path]] = []
    for dest, raw, base in bases:
        file_labels: list[str] = []
        for mod in mods:
            labels = labels_for(mod, dest)
            if len(labels) != counts[mod.id]:
                raise BmgPlanError(
                    f"mod {mod.id!r} has {len(labels)} labels for {dest}, "
                    f"expected {counts[mod.id]}")
            file_labels.extend(labels)
        strings = base + [""] * (common - len(base)) + file_labels
        archive = dest.split("!", 1)[0]
        target = work / "bmg" / Path(archive).stem / "rule.bmg"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(Bmg(raw).rebuilt(strings))
        entries.append((dest, target))
    return BmgPlan(entries, ids)


def plan_files(items: list[tuple[str, bytes]], work: Path,
               mods: list[Mod]) -> BmgPlan:
    return plan_items(items, work, mods, lambda mod, dest: mod.bmg_append)


def plan_rom(rom_path: Path, work: Path, mods: list[Mod]) -> BmgPlan:
    data = Path(rom_path).read_bytes()
    files = nds.read_fnt(data, nds.u32(data, 0x40))
    bmg_mods = [mod for mod in mods if mod.bmg_append or mod.bmg_messages]
    if not bmg_mods:
        return BmgPlan([], {mod.id: [] for mod in mods})

    patterns = {mod.bmg_archives for mod in bmg_mods}
    members = {mod.bmg_member for mod in bmg_mods}
    if "" in patterns or "" in members:
        raise BmgPlanError("a BMG mod is missing bmg.archives or bmg.member")
    if len(members) > 1:
        raise BmgPlanError(f"mods use different BMG members: {sorted(members)}")
    member = next(iter(members))

    items: list[tuple[str, bytes]] = []
    for path in sorted(files):
        if not any(fnmatch(path, pattern) for pattern in patterns):
            continue
        try:
            archive = nds.unpack_narc(nds.nds_member(data, path))
        except ValueError:
            continue
        if member in archive:
            items.append((f"{path}!{member}", archive[member]))
    if not items:
        raise BmgPlanError("no matching BMG archives found in the ROM")
    return plan_items(items, work, mods)
