#!/usr/bin/env python3
"""Persistent GDB RSP proxy.

Keeps one connection to a single-attach target (melonDS) and lets local GDB
clients connect/disconnect freely. Local detach/kill packets are answered
locally and do not detach the upstream target.

    python3 debug/generic/transport/rsp_proxy.py --upstream 3333 --listen 3335
    arm-none-eabi-gdb -ex 'target remote :3335'

The proxy also works in front of the recomp RSP listener.
"""

import argparse
import socket
import sys
import threading
import traceback

from rsp import GdbRspClient


def recv_packet(sock, no_ack):
    payload = None
    while True:
        ch = sock.recv(1)
        if not ch:
            return None
        if ch in (b"+", b"-"):
            continue
        if ch == b"\x03":
            return b"\x03"
        if ch != b"$":
            continue

        payload = bytearray()
        while True:
            ch = sock.recv(1)
            if not ch:
                return None
            if ch == b"#":
                break
            payload.append(ch[0])
        high = sock.recv(1)
        low = sock.recv(1)
        if not high or not low:
            return None
        if int(high + low, 16) != (sum(payload) & 0xFF):
            if not no_ack:
                sock.sendall(b"-")
            continue
        if not no_ack:
            sock.sendall(b"+")
        return bytes(payload)


def send_packet(sock, payload, no_ack):
    frame = b"$" + payload + b"#" + f"{sum(payload) & 0xFF:02x}".encode()
    for _ in range(3):
        sock.sendall(frame)
        if no_ack:
            return
        ack = sock.recv(1)
        if ack == b"+":
            return
        if ack == b"-":
            continue
        return


class Proxy:
    def __init__(self, host, port):
        self.upstream = GdbRspClient(host, port)
        self.lock = threading.Lock()

    def handle(self, client):
        no_ack = False
        try:
            while True:
                packet = recv_packet(client, no_ack)
                if packet is None or packet in (b"k",):
                    return
                if packet == b"\x03":
                    self.upstream.sock.sendall(b"\x03")
                    with self.lock:
                        response = self.upstream._recv_packet()
                elif packet == b"QStartNoAckMode":
                    response = b"OK"
                    no_ack = True
                elif packet == b"D" or packet.startswith(b"vKill"):
                    response = b"OK"
                else:
                    with self.lock:
                        response = self.upstream.command(packet)
                send_packet(client, response, no_ack)
        except (ConnectionError, OSError):
            pass
        except Exception:
            traceback.print_exc(file=sys.stderr)
        finally:
            try:
                client.close()
            except Exception:
                pass

    def serve(self, host, port):
        listener = socket.socket()
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.bind((host, port))
        listener.listen(8)
        print(f"[rsp-proxy] 127.0.0.1:{port} -> upstream "
              f"{self.upstream.sock.getpeername()[0]}:"
              f"{self.upstream.sock.getpeername()[1]}", flush=True)
        try:
            while True:
                client, _ = listener.accept()
                threading.Thread(target=self.handle, args=(client,),
                                 daemon=True).start()
        finally:
            listener.close()
            self.upstream.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--upstream-host", default="127.0.0.1")
    parser.add_argument("--upstream", type=int, required=True,
                        help="target RSP port (melonDS ARM9 3333, recomp RSP)")
    parser.add_argument("--listen-host", default="127.0.0.1")
    parser.add_argument("--listen", type=int, required=True,
                        help="local port for GDB/Ghidra/custom clients")
    args = parser.parse_args()

    try:
        proxy = Proxy(args.upstream_host, args.upstream)
    except OSError as exc:
        print(f"cannot connect upstream: {exc}", file=sys.stderr)
        return 1
    try:
        proxy.serve(args.listen_host, args.listen)
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
