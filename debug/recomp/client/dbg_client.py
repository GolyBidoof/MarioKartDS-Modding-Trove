#!/usr/bin/env python3
"""Client for the ROM-agnostic static-recomp debug server.

The server is enabled by setting DBG_PORT in the recompilation's environment.
It listens on 127.0.0.1 and speaks a small line protocol:

    python3 debug/recomp/client/dbg_client.py status
    python3 debug/recomp/client/dbg_client.py read 0x02000000 64
    python3 debug/recomp/client/dbg_client.py screenshot upper
    python3 debug/recomp/client/dbg_client.py screenshot both full

From Python:

    from dbg_client import Debugger
    d = Debugger()
    d.pause()
    print(d.status())
    d.snapshot("before")
    d.resume(); d.wait(60)
    print(d.diff("before"))
    d.screenshot_upper("upper.bmp")   # native 256x192
    d.close()
"""

import argparse
import os
import socket
import sys


class Debugger:
    def __init__(self, host="127.0.0.1", port=None, timeout=30.0):
        if port is None:
            port = int(os.environ.get("DBG_PORT", "19850"))
        self.sock = socket.create_connection((host, port), timeout=timeout)
        self.sock.settimeout(timeout)
        self.f = self.sock.makefile("rwb")

    def cmd(self, text):
        self.f.write((text + "\n").encode())
        self.f.flush()
        lines = []
        while True:
            line = self.f.readline()
            if not line:
                raise ConnectionError("debug server closed")
            line = line.decode("utf-8", "replace").rstrip("\n")
            if line == "END":
                return lines
            lines.append(line)

    def help(self):
        return self.cmd("help")

    def status(self):
        lines = self.cmd("status")
        out = {"lines": lines}
        for line in lines:
            parts = line.split()
            if not parts:
                continue
            if parts[0] == "host" and len(parts) > 1:
                out["host"] = " ".join(parts[1:])
            elif parts[0] == "frame" and len(parts) > 3:
                out["frame"] = int(parts[1])
                out["paused"] = parts[3] == "1"
                out["at"] = parts[5] if len(parts) > 5 else ""
            elif parts[0] == "breakpoint" and len(parts) > 1:
                out["breakpoint"] = int(parts[1], 16)
        return out

    def where(self):
        return self.status()

    def pause(self):
        return self.cmd("pause")

    def resume(self):
        return self.cmd("resume")

    def wait(self, frames):
        return self.cmd(f"wait {int(frames)}")

    def step(self, frames=1):
        return self.cmd(f"step {int(frames)}")

    def waitpause(self):
        return self.cmd("waitpause")

    def read(self, addr, length, cpu=9):
        lines = self.cmd(f"read 0x{int(addr):08X} {int(length)} {int(cpu)}")
        data = bytearray()
        for line in lines:
            parts = line.split()
            if not parts:
                continue
            data.extend(bytes.fromhex("".join(parts[1:])))
        return bytes(data)

    def read32(self, addr, count=1, cpu=9):
        lines = self.cmd(f"read32 0x{int(addr):08X} {int(count)} {int(cpu)}")
        return [int(line.split()[1], 16) for line in lines]

    def write(self, addr, data, cpu=9):
        if isinstance(data, (bytes, bytearray)):
            data = bytes(data).hex()
        return self.cmd(f"write 0x{int(addr):08X} {data} {int(cpu)}")

    def regs(self, cpu=9):
        return self.cmd(f"regs {int(cpu)}")

    def sym(self, name):
        lines = self.cmd(f"sym {name}")
        if not lines:
            return None
        parts = lines[0].split()
        if len(parts) >= 2:
            try:
                return int(parts[1], 16)
            except ValueError:
                pass
        return None

    def bp(self, what):
        return self.cmd(f"bp {what}")

    def bplist(self):
        return self.cmd("bplist")

    def bpclear(self):
        return self.cmd("bpclear")

    def press(self, spec, frames=2):
        return self.cmd(f"press {spec} {int(frames)}")

    def touch(self, x, y, frames=2):
        return self.cmd(f"touch {int(x)} {int(y)} {int(frames)}")

    def release(self):
        return self.cmd("release")

    def screenshot(self, path=None, screen="both", native=True):
        """Capture both screens by default, at native 256x192 per screen.

        screen: "both", "upper" or "lower".
        native=False keeps the host's full-resolution capture.
        """
        if screen not in ("both", "upper", "lower"):
            raise ValueError("screen must be both, upper or lower")
        command = f"screenshot {screen} {'native' if native else 'full'}"
        if path:
            command += f" {path}"
        return self.cmd(command)

    def screenshot_upper(self, path=None, native=True):
        return self.screenshot(path, "upper", native)

    def screenshot_lower(self, path=None, native=True):
        return self.screenshot(path, "lower", native)

    def screenshot_both(self, path=None, native=True):
        return self.screenshot(path, "both", native)

    def screenshot_full(self, path=None):
        return self.screenshot(path, "both", native=False)

    def call(self, addr, *arguments):
        values = " ".join(f"0x{int(value):08X}" for value in arguments)
        return self.cmd(f"call 0x{int(addr):08X} {values}".rstrip())

    def snapshot(self, name):
        return self.cmd(f"snapshot {name}")

    def diff(self, name):
        return self.cmd(f"diff {name}")

    def find(self, value, start=0, length=0):
        return self.cmd(
            f"find 0x{int(value):08X} 0x{int(start):08X} 0x{int(length):08X}")

    def command(self, text):
        return self.cmd(text)

    def close(self):
        try:
            self.cmd("quit")
        except Exception:
            pass
        try:
            self.sock.close()
        except Exception:
            pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int,
                        default=int(os.environ.get("DBG_PORT", "19850")))
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("command", nargs="*")
    args = parser.parse_args()

    try:
        debugger = Debugger(args.host, args.port, args.timeout)
    except OSError as exc:
        print(f"cannot connect to {args.host}:{args.port}: {exc}",
              file=sys.stderr)
        return 1

    try:
        if not args.command:
            print("connected")
            print("\n".join(debugger.help()))
            try:
                while True:
                    line = input("dbg> ").strip()
                    if not line:
                        continue
                    if line in ("quit", "exit", "detach"):
                        break
                    print("\n".join(debugger.cmd(line)))
            except (EOFError, KeyboardInterrupt):
                pass
        else:
            print("\n".join(debugger.cmd(" ".join(args.command))))
        return 0
    finally:
        debugger.close()


if __name__ == "__main__":
    raise SystemExit(main())
