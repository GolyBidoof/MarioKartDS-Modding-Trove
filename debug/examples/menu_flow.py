#!/usr/bin/env python3
"""Example debug flow for debug/recomp/client/run_scenario.py.

Pause, leave the title, assert the mode-select menu, capture both screens, then
move one step into Time Trials and print the new menu state.

Run with:
    python3 debug/recomp/client/run_scenario.py \
        --binary /path/to/recomp/build/stock/mkds \
        --cwd /path/to/recomp \
        debug/examples/menu_flow.py
"""
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "recomp" / "client"))

from dbg_client import Debugger  # noqa: E402


def menu_fields(line):
    """Parse `menu <id> <name> prev <id> <name> next <id> <name> frame <n>`."""
    parts = line.split()
    if not parts or parts[0] != "menu" or len(parts) < 3:
        return None
    try:
        ident = int(parts[1])
    except ValueError:
        return None
    return {"id": ident, "name": parts[2], "line": line}


def first_menu(debugger):
    for line in debugger.command("menu"):
        parsed = menu_fields(line)
        if parsed:
            return parsed
    return None


def main():
    with Debugger() as d:
        d.pause()
        print("status:", d.status())

        # Let the boot/title scene settle before jumping the scene manager.
        d.wait(120)
        d.command("scene 1")
        d.wait(45)
        menu = first_menu(d)
        print("after scene skip:", menu)
        if not menu or menu["name"] != "mode_select":
            print("expected mode_select; got", menu, file=sys.stderr)
            return 1

        d.snapshot("mode_select")
        d.screenshot_both("dbg_mode_select_both.bmp")
        d.screenshot_lower("dbg_mode_select_lower.bmp")

        # Demonstrate one navigation step: mode select -> Time Trials.
        d.press("DOWN", 2)
        d.wait(15)
        d.press("A", 2)
        d.wait(45)
        print("after Time Trials entry:", first_menu(d))
        d.screenshot_both("dbg_ta_mode_both.bmp")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
