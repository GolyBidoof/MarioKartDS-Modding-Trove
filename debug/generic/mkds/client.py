#!/usr/bin/env python3
"""MKDS-specific navigation/screenshot layer over a generic debug backend.

The generic transports are in debug/generic/transport; text is in debug/recomp/client.
contains only MKDS knowledge: scene/menu addresses, menu names, and the
screenshot convenience methods.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

try:
    from .backends import Backend, Unsupported
except ImportError:  # direct script use from debug/generic/mkds
    from backends import Backend, Unsupported


MENU_NAMES = [
    "mode_select_buttons_in", "mode_select", "mode_select_buttons_out",
    "mode_selected", "gp_class_select", "gp_character_select",
    "gp_kart_select", "gp_cup_select", "vs_character_select",
    "vs_kart_select", "vs_rules", "vs_cup_select", "vs_course_select_inout",
    "vs_course_select", "mg_game_select", "mg_character_select", "mg_rules",
    "mg_arena_select", "mr_level_select", "mr_mission_select",
    "ta_mode_select", "ta_character_select", "ta_kart_select",
    "ta_cup_select", "ta_course_select_inout", "ta_course_select",
    "ta_ghost_select", "goto_title", "goto_ghost", "goto_race", "count",
    "invalid",
]


@dataclass(frozen=True)
class MkdsLayout:
    scene_manager: int = 0x021653B8
    menu_state: int = 0x0217B43C
    menu_scene: int = 1
    default_menu_next: int = 31
    main_base: int = 0x02000000
    main_end: int = 0x02400000


class MkdsClient:
    """Persistent MKDS custom layer.

    The backend keeps its connection open. Call close() explicitly when done.
    """

    def __init__(self, backend: Backend, layout: MkdsLayout = MkdsLayout()):
        self.backend = backend
        self.layout = layout

    def read16(self, address):
        return int.from_bytes(self.backend.read(address, 2), "little")

    def write16(self, address, value):
        self.backend.write(address, int(value & 0xFFFF).to_bytes(2, "little"))

    def scene(self, value: Optional[int] = None):
        if value is not None:
            self.write16(self.layout.scene_manager, value)
            self.write16(self.layout.scene_manager + 2, value)
            self.write16(self.layout.scene_manager + 4, value)
            return value
        return self.read16(self.layout.scene_manager + 2)

    def scene_info(self):
        base = self.layout.scene_manager
        return {
            "previous": self.read16(base),
            "current": self.read16(base + 2),
            "next": self.read16(base + 4),
        }

    def menu(self):
        base = self.backend.read32(self.layout.menu_state)
        if not (self.layout.main_base <= base < self.layout.main_end):
            return None
        frame = self.backend.read32(base)
        previous = self.backend.read32(base + 8)
        current = self.backend.read32(base + 12)
        following = self.backend.read32(base + 16)

        def name(value):
            return MENU_NAMES[value] if 0 <= value < len(MENU_NAMES) else "?"

        return {
            "frame": frame,
            "previous": previous,
            "current": current,
            "next": following,
            "name": name(current),
            "previous_name": name(previous),
            "next_name": name(following),
        }

    def set_menu_state(self, value):
        base = self.backend.read32(self.layout.menu_state)
        if not (self.layout.main_base <= base < self.layout.main_end):
            return False
        self.backend.write32(base, 0)
        self.backend.write32(base + 4, 0)
        self.backend.write32(base + 8, self.backend.read32(base + 12))
        self.backend.write32(base + 12, value)
        self.backend.write32(base + 16, self.layout.default_menu_next)
        return True

    def screenshot(self, path=None, screen="both", native=True):
        if "screenshot" not in self.backend.capabilities:
            raise Unsupported("this backend has no screenshot support")
        if screen not in ("both", "upper", "lower"):
            raise ValueError("screen must be both, upper or lower")
        if path is None:
            path = f"dbg_mkds_{screen}_{'native' if native else 'full'}.bmp"
        return self.backend.screenshot(path, screen, native)

    def screenshot_upper(self, path=None, native=True):
        return self.screenshot(path, "upper", native)

    def screenshot_lower(self, path=None, native=True):
        return self.screenshot(path, "lower", native)

    def screenshot_both(self, path=None, native=True):
        return self.screenshot(path, "both", native)

    def screenshot_full(self, path=None):
        return self.screenshot(path, "both", False)

    def press(self, spec, frames=2):
        if "input" not in self.backend.capabilities:
            raise Unsupported("this backend has no input support")
        return self.backend.press(spec, frames)

    def command(self, text):
        if "command" not in self.backend.capabilities:
            raise Unsupported("this backend has no command channel")
        return self.backend.command(text)

    def close(self):
        self.backend.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()
