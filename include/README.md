# C headers

> **Project:** Mario Kart DS Modding Trove · **Licence:** MIT · **Notes:** `../docs/`

Reusable structures and constants for the formats documented in `../docs/`. They are header-only, depend only on `<stdint.h>`/`<stddef.h>`, and contain no game data.

These are independent declarations of publicly documented Nitro/NDS layouts. Format references are in [`../CREDITS.md`](../CREDITS.md).

| Header | Contents |
|---|---|
| `nitro/nds.h` | NDS header, FNT/FAT, overlay table |
| `nitro/narc.h` | NARC/CARC, LZ77 header |
| `nitro/bmg.h` | MESG/bmg1, INF1/DAT1/MID1 |
| `nitro/blz.h` | BLZ trailer |

Mod-specific headers live with the mod. For example, `mods/options-cc/source/options_class_row.h.tmpl` is copied into the rendered options-cc source tree and included by `options.h`. The headers here are for tools that read or write the generic Nitro formats; they are not compiled into the ARM9 patch.

Mod-specific addresses live with the mod; see `../docs/options-class-row.md`.
