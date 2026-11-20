# Mario Kart DS Modding Trove
# tests/test_headers.py — C format headers compile standalone
# SPDX-License-Identifier: MIT
"""Compile every format header with a host C compiler; skip if none is found."""
import re
import shutil
import subprocess
import tempfile
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
    def test_headers_compile_together(self):
        headers = sorted((REPO / "include").rglob("*.h"))
        source = "\n".join(
            f'#include "{h.relative_to(REPO / "include").as_posix()}"'
            for h in headers)
        result = compile_source(source + "\nint main(void) { return 0; }\n")
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_header_style(self):
        for header in sorted((REPO / "include").rglob("*.h")):
            text = header.read_text()
            rel = header.relative_to(REPO / "include").as_posix()
            self.assertNotRegex(
                text, r"\b[A-Z0-9_]+_SHIFT\s*=\s*\d+",
                f"{rel}: use a union bitfield overlay, not SHIFT/WIDTH enums")
            self.assertNotRegex(
                text, r"offsetof\([^)]*\)\s*==\s*[1-9][0-9]*",
                f"{rel}: offsets must be hexadecimal")
            self.assertNotRegex(
                text, r"#define\s+[A-Z0-9_]*_OFFSET\s+[1-9][0-9]*u?",
                f"{rel}: *_OFFSET constants must be hexadecimal")

    @unittest.skipUnless(CC, "no host C compiler")
    def test_bitfield_overlays_layout(self):
        source = r"""
#include "nitro/mkds/save/save.h"
#include "nitro/mkds/race/mission.h"
#include "nitro/mkds/common/ui_common.h"
#include "nitro/mkds/course/spa.h"
#include "nitro/snd/sdat.h"
int main(void) {
    SavGpInfo0 gp = {0};
    gp.bits.valid = 1;
    gp.bits.character = 0x12;
    gp.bits.kart = 0x34;
    gp.bits.rank_points = 0x56;
    gp.bits.rank = 0x78;
    if (gp.raw != (1u | (0x12u << 1) | (0x34u << 8) |
                   (0x56u << 16) | (0x78u << 24)))
        return 1;

    MkdsMissionFlags mf = {0};
    mf.bits.mirror = 1;
    if (mf.raw != (1u << 4))
        return 2;

    MkdsUiCoord coord = {0};
    coord.bits.value = 0xABC;
    coord.bits.origin = 2;
    coord.bits.param = 1;
    if (coord.raw != (0xABCu | (2u << 12) | (1u << 14)))
        return 3;

    SpaTextureParams tex = {0};
    tex.bits.format = 3;
    tex.bits.reference_id = 0x5A;
    if (tex.raw != (3u | (0x5Au << 18)))
        return 4;

    SdatWaveArcInfo wa = {0};
    wa.bits.file_id = 0x123456;
    wa.bits.load_individually = 1;
    if (wa.raw != (0x123456u | (1u << 24)))
        return 5;

    return 0;
}
"""
        with tempfile.TemporaryDirectory() as tmp:
            exe = Path(tmp) / "bitfields"
            build = subprocess.run(
                [CC, "-std=c11", "-I", str(REPO / "include"),
                 "-x", "c", "-", "-o", str(exe)],
                input=source, text=True, capture_output=True)
            self.assertEqual(build.returncode, 0, build.stderr)
            run = subprocess.run([str(exe)], capture_output=True)
            self.assertEqual(run.returncode, 0,
                             "bitfield overlay layout differs from the file ABI")

    @unittest.skipUnless(CC, "no host C compiler")
    def test_format_helpers(self):
        source = r"""
#include "nitro/mkds/files/emblemtable.h"
#include "nitro/mkds/race/grpconf.h"
#include "nitro/mkds/race/kartappear.h"
#include "nitro/mkds/files/misc.h"
#include "nitro/mkds/save/save.h"
#include "nitro/mkds/race/staffghost.h"
#include "nitro/mkds/common/time.h"
int main(void) {
    if (mkds_frames_to_milliseconds(60) != 1000)
        return 1;
    if (mkds_clock_to_milliseconds(mkds_clock_from_milliseconds(93456)) != 93456)
        return 2;

    MkdsEmblemBitmap emblem = {0};
    emblem.rows[3][2] = 0x5A;
    if (mkds_emblem_pixel(&emblem, 4, 3) != 0x0A)
        return 3;
    if (mkds_emblem_pixel(&emblem, 5, 3) != 0x05)
        return 4;

    if (sizeof(MkdsObjectGroupConfig) != 16)
        return 5;
    if (sizeof(MkdsEmblemStampPlacement) != 8)
        return 6;
    if (MKDS_KART_APPEAR_INDEX(36, 12) != 486)
        return 7;
    if (MKDS_STAFF_TIME_SLOT(40) != 39)
        return 8;

    SavIdentityBlock identity = {0};
    identity.unlock_bits[2] = 0x02;   /* bit 17 -> level 2 */
    if (sav_kart_unlock_level(&identity) != 2)
        return 9;
    identity.unlock_bits[2] = 0x0E;   /* bits 17, 18, 19 -> level 4 */
    if (sav_kart_unlock_level(&identity) != 4)
        return 10;
    return 0;
}
"""
        with tempfile.TemporaryDirectory() as tmp:
            exe = Path(tmp) / "helpers"
            build = subprocess.run(
                [CC, "-std=c11", "-I", str(REPO / "include"),
                 "-x", "c", "-", "-o", str(exe)],
                input=source, text=True, capture_output=True)
            self.assertEqual(build.returncode, 0, build.stderr)
            run = subprocess.run([str(exe)], capture_output=True)
            self.assertEqual(run.returncode, 0, "format helper values differ")

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
