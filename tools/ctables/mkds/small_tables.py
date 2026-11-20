# Mario Kart DS Modding Trove
# tools/ctables/mkds/small_tables.py — typed C emitters for the small MKDS tables
# SPDX-License-Identifier: MIT
"""Emit complete C programs that rebuild the small MKDS binary tables.

Every emitter returns source text with a ``main`` that writes the rebuilt file
to ``argv[1]``. The source uses the real headers under ``include/nitro/mkds``,
designated initializers, semantic field types and ``static const`` tables.

The emitters preserve the bytes they are given. They do not repair inconsistent
headers: a stored file size or count is written back exactly as parsed, so a
malformed-but-parseable file can still round-trip. Structurally unrepresentable
input (truncated rows, a short staff-time table, a truncated item block) raises
``ValueError``.

No stock data lives in this module. Callers pass the original bytes in; tests use
small synthetic fixtures.
"""
from __future__ import annotations

import struct
from typing import Callable

from tools.ctables.common.cnames import enum_name

# ---------------------------------------------------------------------------
# C source helpers
# ---------------------------------------------------------------------------

_BANNER = ["/* {title}. SPDX-License-Identifier: MIT */"]

_MAIN = [
    "int main(int argc, char **argv)",
    "{",
    "    if (argc != 2) {",
    "        return 2;",
    "    }",
    "    FILE *out = fopen(argv[1], \"wb\");",
    "    if (out == NULL) {",
    "        return 3;",
    "    }",
    "    if (!write_table(out)) {",
    "        fclose(out);",
    "        return 4;",
    "    }",
    "    if (fclose(out) != 0) {",
    "        return 5;",
    "    }",
    "    return 0;",
    "}",
]


def _program_loop(title: str, headers: list[str], statics: list[str],
                  body: list[str]) -> str:
    """Build a program whose writer body is supplied verbatim."""
    lines = [line.format(title=title) for line in _BANNER]
    lines.append("")
    lines.append("#include <stdio.h>")
    for header in headers:
        lines.append(f'#include "{header}"')
    lines.append("")
    lines.extend(statics)
    lines.append("")
    lines.append("static int write_table(FILE *out)")
    lines.append("{")
    lines.extend(body)
    lines.append("    return 1;")
    lines.append("}")
    lines.append("")
    lines.extend(_MAIN)
    lines.append("")
    return "\n".join(lines)


def _program(title: str, headers: list[str], statics: list[str],
             writes: list[tuple[str, str, int]]) -> str:
    lines = [line.format(title=title) for line in _BANNER]
    lines.append("")
    lines.append("#include <stdio.h>")
    for header in headers:
        lines.append(f'#include "{header}"')
    lines.append("")
    lines.extend(statics)
    lines.append("")
    lines.append("static int write_table(FILE *out)")
    lines.append("{")
    for pointer, size, count in writes:
        lines.append(
            f"    if (fwrite({pointer}, {size}, {count}, out) != {count}) {{")
        lines.append("        return 0;")
        lines.append("    }")
    lines.append("    return 1;")
    lines.append("}")
    lines.append("")
    lines.extend(_MAIN)
    lines.append("")
    return "\n".join(lines)


def _char_literal(byte: int) -> str:
    if byte == 0:
        return "'\\0'"
    if byte == 0x27:
        return "'\\''"
    if byte == 0x5C:
        return "'\\\\'"
    if 0x20 <= byte <= 0x7E:
        return f"'{chr(byte)}'"
    return f"'\\x{byte:02x}'"


def _char_array(raw: bytes) -> str:
    return "{" + ", ".join(_char_literal(byte) for byte in raw) + "}"


def _bytes_field(raw: bytes) -> str:
    return "{" + ", ".join(f"0x{byte:02X}" for byte in raw) + "}"


def _c_string(raw: bytes) -> str:
    chunks: list[str] = []
    for byte in raw:
        if byte == 0x22:
            chunks.append('\\"')
        elif byte == 0x5C:
            chunks.append("\\\\")
        elif 0x20 <= byte < 0x7F:
            chunks.append(chr(byte))
        else:
            chunks.append(f"\\{byte:03o}")
    return '"' + "".join(chunks) + '"'


def _name_initializer(raw: bytes) -> str:
    """Use a string literal only when the bytes are a NUL-padded C string."""
    nul = raw.find(b"\0")
    if nul >= 0 and all(byte == 0 for byte in raw[nul:]):
        return _c_string(raw[:nul])
    return "{" + ", ".join(f"0x{byte:02x}" for byte in raw) + "}"


def _hex_offset(offset: int) -> str:
    return f"0x{offset:02X}"


def _check_length(data: bytes, minimum: int, what: str) -> None:
    if len(data) < minimum:
        raise ValueError(f"{what}: need at least {minimum} bytes, got {len(data)}")


def _named(value: int, type_name: str) -> str:
    return enum_name(type_name, value) or str(value)


def _ms_text(milliseconds: int) -> str:
    """Format whole milliseconds as m:ss.mmm."""
    minutes, rem = divmod(milliseconds, 60000)
    seconds, millis = divmod(rem, 1000)
    return f"{minutes}:{seconds:02d}.{millis:03d}"


def _frames_text(frames: int) -> str:
    """Format a 60 Hz frame count as m:ss.mmm."""
    return _ms_text((frames * 1000 + 30) // 60)




# ---------------------------------------------------------------------------
# ranktimeGP.rtt — MkdsRankTimeHeader + MkdsRankTimeCourse
# ---------------------------------------------------------------------------

_RANK_TIME_HEADER = struct.Struct("<4sI10H")
_RANK_TIME_COURSE = struct.Struct("<BBHHH")
_RANK_TIME_HEADER_SIZE = 28
_RANK_TIME_COURSE_SIZE = 8


class RankTimeTable:
    """NKTT: 28-byte header followed by 8-byte course rows."""

    @staticmethod
    def emit_source(data: bytes) -> str:
        _check_length(data, _RANK_TIME_HEADER_SIZE, "NKTT")
        payload = len(data) - _RANK_TIME_HEADER_SIZE
        if payload % _RANK_TIME_COURSE_SIZE:
            raise ValueError(
                "NKTT: payload is not a whole number of 8-byte course rows")
        (magic, file_size, course_count, time_delta_weight,
         first_place_weight, start_boost_points, power_slide_points,
         item_hit_points, off_road_divisor, wall_hit_points, damage_points,
         respawn_points) = _RANK_TIME_HEADER.unpack_from(data, 0)
        count = payload // _RANK_TIME_COURSE_SIZE

        statics = [
            "static const MkdsRankTimeHeader rank_time_header = {",
            f"    .magic = {_char_array(magic)},",
            f"    .file_size = {file_size},",
            f"    .course_count = {course_count},",
            f"    .time_delta_factor = {time_delta_weight},",
            f"    .first_place_factor = {first_place_weight},",
            f"    .start_boost_points = {start_boost_points},",
            f"    .power_slide_points = {power_slide_points},",
            f"    .item_hit_points = {item_hit_points},",
            f"    .off_road_time_divisor = {off_road_divisor},",
            f"    .wall_hit_points = {wall_hit_points},",
            f"    .damage_points = {damage_points},",
            f"    .respawn_points = {respawn_points},",
            "};",
        ]
        writes: list[tuple[str, str, int]] = [
            ("&rank_time_header", "sizeof rank_time_header", 1)]

        if count:
            statics.append("")
            statics.append(
                f"static const MkdsRankTimeCourse course_table[{count}] = {{")
            for index in range(count):
                offset = _RANK_TIME_HEADER_SIZE + index * _RANK_TIME_COURSE_SIZE
                (course_id, reserved_01, frames_50cc, frames_100cc,
                 frames_150cc) = _RANK_TIME_COURSE.unpack_from(data, offset)
                slot_name = enum_name("MkdsRankTimeSlot", index) or str(index)
                statics.extend([
                    f"    [{slot_name}] = {{",
                    f"        .course_id = "
                    f"{_named(course_id, 'MkdsRaceCourse')},",
                    f"        .reserved_01 = {reserved_01},",
                    f"        .target_frames_50cc = {frames_50cc},",
                    f"        .target_frames_100cc = {frames_100cc},",
                    f"        .target_frames_150cc = {frames_150cc},",
                    "    },",
                ])
            statics.append("};")
            writes.append(("course_table", "sizeof course_table[0]", count))

        return _program("NKTT rank-time table", ["nitro/mkds/race/ranktime.h"],
                        statics, writes)


# ---------------------------------------------------------------------------
# rankpoint.rpt — MkdsRankPointHeader + MkdsRankPointRow
# ---------------------------------------------------------------------------

_RANK_POINT_HEADER = struct.Struct("<4sI")
_RANK_POINT_ROW = struct.Struct("<8B")
_RANK_POINT_HEADER_SIZE = 8
_RANK_POINT_ROW_SIZE = 8


class RankPointTable:
    """NKPT: 8-byte header followed by 8-byte place-point rows."""

    @staticmethod
    def emit_source(data: bytes) -> str:
        _check_length(data, _RANK_POINT_HEADER_SIZE, "NKPT")
        payload = len(data) - _RANK_POINT_HEADER_SIZE
        if payload % _RANK_POINT_ROW_SIZE:
            raise ValueError(
                "NKPT: payload is not a whole number of 8-byte rows")
        magic, file_size = _RANK_POINT_HEADER.unpack_from(data, 0)
        count = payload // _RANK_POINT_ROW_SIZE

        statics = [
            "static const MkdsRankPointHeader rank_point_header = {",
            f"    .magic = {_char_array(magic)},",
            f"    .file_size = {file_size},",
            "};",
        ]
        writes: list[tuple[str, str, int]] = [
            ("&rank_point_header", "sizeof rank_point_header", 1)]

        if count:
            statics.append("")

            statics.append(
                f"static const MkdsRankPointRow point_rows[{count}] = {{")
            for index in range(count):
                offset = _RANK_POINT_HEADER_SIZE + index * _RANK_POINT_ROW_SIZE
                values = _RANK_POINT_ROW.unpack_from(data, offset)
                if index == 0:
                    designator = "MKDS_RANK_POINT_ROW_GP"
                elif index < 8:
                    designator = f"MKDS_RANK_POINT_ROW_NO_TEAMS({9 - index})"
                elif index < 15:
                    designator = f"MKDS_RANK_POINT_ROW_TEAMS_SMALL({16 - index})"
                else:
                    designator = f"MKDS_RANK_POINT_ROW_TEAMS_FULL({23 - index})"
                statics.append(f"    [{designator}] = {{")
                statics.append("        .place_points = {")
                for place, value in enumerate(values):
                    place_name = enum_name("MkdsRankPointPlace", place) or place
                    statics.append(f"            [{place_name}] = {value},")
                statics.append("        },")
                statics.append("    },")
            statics.append("};")
            writes.append(("point_rows", "sizeof point_rows[0]", count))

        return _program("NKPT rank-point table", ["nitro/mkds/race/rankpoint.h"],
                        statics, writes)


# ---------------------------------------------------------------------------
# mission.mr — MkdsMissionHeader + MkdsMissionEntry
# ---------------------------------------------------------------------------

_MISSION_HEADER = struct.Struct("<4sI")
_MISSION_ENTRY = struct.Struct("<HHh10BHH4HHBB12s")
_MISSION_HEADER_SIZE = 8
_MISSION_ENTRY_SIZE = 44

_MISSION_TASKS = {
    0: "MKDS_MISSION_TASK_GATES",
    1: "MKDS_MISSION_TASK_COINS",
    2: "MKDS_MISSION_TASK_LAPS",
    3: "MKDS_MISSION_TASK_DESTROY",
    4: "MKDS_MISSION_TASK_POWER_SLIDES",
    5: "MKDS_MISSION_TASK_NONE",
    6: "MKDS_MISSION_TASK_FINISH_BEFORE",
    7: "MKDS_MISSION_TASK_BOSS",
    8: "MKDS_MISSION_TASK_RESERVED_8",
    9: "MKDS_MISSION_TASK_RESERVED_9",
    10: "MKDS_MISSION_TASK_RESERVED_10",
}

_ENGINE_CLASSES = {
    0: "MKDS_ENGINE_50CC",
    1: "MKDS_ENGINE_100CC",
    2: "MKDS_ENGINE_150CC",
    3: "MKDS_ENGINE_MIRROR",
}

_MISSION_FLAG_BITS = (
    (0, "no_forward"),
    (1, "no_damage"),
    (2, "no_wall_hit"),
    (3, "no_respawn"),
    (4, "mirror"),
    (5, "backwards"),
)


def _name_text(raw: bytes) -> str:
    return raw.split(b"\0", 1)[0].decode("ascii", "replace")


def _mission_flags(raw: int) -> str:
    if raw & 0xFFC0:
        return (f"        .flags = {{ .raw = 0x{raw:04X} }},"
                "  /* reserved bits preserved */")
    set_bits = [name for bit, name in _MISSION_FLAG_BITS if raw & (1 << bit)]
    if not set_bits:
        return "        .flags = { .raw = 0x0000 },"
    body = ", ".join(f".{name} = 1" for name in set_bits)
    return f"        .flags = {{ .bits = {{ {body} }} }},"


class MissionTable:
    """NKMR: 8-byte header followed by 44-byte mission entries."""

    @staticmethod
    def emit_source(data: bytes) -> str:
        _check_length(data, _MISSION_HEADER_SIZE, "NKMR")
        payload = len(data) - _MISSION_HEADER_SIZE
        if payload % _MISSION_ENTRY_SIZE:
            raise ValueError(
                "NKMR: payload is not a whole number of 44-byte entries")
        magic, entry_count = _MISSION_HEADER.unpack_from(data, 0)
        count = payload // _MISSION_ENTRY_SIZE

        statics = [
            "static const MkdsMissionHeader mission_header = {",
            f"    .magic = {_char_array(magic)},",
            f"    .entry_count = {entry_count},",
            "};",
        ]
        writes: list[tuple[str, str, int]] = [
            ("&mission_header", "sizeof mission_header", 1)]

        if count:
            parsed = [
                _MISSION_ENTRY.unpack_from(
                    data, _MISSION_HEADER_SIZE + index * _MISSION_ENTRY_SIZE)
                for index in range(count)
            ]
            ids = [entry[3] for entry in parsed]
            max_id = max(ids)
            statics.append("")
            statics.append(
                f"static const MkdsMissionEntry mission_entries[{max_id + 1}] = {{")
            for index in range(count):
                offset = _MISSION_HEADER_SIZE + index * _MISSION_ENTRY_SIZE
                fields = _MISSION_ENTRY.unpack_from(data, offset)
                (time_limit, target_time, rank_delta_scale, mission_id, task,
                 course_id, engine_class, character_id, kart_id, menu_id,
                 reserved_0d, camera_index, target_value, win_delay,
                 reserved_12, object_0, object_1, object_2, object_3, flags,
                 enemy_character, enemy_kart, name) = fields
                task_text = _MISSION_TASKS.get(task, str(task))
                engine_text = _ENGINE_CLASSES.get(engine_class,
                                                  str(engine_class))
                character_text = _named(character_id, 'MkdsCharacter')
                enemy_character_text = (
                    enum_name('MkdsCharacter', 0xFF) or "0xFF"
                    if enemy_character == 0xFF
                    else _named(enemy_character, 'MkdsCharacter'))
                enemy_kart_text = (
                    enum_name('MkdsKart', 0xFF) or "0xFF"
                    if enemy_kart == 0xFF
                    else _named(enemy_kart, 'MkdsKart'))
                mission_name = enum_name("MkdsMission", mission_id)
                designator = mission_name if mission_name else str(mission_id)
                statics.extend([
                    f"    [{designator}] = {{",
                    f"        .time_limit = {time_limit},",
                    f"        .target_time = {target_time},",
                    f"        .rank_delta_scale = {rank_delta_scale},",
                    f"        .mission_id = {mission_id},",
                    f"        .task = {task_text},",
                    f"        .course_id = {_named(course_id, 'MkdsMissionCourse')},",
                    f"        .engine_class = {engine_text},",
                    f"        .character_id = {character_text},",
                    f"        .kart_id = {_named(kart_id, 'MkdsKart')},",
                    f"        .menu_index = {menu_id},",
                    f"        .reserved_0d = {reserved_0d},",
                    f"        .camera_index = "
                    f"{_named(camera_index, 'MkdsMissionCamera')},",
                    f"        .target_value = {target_value},",
                    f"        .win_delay = {win_delay},",
                    f"        .reserved_12 = {reserved_12},",
                    "        .object_ids = {"
                    f"{_named(object_0, 'MkdsMapObject')}, "
                    f"{_named(object_1, 'MkdsMapObject')}, "
                    f"{_named(object_2, 'MkdsMapObject')}, "
                    f"{_named(object_3, 'MkdsMapObject')}"
                    "},",
                    _mission_flags(flags),
                    f"        .enemy_character = {enemy_character_text},",
                    f"        .enemy_kart = {enemy_kart_text},",
                    f"        .name = {_name_initializer(name)},",
                    "    },",
                ])
            statics.append("};")
            rendered_ids = ", ".join(str(value) for value in ids)
            statics.extend([
                "",
                f"static const uint8_t mission_entry_ids[{count}] = "
                f"{{ {rendered_ids} }};",
            ])
            body = [
                "    if (fwrite(&mission_header, sizeof mission_header, 1, out) != 1)",
                "        return 0;",
                "",
                "    size_t i;",
                "",
                "    for (i = 0; i < sizeof mission_entry_ids / "
                "sizeof mission_entry_ids[0]; i++) {",
                "        const MkdsMissionEntry *row = "
                "&mission_entries[mission_entry_ids[i]];",
                "        if (fwrite(row, sizeof *row, 1, out) != 1)",
                "            return 0;",
                "    }",
            ]
            return _program_loop("NKMR mission table",
                                 ["nitro/mkds/common/ids.h", "nitro/mkds/race/mission.h"],
                                 statics, body)

        return _program("NKMR mission table", ["nitro/mkds/race/mission.h"],
                        statics, writes)


# ---------------------------------------------------------------------------
# missionTable.mtbl — MkdsMissionMenuHeader + MkdsMissionId ids
# ---------------------------------------------------------------------------

_MISSION_MENU_HEADER = struct.Struct("<4sHH")
_MISSION_MENU_HEADER_SIZE = 8


class MissionMenuTable:
    """NKMT: 8-byte header followed by one mission id per menu slot."""

    @staticmethod
    def emit_source(data: bytes) -> str:
        _check_length(data, _MISSION_MENU_HEADER_SIZE, "NKMT")
        magic, level_count, missions_per_level = (
            _MISSION_MENU_HEADER.unpack_from(data, 0))
        ids = data[_MISSION_MENU_HEADER_SIZE:]
        count = len(ids)

        statics = [
            "static const MkdsMissionMenuHeader mission_menu_header = {",
            f"    .magic = {_char_array(magic)},",
            f"    .level_count = {level_count},",
            f"    .missions_per_level = {missions_per_level},",
            "};",
        ]
        writes: list[tuple[str, str, int]] = [
            ("&mission_menu_header", "sizeof mission_menu_header", 1)]

        if count:
            statics.append("")
            statics.append(
                f"static const MkdsMissionId menu_ids[{count}] = {{")
            for slot, mission_id in enumerate(ids):
                slot_name = enum_name("MkdsMissionMenuSlot", slot)
                mission_name = enum_name("MkdsMission", mission_id)
                if slot_name and mission_name:
                    statics.append(
                        f"    [{slot_name}] = {mission_name},")
                else:
                    statics.append(f"    [{slot}] = {mission_id},")
            statics.append("};")
            writes.append(("menu_ids", "sizeof menu_ids[0]", count))

        return _program("NKMT mission menu table", ["nitro/mkds/race/mission.h"],
                        statics, writes)


# ---------------------------------------------------------------------------
# ItemSlotList.dat — block count byte + MkdsItemSlotBlockHeader + weights
# ---------------------------------------------------------------------------

_ITEM_COLUMN_SYMBOLS = (
    "MKDS_ITEM_SLOT_GREEN_SHELL",
    "MKDS_ITEM_SLOT_RED_SHELL",
    "MKDS_ITEM_SLOT_BANANA",
    "MKDS_ITEM_SLOT_FAKE_ITEM_BOX",
    "MKDS_ITEM_SLOT_MUSHROOM",
    "MKDS_ITEM_SLOT_TRIPLE_MUSHROOM",
    "MKDS_ITEM_SLOT_BOMB",
    "MKDS_ITEM_SLOT_BLUE_SHELL",
    "MKDS_ITEM_SLOT_LIGHTNING",
    "MKDS_ITEM_SLOT_TRIPLE_GREEN_SHELL",
    "MKDS_ITEM_SLOT_TRIPLE_BANANA",
    "MKDS_ITEM_SLOT_TRIPLE_RED_SHELL",
    "MKDS_ITEM_SLOT_STAR",
    "MKDS_ITEM_SLOT_GOLDEN_MUSHROOM",
    "MKDS_ITEM_SLOT_BULLET_BILL",
    "MKDS_ITEM_SLOT_BLOOPER",
    "MKDS_ITEM_SLOT_BOO",
    "MKDS_ITEM_SLOT_ITEM_BOX",
)


class ItemSlotTable:
    """ItemSlotList: 1-byte block count, then typed block headers and weights."""

    @staticmethod
    def emit_source(data: bytes) -> str:
        _check_length(data, 1, "ItemSlotList")
        block_total = data[0]
        blocks: list[tuple[int, int, bytes, int]] = []
        position = 1
        while position < len(data):
            if position + 2 > len(data):
                raise ValueError(
                    "ItemSlotList: truncated block header at "
                    f"+{_hex_offset(position)}")
            slots = data[position]
            columns = data[position + 1]
            block_offset = position
            position += 2
            length = slots * columns
            if position + length > len(data):
                raise ValueError(
                    "ItemSlotList: truncated weight payload at "
                    f"+{_hex_offset(position)} (need {length} bytes)")
            blocks.append((slots, columns, data[position:position + length],
                           block_offset))
            position += length

        statics = [
            f"static const uint8_t block_total = {block_total};",
        ]
        writes: list[tuple[str, str, int]] = [
            ("&block_total", "sizeof block_total", 1)]

        for index, (slots, columns, weights, block_offset) in enumerate(blocks):
            statics.append("")
            statics.extend([
                f"static const MkdsItemSlotBlockHeader block_{index}_header = {{",
                f"    .slot_count = {slots},",
                f"    .column_count = {columns},",
                "};",
            ])
            writes.append((f"&block_{index}_header",
                           f"sizeof block_{index}_header", 1))
            if slots and columns:
                statics.append("")
                statics.append(
                    f"static const MkdsItemSlotWeight block_{index}_weights"
                    f"[{columns}][{slots}] = {{")
                for column in range(columns):
                    if columns == len(_ITEM_COLUMN_SYMBOLS):
                        designator = f"[{_ITEM_COLUMN_SYMBOLS[column]}]"
                    else:
                        designator = f"[{column}]"
                    start = column * slots
                    values = ", ".join(
                        str(byte) for byte in weights[start:start + slots])
                    statics.append(f"        {designator} = {{{values}}},")
                statics.append("};")
                writes.append((f"block_{index}_weights",
                               f"sizeof block_{index}_weights", 1))

        return _program("ItemSlotList weight blocks",
                        ["nitro/mkds/race/itemslots.h"], statics, writes)


# ---------------------------------------------------------------------------
# staff_ghost_time.bin — MkdsStaffGhostTimes
# ---------------------------------------------------------------------------

_STAFF_TIME_SLOTS = 40
_STAFF_TIME_SIZE = 160

# ranktimeGP.rtt table slot -> race course id. The cup order index is
# (slot + 16) mod 32, so this also gives every staff-time course its cup.
_RANK_TIME_COURSE_IDS = (
    10, 11, 13, 14, 35, 16, 12, 9, 15, 36, 37, 38, 39, 23, 40, 1,
    20, 22, 31, 18, 27, 28, 33, 24, 30, 17, 25, 19, 34, 26, 32, 29,
)
_RACE_COURSE_CUP_ORDER = {
    course: (slot + 16) % 32
    for slot, course in enumerate(_RANK_TIME_COURSE_IDS)
}
_CUP_NAMES = ("Mushroom", "Flower", "Star", "Special",
              "Shell", "Banana", "Leaf", "Lightning")


def _course_position(course: int) -> str:
    order = _RACE_COURSE_CUP_ORDER.get(course)
    if order is None:
        return "non-cup/test course"
    return f"{_CUP_NAMES[order // 4]} cup race {order % 4 + 1}"


class StaffGhostTimes:
    """160-byte table of 40 little-endian millisecond thresholds."""

    @staticmethod
    def emit_source(data: bytes) -> str:
        if len(data) != _STAFF_TIME_SIZE:
            raise ValueError(
                "staff_ghost_time.bin: expected 160 bytes, "
                f"got {len(data)}")
        values = struct.unpack("<40I", data)

        statics = [
            "static const MkdsStaffGhostTimes staff_ghost_times = {",
            "    .threshold_ms = {",
        ]
        for index, value in enumerate(values):
            course = index + 1
            race_name = enum_name("MkdsRaceCourse", course)
            designator = (f"[MKDS_STAFF_TIME_SLOT({race_name})]"
                          if race_name else f"[{index}]")
            statics.append(f"        {designator} = {value},")
        statics.extend([
            "    },",
            "};",
        ])
        writes: list[tuple[str, str, int]] = [
            ("&staff_ghost_times", "sizeof staff_ghost_times", 1)]
        return _program("staff_ghost_time thresholds",
                        ["nitro/mkds/race/staffghost.h"], statics, writes)


# ---------------------------------------------------------------------------
# grpconf.tbl — MkdsObjectGroupConfig records
# ---------------------------------------------------------------------------

_GRPCONF_RECORD = struct.Struct("<8H")


class ObjectGroupTable:
    """16-byte object render/collision profiles, keyed by NKM object id."""

    @staticmethod
    def emit_source(data: bytes) -> str:
        if len(data) % _GRPCONF_RECORD.size:
            raise ValueError(
                "grpconf.tbl: payload is not a whole number of 16-byte rows")
        count = len(data) // _GRPCONF_RECORD.size
        records = [
            _GRPCONF_RECORD.unpack_from(data, index * _GRPCONF_RECORD.size)
            for index in range(count)
        ]
        max_id = max(record[0] for record in records)
        statics = [
            "/* sparse by object id; grpconf_ids preserves file order */",
            f"static const MkdsObjectGroupConfig grpconf_table[{max_id + 1}] = {{",
        ]
        for (object_id, model_kind, near_clip, far_clip, collision_shape,
             width, height, depth) in records:
            model_text = _named(model_kind, "MkdsObjectModelKind")
            collision_text = _named(collision_shape, "MkdsObjectCollisionShape")
            object_name = enum_name("MkdsMapObject", object_id)
            designator = object_name if object_name else str(object_id)
            statics.extend([
                f"    [{designator}] = {{",
                f"        .object_id = {object_id},",
                f"        .model_kind = {model_text},",
                f"        .near_clip = {near_clip},",
                f"        .far_clip = {far_clip},",
                f"        .collision_shape = {collision_text},",
                f"        .width = {width},",
                f"        .height = {height},",
                f"        .depth = {depth},",
                "    },",
            ])
        statics.append("};")
        ids = ", ".join(str(record[0]) for record in records)
        statics.extend([
            "",
            f"static const uint16_t grpconf_ids[{count}] = {{ {ids} }};",
        ])
        body = [
            "    size_t i;",
            "",
            "    for (i = 0; i < sizeof grpconf_ids / sizeof grpconf_ids[0]; i++) {",
            "        const MkdsObjectGroupConfig *row = &grpconf_table[grpconf_ids[i]];",
            "        if (fwrite(row, sizeof *row, 1, out) != 1)",
            "            return 0;",
            "    }",
        ]
        return _program_loop("grpconf object group profiles",
                             ["nitro/mkds/common/ids.h", "nitro/mkds/race/grpconf.h"],
                             statics, body)


# ---------------------------------------------------------------------------
# kart_appear.ktbl — NKKT kart/character unlock matrix
# ---------------------------------------------------------------------------

def _enum_or_index(type_name: str, value: int) -> str:
    name = enum_name(type_name, value)
    return name if name else str(value)


class KartAppearanceTable:
    """6-byte header plus 37 rows of 13 one-byte unlock levels."""

    @staticmethod
    def emit_source(data: bytes) -> str:
        if len(data) < 6:
            raise ValueError("kart_appear.ktbl: truncated header")
        magic = data[:4]
        kart_count, character_count = data[4], data[5]
        payload = len(data) - 6
        if payload % 13:
            raise ValueError(
                "kart_appear.ktbl: payload is not a whole number of 13-byte rows")
        rows = payload // 13

        statics = [
            "static const MkdsKartAppearanceHeader kart_appearance_header = {",
            f"    .magic = {_char_array(magic)},",
            f"    .kart_count = {kart_count},",
            f"    .character_count = {character_count},",
            "};",
            "",
            f"static const MkdsKartAppearanceRow kart_appearance_rows[{rows}] = {{",
        ]
        for kart in range(rows):
            designator = _enum_or_index("MkdsKart", kart)
            values = data[6 + kart * 13:6 + (kart + 1) * 13]
            statics.append(f"    [{designator}] = {{")
            statics.append("        .character_level = {")
            for character, value in enumerate(values):
                char_name = _enum_or_index("MkdsCharacter", character)
                level = _named(value, "MkdsKartAppearanceLevel")
                statics.append(f"            [{char_name}] = {level},")
            statics.append("        },")
            statics.append("    },")
        statics.append("};")
        writes = [
            ("&kart_appearance_header", "sizeof kart_appearance_header", 1),
            ("kart_appearance_rows", "sizeof kart_appearance_rows[0]", rows),
        ]
        return _program("NKKT kart appearance matrix",
                        ["nitro/mkds/common/ids.h", "nitro/mkds/race/kartappear.h"],
                        statics, writes)


# ---------------------------------------------------------------------------
# emblem_s.tbl — emblem editor stamp placements
# ---------------------------------------------------------------------------

_EMBLEM_STAMP = struct.Struct("<hhHH")


class EmblemStampTable:
    """4-byte count, 50 placement records and a 6-byte zero trailer."""

    @staticmethod
    def emit_source(data: bytes) -> str:
        if len(data) < 4:
            raise ValueError("emblem_s.tbl: truncated header")
        count = struct.unpack_from("<I", data, 0)[0]
        records = count
        if 4 + records * _EMBLEM_STAMP.size > len(data):
            raise ValueError("emblem_s.tbl: record count exceeds the file")
        trailer = data[4 + records * _EMBLEM_STAMP.size:]
        if records != 50 or len(trailer) != 6:
            raise ValueError(
                "emblem_s.tbl: only the 50-record stock layout is modelled")

        statics = [
            f"static const uint32_t emblem_stamp_count = {count};",
            f"static const MkdsEmblemStampPlacement "
            f"emblem_stamps[{records}] = {{",
        ]
        for index in range(records):
            x, y, kind, stamp_id = _EMBLEM_STAMP.unpack_from(
                data, 4 + index * _EMBLEM_STAMP.size)
            slot_name = enum_name("MkdsEmblemStampSlot", index) or str(index)
            statics.extend([
                f"    [{slot_name}] = {{",
                f"        .x = {x},",
                f"        .y = {y},",
                f"        .kind = {kind},",
                f"        .stamp_id = {stamp_id},",
                "    },",
            ])
        statics.append("};")
        statics.extend([
            "",
            f"static const uint8_t emblem_stamp_trailer[{len(trailer)}] = "
            f"{_bytes_field(trailer)};",
        ])
        writes = [
            ("&emblem_stamp_count", "sizeof emblem_stamp_count", 1),
            ("emblem_stamps", "sizeof emblem_stamps[0]", records),
            ("emblem_stamp_trailer", "sizeof emblem_stamp_trailer", 1),
        ]
        return _program("emblem editor stamp table",
                        ["nitro/mkds/files/emblemtable.h"], statics, writes)


# ---------------------------------------------------------------------------
# emblem2.bin — 32 x 32 4bpp linear bitmap
# ---------------------------------------------------------------------------

class EmblemBitmapTable:
    """512-byte 4bpp emblem bitmap, 32 rows of 16 bytes."""

    @staticmethod
    def emit_source(data: bytes) -> str:
        if len(data) != 512:
            raise ValueError(
                f"emblem2.bin: expected 512 bytes, got {len(data)}")
        statics = [
            "static const MkdsEmblemBitmap emblem = {",
            "    .rows = {",
        ]
        for row in range(32):
            values = ", ".join(
                f"0x{byte:02X}"
                for byte in data[row * 16:(row + 1) * 16])
            statics.append(f"        {{{values}}},")
        statics.extend(["    },", "};"])
        writes = [("&emblem", "sizeof emblem", 1)]
        return _program("emblem2 bitmap",
                        ["nitro/mkds/files/misc.h"], statics, writes)


# ---------------------------------------------------------------------------
# builddate.bin — 30-byte ASCII build stamp
# ---------------------------------------------------------------------------

class BuildDateTable:
    """30 ASCII bytes with no NUL terminator."""

    @staticmethod
    def emit_source(data: bytes) -> str:
        if len(data) != 30:
            raise ValueError(
                f"builddate.bin: expected 30 bytes, got {len(data)}")
        rendered = ", ".join(_char_literal(byte) for byte in data)
        statics = [
            "static const MkdsBuildDate build_date = {",
            f"    .text = {{{rendered}}},",
            "};",
        ]
        writes = [("&build_date", "sizeof build_date", 1)]
        return _program("builddate stamp",
                        ["nitro/mkds/files/misc.h"], statics, writes)


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

EMITTERS: dict[str, type] = {
    "ranktimeGP.rtt": RankTimeTable,
    "rankpoint.rpt": RankPointTable,
    "mission.mr": MissionTable,
    "missionTable.mtbl": MissionMenuTable,
    "ItemSlotList.dat": ItemSlotTable,
    "staff_ghost_time.bin": StaffGhostTimes,
    "grpconf.tbl": ObjectGroupTable,
    "kart_appear.ktbl": KartAppearanceTable,
    "emblem_s.tbl": EmblemStampTable,
    "emblem2.bin": EmblemBitmapTable,
    "builddate.bin": BuildDateTable,
}

Emitter = Callable[[bytes], str]


def emit_source(format_name: str, data: bytes) -> str:
    """Dispatch to the emitter registered for ``format_name``."""
    try:
        emitter = EMITTERS[format_name]
    except KeyError as exc:
        raise KeyError(f"no emitter for {format_name!r}") from exc
    return emitter.emit_source(data)
