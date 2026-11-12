#!/usr/bin/env python3
"""Minimal GDB Remote Serial Protocol client.

Works with our recomp RSP listener and melonDS's built-in GDB stub. It is a
transport only: it knows registers/memory/breakpoints, not Mario Kart.
"""

import socket
import time


class RspError(RuntimeError):
    pass


class GdbRspClient:
    def __init__(self, host="127.0.0.1", port=3333, timeout=10.0):
        self.sock = socket.create_connection((host, port), timeout=timeout)
        self.sock.settimeout(timeout)
        self._buffer = bytearray()
        # melonDS expects the initial client ack; our server ignores it.
        self.sock.sendall(b"+")

    def _read_byte(self):
        while not self._buffer:
            chunk = self.sock.recv(4096)
            if not chunk:
                raise RspError("target disconnected")
            self._buffer.extend(chunk)
        return self._buffer.pop(0)

    def _read_exact(self, count):
        return bytes(self._read_byte() for _ in range(count))

    def _parse_packet(self):
        payload = bytearray()
        while True:
            ch = self._read_byte()
            if ch == ord("#"):
                break
            payload.append(ch)
        high = self._read_byte()
        low = self._read_byte()
        expected = int(bytes([high, low]), 16)
        if expected != (sum(payload) & 0xFF):
            self.sock.sendall(b"-")
            return None
        self.sock.sendall(b"+")
        return bytes(payload)

    def _send_packet(self, payload):
        if isinstance(payload, str):
            payload = payload.encode()
        checksum = sum(payload) & 0xFF
        frame = b"$" + payload + b"#" + f"{checksum:02x}".encode()
        for _ in range(3):
            self.sock.sendall(frame)
            first = self._read_byte()
            if first == ord("+"):
                return None
            if first == ord("-"):
                continue
            if first == ord("$"):
                # Some stubs (older melonDS) answer without a separate ack.
                return self._parse_packet()
            raise RspError(f"unexpected reply byte {bytes([first])!r}")

    def _recv_packet(self):
        while True:
            ch = self._read_byte()
            if ch in (ord("+"), ord("-")):
                continue
            if ch != ord("$"):
                continue
            packet = self._parse_packet()
            if packet is not None:
                return packet

    def command(self, payload):
        response = self._send_packet(payload)
        if response is not None:
            return response
        return self._recv_packet()

    def read(self, address, length):
        data = bytearray()
        while length:
            chunk = min(length, 0x400)
            response = self.command(f"m{int(address):x},{chunk:x}")
            if response.startswith(b"E"):
                raise RspError(response.decode("ascii", "replace"))
            if len(response) != chunk * 2:
                raise RspError(f"short read at {address:#x}: {len(response)//2}")
            data.extend(bytes.fromhex(response.decode("ascii")))
            address += chunk
            length -= chunk
        return bytes(data)

    def write(self, address, data):
        if not isinstance(data, (bytes, bytearray)):
            data = bytes(data)
        for offset in range(0, len(data), 0x400):
            chunk = bytes(data[offset:offset + 0x400])
            response = self.command(
                f"M{int(address) + offset:x},{len(chunk):x}:{chunk.hex()}")
            if response not in (b"OK", b""):
                raise RspError(response.decode("ascii", "replace"))

    def read32(self, address):
        return int.from_bytes(self.read(address, 4), "little")

    def write32(self, address, value):
        self.write(address, int(value & 0xFFFFFFFF).to_bytes(4, "little"))

    def registers(self):
        response = self.command("g")
        if response.startswith(b"E"):
            raise RspError(response.decode("ascii", "replace"))
        if len(response) != 39 * 8:
            raise RspError(f"unexpected register packet length {len(response)}")
        values = []
        for i in range(39):
            values.append(int.from_bytes(
                bytes.fromhex(response[i * 8:(i + 1) * 8].decode("ascii")),
                "little"))
        return values

    def breakpoint(self, address, kind=4):
        return self.command(f"Z0,{int(address):x},{int(kind)}")

    def remove_breakpoint(self, address, kind=4):
        return self.command(f"z0,{int(address):x},{int(kind)}")

    def continue_(self, timeout=None):
        if timeout is not None:
            self.sock.settimeout(timeout)
        self._send_packet("c")
        return self._recv_packet()

    def step(self, timeout=None):
        if timeout is not None:
            self.sock.settimeout(timeout)
        self._send_packet("s")
        return self._recv_packet()

    def interrupt(self):
        self.sock.sendall(b"\x03")
        return self._recv_packet()

    def close(self):
        try:
            self.sock.sendall(b"$D#44")
            self._read_exact(1)
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
