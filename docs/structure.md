# Project structure

> **Project:** Mario Kart DS Modding Trove · **Licence:** MIT

The code separates **generic Nitro format types** from **MKDS file types**. The
same split is used in `include/`, `tools/ctables/` and the documentation index.

## Headers

```text
include/nitro/
  bits.h, fx.h, rgb555.h        shared primitives
  nds.h, narc.h, blz.h, bmg.h   generic containers and compression
  dwc.h                         DWC utility archive envelope
  g2d/                          generic Nitro G2D resources
  g3d/                          generic Nitro G3D resources
  snd/                          generic Nitro sound resources
  mkds/
    common/                     shared MKDS ids, time units, UI coordinate types
    course/                     NKM, KCL and SPA
    save/                       save container and ghost blocks
    race/                       rank, item, kart, mission and object tables
    ui/                         JNLib UI lists, keyboard, emblem layout, banners
    files/                      standalone emblem/builddate files
    rom/                        stock MKDS ROM header constants
    bmg/                        generated per-bank BMG message ids
```

Include the domain path directly, for example
`nitro/mkds/race/ranktime.h`.

## C-table generators

```text
tools/ctables/
  common/                       C formatting, enum-name lookup, compile harness
  generic/                      g2d_tables, g3d_tables, snd_tables
  mkds/                         course, save, UI and small-table emitters
  edit.py                       extract/build entry point
```

Generic emitters read a Nitro resource and rebuild it. MKDS emitters read a
specific stock file and rebuild it. `edit.py` detects the family from the
filename or magic and dispatches to the matching module.

## Documentation

| Area | Documents |
|---|---|
| Generic Nitro | [nitro.md](generic/nitro.md), [formats-g2d.md](generic/formats-g2d.md), [formats-g3d.md](generic/formats-g3d.md), [formats-audio.md](generic/formats-audio.md) |
| MKDS files | [formats-mkds-course.md](mkds/formats-mkds-course.md), [formats-mkds-race.md](mkds/formats-mkds-race.md), [formats-mkds-ui.md](mkds/formats-mkds-ui.md), [formats-save.md](mkds/formats-save.md), [save-file-map.md](mkds/save-file-map.md), [formats-ids.md](mkds/formats-ids.md) |
| Tools and indexes | [header-index.md](header-index.md), [formats-ctables.md](formats-ctables.md), [tools.md](tools.md) |

The per-file index in [header-index.md](header-index.md) maps every header to
the stock file it models and the codec that reads it.
