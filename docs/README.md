# Documentation

> **Project:** Mario Kart DS Modding Trove · **Licence:** MIT

Format and research notes for the data this framework reads and writes. No game data is included; the notes describe structures and observations so the tools can be reused or the work verified.

These notes are written for this project. Generic Nitro/BMG layouts follow public documentation; the Options/engine addresses are this project's observations. Format references are in [`../CREDITS.md`](../CREDITS.md).

- [Project structure](structure.md) — generic Nitro types versus MKDS file types.
- [Header index](header-index.md) — every public header, the stock file it models, and its codec.
- [Generic Nitro formats](generic/README.md) — headers and docs for non-MKDS Nitro resources.
- [MKDS file formats](mkds/README.md) — headers and docs for concrete stock files and save blocks.
- [Nitro ROM formats](generic/nitro.md) — NDS header, FNT/FAT, BLZ, NARC/CARC, LZ77.
- [BMG message banks](mkds/bmg.md) — MESG/bmg1, INF1/DAT1, MKDS `rule.bmg`, repair and append rules.
- [Nitro G2D resources](generic/formats-g2d.md) — NCGR, NCLR/PCMP, NSCR, NCER, NFTR and NANR.
- [Nitro G3D resources](generic/formats-g3d.md) — NSBMD, NSBTX, NSBCA, NSBTP, NSBTA and NSBMA.
- [Nitro sound containers](generic/formats-audio.md) — SDAT, SSEQ, SSAR, SBNK, SWAR and SWAV.
- [MKDS course files](mkds/formats-mkds-course.md) — NKM, KCL and SPA.
- [MKDS JNLib UI files](mkds/formats-mkds-ui.md) — BNCL, BNLL, BNBL, keyboard, emblem layout and banner font resources.
- [MKDS race/save-adjacent data](mkds/formats-mkds-race.md) — ghosts, missions, rank tables, item slots and parameter binaries.
- [MKDS flash save](mkds/formats-save.md) — `.sav` block map, NKSY/NKEM/NKGP/NKTA/NKMR/NKFL/NKFE/NKPG/NKDG records.
- [Save image map](mkds/save-file-map.md) — every offset, block, index space and editable C representation.
- [Shared MKDS identifier spaces](mkds/formats-ids.md) — stage course ids, mission course ids and shared enums.
- [Editable G2D image projects](g2d-projects.md) — indexed BMP + palette + JSON round-trips for NCGR/NCLR, NCER and NSCR.
- [NFTR fonts and NANR animations](g2d-fonts-anim.md) — glyph sheets, animation frames, previews and editable JSON.
- [Typed C tables and exact rebuilds](formats-ctables.md) — compiling typed tables back into the original binaries.
- [Format headers and Toolbox](formats-toolbox-map.md) — how the C headers relate to the C# models.
- [ARM9 autoloads](arm9-autoloads.md) — module params, autoload list and the runtime-address mapping used by the verifier.
- [Options class row](options-class-row.md) — the MKDS tables and engine switch this repository patches, including the per-region observations.
- [Tooling API](tools.md) — overlay reading, DWC utility archives, Thumb `BL` decoding, and the overlay-mod profile recipe.

The generic implementations live in `tools/nds.py`, `tools/bmg.py`, `tools/bmgset.py`, `tools/mods.py` and `tools/patch.py`. Game-specific detection lives with the mod that needs it, e.g. `mods/options-cc/profile.py`.

Overlay profiles can use `tools.nds.overlay_from_nds(path, id)` to read an
overlay's load address and decompressed bytes, and `tools.arm.thumb_bl_target`
to resolve a Thumb `BL` target from a signature.

The Nitro format structures are available as reusable C headers in [`../include/`](../include/). Generic Nitro types live under `include/nitro/g2d/`, `g3d/`, `snd/` and the top-level container headers; concrete MKDS file types live under `include/nitro/mkds/{common,course,save,race,ui,files,rom,bmg}/`. The same split is used by `tools/ctables/{common,generic,mkds}/`. The top-level `mkds_*.h` and `save.h` names are umbrellas. Fixed-point fields use `Fx32`/`Fx16` (4096 = 1.0) and bitfields use `NITRO_BIT()`/`NITRO_MASK()`. Mod-specific headers live with the mod, e.g. `mods/options-cc/source/options_class_row.h.tmpl`.

For where new findings, tools, headers, mods and debug routes should go, see [`../CONTRIBUTING.md`](../CONTRIBUTING.md).
