# Mario Kart DS Modding Trove
# tools/mods.py — mod discovery and selection
# SPDX-License-Identifier: MIT
"""Discover and load the mods under ``mods/``."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
MODS_DIR = REPO / "mods"


@dataclass(frozen=True)
class Source:
    file: str
    when: dict[str, str] | None = None


@dataclass(frozen=True)
class Mod:
    id: str
    name: str
    description: str
    path: Path
    sources: tuple[Source, ...]
    bmg_append: tuple[str, ...]
    verify: str | None
    profile: str | None = None
    bmg_messages: dict[str, tuple[str, ...]] = field(default_factory=dict)
    bmg_archives: str = ""
    bmg_member: str = ""
    bmg_language_prefixes: tuple[str, ...] = ()

    def source_text(self, source: Source) -> str:
        return (self.path / source.file).read_text()

    def verify_path(self) -> Path | None:
        return (self.path / self.verify) if self.verify else None


class ModError(RuntimeError):
    pass


def discover(mods_dir: Path = MODS_DIR) -> dict[str, Mod]:
    found: dict[str, Mod] = {}
    if not mods_dir.is_dir():
        return found
    for directory in sorted(mods_dir.iterdir()):
        config = directory / "mod.json"
        if not config.is_file():
            continue
        raw = json.loads(config.read_text())
        mod_id = raw.get("id")
        if not mod_id:
            raise ModError(f"{config} has no id")
        if mod_id in found:
            raise ModError(f"duplicate mod id {mod_id!r}")
        sources = tuple(
            Source(file=item["file"], when=item.get("when"))
            for item in raw.get("sources", [])
        )
        bmg = raw.get("bmg", {})
        if isinstance(bmg, list):
            bmg = {"append": bmg}
        messages: dict[str, tuple[str, ...]] = {}
        messages_dir = bmg.get("messages")
        if messages_dir:
            msg_path = directory / messages_dir
            if not msg_path.is_dir():
                raise ModError(f"{msg_path} is not a directory")
            for file in sorted(msg_path.glob("*.json")):
                data = json.loads(file.read_text())
                labels = tuple(data.get("labels", ()))
                if not labels:
                    raise ModError(f"{file} has no labels")
                messages[file.stem] = labels
        labels = tuple(messages.get("default", bmg.get("append", ())))
        if messages and "default" not in messages:
            raise ModError(f"{config}: bmg messages have no default.json")
        found[mod_id] = Mod(
            id=mod_id,
            name=raw.get("name", mod_id),
            description=raw.get("description", ""),
            path=directory,
            sources=sources,
            bmg_append=labels,
            verify=raw.get("verify"),
            profile=raw.get("profile"),
            bmg_messages=messages,
            bmg_archives=bmg.get("archives", ""),
            bmg_member=bmg.get("member", ""),
            bmg_language_prefixes=tuple(bmg.get("language_prefixes", ())),
        )
    return found


def select(all_mods: dict[str, Mod], ids: list[str], all_mods_flag: bool) -> list[Mod]:
    if all_mods_flag:
        return [all_mods[key] for key in sorted(all_mods)]
    if not ids:
        raise ModError("choose at least one --mod, or pass --all-mods")
    missing = [mod_id for mod_id in ids if mod_id not in all_mods]
    if missing:
        known = ", ".join(sorted(all_mods)) or "(none)"
        raise ModError(f"unknown mod(s): {', '.join(missing)}; known: {known}")
    return [all_mods[mod_id] for mod_id in dict.fromkeys(ids)]


def describe(all_mods: dict[str, Mod]) -> str:
    if not all_mods:
        return "no mods found under mods/"
    width = max(len(mod.id) for mod in all_mods.values())
    return "\n".join(
        f"{mod.id:<{width}}  {mod.name}" + (f" — {mod.description}" if mod.description else "")
        for mod in sorted(all_mods.values(), key=lambda m: m.id)
    )
