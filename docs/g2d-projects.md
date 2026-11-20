# Editable G2D asset projects

> **Project:** Mario Kart DS Modding Trove · **Tools:** `tools/g2d_asset.py`, `tools/g2d_bulk.py` · **Licence:** MIT

This is the two-way image workflow for Nitro G2D assets. One folder is one
asset bundle: the indexed image carries the palette, the composed image shows
the actual sprite/screen, and `asset.json` keeps only the header fields and
structural data that an image cannot hold.

The format itself is the standard Nitro G2D layout documented in
[`formats-g2d.md`](generic/formats-g2d.md). NitroPaint, Texim and Tinke implement the
same conversions; this tool exists so the project is scriptable, keeps the
MKDS header quirks, and can bridge files that live in another archive.

## One project per consumer

```sh
python3 tools/g2d_asset.py export \
    --ncgr select_character_gp_m.nce.ncgr \
    --palette ../CharacterKartSelect_arc/select_character_gp_m_o.NCLR \
    --ncer select_character_gp_m.nce.ncer \
    -o out/select_character_gp_m

python3 tools/g2d_asset.py describe out/select_character_gp_m
python3 tools/g2d_asset.py rebuild out/select_character_gp_m -o rebuilt
```

An asset folder is driven by the thing that uses the tileset:

| Consumer | Files |
|---|---|
| NSCR screen | `screen.bmp`, `source/`, `asset.json` |
| NCER cells | `sprite_sheet.bmp`, `cells/cell_XXX.bmp`, `cells.json`, `source/`, `asset.json` |
| NCGR without a consumer | `tilesheet.bmp`, `source/`, `asset.json` |

There is no separate `tilesheet.bmp` next to `screen.bmp` or `sprite_sheet.bmp`,
and no `.pal`, `README.txt`, `_preview` or `_indexed` duplicates.

`source/` holds the original atomic NCGR/NCLR/NCER/NSCR files. `asset.json`
contains only non-derivable data:

```json
{
  "sources": {"ncgr": "...", "nclr": "...", "nscr": "..."},
  "ncgr": {"bpp": 4, "tile_count": 32, "per_row": 1},
  "nclr": {"bank_size": 16, "bank_count": 16},
  "nscr": {"width": 256, "height": 256, "color_mode": 0,
           "screen_format": 0, "entries": [{"tile": 1}, ...]}
}
```

Magic, BOM, version, file/block sizes, counts and offsets are regenerated.
Only real deviations (for example the legacy `dbgfont` header) are stored under
`quirks`.

An indexed BMP carries the complete palette in its own palette table. For 4bpp
assets all 16-colour banks are concatenated into the 256-entry BMP palette and
composed pixels use `bank * 16 + colour`. There are no palette sidecars.

## How consumers are paired

The bulk exporter works consumer-first. Every NSCR and NCER picks its NCGR and
NCLR, preferring the same directory, then the same archive family, then the
base archive. Object cells prefer `_o` graphics; background screens prefer
`_b` graphics. When both a screen and a cell set exist for one name, they are
exported as sibling `screen/` and `cells/` projects with the correct tileset
each.

Language copies sit next to each other:

```text
out/g2d/CharacterKartSelect/select_character_gp_m/
  screen/ge/
  screen/fr/
  cells/ge/
  cells/fr/
```

`asset.json` `sources` records the exact atomic files used, so a bridged
palette such as `CharacterKartSelect_arc/select_character_gp_m_o.NCLR` is
visible.

## NCER cells

Each cell has its own image in `cells/`, composited from the shared tiles using
the cell's OAM placement, flips and palette bank. `cells.json` is deliberately
small:

```json
{
  "mapping_mode": 0,
  "bbox": true,
  "cells": [
    {
      "image": "cells/cell_000.bmp",
      "width": 32,
      "height": 32,
      "bbox": {"max_x": 16, "max_y": 16, "min_x": -16, "min_y": -16},
      "oam": [
        {
          "x": -16, "y": -16,
          "size": 2, "tile": 0
        }
      ],
      "sha256": "..."
    }
  ]
}
```

Edit `cell_000.bmp` to change that cell. On rebuild the tool inverse-maps the
image back into the tiles covered by its OAM entries. Cells whose image hash is
unchanged are skipped, so an unedited project still rebuilds byte-for-byte.
Cells that share tiles stay consistent because the rebuild updates the shared
tile data.

`cells.json` is also the place to change OAM attributes, bounding boxes or the
mapping mode. Creating a completely new cell needs a tile allocator and is not
part of this version.

## NSCR screens

`screen.bmp` is the assembled map with palette banks and H/V flips applied.
`asset.json` keeps the 16-bit screen entries and SCRN header. The composed
image is a visual check; the entries are authoritative for reconstruction.

## Bulk export

```sh
python3 tools/g2d_bulk.py path/to/extracted/root/data -o out/g2d
```

On the stock corpus this produces **737 projects** from 672 NCGR, 434 NCLR,
284 NCER and 470 NSCR files, with no errors: **446 screen projects**, **220
cell projects** and **71 tiles-only projects**. Tilesets already attached to a
screen or cell project do not get a second standalone folder. It also writes:

- `out/g2d/index.json` — projects, source files, language, bridge flags, errors
- `out/g2d/index.html` — preview gallery

### Cross-archive bridging

Language archives often contain only NCGR/NCER graphics and no palette. For
example `CharacterKartSelect_ge_arc/select_character_gp_m.nce.ncgr` has no
sibling NCLR; its palette is
`CharacterKartSelect_arc/select_character_gp_m_o.NCLR` in the base archive.

The bulk exporter matches missing palettes and shared NCGR files across the
whole extracted tree, preferring the same directory, then the same archive
family, then the base archive. Object assets prefer `_o` palettes; background
assets prefer `_b`. `index.json` marks a bridged file with `bridged_nclr` or
`bridged_ncgr`. In the stock corpus this bridged 802 palettes and 401 shared
graphics.

## Creating assets

- Bulk output groups language copies under one asset folder, for example
  `CharacterKartSelect/select_character_gp_m/cells/{us,fr,ge,it,es}/`.
- Palette-only export is available explicitly with
  `g2d_asset export --palette file.nclr -o project/`, but bulk does not create
  palette-only folders.
- New NCER: copy a project, replace `cells/cell_XXX.bmp` and the matching
  `cells.json` entries. Reuse an existing OAM layout; new tile allocation is
  future work.
- New NSCR: edit `entries` in `asset.json` and rebuild.

## Limits

- The BMP palette is 8-bit; edited colours are rounded back to RGB555.
- `screen.bmp` is a rendered view. Editing it does not yet re-encode the NSCR
  tilemap; the original atomic files under `source/` are the baseline.
- Editing `cells/cell_XXX.bmp` does rebuild the shared NCGR tiles.
- `cells.json` edits are authoritative for OAM/bbox/attributes; `asset.json`
  keeps only the non-derivable NCGR/NCLR/NSCR data.
- Compressed G2D members should be decompressed before export; recompression
  is a separate step.
