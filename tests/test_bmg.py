# Mario Kart DS Modding Trove
# tests/test_bmg.py — synthetic BMG tests
# SPDX-License-Identifier: MIT
"""Synthetic BMG tests; no game data is read or stored."""
import struct
import unittest

from tools.bmg import Bmg, append_labels, base_string_count, strip_labels

LABELS = ("LABEL_A", "LABEL_B", "LABEL_C")


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
        if len(data) & 1:
            data += b"\0"

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


class BmgTests(unittest.TestCase):
    def setUp(self):
        self.raw = make_bmg(["ALPHA", "BETA", "GAMMA"])

    def test_count_and_append(self):
        self.assertEqual(base_string_count(self.raw, LABELS), 3)
        out = append_labels(self.raw, 3, LABELS)
        self.assertEqual(Bmg(out).strings,
                         ["ALPHA", "BETA", "GAMMA", *LABELS])

    def test_append_is_idempotent(self):
        once = append_labels(self.raw, 3, LABELS)
        twice = append_labels(once, 3, LABELS)
        self.assertEqual(Bmg(once).strings, Bmg(twice).strings)
        self.assertEqual(once, twice)

    def test_common_base_pads_with_empty_messages(self):
        out = append_labels(self.raw, 5, LABELS)
        self.assertEqual(Bmg(out).strings,
                         ["ALPHA", "BETA", "GAMMA", "", "", *LABELS])

    def test_declared_count_larger_than_slots_is_capped(self):
        broken = bytearray(self.raw)
        struct.pack_into("<H", broken, 0x28, 5)
        self.assertEqual(base_string_count(bytes(broken), LABELS), 3)
        out = append_labels(bytes(broken), 3, LABELS)
        self.assertEqual(Bmg(out).strings[:3], ["ALPHA", "BETA", "GAMMA"])

    def test_rebuilt_layout_is_well_formed(self):
        out = append_labels(self.raw, 3, LABELS)
        inf = out.find(b"INF1")
        dat = out.find(b"DAT1")
        self.assertGreater(dat, inf)
        self.assertEqual((dat - (inf + 16)) % 4, 0)
        self.assertEqual((0x20 + struct.unpack_from("<I", out, inf + 4)[0]) % 0x20, 0)
        self.assertEqual(struct.unpack_from("<I", out, 0x08)[0], len(out))

    def test_generic_labels_and_strip(self):
        labels = ["SMALL", "BIG"]
        out = append_labels(self.raw, 3, labels)
        self.assertEqual(Bmg(out).strings,
                         ["ALPHA", "BETA", "GAMMA", *labels])
        self.assertEqual(strip_labels(Bmg(out).strings, labels),
                         ["ALPHA", "BETA", "GAMMA"])

    def test_two_label_sets_can_share_a_base(self):
        labels = ["ALPHA", "BETA"]
        out = append_labels(self.raw, 3, labels)
        self.assertEqual(Bmg(out).strings[-2:], labels)


if __name__ == "__main__":
    unittest.main()
