# Mario Kart DS Modding Trove
# mods/options-cc/verify.py — output checks for the Options mod
# SPDX-License-Identifier: MIT
"""Checks that the options-cc mod landed in an output ROM."""
from tools.verify import check


def verify(ctx):
    p = ctx.profile
    check(len(ctx.new_ids) == 3, "expected three label ids")

    check(ctx.u16(p.row_count) == 7, "CLASS row count is not 7")
    check(ctx.u16(p.mirror_load) == 0x2506, "Mirror load site not patched")
    check(ctx.u16(p.mirror_compare) == 0x2806, "Mirror compare site not patched")

    ids = [p.stock_ids[0], p.stock_ids[1], p.stock_ids[2],
           *ctx.new_ids, p.stock_ids[3]]
    ptr = ctx.u32(p.msg_ptr)
    got = [ctx.u16(ptr + i * 2) for i in range(7)]
    check(got == ids, f"CLASS message ids {got} != {ids}")

    for address, want, label in (
        (p.option_to_cc, [0, 1, 2, 3, 4, 5, 2], "option->cc"),
        (p.cc_to_option, [0, 1, 2, 3, 4, 5], "cc->option"),
        (p.unlock_a, [0, 1, 2, 2, 2, 2], "unlock A"),
        (p.unlock_b, [0, 1, 2, 2, 2, 2], "unlock B"),
    ):
        ptr = ctx.u32(address)
        got = [ctx.u32(ptr + i * 4) for i in range(len(want))]
        check(got == want, f"{label} table {got} != {want}")

    if p.engine_mode == "patch":
        inst = ctx.u32(p.engine_hook)
        check(inst >> 24 == 0xEA, "engine hook is not an ARM branch")
        imm = inst & 0xFFFFFF
        if imm & 0x800000:
            imm -= 0x1000000
        target = (p.engine_hook + 8 + imm * 4) & 0xFFFFFFFF
        try:
            ctx.image.offset(target)
        except KeyError:
            check(False, f"engine branch target {target:#x} is outside the image")
    else:
        check(ctx.u32(p.engine_hook) == p.engine_word,
              "the pre-existing engine redirect was disturbed")
