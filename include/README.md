# C headers

> **Project:** Mario Kart DS Modding Trove · **Licence:** MIT · **Notes:** `../docs/`

Reusable structures and constants for the formats documented in `../docs/`. They are header-only, depend only on `<stdint.h>`/`<stddef.h>`, and contain no game data. Fixed-point fields use `Fx32`/`Fx16` from `nitro/fx.h`: both are signed integers with 12 fractional bits, so 4096 means 1.0. Bit positions and masks use `NITRO_BIT(n)` and `NITRO_MASK(width, shift)` from `nitro/bits.h`; RGB555 colour words use `NitroRgb555` and `NITRO_RGB555(r, g, b)` from `nitro/rgb555.h`. File offsets stay hexadecimal; sizes, counts and strides are decimal. Packed on-disk words use a `union { raw; struct { ... } bits; }` overlay, with a size assertion and a runtime layout check in `tests/test_headers.py`. Names such as `NitroG2dCharacterCount` are project-defined descriptive typedefs, not copied Nitro SDK identifiers.

These are independent declarations of publicly documented Nitro/NDS layouts and this project's MKDS observations. Format references are in [`../CREDITS.md`](../CREDITS.md).

| Header | Contents |
|---|---|
| `nitro/nds.h` | NDS header, FNT/FAT, overlay table |
| `nitro/narc.h` | NARC/CARC, LZ77 header |
| `nitro/bmg.h` | MESG/bmg1, INF1/DAT1/MID1 |
| `nitro/blz.h` | BLZ trailer |
| `nitro/dwc.h` | DWC utility archive envelope |
| `nitro/rgb555.h` | RGB555 colour word helpers |
| `nitro/g2d/` | generic NCGR, NCLR/PCMP, NSCR, NCER, NFTR, NANR |
| `nitro/g3d/` | generic NSBMD, NSBTX, NSBCA, NSBTP, NSBTA, NSBMA |
| `nitro/snd/` | generic SDAT, SSEQ, SSAR, SBNK, SWAR, SWAV |
| `nitro/mkds/common/` | shared ids, time units and UI coordinate types |
| `nitro/mkds/course/` | NKM, KCL, SPA |
| `nitro/mkds/save/` | save container and NKDG/NKPG ghost blocks |
| `nitro/mkds/race/` | rank, item, kart, mission and object tables |
| `nitro/mkds/ui/` | BNCL, BNLL, BNBL, KBD/KBDMAP, LLD, NBFC/NBFP |
| `nitro/mkds/files/` | emblem bitmap/builddate and emblem stamp table |
| `nitro/mkds/rom/` | stock AMCP NDS header offsets and sizes |
| `nitro/mkds/bmg/` | generated BMG message-id enums |

The first group (`nds`, `narc`, `bmg`, `blz`, `dwc`, `g2d`, `g3d`, `snd`) is
generic Nitro format types. Everything under `nitro/mkds/` corresponds to a
concrete MKDS file, save block or shared MKDS identifier space. The top-level
`mkds_*.h` and `save.h` names are umbrellas.

Mod-specific headers live with the mod. For example,
`mods/options-cc/source/options_class_row.h.tmpl` is copied into the rendered
options-cc source tree and included by `options.h`. The headers here are for
tools that read or write the generic Nitro formats; they are not compiled into
the ARM9 patch.
