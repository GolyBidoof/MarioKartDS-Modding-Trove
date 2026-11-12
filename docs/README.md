# Documentation

> **Project:** Mario Kart DS Modding Trove · **Licence:** MIT

Format and research notes for the data this framework reads and writes. No game data is included; the notes describe structures and observations so the tools can be reused or the work verified.

These notes are written for this project. Generic Nitro/BMG layouts follow public documentation; the Options/engine addresses are this project's observations. Format references are in [`../CREDITS.md`](../CREDITS.md).

- [Nitro ROM formats](nitro.md) — NDS header, FNT/FAT, BLZ, NARC/CARC, LZ77.
- [BMG message banks](bmg.md) — MESG/bmg1, INF1/DAT1, MKDS `rule.bmg`, repair and append rules.
- [ARM9 autoloads](arm9-autoloads.md) — module params, autoload list and the runtime-address mapping used by the verifier.
- [Options class row](options-class-row.md) — the MKDS tables and engine switch this repository patches, including the per-region observations.

The generic implementations live in `tools/nds.py`, `tools/bmg.py`, `tools/bmgset.py`, `tools/mods.py` and `tools/patch.py`. Game-specific detection lives with the mod that needs it, e.g. `mods/options-cc/profile.py`.

The Nitro format structures are available as reusable C headers in [`../include/`](../include/). Mod-specific headers live with the mod, e.g. `mods/options-cc/source/options_class_row.h.tmpl`.

For where new findings, tools, headers, mods and debug routes should go, see [`../CONTRIBUTING.md`](../CONTRIBUTING.md).
