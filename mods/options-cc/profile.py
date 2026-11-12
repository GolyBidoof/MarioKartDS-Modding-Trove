# Mario Kart DS Modding Trove
# mods/options-cc/profile.py — MKDS Options/engine ARM9 profile detector
# SPDX-License-Identifier: MIT
# Layout notes: docs/options-class-row.md
"""Locate the Options CLASS-row tables and engine switch by pattern.

No symbol file is read.  Stock EU/US/JP images and pre-modded images share
this data layout (JP is shifted), and the instruction sites are unique byte
patterns.
"""
from __future__ import annotations

import json
import struct
from dataclasses import dataclass
from pathlib import Path

ENGINE = json.loads((Path(__file__).parent / "engine.json").read_text())


def q12(value: float) -> int:
    return int(value * ENGINE["q12_one"] + 0.5)


DEFAULT_ARM9_BASE = 0x02000000

ROW_COUNT_OFF = 0x34
CC_TO_OPTION_OFF = 0x70
OPTION_TO_CC_OFF = 0x8C
UNLOCK_OFF = -0x49C

MIRROR_LOAD = bytes.fromhex("032504e0")
MIRROR_COMPARE = bytes.fromhex("032806d1")
MIRROR_COMPARE_DELTA = 0x688

CC_SWITCH = bytes.fromhex("000090e5100090e5000050e3")
MSG_TABLE = bytes.fromhex("0500060007000800")


class ProfileError(RuntimeError):
    pass


@dataclass(frozen=True)
class Profile:
    arm9_base: int
    main_end: int            # file offset where the autoload payload starts
    row_count: int
    msg_ptr: int
    option_to_cc: int
    cc_to_option: int
    unlock_a: int
    unlock_b: int
    mirror_load: int
    mirror_compare: int
    stock_ids: tuple[int, ...]
    engine_mode: str         # "patch" = stock switch, "present" = already redirected
    engine_hook: int | None
    engine_config: int | None
    engine_resume: int | None
    engine_word: int
    max_speed_50: float
    max_speed_100: float
    max_speed_150: float
    max_speed_200: float
    max_speed_250: float
    max_speed_300: float
    max_speed_50_q12: int
    max_speed_100_q12: int
    max_speed_150_q12: int
    max_speed_200_q12: int
    max_speed_250_q12: int
    max_speed_300_q12: int
    drift_50: int
    drift_100: int
    drift_150: int
    drift_200: int
    drift_250: int
    drift_300: int
    drift_50_mvn: int
    drift_100_mvn: int

    def summary(self) -> list[str]:
        lines = [
            f"profile: row_count={self.row_count:#x} "
            f"msg_ptr={self.msg_ptr:#x} option_to_cc={self.option_to_cc:#x} "
            f"cc_to_option={self.cc_to_option:#x}",
            f"         unlock_a={self.unlock_a:#x} unlock_b={self.unlock_b:#x} "
            f"mirror_load={self.mirror_load:#x} "
            f"mirror_compare={self.mirror_compare:#x}",
        ]
        if self.engine_mode == "patch":
            lines.append(
                f"         engine: hook={self.engine_hook:#x} "
                f"config={self.engine_config:#x} "
                f"resume={self.engine_resume:#x}")
        else:
            lines.append(
                f"         engine: existing redirect at {self.engine_hook:#x} "
                f"({self.engine_word:#x})")
        return lines


def _u16(data: bytes, off: int) -> int:
    return struct.unpack_from("<H", data, off)[0]


def _u32(data: bytes, off: int) -> int:
    return struct.unpack_from("<I", data, off)[0]


def find_all(data: bytes, needle: bytes, limit: int) -> list[int]:
    out = []
    pos = data.find(needle, 0, limit)
    while pos >= 0:
        out.append(pos)
        pos = data.find(needle, pos + 1, limit)
    return out


def module_autoload_start(arm9: bytes) -> int:
    magic = struct.pack("<II", 0xDEC00621, 0x2106C0DE)
    pos = arm9.find(magic)
    if pos < 0:
        raise ProfileError("module params magic not found")
    mp = pos - 0x1C
    return _u32(arm9, mp + 8)


def detect(arm9: bytes, base: int = DEFAULT_ARM9_BASE) -> Profile:
    if base == 0:
        base = DEFAULT_ARM9_BASE
    autoload_start = module_autoload_start(arm9)
    main_end = autoload_start - base
    if not 0 < main_end <= len(arm9):
        raise ProfileError(f"bad autoload start {autoload_start:#x}")

    # The [5,6,7,8] bytes alone occur elsewhere; the row-count u16 and the
    # two table shapes identify the real Options cluster.
    msg = None
    for off in find_all(arm9, MSG_TABLE, main_end):
        if off + 0x9C > main_end:
            continue
        if (_u16(arm9, off + ROW_COUNT_OFF) == 4
                and _u32(arm9, off + CC_TO_OPTION_OFF) == 0
                and _u32(arm9, off + CC_TO_OPTION_OFF + 4) == 1
                and _u32(arm9, off + CC_TO_OPTION_OFF + 8) == 2
                and _u32(arm9, off + OPTION_TO_CC_OFF) == 0
                and _u32(arm9, off + OPTION_TO_CC_OFF + 4) == 1
                and _u32(arm9, off + OPTION_TO_CC_OFF + 8) == 2
                and _u32(arm9, off + OPTION_TO_CC_OFF + 12) == 1):
            msg = off
            break
    if msg is None:
        raise ProfileError("Options CLASS-row table layout not found")

    row_count = base + msg + ROW_COUNT_OFF
    cc_to_option_table = base + msg + CC_TO_OPTION_OFF
    option_to_cc_table = base + msg + OPTION_TO_CC_OFF
    unlock_table = base + msg + UNLOCK_OFF
    msg_table = base + msg

    if _u32(arm9, unlock_table - base) != 0 or \
            _u32(arm9, unlock_table - base + 4) != 1 or \
            _u32(arm9, unlock_table - base + 8) != 2:
        raise ProfileError("unlock-category table layout not found")

    def refs(value: int) -> list[int]:
        return [base + off for off in find_all(arm9, struct.pack("<I", value), main_end)]

    msg_refs = refs(msg_table)
    opt_refs = refs(option_to_cc_table)
    cc_refs = refs(cc_to_option_table)
    unlock_refs = refs(unlock_table)
    if len(msg_refs) != 1 or len(opt_refs) != 1 or len(cc_refs) != 1 or len(unlock_refs) != 2:
        raise ProfileError(
            "table references are not unique: "
            f"msg={len(msg_refs)} opt={len(opt_refs)} cc={len(cc_refs)} "
            f"unlock={len(unlock_refs)}")

    mirror_load = find_all(arm9, MIRROR_LOAD, main_end)
    if len(mirror_load) != 1:
        raise ProfileError(f"expected one Mirror load site, found {len(mirror_load)}")
    mirror_load = base + mirror_load[0]
    cands = find_all(arm9, MIRROR_COMPARE, main_end)
    if not cands:
        raise ProfileError("Mirror compare site not found")
    mirror_compare = min(
        cands, key=lambda off: abs(off - (mirror_load - base + MIRROR_COMPARE_DELTA)))
    if abs((base + mirror_compare) - (mirror_load + MIRROR_COMPARE_DELTA)) > 0x10:
        raise ProfileError("Mirror compare site is not where the stock layout puts it")
    mirror_compare = base + mirror_compare

    stock_ids = tuple(_u16(arm9, msg + 2 * i) for i in range(4))

    engine_mode = None
    engine_hook = engine_config = engine_resume = None
    engine_word = 0
    for off in find_all(arm9, CC_SWITCH, main_end):
        site = off - 4
        if site < 0 or site + 0x30 > main_end:
            continue
        inst = _u32(arm9, site)
        if (inst & 0x0F7F0000) == 0x051F0000:
            u = (inst >> 23) & 1
            imm = inst & 0xFFF
            literal = site + 8 + (imm if u else -imm)
            if not 0 <= literal + 4 <= main_end:
                continue
            config = _u32(arm9, literal)
            ldr100 = _u32(arm9, site + 0x18)
            ldr50 = _u32(arm9, site + 0x24)
            if (ldr100 & 0x0F7F0000) != 0x051F0000 or (ldr50 & 0x0F7F0000) != 0x051F0000:
                continue
            # The stock 100cc pair is conditional (LDREQ/MVNEQ); ignore the
            # condition field when identifying it.
            if (_u32(arm9, site + 0x1C) & 0x0FFFFFFF) != 0x03E04013:
                continue
            if (_u32(arm9, site + 0x28) & 0x0FFFFFFF) != 0x03E04027:
                continue
            engine_mode = "patch"
            engine_hook = base + site
            engine_config = config
            engine_resume = base + site + 0x2C
            engine_word = inst
            break
        if (inst & 0x0F000000) == 0x0A000000:
            # Already redirected by an earlier mod.  Record the site so
            # verification can assert it was not touched; never follow it.
            engine_mode = "present"
            engine_hook = base + site
            engine_word = inst
            break
    if engine_mode is None:
        raise ProfileError("engine CC switch not found")

    speeds = {mode: q12(value) for mode, value in ENGINE["max_speed"].items()}
    drift = {mode: int(value) for mode, value in ENGINE["drift"].items()}

    return Profile(
        arm9_base=base,
        main_end=main_end,
        row_count=row_count,
        msg_ptr=msg_refs[0],
        option_to_cc=opt_refs[0],
        cc_to_option=cc_refs[0],
        unlock_a=unlock_refs[0],
        unlock_b=unlock_refs[1],
        mirror_load=mirror_load,
        mirror_compare=mirror_compare,
        stock_ids=stock_ids,
        engine_mode=engine_mode,
        engine_hook=engine_hook,
        engine_config=engine_config,
        engine_resume=engine_resume,
        engine_word=engine_word,
        max_speed_50=float(ENGINE["max_speed"]["50"]),
        max_speed_100=float(ENGINE["max_speed"]["100"]),
        max_speed_150=float(ENGINE["max_speed"]["150"]),
        max_speed_200=float(ENGINE["max_speed"]["200"]),
        max_speed_250=float(ENGINE["max_speed"]["250"]),
        max_speed_300=float(ENGINE["max_speed"]["300"]),
        max_speed_50_q12=speeds["50"],
        max_speed_100_q12=speeds["100"],
        max_speed_150_q12=speeds["150"],
        max_speed_200_q12=speeds["200"],
        max_speed_250_q12=speeds["250"],
        max_speed_300_q12=speeds["300"],
        drift_50=drift["50"],
        drift_100=drift["100"],
        drift_150=drift["150"],
        drift_200=drift["200"],
        drift_250=drift["250"],
        drift_300=drift["300"],
        drift_50_mvn=-drift["50"] - 1,
        drift_100_mvn=-drift["100"] - 1,
    )
