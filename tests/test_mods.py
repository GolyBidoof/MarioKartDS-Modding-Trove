# Mario Kart DS Modding Trove
# tests/test_mods.py — discovery, independence, multi-mod BMG planning
# SPDX-License-Identifier: MIT
"""Mod discovery, independence checks, and multi-mod BMG planning."""
import json
import struct
import tempfile
import unittest
from pathlib import Path

from tools import bmgset, mods, patch
from tools.bmg import Bmg


def make_bmg(messages):
    header = bytearray(0x20)
    header[:4] = b"MESG"
    header[4:8] = b"bmg1"
    struct.pack_into("<I", header, 0x0C, 2)
    struct.pack_into("<I", header, 0x10, 2)
    data = bytearray()
    offsets = []
    for text in messages:
        offsets.append(len(data))
        data += text.encode("utf-16-le") + b"\0\0"
    inf = bytearray(b"INF1" + b"\0\0\0\0"
                    + struct.pack("<HH", len(messages), 4) + b"\0" * 4)
    for off in offsets:
        inf += struct.pack("<I", off)
    while (0x20 + len(inf)) % 0x20:
        inf += b"\0"
    struct.pack_into("<I", inf, 4, len(inf))
    dat = bytearray(b"DAT1" + b"\0\0\0\0" + data)
    while len(dat) % 4:
        dat += b"\0"
    struct.pack_into("<I", dat, 4, len(dat))
    out = header + inf + dat
    struct.pack_into("<I", out, 0x08, len(out))
    return bytes(out)


def fake_mod(mod_id, labels, path):
    return mods.Mod(id=mod_id, name=mod_id, description="", path=path,
                    sources=(), bmg_append=tuple(labels), verify=None)


class ModTests(unittest.TestCase):
    def test_discover_and_select(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for mod_id, label in (("alpha", "A"), ("beta", "B")):
                directory = root / mod_id
                directory.mkdir()
                (directory / "mod.json").write_text(json.dumps({
                    "id": mod_id, "name": mod_id.upper(),
                    "bmg": {"append": [label]},
                }))
            found = mods.discover(root)
            self.assertEqual(sorted(found), ["alpha", "beta"])
            selected = mods.select(found, ["beta"], False)
            self.assertEqual([m.id for m in selected], ["beta"])
            with self.assertRaises(mods.ModError):
                mods.select(found, ["nope"], False)

    def test_conflicting_addresses_are_rejected(self):
        patch.check_conflicts({
            "a": ["ncp_over(0x02000000) int x;"],
            "b": ["ncp_over(0x02000004) int y;"],
        })
        with self.assertRaises(patch.ToolError):
            patch.check_conflicts({
                "a": ["ncp_over(0x02000000) int x;"],
                "b": ["ncp_over(0x02000000) int y;"],
            })

    def test_named_ncp_over_addresses_are_resolved(self):
        named = "#define ROW 0x02000000\nNCP_OVER(ROW) uint16_t x;"
        raw = "ncp_over(0x02000000) uint16_t y;"
        with self.assertRaises(patch.ToolError):
            patch.check_conflicts({"a": [named], "b": [raw]})

    def test_named_addresses_can_cross_files(self):
        header = "#define ROW 0x02000000\n"
        source = "NCP_OVER(ROW) uint16_t x;"
        raw = "ncp_over(0x02000000) uint16_t y;"
        with self.assertRaises(patch.ToolError):
            patch.check_conflicts({"a": [header, source], "b": [raw]})

    def test_unresolved_placeholder_is_rejected(self):
        with self.assertRaises(patch.ToolError):
            patch.render("x = {{missing}};", {})

    def test_engine_q12_values(self):
        repo = Path(__file__).resolve().parent.parent
        profile = patch._load_module(
            repo / "mods" / "options-cc" / "profile.py", "options_profile")
        self.assertEqual(profile.q12(0.7), 2867)
        self.assertEqual(profile.q12(0.85), 3482)
        self.assertEqual(profile.q12(1.0), 4096)
        self.assertEqual(profile.q12(1.15), 4710)
        self.assertEqual(profile.q12(1.3), 5325)
        self.assertEqual(profile.q12(1.45), 5939)
        self.assertEqual(profile.ENGINE["drift"]["50"], -40)
        self.assertEqual(profile.ENGINE["drift"]["100"], -20)

    def test_two_mods_get_distinct_bmg_ids(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            one = fake_mod("one", ["ONE"], root)
            two = fake_mod("two", ["TWO", "THREE"], root)
            items = [("data/Scene/Menu_us.carc!rule.bmg",
                      make_bmg(["ALPHA", "BETA", "GAMMA"]))]

            plan = bmgset.plan_files(items, root / "work", [one, two])
            self.assertEqual(plan.ids["one"], [3])
            self.assertEqual(plan.ids["two"], [4, 5])
            self.assertEqual(len(plan.files), 1)
            dest, generated = plan.files[0]
            self.assertEqual(dest, "data/Scene/Menu_us.carc!rule.bmg")
            self.assertEqual(Bmg(generated.read_bytes()).strings,
                             ["ALPHA", "BETA", "GAMMA", "ONE", "TWO", "THREE"])

    def test_duplicate_mod_selection_is_deduplicated(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            found = {"one": fake_mod("one", ["ONE"], root)}
            selected = mods.select(found, ["one", "one"], False)
            self.assertEqual([mod.id for mod in selected], ["one"])

    def test_duplicate_labels_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            items = [("data/Scene/Menu_us.carc!rule.bmg", make_bmg(["ALPHA"]))]
            one = fake_mod("one", ["SAME"], root)
            two = fake_mod("two", ["SAME"], root)
            with self.assertRaises(bmgset.BmgPlanError):
                bmgset.plan_files(items, root / "work", [one, two])

    def test_discover_messages(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            directory = root / "m"
            (directory / "messages").mkdir(parents=True)
            (directory / "mod.json").write_text(json.dumps({
                "id": "m",
                "bmg": {"messages": "messages"},
            }))
            (directory / "messages" / "default.json").write_text(
                '{"labels": ["A"]}')
            (directory / "messages" / "es.json").write_text(
                '{"labels": ["B"]}')
            mod = mods.discover(root)["m"]
            self.assertEqual(mod.bmg_append, ("A",))
            self.assertEqual(mod.bmg_messages["es"], ("B",))

    def test_per_language_labels(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            mod = mods.Mod(
                id="one", name="one", description="", path=root, sources=(),
                bmg_append=("200cc", "250cc", "300cc"),
                bmg_messages={
                    "default": ("200cc", "250cc", "300cc"),
                    "es": ("200 cc", "250 cc", "300 cc"),
                    "ge": ("200 ccm", "250 ccm", "300 ccm"),
                },
                bmg_language_prefixes=("MenuDL_", "Menu_"),
                verify=None)
            items = [
                ("data/Scene/Menu_us.carc!rule.bmg", make_bmg(["ALPHA"])),
                ("data/Scene/Menu_es.carc!rule.bmg", make_bmg(["ALPHA"])),
                ("data/Scene/Menu_ge.carc!rule.bmg", make_bmg(["ALPHA"])),
            ]
            plan = bmgset.plan_items(items, root / "work", [mod])
            by_dest = {dest: Bmg(path.read_bytes()).strings
                       for dest, path in plan.files}
            self.assertEqual(by_dest["data/Scene/Menu_us.carc!rule.bmg"][-3:],
                             ["200cc", "250cc", "300cc"])
            self.assertEqual(by_dest["data/Scene/Menu_es.carc!rule.bmg"][-3:],
                             ["200 cc", "250 cc", "300 cc"])
            self.assertEqual(by_dest["data/Scene/Menu_ge.carc!rule.bmg"][-3:],
                             ["200 ccm", "250 ccm", "300 ccm"])


if __name__ == "__main__":
    unittest.main()
