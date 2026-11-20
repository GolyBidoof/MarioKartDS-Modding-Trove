# Mario Kart DS Modding Trove
# tests/test_ctables_small.py — exact rebuild tests for the small MKDS tables
# SPDX-License-Identifier: MIT
"""Compile typed C emitters with synthetic fixtures and compare the bytes.

The fixtures here are built in memory, so the tests run without a ROM or any
stock file. Byte-exact stock validation is a separate local step.
"""
from __future__ import annotations

import struct
import unittest

from tools.ctables.common import harness
from tools.ctables.mkds import small_tables as st

requires_cc = unittest.skipUnless(harness.CC, "no host C compiler")


# ---------------------------------------------------------------------------
# Synthetic fixture builders
# ---------------------------------------------------------------------------

def rank_time(entries, *, magic=b"NKTT", file_size=None, course_count=None,
              time_delta_weight=1000, first_place_weight=150,
              start_boost_points=25, power_slide_points=2,
              item_hit_points=5, off_road_divisor=3, wall_hit_points=20,
              damage_points=30, respawn_points=70):
    body = b"".join(struct.pack("<BBHHH", *entry) for entry in entries)
    size = 28 + len(body) if file_size is None else file_size
    count = len(entries) if course_count is None else course_count
    return struct.pack(
        "<4sI10H", magic, size, count, time_delta_weight,
        first_place_weight, start_boost_points, power_slide_points,
        item_hit_points, off_road_divisor, wall_hit_points, damage_points,
        respawn_points) + body


def rank_point(rows, *, magic=b"NKPT", file_size=None):
    body = b"".join(struct.pack("<8B", *row) for row in rows)
    size = 8 + len(body) if file_size is None else file_size
    return struct.pack("<4sI", magic, size) + body


def mission_entry(*, time_limit=0, target_time=0, rank_delta_scale=0,
                  mission_id=0, task=0, course_id=0, engine_class=0,
                  character_id=0, kart_id=0, menu_id=0, reserved_0d=0,
                  camera_index=0, target_value=0, win_delay=0,
                  reserved_12=0, object_ids=(0, 0, 0, 0), flags=0,
                  enemy_character=0xFF, enemy_kart=0xFF, name=b"mr00"):
    name_bytes = bytes(name).ljust(12, b"\0")[:12]
    return struct.pack(
        "<HHh10BHH4HHBB12s",
        time_limit, target_time, rank_delta_scale, mission_id, task,
        course_id, engine_class, character_id, kart_id, menu_id, reserved_0d,
        camera_index, target_value, win_delay, reserved_12, *object_ids,
        flags, enemy_character, enemy_kart, name_bytes)


def mission_file(entries, *, magic=b"NKMR", entry_count=None):
    body = b"".join(entries)
    count = len(entries) if entry_count is None else entry_count
    return struct.pack("<4sI", magic, count) + body


def mission_menu(ids, *, magic=b"NKMT", level_count=7,
                 missions_per_level=9):
    return struct.pack("<4sHH", magic, level_count,
                       missions_per_level) + bytes(ids)


def item_slots(blocks, *, block_total=None):
    out = bytearray([len(blocks) if block_total is None else block_total])
    for slots, columns, weights in blocks:
        assert len(weights) == slots * columns
        out += bytes([slots, columns])
        out += bytes(weights)
    return bytes(out)


def staff_times(values):
    assert len(values) == 40
    return struct.pack("<40I", *values)


# ---------------------------------------------------------------------------
# Shared assertions
# ---------------------------------------------------------------------------

class ExactRebuild:
    def assert_rebuilds(self, source: str, expected: bytes):
        ok, produced, error = harness.compile_and_compare(source, expected)
        if not ok:
            self.fail(error or (
                f"rebuilt {len(produced)} bytes, expected {len(expected)}; "
                f"first difference at "
                f"{next((i for i, (a, b) in enumerate(zip(produced, expected)) if a != b), 'length')}"
            ))

    def assert_no_shift_width_enums(self, source: str):
        self.assertNotIn("_SHIFT", source)
        self.assertNotIn("_WIDTH", source)


# ---------------------------------------------------------------------------
# ranktimeGP.rtt
# ---------------------------------------------------------------------------

@requires_cc
class RankTimeTests(unittest.TestCase, ExactRebuild):
    def test_round_trip(self):
        data = rank_time([
            (10, 0xAB, 5610, 4620, 3960),
            (11, 0x00, 8250, 6600, 5940),
        ], file_size=999, course_count=32)
        source = st.RankTimeTable.emit_source(data)
        self.assert_rebuilds(source, data)
        self.assertIn('#include "nitro/mkds/race/ranktime.h"', source)
        self.assertIn("static const MkdsRankTimeHeader", source)
        self.assertIn("static const MkdsRankTimeCourse course_table[2]", source)
        self.assertIn(".course_id = MKDS_RACE_COURSE_N64_MOO_MOO_FARM,", source)
        self.assertIn(".reserved_01 = 171,", source)
        self.assertIn(".target_frames_50cc = 5610,", source)
        self.assertIn(".target_frames_150cc = 3960,", source)
        self.assert_no_shift_width_enums(source)

    def test_empty_table(self):
        data = rank_time([], course_count=0)
        source = st.RankTimeTable.emit_source(data)
        self.assert_rebuilds(source, data)
        self.assertNotIn("course_table", source)

    def test_rejects_truncated_header_and_row(self):
        with self.assertRaises(ValueError):
            st.RankTimeTable.emit_source(b"NKTT" + b"\0" * 23)
        with self.assertRaises(ValueError):
            st.RankTimeTable.emit_source(rank_time([]) + b"\0" * 7)

    def test_no_redundant_offset_comments(self):
        source = st.RankTimeTable.emit_source(rank_time([(1, 0, 2, 3, 4)]))
        self.assertNotIn("/* +0x", source)


# ---------------------------------------------------------------------------
# rankpoint.rpt
# ---------------------------------------------------------------------------

@requires_cc
class RankPointTests(unittest.TestCase, ExactRebuild):
    def test_round_trip(self):
        data = rank_point([
            (10, 8, 6, 4, 3, 2, 1, 0),
            (15, 11, 8, 3, 1, 0, 0, 0),
            (0, 255, 0, 0, 0, 0, 0, 0),
        ], file_size=1234)
        source = st.RankPointTable.emit_source(data)
        self.assert_rebuilds(source, data)
        self.assertIn('#include "nitro/mkds/race/rankpoint.h"', source)
        self.assertIn("static const MkdsRankPointRow point_rows[3]", source)
        self.assertIn("[MKDS_RANK_POINT_PLACE_1] = 15,", source)
        self.assertIn("[MKDS_RANK_POINT_PLACE_8] = 0,", source)
        self.assert_no_shift_width_enums(source)

    def test_empty_table(self):
        data = rank_point([])
        source = st.RankPointTable.emit_source(data)
        self.assert_rebuilds(source, data)
        self.assertNotIn("point_rows", source)

    def test_rejects_partial_row(self):
        with self.assertRaises(ValueError):
            st.RankPointTable.emit_source(rank_point([]) + b"\0" * 7)


# ---------------------------------------------------------------------------
# mission.mr
# ---------------------------------------------------------------------------

@requires_cc
class MissionTests(unittest.TestCase, ExactRebuild):
    def test_round_trip(self):
        entries = [
            mission_entry(
                time_limit=1500, target_time=1500, rank_delta_scale=100,
                mission_id=1, task=0, course_id=1, engine_class=1,
                character_id=6, kart_id=18, menu_id=3, camera_index=0,
                target_value=1, win_delay=2, object_ids=(7, 8, 9, 10),
                flags=0x0025, enemy_character=0xFF, enemy_kart=0xFF,
                name=b"mr01"),
            mission_entry(
                time_limit=0xFFFF, target_time=0, rank_delta_scale=-25,
                mission_id=91, task=6, course_id=25, engine_class=2,
                character_id=7, kart_id=21, menu_id=0, reserved_0d=0x5A,
                camera_index=1, target_value=0x80, win_delay=0x1234,
                reserved_12=0xABCD, object_ids=(0, 0xFFFF, 3, 4),
                flags=0x8041, enemy_character=9, enemy_kart=10,
                name=b"mr07"),
        ]
        data = mission_file(entries, entry_count=99)
        source = st.MissionTable.emit_source(data)
        self.assert_rebuilds(source, data)
        self.assertIn('#include "nitro/mkds/race/mission.h"', source)
        self.assertIn("static const MkdsMissionEntry mission_entries[92]",
                      source)
        self.assertIn("static const uint8_t mission_entry_ids[2]", source)
        self.assertIn(".task = MKDS_MISSION_TASK_GATES,", source)
        self.assertIn(".task = MKDS_MISSION_TASK_FINISH_BEFORE,", source)
        self.assertIn(".engine_class = MKDS_ENGINE_100CC,", source)
        self.assertIn(".bits = { .no_forward = 1, .no_wall_hit = 1, "
                      ".backwards = 1 }", source)
        self.assertIn(".raw = 0x8041", source)
        self.assertIn(".rank_delta_scale = -25,", source)
        self.assert_no_shift_width_enums(source)

    def test_name_with_bytes_after_nul_uses_array(self):
        data = mission_file([
            mission_entry(name=b"m\0\nbcdefghijk"),
        ])
        source = st.MissionTable.emit_source(data)
        self.assert_rebuilds(source, data)
        self.assertIn(".name = {0x6d, 0x00, 0x0a", source)

    def test_empty_table(self):
        data = mission_file([])
        source = st.MissionTable.emit_source(data)
        self.assert_rebuilds(source, data)
        self.assertNotIn("mission_entries", source)

    def test_rejects_partial_entry(self):
        with self.assertRaises(ValueError):
            st.MissionTable.emit_source(mission_file([]) + b"\0" * 43)


# ---------------------------------------------------------------------------
# missionTable.mtbl
# ---------------------------------------------------------------------------

@requires_cc
class MissionMenuTests(unittest.TestCase, ExactRebuild):
    def test_round_trip(self):
        data = mission_menu([54, 55, 12, 52], level_count=2,
                            missions_per_level=2)
        source = st.MissionMenuTable.emit_source(data)
        self.assert_rebuilds(source, data)
        self.assertIn("static const MkdsMissionMenuHeader", source)
        self.assertIn("static const MkdsMissionId menu_ids[4]", source)
        self.assertIn(".level_count = 2,", source)
        self.assertIn(".missions_per_level = 2,", source)
        self.assert_no_shift_width_enums(source)

    def test_empty_id_table(self):
        data = mission_menu([])
        source = st.MissionMenuTable.emit_source(data)
        self.assert_rebuilds(source, data)
        self.assertNotIn("menu_ids", source)

    def test_rejects_short_header(self):
        with self.assertRaises(ValueError):
            st.MissionMenuTable.emit_source(b"NKMT\0\0\0")


# ---------------------------------------------------------------------------
# ItemSlotList.dat
# ---------------------------------------------------------------------------

@requires_cc
class ItemSlotTests(unittest.TestCase, ExactRebuild):
    def test_round_trip(self):
        data = item_slots([
            (2, 3, [45, 25, 15, 5, 0, 0]),
            (1, 18, list(range(18))),
            (3, 2, [1, 2, 3, 4, 5, 6]),
        ], block_total=9)
        source = st.ItemSlotTable.emit_source(data)
        self.assert_rebuilds(source, data)
        self.assertIn('#include "nitro/mkds/race/itemslots.h"', source)
        self.assertIn("static const MkdsItemSlotBlockHeader block_0_header",
                      source)
        self.assertIn(".slot_count = 2,", source)
        self.assertIn(".column_count = 3,", source)
        self.assertIn("block_1_weights[18][1]", source)
        self.assertIn("[MKDS_ITEM_SLOT_GREEN_SHELL] = {0},", source)
        self.assertIn("[MKDS_ITEM_SLOT_ITEM_BOX] = {17},", source)
        self.assertIn("block_0_weights[3][2]", source)
        self.assertIn("[0] = {45, 25},", source)
        self.assert_no_shift_width_enums(source)

    def test_zero_blocks(self):
        data = b"\x00"
        source = st.ItemSlotTable.emit_source(data)
        self.assert_rebuilds(source, data)
        self.assertIn("block_total = 0;", source)

    def test_zero_sized_block_payload(self):
        data = item_slots([(0, 18, [])])
        source = st.ItemSlotTable.emit_source(data)
        self.assert_rebuilds(source, data)
        self.assertNotIn("block_0_weights", source)

    def test_rejects_truncated_header_and_payload(self):
        with self.assertRaises(ValueError):
            st.ItemSlotTable.emit_source(b"\x01\x02")
        with self.assertRaises(ValueError):
            st.ItemSlotTable.emit_source(b"\x01\x02\x03" + b"\0" * 5)


# ---------------------------------------------------------------------------
# staff_ghost_time.bin
# ---------------------------------------------------------------------------

@requires_cc
class StaffGhostTests(unittest.TestCase, ExactRebuild):
    def test_round_trip(self):
        data = staff_times([index * 1000 + 7 for index in range(40)])
        source = st.StaffGhostTimes.emit_source(data)
        self.assert_rebuilds(source, data)
        self.assertIn('#include "nitro/mkds/race/staffghost.h"', source)
        self.assertIn("static const MkdsStaffGhostTimes staff_ghost_times",
                      source)
        self.assertIn(".threshold_ms = {", source)
        self.assertIn(
            "[MKDS_STAFF_TIME_SLOT(MKDS_RACE_COURSE_GCN_YOSHI_CIRCUIT)] = 7,", source)
        self.assertIn(
            "[MKDS_STAFF_TIME_SLOT(MKDS_RACE_COURSE_GBA_SKY_GARDEN)] = 39007,", source)
        self.assert_no_shift_width_enums(source)

    def test_all_zero(self):
        data = staff_times([0] * 40)
        source = st.StaffGhostTimes.emit_source(data)
        self.assert_rebuilds(source, data)

    def test_rejects_wrong_size(self):
        with self.assertRaises(ValueError):
            st.StaffGhostTimes.emit_source(b"\0" * 156)


# ---------------------------------------------------------------------------
# grpconf.tbl
# ---------------------------------------------------------------------------

def grpconf(records):
    return b"".join(struct.pack("<8H", *record) for record in records)


@requires_cc
class ObjectGroupTests(unittest.TestCase, ExactRebuild):
    def test_round_trip(self):
        data = grpconf([
            (101, 1, 15, 1300, 1, 10, 0, 0),
            (103, 2, 18, 1300, 4, 10, 10, 10),
            (777, 0, 0, 0, 0, 0, 0, 0),
        ])
        source = st.ObjectGroupTable.emit_source(data)
        self.assert_rebuilds(source, data)
        self.assertIn('#include "nitro/mkds/race/grpconf.h"', source)
        self.assertIn("static const MkdsObjectGroupConfig grpconf_table[778]",
                      source)
        self.assertIn("static const uint16_t grpconf_ids[3]", source)
        self.assertIn("[MKDS_OBJECT_ITEM_BOX] = {", source)
        self.assertIn(".model_kind = MKDS_OBJECT_MODEL_BILLBOARD,", source)
        self.assertIn(".model_kind = MKDS_OBJECT_MODEL_THREE_D,", source)
        self.assertIn(".collision_shape = MKDS_OBJECT_COLLISION_BOX,", source)

    def test_rejects_partial_record(self):
        with self.assertRaises(ValueError):
            st.ObjectGroupTable.emit_source(b"\0" * 17)


# ---------------------------------------------------------------------------
# kart_appear.ktbl
# ---------------------------------------------------------------------------

def kart_appear(rows):
    return b"NKKT" + bytes([len(rows), 13]) + bytes(
        value for row in rows for value in row)


@requires_cc
class KartAppearanceTests(unittest.TestCase, ExactRebuild):
    def test_round_trip(self):
        rows = [[0] * 13 for _ in range(37)]
        rows[0][0] = 1
        rows[0][12] = 0
        rows[36][12] = 1
        data = kart_appear(rows)
        source = st.KartAppearanceTable.emit_source(data)
        self.assert_rebuilds(source, data)
        self.assertIn('#include "nitro/mkds/race/kartappear.h"', source)
        self.assertIn("static const MkdsKartAppearanceHeader", source)
        self.assertIn("static const MkdsKartAppearanceRow "
                      "kart_appearance_rows[37]", source)
        self.assertIn("[MKDS_KART_STANDARD_MR] = {", source)
        self.assertIn("[MKDS_CHARACTER_MARIO] = MKDS_KART_APPEAR_DEFAULT,",
                      source)
        self.assert_no_shift_width_enums(source)

    def test_rejects_partial_row(self):
        with self.assertRaises(ValueError):
            st.KartAppearanceTable.emit_source(b"NKKT\x01\x0d" + b"\0" * 12)


# ---------------------------------------------------------------------------
# emblem_s.tbl, emblem2.bin, builddate.bin
# ---------------------------------------------------------------------------

@requires_cc
class EmblemAndBuildTests(unittest.TestCase, ExactRebuild):
    def test_emblem_stamp_table(self):
        stamps = b"".join(
            struct.pack("<hhHH", index, index * 2, 1, index + 1)
            for index in range(50))
        data = struct.pack("<I", 50) + stamps + b"\0" * 6
        source = st.EmblemStampTable.emit_source(data)
        self.assert_rebuilds(source, data)
        self.assertIn('#include "nitro/mkds/files/emblemtable.h"', source)
        self.assertIn("static const MkdsEmblemStampPlacement emblem_stamps[50]",
                      source)
        self.assertIn(".stamp_id = 50,", source)

    def test_emblem_bitmap(self):
        data = bytes(range(256)) * 2
        source = st.EmblemBitmapTable.emit_source(data)
        self.assert_rebuilds(source, data)
        self.assertIn("static const MkdsEmblemBitmap emblem", source)

    def test_build_date(self):
        data = b"Build: 2005 10/8(Sat) 23:05:54"
        source = st.BuildDateTable.emit_source(data)
        self.assert_rebuilds(source, data)
        self.assertIn("static const MkdsBuildDate build_date", source)

    def test_size_guards(self):
        with self.assertRaises(ValueError):
            st.EmblemBitmapTable.emit_source(b"\0" * 511)
        with self.assertRaises(ValueError):
            st.BuildDateTable.emit_source(b"\0" * 29)
        with self.assertRaises(ValueError):
            st.EmblemStampTable.emit_source(struct.pack("<I", 49) + b"\0" * 396)


# ---------------------------------------------------------------------------
# Registry and shared style
# ---------------------------------------------------------------------------

@requires_cc
class RegistryTests(unittest.TestCase, ExactRebuild):
    def test_every_format_is_registered(self):
        self.assertEqual(set(st.EMITTERS), {
            "ranktimeGP.rtt", "rankpoint.rpt", "mission.mr",
            "missionTable.mtbl", "ItemSlotList.dat",
            "staff_ghost_time.bin", "grpconf.tbl", "kart_appear.ktbl",
            "emblem_s.tbl", "emblem2.bin", "builddate.bin",
        })

    def test_dispatch_and_unknown_name(self):
        data = staff_times([1] * 40)
        self.assertEqual(st.emit_source("staff_ghost_time.bin", data),
                         st.StaffGhostTimes.emit_source(data))
        with self.assertRaises(KeyError):
            st.emit_source("nope.bin", data)

    def test_comments_use_hex_offsets(self):
        samples = [
            st.RankTimeTable.emit_source(rank_time([(1, 0, 2, 3, 4)])),
            st.RankPointTable.emit_source(rank_point([(1,) * 8])),
            st.MissionTable.emit_source(mission_file([mission_entry()])),
            st.MissionMenuTable.emit_source(mission_menu([1])),
            st.ItemSlotTable.emit_source(item_slots([(1, 2, [3, 4])])),
            st.StaffGhostTimes.emit_source(staff_times([1] * 40)),
        ]
        for source in samples:
            for line in source.splitlines():
                marker = line.find("/* +")
                if marker >= 0:
                    self.assertIn("0x", line[marker:], line)


if __name__ == "__main__":
    unittest.main()
