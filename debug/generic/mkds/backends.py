#!/usr/bin/env python3
"""Generic transport adapters for the MKDS custom layer."""

from __future__ import annotations

import os
import sys
from typing import Protocol

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "transport"))

from rsp import GdbRspClient  # noqa: E402


class Unsupported(RuntimeError):
    pass


class Backend(Protocol):
    capabilities: set[str]

    def read(self, address: int, length: int) -> bytes: ...
    def write(self, address: int, data: bytes) -> None: ...
    def read32(self, address: int) -> int: ...
    def write32(self, address: int, value: int) -> None: ...
    def command(self, text: str): ...
    def screenshot(self, path: str, screen: str, native: bool): ...
    def press(self, spec: str, frames: int): ...
    def close(self) -> None: ...


class RspBackend:
    """A persistent GDB RSP connection (recomp RSP, melonDS, or proxy)."""

    capabilities = {"nav"}

    def __init__(self, host="127.0.0.1", port=3333):
        self.rsp = GdbRspClient(host, port)

    def read(self, address, length):
        return self.rsp.read(address, length)

    def write(self, address, data):
        self.rsp.write(address, bytes(data))

    def read32(self, address):
        return self.rsp.read32(address)

    def write32(self, address, value):
        self.rsp.write32(address, value)

    def command(self, text):
        raise Unsupported("RSP has no arbitrary command channel")

    def screenshot(self, path, screen, native):
        raise Unsupported(
            "RSP exposes CPU memory, not the emulator's composited framebuffer")

    def press(self, spec, frames):
        raise Unsupported("RSP has no input-injection channel")

    def close(self):
        self.rsp.close()
