# Mario Kart DS Modding Trove
# tools/ctables/common/harness.py — compile a typed C table and compare its bytes
# SPDX-License-Identifier: MIT
"""Compile a C source that writes one binary file, then compare it byte-for-byte."""
from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
CC = shutil.which("cc") or shutil.which("clang") or shutil.which("gcc")


def compile_and_write(source: str, output: Path) -> str:
    """Compile a table program and run it, writing ``output``. Return error text."""
    if not CC:
        raise RuntimeError("no host C compiler")
    with tempfile.TemporaryDirectory() as tmp:
        exe = Path(tmp) / "table_writer"
        build = subprocess.run(
            [CC, "-std=c11", "-I", str(REPO / "include"),
             "-x", "c", "-", "-o", str(exe)],
            input=source, text=True, capture_output=True)
        if build.returncode != 0:
            return build.stderr
        run = subprocess.run([str(exe), str(output)], capture_output=True)
        if run.returncode != 0:
            return run.stderr.decode("utf-8", "replace")
        return ""


def compile_and_compare(source: str, expected: bytes) -> tuple[bool, bytes, str]:
    """Return (ok, produced_bytes, compiler_or_runtime_error)."""
    if not CC:
        raise RuntimeError("no host C compiler")
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        exe = tmp_path / "table_writer"
        out = tmp_path / "out.bin"
        build = subprocess.run(
            [CC, "-std=c11", "-I", str(REPO / "include"),
             "-x", "c", "-", "-o", str(exe)],
            input=source, text=True, capture_output=True)
        if build.returncode != 0:
            return False, b"", build.stderr
        run = subprocess.run([str(exe), str(out)], capture_output=True)
        if run.returncode != 0:
            return False, b"", run.stderr.decode("utf-8", "replace")
        produced = out.read_bytes() if out.exists() else b""
        return produced == expected, produced, ""
