# NFTR fonts and NANR animations

> **Project:** Mario Kart DS Modding Trove · **Tool:** `tools/g2d_font_anim.py` · **Licence:** MIT

NFTR fonts and NANR cell animations are not simple bitmaps, but both can be
turned into editable visual projects.

## NFTR fonts

```sh
python3 tools/g2d_font_anim.py nftr-export LC_Font_s.NFTR -o out/fonts/LC_Font_s
python3 tools/g2d_font_anim.py nftr-rebuild out/fonts/LC_Font_s -o rebuilt.NFTR
```

A project contains:

| File | Purpose |
|---|---|
| `font.bmp` | glyph atlas, one tile per glyph |
| `glyphs/glyph_XXX.bmp` | one indexed image per glyph |
| `font.json` | glyph metrics, character mapping, encoding, FINF/CGLP fields |
| `source/` | original NFTR |

Glyphs are decoded from the continuous MSB-first bitstream for 1/2/3 bpp.
`font.json` keeps the character-code to glyph mapping and CWDH widths, so
changing a glyph image or a width does not require touching the binary.

The rebuild emits a canonical NFTR with FINF, CGLP, one CWDH and the CMAP
chain. It preserves glyphs, widths and character mapping, but it may not keep
the original multi-block CWDH/CMAP layout byte-for-byte.

## NANR animations

```sh
python3 tools/g2d_font_anim.py nanr-export anim.NANR \
    --ncer anim.NCER --ncgr anim.NCGR --palette anim.NCLR \
    -o out/anim

python3 tools/g2d_font_anim.py nanr-rebuild out/anim -o rebuilt.NANR
```

A project contains:

| File | Purpose |
|---|---|
| `frames/frame_XXX.bmp` | each animation frame, composed from the NCER cell |
| `sheet.bmp` | contact sheet of every frame |
| `preview.html` | browser preview that cycles the frames at their durations |
| `anim.json` | animations, frame records, cell indices, play modes |
| `cells/` | editable NCER project: `sprite_sheet.bmp`, per-cell BMPs, `cells.json` |
| `source/` | original NANR/NCER/NCGR/NCLR |

`anim.json` is the editable timing/frame list:

```json
{
  "animations": [
    {"frame_count": 6, "loop_start": 0, "animation_type": 65536,
     "play_mode": 2, "first_frame_offset": 24}
  ],
  "frames": [
    {"cell": 16, "duration": 4, "reserved": 0}
  ]
}
```

Change `cell` to point at a different NCER cell, change `duration` for timing,
or edit the animation records, then rebuild.

Edit individual cells under `cells/cells/` and rebuild the cell project first:

```sh
python3 tools/g2d_asset.py rebuild out/anim/Scene/Nickname_arc/Keyboard_s_o/cells \
    -o out/anim/Scene/Nickname_arc/Keyboard_s_o/cells-rebuilt
python3 tools/g2d_font_anim.py nanr-rebuild \
    out/anim/Scene/Nickname_arc/Keyboard_s_o -o rebuilt.NANR
```

The NANR frame list stores cell indices, so the rebuilt NCER/NCGR and the
rebuilt NANR stay linked. `frames/` and `sheet.bmp` are previews generated from
the source cells.

## Current stock export

The bulk run under `out/` covers all 14 stock NFTR fonts and all 5 stock NANR
animations:

```text
out/fonts/Main2D_arc/LC_Font_s/
out/fonts/Static2D_arc/MBChild_ja/
out/anim/Scene/Emblem_arc/emblem_m/
out/anim/Scene/Nickname_arc/Keyboard_s_o/
```

Open `font.bmp`, `sheet.bmp` or `preview.html` to inspect them. `out/` is not
committed.
