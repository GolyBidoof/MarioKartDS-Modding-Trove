# Options class row

> **Project:** Mario Kart DS Modding Trove · **Licence:** MIT · **Code:** `mods/options-cc/profile.py`, `mods/options-cc/source/*.tmpl`

The MKDS **Options / VS-rules** class row. This is not the 2×2 GP class-select tile screen; that screen has its own fixed layout.

## Table layout

Relative to the CLASS message-id table at `M`:

| Offset | Meaning | Stock value |
|---|---|---|
| `M + 0x00` | message ids (`uint16_t`) | 5, 6, 7, 8 |
| `M + 0x34` | row option count (`uint16_t`) | 4 |
| `M + 0x70` | CC mode → row option (`uint32_t`) | 0, 1, 2 |
| `M + 0x8C` | row option → CC mode (`uint32_t`) | 0, 1, 2, 1 |
| `M - 0x49C` | CC mode → unlock category (`uint32_t`) | 0, 1, 2 |

The fourth `option → CC` value is handled by a separate `cmp r0, #3` path, which is why the Mirror site is patched independently of the table.

## Addresses observed

| | EU / US | JP |
|---|---|---|
| message table `M` | `0x0215CC8C` | `0x0215CDAC` |
| row count | `0x0215CCC0` | `0x0215CDE0` |
| message-id pointer literal | `0x0216DC0C` (EU), `0x0216DBEC` (US) | `0x0216DC8C` |
| option → CC literal | `0x0211C59C` | `0x0211C6C0` |
| CC → option literal | `0x0211BF84` | `0x0211C0A8` |
| unlock category literals | `0x021187C4`, `0x02118B44` | `0x021188E8`, `0x02118C68` |
| Mirror load site | `0x0211BE7A` | `0x0211BF9E` |
| Mirror compare site | `0x0211C502` | `0x0211C626` |

These are observations of the retail images, not constants the tool requires: `mods/options-cc/profile.py` finds them by pattern. `python3 apply.py <rom> --dry-run` prints the values it found for a given image.

## How the tables were found

1. Scan the ARM9 main image for the `uint16_t` sequence `5,6,7,8`. It occurs in several places, so the candidate must also have the row count `4` at `+0x34` and the two table shapes at `+0x70` and `+0x8C`.
2. The table addresses appear in literal pools: once for the message table, the option→CC table and the CC→option table, and twice for the unlock table. Those literal-word addresses are what the patch overwrites.
3. Mirror load is the unique `03 25 04 e0` (`movs r5,#3; b`). Mirror compare is `03 28 06 d1` (`cmp r0,#3; bne`) at `Mirror load + 0x688`.

## Patched values

- row count: 7
- message ids: `5, 6, 7, 24, 25, 26, 8`
- option → CC: `0, 1, 2, 3, 4, 5, 2`
- CC → option: `0, 1, 2, 3, 4, 5`
- CC → unlock: `0, 1, 2, 2, 2, 2`
- Mirror load/compare opcodes: `0x2506` / `0x2806`

## Engine switch

`driver_initPhysicalParams` reads the race CC mode from the pointer at `gRaceMultiConfig`, `+0x10`. `r5` scales `maxSpeed` in Q12; `r4` is added to `drift`.

Q12 means `4096 = 1.0`. The source values are decimal floats in `mods/options-cc/engine.json`; the tool converts them to Q12 for the ARM patch, because the ARM9 has no FPU and no floating-point code is needed. The C header exposes the speeds as EABI `float` (`mkds_f32`) and provides `MKDS_Q12()`; the generated assembly uses the Q12 integers. The drift values are the integer added to `->drift` in the game's field units, not Q12.

| Mode | maxSpeed (float) | maxSpeed (Q12) | drift |
|---|---|---|---|
| 50cc | 0.70 | 2867 | −40 |
| 100cc | 0.85 | 3482 | −20 |
| 150cc | 1.00 | 4096 | 0 |
| 200cc | 1.15 | 4710 | +20 |
| 250cc | 1.30 | 5325 | +40 |
| 300cc | 1.45 | 5939 | +60 |

The stock image encodes the 100cc pair conditionally (`LDREQ`/`MVNEQ`); the detector masks the condition field. The 50cc pair is unconditional.

| | EU / US | JP |
|---|---|---|
| hook site | `0x020726E4` | `0x02072824` |
| race-config pointer | `0x021759C0` (EU), `0x021759A0` (US) | `0x02175A40` |
| resume address | `0x02072710` | `0x02072850` |

If the hook site is already an ARM branch, the image has an earlier engine redirect. The mod's engine source is skipped and the word is recorded so verification can assert it stayed byte-identical.

## Notes

These are research observations of the retail images. No copyrighted game data is included. The tools that use this layout are `mods/options-cc/profile.py`, `mods/options-cc/source/options.c.tmpl`, `mods/options-cc/source/engine.s.tmpl` and `mods/options-cc/verify.py`.
