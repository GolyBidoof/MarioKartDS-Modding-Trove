# Mario Kart DS Modding Trove
# tests/test_headers.py — C format headers compile standalone
# SPDX-License-Identifier: MIT
"""Compile every format header with a host C compiler; skip if none is found."""
import re
import shutil
import subprocess
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
CC = shutil.which("cc") or shutil.which("clang") or shutil.which("gcc")


def compile_source(source: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [CC, "-std=c11", "-I", str(REPO / "include"),
         "-fsyntax-only", "-x", "c", "-"],
        input=source, text=True, capture_output=True)


class HeaderTests(unittest.TestCase):
    @unittest.skipUnless(CC, "no host C compiler")
    def test_headers_compile(self):
        for header in sorted((REPO / "include").rglob("*.h")):
            rel = header.relative_to(REPO / "include").as_posix()
            result = compile_source(
                f'#include "{rel}"\nint main(void) {{ return 0; }}\n')
            self.assertEqual(result.returncode, 0,
                             f"{rel}:\n{result.stderr}")

    @unittest.skipUnless(CC, "no host C compiler")
    def test_mod_header_compiles(self):
        header = (REPO / "mods" / "options-cc" / "source"
                  / "options_class_row.h.tmpl")
        text = re.sub(r"\{\{profile\.[^}]+\}\}", "0.0", header.read_text())
        result = compile_source(text + "\nint main(void) { return 0; }\n")
        self.assertEqual(result.returncode, 0,
                         f"options_class_row.h:\n{result.stderr}")


if __name__ == "__main__":
    unittest.main()
