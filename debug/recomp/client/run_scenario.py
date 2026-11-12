#!/usr/bin/env python3
"""Launch a static recompilation with DBG_PORT set and run a Python scenario.

    python3 debug/recomp/client/run_scenario.py --binary ./build/game scenario.py

The scenario sees DBG_PORT in its environment and can import Debugger from
dbg_client. The child process is terminated when the scenario finishes.
"""

import argparse
import os
import runpy
import socket
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent


def free_port():
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


def wait_for_port(port, timeout, process):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            connection = socket.create_connection(("127.0.0.1", port),
                                                  timeout=0.1)
            connection.close()
            return True
        except OSError:
            if process.poll() is not None:
                return False
            time.sleep(0.05)
    return False


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", required=True,
                        help="path to the static recompilation executable")
    parser.add_argument("--cwd", default=".",
                        help="working directory for the child process")
    parser.add_argument("--port", type=int, default=0,
                        help="debug port (default: choose a free one)")
    parser.add_argument("--timeout", type=float, default=10.0,
                        help="seconds to wait for the debug server")
    parser.add_argument("--env", action="append", default=[],
                        metavar="KEY=VALUE",
                        help="extra environment variable (repeatable)")
    parser.add_argument("--arg", action="append", default=[],
                        help="argument for the child process (repeatable)")
    parser.add_argument("--log", default="dbg_scenario.log",
                        help="child stdout/stderr log")
    parser.add_argument("scenario")
    args = parser.parse_args()

    port = args.port or free_port()
    cwd = Path(args.cwd).expanduser().resolve()
    binary = Path(args.binary).expanduser()
    if not binary.is_absolute():
        binary = (cwd / binary).resolve()
    if not binary.is_file():
        parser.error(f"not a file: {binary}")

    env = dict(os.environ)
    env["DBG_PORT"] = str(port)
    for entry in args.env:
        if "=" not in entry:
            parser.error(f"--env expects KEY=VALUE: {entry}")
        key, value = entry.split("=", 1)
        env[key] = value

    log = open(args.log, "wb")
    process = subprocess.Popen(
        [str(binary), *args.arg],
        cwd=cwd,
        env=env,
        stdout=log,
        stderr=subprocess.STDOUT,
    )

    try:
        if not wait_for_port(port, args.timeout, process):
            if process.poll() is not None:
                print("process exited before opening the debug port",
                      file=sys.stderr)
            else:
                print(f"debug port {port} did not open within "
                      f"{args.timeout:g}s", file=sys.stderr)
            return 1

        os.environ["DBG_PORT"] = str(port)
        sys.path.insert(0, str(HERE))
        runpy.run_path(args.scenario, run_name="__main__")
        return 0
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
        log.close()


if __name__ == "__main__":
    raise SystemExit(main())
