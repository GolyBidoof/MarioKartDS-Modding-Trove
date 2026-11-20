# Mario Kart DS Modding Trove
# tools/bmg_headers.py — generate message-id headers from BMG banks
# SPDX-License-Identifier: MIT
"""Generate C message-id enums for the stock BMG banks.

    python3 tools/bmg_headers.py path/to/extracted/root -o include/nitro/mkds/bmg

The generated headers contain message ids and semantic enum keys. Full
localized text is produced separately by ``tools/bmg_dump.py``; long messages
are left as numbered ids so the repository does not become a text dump.

Keys for characters, cups, courses, karts and modes embed the shared constant
name, for example ``MKDS_BMG_COMMON_COURSE_YOSHI_FALLS``. Mission keys use
``missionTable.mtbl`` and ``mission.mr`` when those files are present under the
source root. Generated lines carry no per-message comments.
"""
from __future__ import annotations

import argparse
import re
import struct
import sys
from pathlib import Path
from typing import Optional

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from tools.bmg import Bmg, BmgError, render_message  # noqa: E402


def _identifier(text: str, index: int) -> str:
    clean = re.sub(r"<1A:[^>]*>", "", render_message(text))
    clean = clean.replace("\n", " ").replace("\r", " ")
    clean = "".join(ch if 32 <= ord(ch) < 127 else " " for ch in clean)
    clean = clean.replace("'", "")
    clean = re.sub(r"[^0-9A-Za-z]+", "_", clean).strip("_").upper()
    if not clean or len(clean) > 40 or clean[0].isdigit():
        return f"MSG_{index:03d}"
    return clean




def _bank_name(path: Path) -> str:
    stem = path.stem
    for suffix in ("_us", "_ja", "_es", "_fr", "_ge", "_it"):
        if stem.endswith(suffix):
            stem = stem[:-3]
            break
    return re.sub(r"[^0-9A-Za-z]+", "_", stem).strip("_").lower()


# The 32 cup courses, in the stock cup order used by common.bmg 45..76 and
# ghost.bmg 19..50. The ids are the race CourseId values documented in
# docs/mkds/formats-ids.md.
# Manual enum-key overrides for messages whose label maps to a known shared
# constant. The values are suffixes; emit_bank prefixes MKDS_BMG_<BANK>_.
# This is intentionally explicit: a text-derived key such as BOWSER would not
# say whether it belongs to the character, kart or course namespace.
KEY_OVERRIDES: dict[str, dict[int, str]] = {
    "common": {
        7: "FRIEND_CODE_ENTER",
        8: "FRIEND_CODE_TEMPORARY_NAME",
        9: "FRIEND_CODE_REGISTERED",
        10: "FRIEND_CODE_INCORRECT",
        11: "FRIEND_CODE_ALREADY_REGISTERED",
        12: "FRIEND_CODE_NICKNAME_CONFIRM",
        13: "FRIEND_CODE_RACE_NAME_CONFIRM",
        14: "FRIEND_CODE_RACE_NAME_CONFIRM_2",
        15: "FRIEND_CODE_ENTER_NICKNAME",
        16: "FRIEND_CODE_NICKNAME_REGISTERED",
        17: "FRIEND_CODE_CONFIRM",
        18: "FRIEND_CODE_COMPLETE",
        20: "CHARACTER_MARIO",
        21: "CHARACTER_LUIGI",
        22: "CHARACTER_PEACH",
        23: "CHARACTER_YOSHI",
        24: "CHARACTER_TOAD",
        25: "CHARACTER_DONKEY_KONG",
        26: "CHARACTER_WARIO",
        27: "CHARACTER_BOWSER",
        28: "CHARACTER_DAISY",
        29: "CHARACTER_DRY_BONES",
        30: "CHARACTER_WALUIGI",
        31: "CHARACTER_ROB",
        32: "CHARACTER_SHY_GUY",
        # Nitro/Retro GP are proven by the labels, but no MKDS_MODE_* enum
        # distinguishes them, so these keys have no extra reference comment.
        35: "MODE_NITRO_GP",
        36: "MODE_RETRO_GP",
        37: "CUP_MUSHROOM",
        38: "CUP_FLOWER",
        39: "CUP_STAR",
        40: "CUP_SPECIAL",
        41: "CUP_SHELL",
        42: "CUP_BANANA",
        43: "CUP_LEAF",
        44: "CUP_LIGHTNING",
        45: "COURSE_FIGURE_8_CIRCUIT",
        46: "COURSE_YOSHI_FALLS",
        47: "COURSE_CHEEP_CHEEP_BEACH",
        48: "COURSE_LUIGIS_MANSION",
        49: "COURSE_DESERT_HILLS",
        50: "COURSE_DELFINO_SQUARE",
        51: "COURSE_WALUIGI_PINBALL",
        52: "COURSE_SHROOM_RIDGE",
        53: "COURSE_DK_PASS",
        54: "COURSE_TICK_TOCK_CLOCK",
        55: "COURSE_MARIO_CIRCUIT",
        56: "COURSE_AIRSHIP_FORTRESS",
        57: "COURSE_WARIO_STADIUM",
        58: "COURSE_PEACH_GARDENS",
        59: "COURSE_BOWSER_CASTLE",
        60: "COURSE_RAINBOW_ROAD",
        61: "COURSE_SNES_MARIO_CIRCUIT_1",
        62: "COURSE_N64_MOO_MOO_FARM",
        63: "COURSE_GBA_PEACH_CIRCUIT",
        64: "COURSE_GCN_LUIGI_CIRCUIT",
        65: "COURSE_SNES_DONUT_PLAINS_1",
        66: "COURSE_N64_FRAPPE_SNOWLAND",
        67: "COURSE_GBA_BOWSER_CASTLE_2",
        68: "COURSE_GCN_BABY_PARK",
        69: "COURSE_SNES_KOOPA_BEACH_2",
        70: "COURSE_N64_CHOCO_MOUNTAIN",
        71: "COURSE_GBA_LUIGI_CIRCUIT",
        72: "COURSE_GCN_MUSHROOM_BRIDGE",
        73: "COURSE_SNES_CHOCO_ISLAND_2",
        74: "COURSE_N64_BANSHEE_BOARDWALK",
        75: "COURSE_GBA_SKY_GARDEN",
        76: "COURSE_GCN_YOSHI_CIRCUIT",
        77: "BATTLE_BLOCK_FORT",
        78: "BATTLE_PIPE_PLAZA",
        79: "BATTLE_NINTENDO_DS",
        80: "BATTLE_TWILIGHT_HOUSE",
        81: "BATTLE_PALM_SHORE",
        82: "BATTLE_TART_TOP",
        110: "ENGINE_50CC",
        111: "ENGINE_100CC",
        112: "ENGINE_150CC",
        113: "ENGINE_MIRROR",
    },
    "kart_select": {
        6: "KART_STANDARD_MR",
        7: "KART_SHOOTING_STAR",
        8: "KART_B_DASHER",
        9: "KART_STANDARD_LG",
        10: "KART_POLTERGUST_4000",
        11: "KART_STREAMLINER",
        12: "KART_STANDARD_PC",
        13: "KART_LIGHT_TRIPPER",
        14: "KART_ROYALE",
        15: "KART_STANDARD_YS",
        16: "KART_EGG_1",
        17: "KART_CUCUMBER",
        18: "KART_STANDARD_TD",
        19: "KART_MUSHMELLOW",
        20: "KART_FOUR_WHEEL_CRADLE",
        21: "KART_STANDARD_DK",
        22: "KART_WILDLIFE",
        23: "KART_RAMBI_RIDER",
        24: "KART_STANDARD_WR",
        25: "KART_BRUTE",
        26: "KART_DRAGONFLY",
        27: "KART_STANDARD_BW",
        28: "KART_HURRICANE",
        29: "KART_TYRANT",
        30: "KART_STANDARD_DS",
        31: "KART_LIGHT_DANCER",
        32: "KART_POWER_FLOWER",
        33: "KART_STANDARD_DB",
        34: "KART_DRY_BOMBER",
        35: "KART_BANISHER",
        36: "KART_STANDARD_WL",
        37: "KART_GOLD_MANTIS",
        38: "KART_ZIPPER",
        39: "KART_STANDARD_RB",
        40: "KART_ROB_BLS",
        41: "KART_ROB_LGS",
    },
    "ghost": {
        19: "COURSE_FIGURE_8_CIRCUIT",
        20: "COURSE_YOSHI_FALLS",
        21: "COURSE_CHEEP_CHEEP_BEACH",
        22: "COURSE_LUIGIS_MANSION",
        23: "COURSE_DESERT_HILLS",
        24: "COURSE_DELFINO_SQUARE",
        25: "COURSE_WALUIGI_PINBALL",
        26: "COURSE_SHROOM_RIDGE",
        27: "COURSE_DK_PASS",
        28: "COURSE_TICK_TOCK_CLOCK",
        29: "COURSE_MARIO_CIRCUIT",
        30: "COURSE_AIRSHIP_FORTRESS",
        31: "COURSE_WARIO_STADIUM",
        32: "COURSE_PEACH_GARDENS",
        33: "COURSE_BOWSER_CASTLE",
        34: "COURSE_RAINBOW_ROAD",
        35: "COURSE_SNES_MARIO_CIRCUIT_1",
        36: "COURSE_N64_MOO_MOO_FARM",
        37: "COURSE_GBA_PEACH_CIRCUIT",
        38: "COURSE_GCN_LUIGI_CIRCUIT",
        39: "COURSE_SNES_DONUT_PLAINS_1",
        40: "COURSE_N64_FRAPPE_SNOWLAND",
        41: "COURSE_GBA_BOWSER_CASTLE_2",
        42: "COURSE_GCN_BABY_PARK",
        43: "COURSE_SNES_KOOPA_BEACH_2",
        44: "COURSE_N64_CHOCO_MOUNTAIN",
        45: "COURSE_GBA_LUIGI_CIRCUIT",
        46: "COURSE_GCN_MUSHROOM_BRIDGE",
        47: "COURSE_SNES_CHOCO_ISLAND_2",
        48: "COURSE_N64_BANSHEE_BOARDWALK",
        49: "COURSE_GBA_SKY_GARDEN",
        50: "COURSE_GCN_YOSHI_CIRCUIT",
        51: "COURSE_FIGURE_8_CIRCUIT_2",
        52: "COURSE_YOSHI_FALLS_2",
        53: "COURSE_CHEEP_CHEEP_BEACH_2",
        54: "COURSE_LUIGIS_MANSION_2",
        55: "COURSE_DESERT_HILLS_2",
        56: "COURSE_DELFINO_SQUARE_2",
        57: "COURSE_WALUIGI_PINBALL_2",
        58: "COURSE_SHROOM_RIDGE_2",
        59: "COURSE_DK_PASS_2",
        60: "COURSE_TICK_TOCK_CLOCK_2",
        61: "COURSE_MARIO_CIRCUIT_2",
        62: "COURSE_AIRSHIP_FORTRESS_2",
        63: "COURSE_WARIO_STADIUM_2",
        64: "COURSE_PEACH_GARDENS_2",
        65: "COURSE_BOWSER_CASTLE_2",
        66: "COURSE_RAINBOW_ROAD_2",
        67: "COURSE_SNES_MARIO_CIRCUIT_1_2",
        68: "COURSE_N64_MOO_MOO_FARM_2",
        69: "COURSE_GBA_PEACH_CIRCUIT_2",
        70: "COURSE_GCN_LUIGI_CIRCUIT_2",
        71: "COURSE_SNES_DONUT_PLAINS_1_2",
        72: "COURSE_N64_FRAPPE_SNOWLAND_2",
        73: "COURSE_GBA_BOWSER_CASTLE_2_2",
        74: "COURSE_GCN_BABY_PARK_2",
        75: "COURSE_SNES_KOOPA_BEACH_2_2",
        76: "COURSE_N64_CHOCO_MOUNTAIN_2",
        77: "COURSE_GBA_LUIGI_CIRCUIT_2",
        78: "COURSE_GCN_MUSHROOM_BRIDGE_2",
        79: "COURSE_SNES_CHOCO_ISLAND_2_2",
        80: "COURSE_N64_BANSHEE_BOARDWALK_2",
        81: "COURSE_GBA_SKY_GARDEN_2",
        82: "COURSE_GCN_YOSHI_CIRCUIT_2",
    },
    "menu": {
        0: "BATTLE_BLOCK_FORT",
        1: "BATTLE_PIPE_PLAZA",
        2: "BATTLE_NINTENDO_DS",
        3: "BATTLE_TWILIGHT_HOUSE",
        4: "BATTLE_PALM_SHORE",
        5: "BATTLE_TART_TOP",
        6: "MODE_BALLOON_BATTLE",
        7: "MODE_SHINE_RUNNERS",
        8: "GHOST_TIME",
        9: "GHOST_GHOST_DATA",
        10: "GHOST_NONE",
        11: "GHOST_MY_GHOST_DATA",
        12: "GHOST_DOWNLOADED_GHOST_DATA",
        13: "GHOST_STAFF_GHOST_DATA",
    },
    "rule": {
        5: "ENGINE_50CC",
        6: "ENGINE_100CC",
        7: "ENGINE_150CC",
        8: "ENGINE_MIRROR",
        11: "CPU_EASY",
        12: "CPU_NORMAL",
        13: "CPU_HARD",
        14: "RULE_IN_ORDER",
        15: "RULE_RANDOM",
        16: "RULE_CHOOSE",
    },
}


# One enum block per semantic domain. Each entry is (type suffix, index
# ranges); ranges are half-open. Banks not listed keep a single
# MkdsBmg<Bank>Message enum. Indices left over from a larger or newer bank are
# appended to the Misc block so no message is lost.
DOMAINS: dict[str, tuple[tuple[str, tuple[tuple[int, int], ...]], ...]] = {
    "common": (
        ("FriendCode", ((7, 19),)),
        ("Ui", ((0, 7), (19, 20), (93, 110))),
        ("Character", ((20, 33),)),
        ("Duplicate", ((33, 35),)),
        ("Mode", ((35, 37),)),
        ("Cup", ((37, 45),)),
        ("Course", ((45, 77),)),
        ("Battle", ((77, 83),)),
        ("Engine", ((110, 114),)),
        ("Misc", ((83, 93), (114, 140))),
    ),
    "kart_select": (
        ("Stats", ((0, 6),)),
        ("Kart", ((6, 42),)),
    ),
    "ghost": (
        ("Ui", ((0, 19),)),
        ("Course", ((19, 51),)),
        ("RepeatedCourse", ((51, 83),)),
    ),
    "menu": (
        ("Battle", ((0, 6),)),
        ("BattleMode", ((6, 8),)),
        ("Ghost", ((8, 14),)),
        ("Misc", ((14, 23),)),
    ),
    "rule": (
        ("Label", ((0, 5),)),
        ("Engine", ((5, 9),)),
        ("Toggle", ((9, 11),)),
        ("Cpu", ((11, 14),)),
        ("Order", ((14, 17),)),
        ("Misc", ((17, 24),)),
    ),
}


def pick_sources(root: Path) -> dict[str, Path]:
    """One source per bank, preferring the US copy."""
    chosen: dict[str, Path] = {}
    for path in sorted(root.rglob("*.bmg")):
        bank = _bank_name(path)
        current = chosen.get(bank)
        if current is None:
            chosen[bank] = path
            continue
        # Prefer a US bank, then the shortest path (base archive).
        path_us = any("_us" in part for part in path.parts)
        current_us = any("_us" in part for part in current.parts)
        if path_us and not current_us:
            chosen[bank] = path
        elif path_us == current_us:
            if len(path.parts) < len(current.parts):
                chosen[bank] = path
    return chosen


def _domain_blocks(bank: str, count: int) -> list[tuple[str, list[int]]]:
    """Partition message indices into ordered semantic enum blocks."""
    spec = DOMAINS.get(bank)
    if not spec:
        return [("", list(range(count)))]

    assigned: set[int] = set()
    blocks: list[tuple[str, list[int]]] = []
    for suffix, ranges in spec:
        indices = sorted({
            index for start, stop in ranges
            for index in range(max(0, start), min(stop, count))
            if index not in assigned
        })
        if indices:
            blocks.append((suffix, indices))
            assigned.update(indices)

    remaining = [index for index in range(count) if index not in assigned]
    if remaining:
        for position, (suffix, indices) in enumerate(blocks):
            if suffix == "Misc":
                blocks[position] = ("Misc", sorted(set(indices) | set(remaining)))
                break
        else:
            blocks.append(("Misc", remaining))
    return blocks



def _stock_path(root: Path, explicit: Optional[str], candidates: tuple[str, ...],
                name: str) -> Optional[Path]:
    """Resolve an optional stock file, preferring known archive-relative paths."""
    if explicit:
        return Path(explicit)
    for relative in candidates:
        path = root / relative
        if path.is_file():
            return path
    matches = sorted(root.rglob(name))
    return matches[0] if matches else None


def read_mission_table(path: Path) -> tuple[int, int, list[int]]:
    """Read an NKMT mission table: magic, level count, slots per level, ids."""
    raw = path.read_bytes()
    if len(raw) < 8 or raw[:4] != b"NKMT":
        raise ValueError("not an NKMT mission table")
    levels, per_level = struct.unpack_from("<HH", raw, 4)
    count = levels * per_level
    if count == 0:
        raise ValueError("mission table has no slots")
    ids = list(raw[8:8 + count])
    if len(ids) != count:
        raise ValueError(f"mission table declares {count} slots but is short")
    return levels, per_level, ids




def _mission_task_label(text: str) -> str:
    """First readable word of a mission objective, used in the enum key."""
    clean = re.sub(r"<1A:[^>]*>", "", render_message(text))
    clean = clean.replace("\n", " ").replace("\r", " ")
    clean = re.sub(r"[^0-9A-Za-z]+", " ", clean).strip().upper()
    words = clean.split()
    if not words:
        return ""
    word = words[0]
    if word[0].isdigit() or len(word) > 20:
        return ""
    return word


def mission_key_overrides(messages: list[str],
                          mission_ids: list[int]) -> dict[int, str]:
    """Name mission enum keys by mission record and task, not message slot."""
    overrides: dict[int, str] = {}
    for slot, mission_id in enumerate(mission_ids[:len(messages)]):
        key = f"MR{mission_id}"
        task = _mission_task_label(messages[slot])
        if task:
            key += f"_{task}"
        overrides[slot] = key
    return overrides


def mission_slots(root: Path, mtbl: Optional[str]) -> list[int]:
    """Return menu-slot -> mission-id mapping when the stock table exists."""
    mtbl_path = _stock_path(
        root, mtbl,
        ("Main2D_arc/missionTable.mtbl",
         "data/Main2D_arc/missionTable.mtbl"),
        "missionTable.mtbl")
    if mtbl_path is None:
        return []
    try:
        _, _per_level, ids = read_mission_table(mtbl_path)
    except (OSError, ValueError):
        return []
    return ids


def _enum_lines(prefix: str, ident: str, index: int) -> list[str]:
    return [f"    {prefix}{ident} = {index},"]


def emit_bank(bank: str, source: Path, relative: Path,
              key_overrides: Optional[dict[int, str]] = None) -> str:
    data = source.read_bytes()
    messages = Bmg(data).strings
    enum_base = "MkdsBmg" + "".join(part.title() for part in bank.split("_"))
    prefix = "MKDS_BMG_" + bank.upper() + "_"
    used: dict[str, int] = {}
    header = [
        f"/* {bank}.h — message ids for {relative.as_posix()}. "
        "SPDX-License-Identifier: MIT */",
        "#pragma once",
        "",
    ]
    for suffix, indices in _domain_blocks(bank, len(messages)):
        type_name = f"{enum_base}{suffix}Message"
        header.append("typedef enum {")
        for index in indices:
            text = messages[index]
            ident = (key_overrides or {}).get(index) or _identifier(text, index)
            count = used.get(ident, 0) + 1
            used[ident] = count
            if count > 1:
                ident = f"{ident}_{count}"
            header.extend(_enum_lines(prefix, ident, index))
        header.append(f"}} {type_name};")
        header.append("")
    header.extend([
        f"#define MKDS_BMG_{bank.upper()}_COUNT {len(messages)}u",
        "",
    ])
    return "\n".join(header)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", help="directory tree containing .bmg files")
    parser.add_argument("-o", "--output", required=True,
                        help="header directory, for example include/nitro/mkds/bmg")
    parser.add_argument(
        "--missions-mtbl",
        help="NKMT mission table (default: <root>/Main2D_arc/missionTable.mtbl)")
    args = parser.parse_args(argv)

    root = Path(args.root)
    outdir = Path(args.output)
    sources = pick_sources(root)
    if not sources:
        parser.error(f"no .bmg files under {root}")

    mission_ids = mission_slots(root, args.missions_mtbl)
    key_overrides = {bank: dict(table) for bank, table in KEY_OVERRIDES.items()}
    if "mission" in sources and mission_ids:
        mission_messages = Bmg(sources["mission"].read_bytes()).strings
        key_overrides["mission"] = mission_key_overrides(
            mission_messages, mission_ids)
    outdir.mkdir(parents=True, exist_ok=True)
    includes = []
    errors = []
    for bank, source in sorted(sources.items()):
        relative = source.relative_to(root)
        try:
            text = emit_bank(bank, source, relative,
                             key_overrides.get(bank))
        except (OSError, BmgError) as exc:
            errors.append((relative, exc))
            continue
        (outdir / f"{bank}.h").write_text(text, encoding="utf-8")
        includes.append(bank)

    umbrella = [
        "/* bmg_messages.h — all generated BMG message ids. "
        "SPDX-License-Identifier: MIT */",
        "#pragma once",
        "",
    ]
    umbrella.extend(f'#include "nitro/mkds/bmg/{bank}.h"' for bank in includes)
    umbrella.append("")
    (outdir.parent / "bmg_messages.h").write_text("\n".join(umbrella),
                                                   encoding="utf-8")

    print(f"{len(includes)} BMG message headers -> {outdir}")
    for relative, exc in errors:
        print(f"error: {relative}: {exc}", file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
