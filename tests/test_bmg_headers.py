# Mario Kart DS Modding Trove
# tests/test_bmg_headers.py — generated BMG header cross-references
# SPDX-License-Identifier: MIT
"""Synthetic tests for tools/bmg_headers.py; no stock files are read."""
import re
import struct
import tempfile
import unittest
from pathlib import Path

from tests.test_bmg import make_bmg
from tools import bmg_headers

MISSION_LABEL = "ABCDEFGHIJKLMNOPQRSTUVWXYZABCDEFGHIJKLMN"


def write_mission_files(root: Path, ids=(10, 4, 7, 2),
                        levels: int = 2, per_level: int = 2) -> None:
    mtbl = root / "Main2D_arc" / "missionTable.mtbl"
    mtbl.parent.mkdir(parents=True)
    mtbl.write_bytes(struct.pack("<4sHH", b"NKMT", levels, per_level)
                     + bytes(ids))

    records = bytearray(b"NKMR" + b"\0" * 4)
    for mission_id in range(1, max(ids) + 1):
        record = bytearray(44)
        name = f"mr{mission_id:02d}".encode("ascii")
        record[0x20:0x20 + len(name)] = name
        records += record
    mr = root / "Scene" / "Menu_arc" / "mission.mr"
    mr.parent.mkdir(parents=True)
    mr.write_bytes(bytes(records))


def write_banks(root: Path) -> None:
    banks = {
        "Main2D_us_arc/common.bmg": [""] * 114,
        "CharacterKartSelect_us_arc/kart_select.bmg": [""] * 42,
        "Scene/Ghost_us_arc/ghost.bmg": [""] * 83,
        "Scene/Menu_us_arc/menu.bmg": [""] * 14,
        "Scene/Menu_us_arc/rule.bmg": [""] * 17,
        "Scene/Menu_us_arc/mission.bmg": [MISSION_LABEL, "B", "C", "D"],
    }
    for relative, messages in banks.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(make_bmg(messages))




class GeneratorTests(unittest.TestCase):
    def test_cross_references_and_mission_slots(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "data"
            out = Path(tmp) / "bmg"
            write_mission_files(root)
            write_banks(root)
            self.assertEqual(
                bmg_headers.main([str(root), "-o", str(out)]), 0)

            common = (out / "common.h").read_text()
            for type_name in (
                    "MkdsBmgCommonFriendCodeMessage",
                    "MkdsBmgCommonUiMessage",
                    "MkdsBmgCommonCharacterMessage",
                    "MkdsBmgCommonDuplicateMessage",
                    "MkdsBmgCommonModeMessage",
                    "MkdsBmgCommonCupMessage",
                    "MkdsBmgCommonCourseMessage",
                    "MkdsBmgCommonBattleMessage",
                    "MkdsBmgCommonEngineMessage",
                    "MkdsBmgCommonMiscMessage"):
                self.assertIn(f"}} {type_name};", common)
            self.assertIn(
                "MKDS_BMG_COMMON_FRIEND_CODE_REGISTERED = 9", common)
            self.assertIn("MKDS_BMG_COMMON_CHARACTER_MARIO = 20", common)
            self.assertIn("MKDS_BMG_COMMON_CHARACTER_SHY_GUY = 32", common)
            self.assertIn("MKDS_BMG_COMMON_CUP_MUSHROOM = 37", common)
            self.assertIn(
                "MKDS_BMG_COMMON_COURSE_FIGURE_8_CIRCUIT = 45", common)
            self.assertIn("MKDS_BMG_COMMON_BATTLE_BLOCK_FORT = 77", common)
            self.assertIn("MKDS_BMG_COMMON_ENGINE_50CC = 110", common)
            self.assertNotIn("MKDS_CHARACTER_MARIO */", common)

            karts = (out / "kart_select.h").read_text()
            self.assertIn("} MkdsBmgKartSelectStatsMessage;", karts)
            self.assertIn("} MkdsBmgKartSelectKartMessage;", karts)
            self.assertIn(
                "MKDS_BMG_KART_SELECT_KART_STANDARD_MR = 6", karts)
            self.assertIn("MKDS_BMG_KART_SELECT_KART_ROB_LGS = 41", karts)

            ghost = (out / "ghost.h").read_text()
            for type_name in (
                    "MkdsBmgGhostUiMessage",
                    "MkdsBmgGhostCourseMessage",
                    "MkdsBmgGhostRepeatedCourseMessage"):
                self.assertIn(f"}} {type_name};", ghost)
            self.assertIn(
                "MKDS_BMG_GHOST_COURSE_FIGURE_8_CIRCUIT = 19", ghost)
            self.assertIn(
                "MKDS_BMG_GHOST_COURSE_FIGURE_8_CIRCUIT_2 = 51", ghost)

            menu = (out / "menu.h").read_text()
            for type_name in (
                    "MkdsBmgMenuBattleMessage",
                    "MkdsBmgMenuBattleModeMessage",
                    "MkdsBmgMenuGhostMessage"):
                self.assertIn(f"}} {type_name};", menu)
            self.assertIn("MKDS_BMG_MENU_BATTLE_BLOCK_FORT = 0", menu)
            self.assertIn("MKDS_BMG_MENU_MODE_BALLOON_BATTLE = 6", menu)
            self.assertIn("MKDS_BMG_MENU_GHOST_MY_GHOST_DATA = 11", menu)

            rule = (out / "rule.h").read_text()
            for type_name in (
                    "MkdsBmgRuleLabelMessage",
                    "MkdsBmgRuleEngineMessage",
                    "MkdsBmgRuleToggleMessage",
                    "MkdsBmgRuleCpuMessage",
                    "MkdsBmgRuleOrderMessage"):
                self.assertIn(f"}} {type_name};", rule)
            self.assertIn("MKDS_BMG_RULE_ENGINE_50CC = 5", rule)
            self.assertIn("MKDS_BMG_RULE_CPU_EASY = 11", rule)
            self.assertIn("MKDS_BMG_RULE_RULE_IN_ORDER = 14", rule)

            for header in (common, karts, ghost, menu, rule):
                keys = re.findall(
                    r"^\s+(MKDS_BMG_[A-Z0-9_]+)\s*=\s*\d+", header, re.M)
                self.assertEqual(len(keys), len(set(keys)))

            mission = (out / "mission.h").read_text()
            self.assertIn("} MkdsBmgMissionMessage;", mission)
            self.assertIn("MKDS_BMG_MISSION_MR4_B = 1", mission)

    def test_duplicate_mission_slot_gets_suffix(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "data"
            out = Path(tmp) / "bmg"
            write_mission_files(root, ids=(10, 10), levels=1, per_level=2)
            mission = root / "Scene" / "Menu_us_arc" / "mission.bmg"
            mission.parent.mkdir(parents=True)
            mission.write_bytes(make_bmg(["COLLECT COINS", "COLLECT COINS"]))
            self.assertEqual(
                bmg_headers.main([str(root), "-o", str(out)]), 0)
            text = (out / "mission.h").read_text()
            self.assertIn("MKDS_BMG_MISSION_MR10_COLLECT = 0", text)
            self.assertIn("MKDS_BMG_MISSION_MR10_COLLECT_2 = 1", text)

    def test_missing_mission_files_are_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "data"
            out = Path(tmp) / "bmg"
            mission = root / "Scene" / "Menu_us_arc" / "mission.bmg"
            mission.parent.mkdir(parents=True)
            mission.write_bytes(make_bmg(["ONLY MISSION"]))
            self.assertEqual(
                bmg_headers.main([str(root), "-o", str(out)]), 0)
            text = (out / "mission.h").read_text()
            self.assertNotIn("cross-reference", text)
            self.assertNotIn("menu slot", text)

    def test_explicit_mission_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "data"
            out = Path(tmp) / "bmg"
            stock = Path(tmp) / "stock"
            write_mission_files(stock)
            mission = root / "Scene" / "Menu_us_arc" / "mission.bmg"
            mission.parent.mkdir(parents=True)
            mission.write_bytes(make_bmg(["A", "B"]))
            self.assertEqual(bmg_headers.main([
                str(root), "-o", str(out),
                "--missions-mtbl",
                str(stock / "Main2D_arc" / "missionTable.mtbl"),
            ]), 0)
            text = (out / "mission.h").read_text()
            self.assertIn("typedef enum", text)
            self.assertNotIn("menu slot", text)


if __name__ == "__main__":
    unittest.main()
