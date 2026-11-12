import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "debug" / "generic"))

from mkds import MkdsClient, MkdsLayout, Unsupported  # noqa: E402


class FakeBackend:
    capabilities = {"nav", "screenshot"}

    def __init__(self):
        self.base = 0x02000000
        self.memory = bytearray(0x4000)
        self.screenshots = []
        self.closed = False

    def _offset(self, address):
        offset = address - self.base
        if offset < 0 or offset >= len(self.memory):
            raise ValueError(f"address {address:#x} outside fake memory")
        return offset

    def read(self, address, length):
        offset = self._offset(address)
        return bytes(self.memory[offset:offset + length])

    def write(self, address, data):
        offset = self._offset(address)
        self.memory[offset:offset + len(data)] = bytes(data)

    def read32(self, address):
        return int.from_bytes(self.read(address, 4), "little")

    def write32(self, address, value):
        self.write(address, int(value & 0xFFFFFFFF).to_bytes(4, "little"))

    def command(self, text):
        return [text]

    def screenshot(self, path, screen, native):
        self.screenshots.append((path, screen, native))
        return [f"screenshot {path}"]

    def press(self, spec, frames):
        return [spec, frames]

    def close(self):
        self.closed = True


class MkdsCustomLayerTests(unittest.TestCase):
    def setUp(self):
        self.backend = FakeBackend()
        self.layout = MkdsLayout(scene_manager=0x02000020,
                                 menu_state=0x02000000)
        self.client = MkdsClient(self.backend, self.layout)

    def test_scene_read_write(self):
        self.client.scene(7)
        self.assertEqual(self.client.scene(), 7)
        self.assertEqual(self.client.scene_info(),
                         {"previous": 7, "current": 7, "next": 7})

    def test_menu_names_and_state(self):
        self.backend.write32(0x02000000, 0x02000100)
        self.backend.write32(0x0200010C, 5)
        menu = self.client.menu()
        self.assertEqual(menu["current"], 5)
        self.assertEqual(menu["name"], "gp_character_select")
        self.assertTrue(self.client.set_menu_state(6))
        self.assertEqual(self.client.menu()["name"], "gp_kart_select")

    def test_native_screenshots(self):
        self.client.screenshot_upper("upper.bmp")
        self.client.screenshot_lower("lower.bmp")
        self.client.screenshot_both("both.bmp")
        self.client.screenshot_full("full.bmp")
        self.assertEqual(self.backend.screenshots, [
            ("upper.bmp", "upper", True),
            ("lower.bmp", "lower", True),
            ("both.bmp", "both", True),
            ("full.bmp", "both", False),
        ])

    def test_unsupported_backend(self):
        backend = FakeBackend()
        backend.capabilities = {"nav"}
        client = MkdsClient(backend, self.layout)
        with self.assertRaises(Unsupported):
            client.screenshot_upper("x.bmp")


if __name__ == "__main__":
    unittest.main()
