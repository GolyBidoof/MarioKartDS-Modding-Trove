#!/usr/bin/env python3
"""Interactive MKDS custom layer.

    python3 debug/generic/mkds/cli.py --backend recomp --port 19850 scene
    python3 debug/generic/mkds/cli.py --backend rsp --port 3335 menu
    python3 debug/generic/mkds/cli.py --backend rsp --port 3335 screenshot upper

With no command it keeps one connection open and prompts.
"""

import argparse
import shlex

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "recomp", "mkds"))
sys.path.insert(0, HERE)

from backends import RspBackend, Unsupported  # noqa: E402
from text_backend import RecompBackend  # noqa: E402
from client import MkdsClient, MkdsLayout  # noqa: E402


def show(value):
    if isinstance(value, dict):
        for key, item in value.items():
            print(f"{key}: {item}")
    else:
        print(value)


def dispatch(client, line):
    parts = shlex.split(line)
    if not parts:
        return True
    command, args = parts[0], parts[1:]

    if command in ("quit", "exit", "close"):
        return False
    if command == "status":
        print("capabilities:", ", ".join(sorted(client.backend.capabilities)))
        show(client.scene_info())
        show(client.menu())
    elif command == "scene":
        show(client.scene(int(args[0], 0) if args else None))
    elif command == "menu":
        show(client.menu())
    elif command == "menu_state":
        show(client.set_menu_state(int(args[0], 0)))
    elif command == "screenshot":
        screen = args[0] if args else "both"
        native = not (len(args) > 1 and args[1] == "full")
        path = args[2] if len(args) > 2 else None
        show(client.screenshot(path, screen, native))
    elif command == "read":
        data = client.backend.read(int(args[0], 0), int(args[1], 0))
        print(data.hex())
    elif command == "write":
        client.backend.write(int(args[0], 0), bytes.fromhex(args[1]))
        print("ok")
    elif command == "press":
        frames = int(args[1]) if len(args) > 1 else 2
        show(client.press(args[0], frames))
    elif command == "command":
        show(client.command(" ".join(args)))
    else:
        print("commands: status scene menu menu_state screenshot read write "
              "press command quit")
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backend", choices=("recomp", "rsp"), default="recomp")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=None)
    parser.add_argument("--scene-manager", type=lambda x: int(x, 0),
                        default=MkdsLayout.scene_manager)
    parser.add_argument("--menu-state", type=lambda x: int(x, 0),
                        default=MkdsLayout.menu_state)
    parser.add_argument("command", nargs="*")
    args = parser.parse_args()

    layout = MkdsLayout(scene_manager=args.scene_manager,
                        menu_state=args.menu_state)
    if args.backend == "recomp":
        backend = RecompBackend(args.host, args.port)
    else:
        backend = RspBackend(args.host, args.port or 3333)
    client = MkdsClient(backend, layout)

    try:
        if args.command:
            dispatch(client, " ".join(args.command))
            return 0
        while True:
            try:
                line = input("mkds> ").strip()
            except (EOFError, KeyboardInterrupt):
                break
            try:
                if not dispatch(client, line):
                    break
            except Unsupported as exc:
                print(f"unsupported: {exc}")
            except Exception as exc:
                print(f"error: {exc}")
    finally:
        client.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
