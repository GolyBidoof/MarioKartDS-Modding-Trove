#!/usr/bin/env python3
"""Recomp-only text-protocol backend for the generic MKDS custom layer."""

from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "client"))
sys.path.insert(0, os.path.join(HERE, "..", "..", "generic", "mkds"))

from dbg_client import Debugger  # noqa: E402
from backends import Backend, Unsupported  # noqa: E402


class RecompBackend:
    """The recomp text protocol (dbg_client)."""

    capabilities = {"nav", "screenshot", "input", "command"}

    def __init__(self, host="127.0.0.1", port=None):
        self.debugger = Debugger(host=host, port=port)

    def read(self, address, length):
        return self.debugger.read(address, length)

    def write(self, address, data):
        self.debugger.write(address, bytes(data))

    def read32(self, address):
        return self.debugger.read32(address)[0]

    def write32(self, address, value):
        self.debugger.write(address, int(value & 0xFFFFFFFF).to_bytes(4, "little"))

    def command(self, text):
        return self.debugger.cmd(text)

    def screenshot(self, path, screen, native):
        return self.debugger.screenshot(path, screen, native)

    def press(self, spec, frames):
        return self.debugger.press(spec, frames)

    def close(self):
        self.debugger.close()
