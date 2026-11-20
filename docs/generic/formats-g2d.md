# Nitro G2D resources

> **Project:** Mario Kart DS Modding Trove · **Licence:** MIT · **Code:** `include/nitro/g2d.h`

MKDS 2D assets use the Nitro G2D binary resource family: NCGR character graphics, NCLR palettes, NSCR screen maps, NCER cells, NFTR fonts and NANR cell animations. This note records the MKDS corpus layout facts and the points where the stock files depart from the standard Nitro layout; the standard block layouts themselves are the ones published by GBATEK and implemented by Mario Kart Toolbox, and are not re-derived here. All offsets are from the start of the file unless a block-relative base is stated.

The stock corpus under `unpacked/mkds_stock/root` contains 672 NCGR, 434 NCLR, 470 NSCR, 284 NCER, 14 NFTR and 5 NANR files. Counts are case-insensitive, because MKDS mixes `.NCGR` and `.ncgr` (and similarly for the other extensions). The generic layout is in the sections above; the MKDS-specific scene mapping, pairing rules and edit guidance start at [MKDS usage and configuration](#mkds-usage-and-configuration).

## Common header and block envelope

The 16-byte resource header and the 8-byte block header are the standard Nitro G2D envelope. The reusable declarations are `G2dFileHeader`, `G2dBlockHeader`, `G2D_HEADER_SIZE` and `G2D_BLOCK_HEADER_SIZE` in [`../include/nitro/g2d.h`](../include/nitro/g2d.h). Shared field vocabulary (`NitroG2dMagic`, `NitroG2dSize`, `NitroG2dOffset`, `NitroG2dImageFormat`, ...) lives in [`../include/nitro/g2d/common.h`](../include/nitro/g2d/common.h) and every format header reuses it; the typedefs are aliases and do not change the documented byte widths.

| File offset | Width | Field |
|---|---|---|
| 0x00 | 4 | magic, stored in reverse ASCII order (`RGCN`, `RLCN`, `RCSN`, `RECN`, `RTFN`, `RNAN`) |
| 0x04 | 2 | byte-order mark, `0xFEFF` for little-endian |
| 0x06 | 2 | version |
| 0x08 | 4 | total file size, including this header |
| 0x0C | 2 | header size, always `0x10` |
| 0x0E | 2 | number of following blocks |

| Block offset | Width | Field |
|---|---|---|
| +0x00 | 4 | block magic, again reverse ASCII (`RAHC`, `TTLP`, `NRCS`, `KBEC`, `FNIF`, `KNBA`, ...) |
| +0x04 | 4 | block size, including this 8-byte header |
| +0x08 | variable | block payload |

All multi-byte fields in the corpus are little-endian. The byte-order mark is `0xFEFF` in every file except `data/Boot/dbgfont.NCGR` and `data/Boot/dbgfont.NCLR`, which store `0x0000` but are still little-endian; no `0xFFFE` big-endian file was found. Treat `0x0000` as a legacy “unspecified” marker, not as big-endian.

| Format | Version | Blocks | Files |
|---|---|---|---|
| NCGR | 0x0101 | 2 | 337 |
| NCGR | 0x0100 | 1 | 334 |
| NCGR | 0x0001 | 1 | 1 |
| NCLR | 0x0100 | 1 or 2 | 433 |
| NCLR | 0x0001 | 1 | 1 |
| NSCR | 0x0100 | 1 | 470 |
| NCER | 0x0100 | 1 or 3 | 284 |
| NFTR | 0x0100 | 4 or 9 | 9 |
| NFTR | 0x0001 | 9 | 5 |
| NANR | 0x0100 | 3 | 5 |

Blocks are normally 4-byte aligned, but two standard exceptions matter for readers: NCLR PCMP blocks have size `0x10 + 2*n`, and NCER LABL blocks end immediately after the last NUL, so the following UEXT block can start unaligned. Do not assume every block offset is a multiple of four.

## NCGR — character graphics

NCGR has a mandatory CHAR block (`RAHC`) and an optional CPOS block (`SOPC`). The CHAR and CPOS layouts are the standard Nitro layouts; the declarations are `NcgrCharBlock` and `NcgrCposBlock` in the header.

| CHAR offset | Width | Field |
|---|---|---|
| +0x00 | 4 | `RAHC` |
| +0x04 | 4 | block size |
| +0x08 | 2 | height in 8×8 tiles; `0xFFFF` when unused |
| +0x0A | 2 | width in 8×8 tiles; `0xFFFF` when unused |
| +0x0C | 4 | colour format: `3` = 4bpp, `4` = 8bpp |
| +0x10 | 4 | mapping type: `0` = 2D, `0x10` = 1D 32K |
| +0x14 | 4 | character format; low byte 0 = tiled, 1 = bitmap, bit 8 = VRAM transfer |
| +0x18 | 4 | character data size in bytes |
| +0x1C | 4 | character data offset from CHAR+8; always `0x18` in the corpus |
| +0x20 | variable | character data |

| CPOS offset | Width | Field |
|---|---|---|
| +0x00 | 4 | `SOPC` |
| +0x04 | 4 | block size, always `0x10` |
| +0x08 | 2 | source x; must be `0` in the SDK partial-load path |
| +0x0A | 2 | source y; the SDK uses `y * width` as a character-unit source offset |
| +0x0C | 2 | width, in the same tile units as CHAR; used as the row stride in that offset |
| +0x0E | 2 | height, in the same tile units as CHAR; not read by the SDK loader |

The first byte of the character data is at file offset `0x30`, because the data offset is relative to CHAR+8. The CHAR payload is exactly `0x20 + data_size` bytes in 671 files; there is no trailing alignment padding. One file, `data/Boot/dbgfont.NCGR`, is the exception: its block size and header file size are 8 bytes shorter than the actual file, and the file ends with 8 bytes that are not covered by the declared sizes.

MKDS observations:

- 337 of 672 files (50.1%) have the second CPOS block, and all 337 use version `0x0101`; the 334 CHAR-only files use version `0x0100`, and the legacy Boot file uses `0x0001`. Version `0x0101` is therefore a reliable “CPOS present” signal in this corpus.
- Colour format `3` (4bpp) occurs in 600 files and format `4` (8bpp) in 72.
- Mapping type `0x10` (1D 32K) occurs in 262 files; mapping type `0` (2D) occurs in 410.
- The 262 files with mapping type `0x10` all store `0xFFFF` for both height and width. Every 2D file stores real tile dimensions, typically a 32-tile-wide sheet with height 1–32 tiles.
- All 672 CHAR blocks store `0x18` at +0x1C and therefore place data at +0x20. In the 671 normal files, the data size at +0x18 equals the remaining block payload.
- CPOS width is 32 in all but one file (`data/Course/mini_stage2Tex_arc/Map2D/local.NCGR`, width 10); height varies from 2 to 32. CPOS x and y are zero in every file.
- Examples: `data/Course/old_hyudoro_64Tex_arc/Map2D/global.NCGR` (4bpp, 1D 32K, CPOS present), `data/Course/old_hyudoro_64Tex_arc/Map2D/local.NCGR` (8bpp, 2D, CPOS present), `data/Boot/dbgfont.NCGR` (legacy header, BOM `0x0000`).

## NCLR — palettes

NCLR has a mandatory PLTT block (`TTLP`) and an optional PCMP block (`PMCP`). The normal magic is `RLCN`; one legacy Boot file uses `RPCN` (`data/Boot/dbgfont.NCLR`). The PLTT, PCMP and legacy-magic behaviour are the standard Nitro layout plus the legacy alias; the declarations are `NclrPlttBlock` and `NclrPcmpBlock`.

| PLTT offset | Width | Field |
|---|---|---|
| +0x00 | 4 | `TTLP` |
| +0x04 | 4 | block size |
| +0x08 | 4 | palette format: `3` = 4bpp bank, `4` = 8bpp |
| +0x0C | 4 | extended-palette flag: `1` = load into extended-palette VRAM |
| +0x10 | 4 | declared palette data size; legacy inverted/placeholder in PCMP files, use `block_size - 0x18` |
| +0x14 | 4 | palette data offset from PLTT+8; always `0x10` in the corpus |
| +0x18 | variable | 16-bit BGR555 palette entries |

| PCMP offset | Width | Field |
|---|---|---|
| +0x00 | 4 | `PMCP` |
| +0x04 | 4 | block size, `0x10 + 2*n` |
| +0x08 | 2 | number of stored palette banks (`numPalette`) |
| +0x0A | 2 | reserved, `0xBEEF` in every corpus file |
| +0x0C | 4 | index table offset from PCMP+8; always `8` in the corpus, so entries start at +0x10 |
| +0x10 | 2×n | original palette number for each stored bank |

MKDS observations:

- 434 files: 433 use `RLCN`, one uses the legacy `RPCN` magic. The legacy file still contains a normal `TTLP` block.
- 374 files are PLTT-only (373 `RLCN` plus the one `RPCN`); 60 add a PCMP block.
- Palette format `3` occurs in 351 files and format `4` in 83. The `3` files include one 128-colour palette and one malformed 224-colour declaration.
- PLTT block size is `0x18 + actual palette bytes`; a normal 512-byte palette block is `0x218`. There is no alignment padding between PLTT and PCMP.
- The byte at PLTT+0x0C is the SDK extended-palette boolean (`bExtendedPlt`), not a compression flag or a size. `1` means the palette is intended for extended-palette VRAM. The SDK unpacks it into the palette data and uses it to select the OBJ extended-palette transfer in `NNS_G2dLoadPalette`; it is also copied into the palette proxy. For BG loads the SDK chooses the destination from the screen colour mode and palette format, but still carries the flag in the proxy. The flag never changes the stored payload size.
- The 44 files with `7680` are all format `4` (256-colour), extended flag `1`, actual PLTT payload 512 bytes, and PCMP count 1 with index `0`. `7680` is `0x1E00` = `0x2000 - 0x200`, the legacy inverted size convention for one stored 512-byte bank in a 16-bank 8bpp extended-palette slot; the “15 banks” is the arithmetic complement, not a 15-bank allocation. The writer is the SDK `g2dcvtr` `-pcm` path (option added in 0.9.0, 12/06/2004; the checked tool binary is 1.0.2, 2005-09-01). The manual says `-pcm` is meaningless in 256-colour mode, so these PCMP blocks are converter artefacts rather than required runtime data. The 14 files that declare `0` carry the same one-bank 512-byte payload with the size field zeroed; whether that came from a different converter revision or a build flag is not proven.
- The consumer paths explain why the mismatch does not break the stock maps. The SDK PCMP loader (`NNS_G2dLoadPaletteEx`, and BG loading with a PCMP pointer) ignores `szByte`: it copies one bank of `GetPlttSize` bytes per PCMP entry, 512 bytes for a 256-colour palette, to `index * 512`. The MKDS course 2D loader does not use PCMP: it raw-copies `szByte` (7680 in those 44 files) to the BG palette, which reads past the 512-byte payload, then copies exactly 512 bytes of the local palette into a 1024-byte work buffer and reloads 512 bytes from that buffer before display. The visible local palette is therefore the one 512-byte bank; the 7680 declaration is a stale/converter size mismatch and the extra 7168 bytes are not palette data. The 14 files that declare `0` have the same 512-byte payload and are likewise superseded by the 512-byte buffer path.
- No MKDS call site for the SDK PCMP loader was found in the checked sources. The course loader reads only the PLTT payload; the PCMP block is still required for tool-compatible bank placement and should be preserved. One malformed file declares `448` bytes but its PLTT block contains only 64 bytes (`data/Static2D_arc/multi_download_00_b.NCLR`). Read palette bytes as `block_size - 0x18`.
- PCMP index counts are 1 in 58 files, 2 in one file and 8 in one file. The index table is a list of original palette numbers, not byte offsets.
- Examples: `data/Course/old_hyudoro_64Tex_arc/Map2D/local.NCLR` (PLTT + one-entry PCMP), `data/Course/mini_stage2Tex_arc/Map2D/local.NCLR` (eight-entry PCMP), `data/Static2D_arc/multi_download_00_b.NCLR` (truncated palette plus two-entry PCMP), `data/Boot/dbgfont.NCLR` (legacy `RPCN`).

## NSCR — screen maps

NSCR contains one SCRN block (`NRCS`). The layout is the standard Nitro screen block; the declaration is `NscrScreenBlock`.

| SCRN offset | Width | Field |
|---|---|---|
| +0x00 | 4 | `NRCS` |
| +0x04 | 4 | block size, `0x14 + data_size` |
| +0x08 | 2 | width |
| +0x0A | 2 | height |
| +0x0C | 2 | colour mode: `0` = 16×16, `1` = 256×1, `2` = 256×16 |
| +0x0E | 2 | screen format: `0` = text, `1` = affine, `2` = affine extended |
| +0x10 | 4 | screen data size in bytes |
| +0x14 | variable | 16-bit screen entries |

MKDS observations:

- All 470 files contain exactly one SCRN block, version `0x0100`, with no trailing padding.
- Width and height are stored in pixels, not in the 32/64-tile units used by some Nitro files: the observed values are 256 and 512, and `data_size` is always `width * height / 32`. That matches 8×8 tiles with two bytes per entry.
- Colour modes split 366 / 17 / 87 for modes `0` / `1` / `2`. Screen formats split 384 text / 86 affine-extended. One file (`data/Course/desert_courseTex_arc/Map2D/global1.NSCR`) combines colour mode `2` with screen format `0`.
- The observed combinations are 256×256 mode 0, 512×512 mode 2, 256×512 and 512×256 mode 0, 512×512 mode 0, and 256×256 mode 1/2. SCRN block sizes are 0x814, 0x1014 and 0x2014 (file sizes 0x824, 0x1024 and 0x2024) depending on the map.
- Text entries use the standard 16-bit fields: bits 0–9 tile index, bit 10 horizontal flip, bit 11 vertical flip, bits 12–15 palette. Affine and affine-extended entries reuse the same 16-bit slot with format-specific fields; the flip and palette fields do not apply there.
- Examples: `data/Course/old_hyudoro_64Tex_arc/Map2D/global2.NSCR` (256×256, text), `data/Course/old_hyudoro_64Tex_arc/Map2D/local3.NSCR` (512×512, affine extended).

## NCER — cells

NCER has a mandatory CEBK block (`KBEC`) and optional LABL (`LBAL`) and UEXT (`TXEU`) blocks. The CEBK header, per-cell record and OAM-data layout are the standard Nitro layout; the declarations are `NcerCebkHeader`, `NcerCell`, `NcerCellBbox` and `G2dUextBlock`.

| CEBK offset | Width | Field |
|---|---|---|
| +0x00 | 4 | `KBEC` |
| +0x04 | 4 | block size |
| +0x08 | 2 | number of cells |
| +0x0A | 2 | bank attributes; bit 0 = per-cell bounding box |
| +0x0C | 4 | cell array offset from CEBK+8; always `0x18`, so the array starts at CEBK+0x20 |
| +0x10 | 4 | mapping mode: `0`–`3` = 1D 32K/64K/128K/256K, `4` = 2D |
| +0x14 | 4 | VRAM transfer data offset; zero in the corpus |
| +0x18 | 4 | string-bank pointer, runtime-fixed; zero on disk |
| +0x1C | 4 | extended-data pointer, runtime-fixed; zero on disk |
| +0x20 | variable | cell array, then OAM data |

| Cell offset | Width | Field |
|---|---|---|
| +0x00 | 2 | number of OAM attributes in this cell |
| +0x02 | 2 | cell attributes |
| +0x04 | 4 | OAM data offset from the start of the OAM-data area |
| +0x08 | 8 | bounding box, only when CEBK bank attribute bit 0 is set: max X, max Y, min X, min Y, each `int16_t` |

The cell array stride is 8 bytes without the bounding box and 16 bytes with it. The OAM-data area starts immediately after the last cell record. Each OAM attribute set is three `uint16_t` values (6 bytes), so a cell with `n` OAM entries occupies `6*n` bytes in that area. Cell attributes use the standard bit layout: bits 0–5 bounding-sphere radius, bit 8 horizontal flip, bit 9 vertical flip, bit 10 both flips, bit 11 bounding box present.

LABL starts at +0x08 with an array of `uint32_t` label offsets. Offset 0 is always zero and the offsets are relative to the first label string, so the label area starts after the offset array. NCER does not store the label count; use the `animation_count` from the paired NANR’s KNBA block, or infer the count from where the first string begins. UEXT is 12 bytes: `TXEU`, size `0x0C`, and one `uint32_t` value.

MKDS observations:

- 284 files: 262 contain only CEBK, use mapping mode `0`, and set the bounding-box bank attribute. The other 22 contain CEBK + LABL + UEXT, use mapping mode `4` (2D), and split 17 without / 5 with the bounding-box attribute.
- Cell counts range from 1 to 201: the 262 single-block files contain 1–58 cells, while the 22 three-block files contain 1–201.
- OAM counts per cell range from 0 to 33. 283 cells have zero OAM entries, which is valid and must not be treated as corruption.
- Cell attribute values are mostly `0`, `2`, `3`, `6`, `0x0803` and `0x0806`; the `0x0800` bit marks a bounding box and appears together with the radius bits.
- UEXT’s value is `1` in all 22 files.
- Mario Kart Toolbox has an NCER writer but no NCER reader: `Ncer.cs` only serialises caller-supplied cells. Any reader must implement the CEBK cell-array/OAM-offset rules above.
- Examples: `data/Main2D_ge_arc/player_character_L.nce.ncer` (13 cells, bounding boxes, no LABL), `data/Scene/Nickname_arc/Keyboard_s_o.NCER` (22 cells, 2D mapping, LABL + UEXT), `data/Scene/Emblem_arc/emblem_s.NCER` (129 cells, 75 labels).

## NFTR — fonts

NFTR contains FINF (`FNIF`), CGLP (`PLGC`), one or more CWDH (`HDWC`) and one or more CMAP (`PAMC`) blocks. The block layouts are the standard Nitro font layout; the declarations are `NftrInfoBlock`, `NftrGlyphBlock`, `NftrCharWidth`, `NftrWidthBlock`, `NftrCodeMapBlock` and `NftrScanEntry`, with `NftrInfoBlockOld` and `NftrCharWidthOld` for the version `0x0001` forms.

| FINF offset | Width | Field |
|---|---|---|
| +0x00 | 4 | `FNIF` |
| +0x04 | 4 | block size, `0x1C` |
| +0x08 | 1 | font type; zero in the corpus |
| +0x09 | 1 | line feed |
| +0x0A | 2 | alternate character index |
| +0x0C | 1 | default left |
| +0x0D | 1 | default glyph width |
| +0x0E | 1 | default character advance in version `0x0100`; encoding in version `0x0001` |
| +0x0F | 1 | encoding in version `0x0100`; reserved in version `0x0001` |
| +0x10 | 4 | CGLP offset from file+8 |
| +0x14 | 4 | first CWDH offset from file+8 |
| +0x18 | 4 | first CMAP offset from file+8 |

| CGLP offset | Width | Field |
|---|---|---|
| +0x00 | 4 | `PLGC` |
| +0x04 | 4 | block size |
| +0x08 | 1 | cell width |
| +0x09 | 1 | cell height |
| +0x0A | 2 | cell size in bytes |
| +0x0C | 1 | baseline |
| +0x0D | 1 | maximum character width |
| +0x0E | 1 | bits per pixel |
| +0x0F | 1 | reserved |
| +0x10 | variable | glyph bitmap data |

| CWDH offset | Width | Field |
|---|---|---|
| +0x00 | 4 | `HDWC` |
| +0x04 | 4 | block size |
| +0x08 | 2 | first glyph index |
| +0x0A | 2 | last glyph index |
| +0x0C | 4 | next CWDH offset from file+8; zero ends the chain |
| +0x10 | 3×n or 2×n | widths: version `0x0100` uses left `int8_t`, width `uint8_t`, advance `int8_t` (3 bytes); version `0x0001` uses left `int8_t`, width `uint8_t` (2 bytes) |

| CMAP offset | Width | Field |
|---|---|---|
| +0x00 | 4 | `PAMC` |
| +0x04 | 4 | block size |
| +0x08 | 2 | first character code |
| +0x0A | 2 | last character code |
| +0x0C | 2 | mapping method: `0` direct, `1` table, `2` scan |
| +0x0E | 2 | reserved |
| +0x10 | 4 | next CMAP offset from file+8; zero ends the chain |
| +0x14 | variable | direct: one `uint16_t` glyph base; table: one `uint16_t` per code; scan: `uint16_t` count followed by `(code, glyph)` pairs |

The encoding byte is the NITRO font encoding selector: `0` = UTF-8, `1` = UTF-16, `2` = Shift-JIS, `3` = CP1252. Version `0x0100` stores it at FINF+0x0F. Version `0x0001` predates the separate byte: it stores the encoding at FINF+0x0E and leaves +0x0F reserved, so the auto initialiser moves +0x0E into the encoding field before choosing a splitter. MKDS builds its fonts through that automatic initialiser (`NNS_G2dFontInitAuto`), which reads the resulting encoding and selects the matching character splitter; there is no separate game-side encoding override.

Glyph images are packed row-major, most-significant bit first within each byte, as one continuous bitstream with no per-row byte alignment. The first pixel of the glyph is the high bits of the first byte, and the row continues across byte boundaries; `cell_size` is `ceil(cell_width * cell_height * bpp / 8)`. Decoding the stock `A` and `a` glyphs at 1, 2 and 3 bpp with this order produces the expected shapes. Glyphs are left-aligned inside the fixed cell, and the remaining right-side pixels are blank.

MKDS observations:

- 14 files: 6 four-block fonts and 8 nine-block fonts. All are version `0x0100` (9 files) or `0x0001` (5 files); the version `0x0001` files are all nine-block.
- Encoding is `1` (UTF-16) in every version `0x0100` file and `0` (UTF-8) in every version `0x0001` file. The default character advance is non-zero in the `0x0100` files and zero in the `0x0001` files.
- The six `MBChild_<lang>.NFTR` fonts use encoding `1` and their CMAPs cover every character in the paired `MBChild_<lang>.bmg`, whose text is UTF-16LE (BMG header encoding value `2`). The Japanese font maps code points such as `0x3002` and `0x3044`, and the Latin fonts map `0x152`, `0x153`, `0x201c` and `0x201d`; those are UTF-16 code units, not UTF-8 byte sequences. The three `Main2D` fonts also use encoding `1` and cover the UTF-16 text in the per-language `common.bmg` files. This verifies the `1` = UTF-16 assignment against paired text, not only against the SDK enum.
- The five legacy `0x0001` fonts store encoding `0` at FINF+0x0E (UTF-8). They are the `Edit`/`Test` fonts and have no paired BMG in the corpus; the game’s auto initialiser would split their text as UTF-8.
- Font type is `0` everywhere. Line feed values are 11, 13, 15 and 20. CGLP bits per pixel are 1, 2 and 3.
- Glyph counts run from 22 to 462. The glyph count is the CWDH range (`last - first + 1`) and also equals `floor((CGLP block size - 0x10) / cell_size)`. In version `0x0100` the CWDH entries are 3 bytes and the block is padded to 4 bytes, so the CWDH division can leave 2 bytes of padding; in version `0x0001` the entries are 2 bytes and the division is exact in every stock file.
- The 6 four-block fonts contain FINF, CGLP, CWDH and one scan CMAP. The 8 nine-block fonts contain FINF, CGLP, CWDH, three direct CMAPs (ASCII and two Japanese ranges), two table CMAPs and one scan CMAP.
- Every CWDH chain has a single block with `next_offset == 0`. CMAP chains are linked through `next_offset`; the final scan block has `next_offset == 0`. The `PAMC` blocks are physically ordered before their `next_offset` targets, and the next offset is relative to file+8.
- The scan CMAP covers code range `0x0000`–`0xFFFF` and is the final mapping consulted for unmapped codes.
- Examples: `data/Main2D_arc/LC_Font_s.NFTR` (nine blocks, 438 glyphs), `data/Static2D_arc/MBChild_es.NFTR` (four blocks, 24 glyphs), `data/Scene/Edit_arc/selectFont.NFTR` (version `0x0001`, 460 glyphs, encoding `0`).

## NANR — cell animations

NANR contains a mandatory KNBA block (`KNBA`), plus the same optional LABL (`LBAL`) and UEXT (`TXEU`) blocks as NCER. The KNBA and animation/frame layouts are the standard Nitro animation layout; the declarations are `NanrKnbaHeader`, `NanrAnimationType`, `NanrAnimation`, `NanrFrame` and `G2dUextBlock`.

| KNBA offset | Width | Field |
|---|---|---|
| +0x00 | 4 | `KNBA` |
| +0x04 | 4 | block size |
| +0x08 | 2 | animation count; also the LABL label count |
| +0x0A | 2 | total frame-block count |
| +0x0C | 4 | animation array offset from KNBA+8 |
| +0x10 | 4 | frame-block array offset from KNBA+8 |
| +0x14 | 4 | frame-data offset from KNBA+8 |
| +0x18 | 8 | zero padding |

| Animation offset | Width | Field |
|---|---|---|
| +0x00 | 2 | number of frames in this animation |
| +0x02 | 2 | loop-start frame index |
| +0x04 | 4 | animation type and element: upper 16 = type, lower 16 = element |
| +0x08 | 4 | playback mode |
| +0x0C | 4 | first frame-record offset from the frame-block array |

| Frame offset | Width | Field |
|---|---|---|
| +0x00 | 4 | content offset from the frame-data base |
| +0x04 | 2 | frame duration in video frames (60 Hz units) |
| +0x06 | 2 | padding |

The animation type field packs two selectors: upper 16 bits `0` invalid, `1` cell, `2` multi-cell location; lower 16 bits `0` index only, `1` index plus SRT, `2` index plus translation. Playback mode `0` is invalid, `1` plays once forward, `2` repeats forward, `3` plays forward then reverse once, and `4` repeats the forward/reverse cycle. The SDK animation unpack routine (`NNS_G2dUnpackNAN`, called by the game’s animation wrapper) fixes the KNBA pointers and adds the frame-block base to each animation’s +0x0C and the frame-data base to each frame record’s +0x00; it does not decode the frame payload itself. All 141 animation records in the stock corpus decode as type `1` (cell), element `0` (index only), playback mode `2` (repeat/forward loop), and loop start `0`, so each referenced frame payload is a single 16-bit cell index. Each animation’s result array ends on a 4-byte boundary; when its length is `2 mod 4`, the converter writes a `0xCCCC` pad word. That word is padding, not a frame value or an end marker: every `0xCCCC` word is unreferenced by a frame record, and every referenced word is a valid cell index. A one-frame animation therefore occupies 4 bytes (index plus pad), while multi-frame results are contiguous 2-byte indices with no per-frame pad. `Keyboard_s_o` uses content offsets `0`, `4`, `8` and `0x0C` for its four animations and shares results at `0x0E` and `0x10` within its last animation, while `emblem_camera_s` uses `0`, `4` and `6`, proving there is no fixed stride. Readers must follow each frame record’s +0x00 offset. The index-plus-translation (8-byte) and index-plus-SRT (16-byte) payload forms defined by the format do not occur in the MKDS corpus. LABL stores `uint32_t` offsets at +0x08, relative to the first label, exactly as in NCER; the count comes from KNBA+0x08. UEXT is 12 bytes with a `0x0C` size and one value.

MKDS observations:

- All 5 files use version `0x0100` and contain KNBA + LABL + UEXT.
- KNBA animation counts are 4, 2, 10, 75 and 50; frame-block counts are 9, 3, 55, 128 and 87.
- All 141 animation records use type `1` (cell), element `0` (index only) and playback mode `2` (forward loop), with loop start `0`. The 282 frame references decode to cell indices `0`–`128`; no referenced frame payload is `0xCCCC`.
- UEXT’s value is `1` in all 5 files.
- Every frame content word is a valid NCER cell index (the maximum equals `cell_count - 1`). There are no out-of-range indices and no non-`0xCCCC` unreferenced data words.
- The `0xCCCC` pad-word totals are 3 (`Keyboard_s_o`), 1 (`emblem_camera_s`), 4 (`emblem_m`), 26 (`Emblem_arc/emblem_s`) and 31 (`Edit_arc/emblem_s`).
- The label count equals the KNBA animation count in every file, and the LABL strings match the paired NCER’s LABL strings exactly and in the same order for all five pairs (`Keyboard_s_o`, `emblem_camera_s`, `emblem_m`, `emblem_s` in both archives). The animation record at index `i` uses label `i`; this is the mapping that resolves an NCER LABL block without a stored count.
- Examples: `data/Scene/Nickname_arc/Keyboard_s_o.NANR` (4 animations, 9 frames), `data/Scene/Emblem_arc/emblem_s.NANR` (75 animations, 128 frames), `data/Scene/Edit_arc/emblem_s.NANR` (50 animations, 87 frames).

## Known gaps

- No big-endian (`0xFFFE`) G2D resource was found in the stock corpus. The two `0x0000` Boot files are little-endian; a reader should not infer big-endian from a zero BOM.
- NCER has no reader in Mario Kart Toolbox (`Ncer.cs` writes only), so the CEBK cell-array and OAM-offset rules have to be implemented by the consumer.
- NCER LABL does not store its label count. Without the paired NANR, the count must be inferred from the first label-string offset; the stock files always make label 0 start after the offset array.
- The NCGR legacy Boot file’s declared block size and file size are 8 bytes short of the actual file. The game’s block finder walks the block count and per-block sizes rather than the total file size, so the CHAR block still resolves; the mismatch is cosmetic.
- No NANR reader was found in the checked Mario Kart Toolbox tree. The five stock files exercise only the cell/index form; no stock sample of the index-plus-SRT or index-plus-translation payloads exists, so only the index decoder is proven against the corpus.

---

## MKDS usage and configuration

This part is game-specific. “Proven” means a game-code resource string, a Mario Kart Toolbox path table, or a loader call names the resource; “inferred” means the archive name, file stem, or corpus correlation is the evidence. Archive paths are corpus-relative.

### Resource map by scene and archive

| Archive or scene | G2D resources | Role | Evidence |
|---|---|---|---|
| `data/Boot` | `dbgfont.NCGR`, `dbgfont.NCLR` | Boot/debug 4bpp font atlas; legacy version `0x0001`, BOM `0x0000` | inferred from path and name; legacy header observed |
| `data/Course/*/Map2D` (59 directories; 158 NCGR, 159 NCLR, 196 NSCR) | `global.NCGR/NCLR` + `global1.NSCR`; `global2.NCGR/NCLR` + `global2.NSCR`; `local.NCGR/NCLR` + `local2.NSCR` / `local3.NSCR` | Race minimap: global map, global background, local map; one local texture/palette feeds `local2` and `local3` | proven for the path grouping by `MkdsCourseTexPaths` / `MkdsBinaryCourse` |
| `data/CupPicture` (32 triplets) | `select_cup_<kind>NN_m_b.NCGR`, `_m_b.NCLR`, `_m_picture.NSCR`, where `<kind>` is `nitro` or `retro` | Cup-select artwork for the 16 nitro and 16 retro cups | proven by the game’s `%s%s%02d%s` path template and `cpic_loadCharacter/Palette/Screen` |
| `data/CharacterKartSelect_arc` + five `CharacterKartSelect_<lang>_arc` | `select_character_gp_*`, `select_character_s`, `select_kart_s_b`, `select_menu_etc*`, plus `_o.NCLR` and `.nce.ncgr/.nce.ncer` | Character select, kart select, names/titles, background and menu furniture | proven by `charSelect.c` and `kartSelect.c` |
| `data/Main2D_arc` + five `Main2D_<lang>_arc` | `LC_Font_s/m.NFTR`, `marioFont.NFTR`; `player_character_L/M` NCGR + NCER + `_o.NCLR`; `_shyguy_o.NCLR` | Global UI fonts and the two player-character sprite/cell sets | fonts proven by `m2d_load`; player-character loader proven, exact scenes inferred |
| `data/Scene/Menu_arc` plus `gp`, `mg`, `mr`, `ta` and five language arcs | `select_game_*`, `select_cup_*`, `select_engine_*`, `select_battle_stage_*`, `Mission_run_*`, `TimeAttack_top_menu_*`, `select_ghost_*`, `cup_mark`, `trophy_icon`, `wait` | Main menu, cup/game/engine/battle/mission/Time Trials selection | partly proven by `gameSelect.c` and `kartSelect.c`; the rest inferred from archive and stems |
| `data/Scene/GeneralMenu_arc` | `back_screen`, `select_choises`, `select_return`, `txt_system` | Shared menu background, choice strip, return button and system text | inferred |
| `data/Scene/MenuDL_arc` + five language arcs | `select_game`, `select_race_rule_*download*`, `select_menu_etc_download`, `wait` | Download Play menu and race-rule selection | inferred |
| `data/Scene/WiFiMenu_arc` + five language arcs | `WiFi_VS_course_select`, `WiFi_VS_matching`, `WiFi_VS_setting`, `WiFi_aikotoba`, `WiFi_top_menu`, `back_screen` | Wi-Fi course select, matching, settings, passphrase and top menu | course select proven by `wifiMenuTrackSelectScene.c`; the rest inferred |
| `data/Scene/WLMenu_arc` + five language arcs | `multi_select_*` | Wireless Link multi-card member/group selection | inferred |
| `data/Scene/Option_arc` + five language arcs | `Option_top_menu`, `Option_select_menu`, `Option_embrem_select`, `Option_hensyu_menu` | Options menu and emblem edit entry | inferred |
| `data/Scene/Record_arc` + five language arcs | `Record_top_menu`, `Record_Gpx`, `Record_T_att`, `Record_VS`, `Record_all`, `cup_mark`, `Record_trophy` | Records, statistics, cup marks and trophies | inferred |
| `data/Scene/Ghost_arc` + five language arcs | `TimeAttack_ghost_get/send`, `Kart_icon_o_all`, `Kart_icon_o_A/B/C` | Ghost download/send screens and kart icons | inferred |
| `data/Scene/Race_arc` plus `Race_gp`, `Race_mg`, `Race_mr`, `Race_ta`, `Race_nt` and language arcs | `race_m`, `race_s`, `race_goal_*`, `race_start_*`, `race_battle`, `race_mr`, `race_ta`, `race_transfer` | Race HUD, pause, goal, start, transfer, battle/Mission/TA overlays | `race_start_gp_m` proven by `courseIntro.c`; the rest inferred |
| `data/Scene/Result_arc` + five language arcs | `results_gp_m_b`, `results_gp_m1/m2`, `results_gp_m.nce.*`, `results_gp_m_o`, `results_gp_s*`, `cup_name_left` | GP results main/sub screen sets, cup-name cells | proven by `gpResult.c` |
| `data/Scene/ResultDL_arc` + five language arcs | `results_battle_*` | Download Play battle results, win/lose/draw/Versus screens | inferred |
| `data/Scene/Emblem_arc` + five `Emblem_<lang>_arc` | `emblem_s`, `emblem_m`, `emblem_camera_s` NCER+NANR; `emblem_*_b/o`; template screens; `choises_s` | Emblem viewer/editor, emblem camera, template and tool screens | inferred from archive and stems; `emblem_s_b.NCLR` is proven as the race 3D emblem palette |
| `data/Scene/Edit_arc` | `emblem_s` NCER+NANR, `selectFont.NFTR`, `emblem_s_b/o`, `choises_s_3`, template screens | Emblem edit mode | inferred; `emblem_s` here has a different cell/label count from `Emblem_arc` |
| `data/Scene/Keyboard_arc` and `Nickname_arc` | `Keyboard_s_o` NCER, with the NANR in `Nickname_arc`; `Keyboard_s_b_<layout>` NCGR+NSCR; `Keyboard_s_b.NCLR`; `Keyboard_s_o.NCLR`; `back_screen`; `.kbd`/`.kbdmap` tables | Nickname keyboard layouts and cursor/key objects | `Keyboard_s_o` proven by the game keyboard loader; layouts inferred |
| `data/Scene/Title_arc` + five language arcs | `title_m_b`, `title_s_b`, `title_true_*`, `title_m1/m2`, `title_s_bg`, `title_s` NCER/NCLR | Title screen and true/alternate backgrounds | proven by `title.c` |
| `data/Scene/Logo_arc` | `logo_R_Nintendo`, `allRightsReserved`, `ESRB_Online` | Boot, publisher, legal and rating logos | two proven by `logo.c`; ESRB inferred |
| `data/Scene/Ending_arc` and `StaffRoll_arc` | `ending_*`, `thanksYou`, `logo_end_*`, `ending_staffRoll*` | Ending sequence and staff roll | inferred |
| `data/Static2D_arc` | `MBChild_<lang>.NFTR`, `multi_download_00_b`, `search_icon_00`, `search_icon_layout_00` | Download Play child font, multi-download wait screen, search icon | proven by the child/multi-download/search loaders |
| `data/KartModel*` | `emblem_s_b.NCLR`, `kart_a.NCLR`, `HH_color.NCLR` | 3D kart, character and emblem model palettes | emblem palette proven by race driver labels; the other palettes inferred |
| `data/Scene/Test_arc` | `LC_Font_l/m`, `marioFont`, `selectFont`, `choises_s` | Test-scene copies, including the only `LC_Font_l.NFTR` | inferred (test archive) |

### Pairing rules

Course maps are the clearest case. `global.NCGR` + `global.NCLR` feed `global1.NSCR`; `global2.NCGR` + `global2.NCLR` feed `global2.NSCR`; `local.NCGR` + `local.NCLR` feed both `local2.NSCR` and `local3.NSCR`. `local2` and `local3` are different screen maps over the same local texture and palette, so a local texture or palette edit changes both maps. `global2` is the global-map background (Toolbox’s `GlobalMapBackgroundGraphics`), not the local map; when a course has `global2.NSCR` but no `global2.NCGR/NCLR` (11 stock directories), the background screen map is inferred to reuse `global.NCGR`/`global.NCLR` because no other texture or palette exists in that archive. `AwardTex_arc` and `StaffRollTex_arc` use the same `Map2D` layout but are special award/staff-roll archives, and the `MR_stage*` mission archives may carry only the local set.

| Resource family | Texture | Palette | Screen/layout | Cell or animation |
|---|---|---|---|---|
| Course global map | `global.NCGR` | `global.NCLR` | `global1.NSCR` | none |
| Course global background | `global2.NCGR` (or `global.NCGR` when absent) | `global2.NCLR` (or `global.NCLR` when absent) | `global2.NSCR` | none |
| Course local map | `local.NCGR` | `local.NCLR` | `local2.NSCR` and/or `local3.NSCR` | none |
| Menu background | `<stem>_b.NCGR` | `<stem>_b.NCLR` | `<stem>.NSCR`, or `_m`/`_s` variants | optional `.bncl`/`.bnll` |
| Menu objects | `<stem>.nce.ncgr` or `<stem>_b.NCGR` | `<stem>_o.NCLR` | existing background screen | `<stem>.nce.ncer` plus `.bncl`/`.bnll` or NANR |
| Cup picture | `select_cup_<kind>NN_m_b.NCGR` | `select_cup_<kind>NN_m_b.NCLR` | `select_cup_<kind>NN_m_picture.NSCR` | none |
| Emblem scene | `emblem_*_b.NCGR`, `emblem_*.nce.ncgr` | `emblem_*_b.NCLR`, `emblem_*_o.NCLR` | `emblem_*.NSCR` | `emblem_*.NCER` + `emblem_*.NANR` |
| Keyboard | `Keyboard_s_b_<layout>.NCGR` | `Keyboard_s_b.NCLR` | `Keyboard_s_b_<layout>.NSCR` | object set `Keyboard_s_o` NCER + NANR (NANR in `Nickname_arc`) |
| Font | none | none | none | NFTR only; `MBChild_<lang>.NFTR` pairs with `MBChild_<lang>.bmg` |

The naming suffixes are partly proven and partly inferred. `_b` is the background texture/palette pair and `_o` is the object/cell palette, proven by the game loading `<stem>_b.NCGR`/`_b.NCLR` with the screen map and `<stem>.nce.ncgr`/`.nce.ncer` with `_o.NCLR`. `_m`/`_s` appear as paired main/sub-screen layouts and are loaded together, so they are inferred to mean upper/main and lower/sub screen. `_gp`, `_ta`, `_vs`, `_mg`, `_mr` and `_DL`/`_WL`/`_WiFi` follow the game modes Grand Prix, Time Trials, Versus, Battle, Mission Run, Download Play, Wireless Link and Wi-Fi.

NCLR and NCGR formats normally agree: the course global maps use 4bpp NCGR (`color_format 3`) with 4bpp NCLR (`palette_format 3`), while the course local maps normally use 8bpp NCGR (`color_format 4`) with 8bpp NCLR (`palette_format 4`); `mini_stage2Tex_arc` is the compact palette exception, with a format-3 local NCLR and eight PCMP-mapped banks. Eight `global.NCLR` files declare format 4 while their `global.NCGR` is format 3; the palette payload is still a 512-byte, 16-bank palette, so use the NCGR format and the actual PLTT payload when editing.

PCMP is rare in MKDS. It appears only for the local course palettes and one `Static2D` palette:

| File | Palette format | Actual PLTT payload | PCMP entries | Original palette numbers |
|---|---|---|---|---|
| `local.NCLR` in most course archives | 4 (8bpp) | 512 bytes | 1 | `(0)` |
| `mini_stage2Tex_arc/Map2D/local.NCLR` | 3 (4bpp) | 256 bytes (8 banks) | 8 | `0,1,2,3,4,5,6,7` |
| `Static2D_arc/multi_download_00_b.NCLR` | 3 (4bpp) | 64 bytes (2 banks) | 2 | `0,1` |

The table is standard compressed-palette metadata: PLTT stores only the used banks packed in order, and the table gives each stored bank’s original palette number. The SDK compressed loader restores those numbers, but no checked MKDS call site uses it; the course loader transfers the raw PLTT payload. Editing the PCMP table alone therefore does not recolor anything through the checked path. Keep the PLTT payload and its bank order intact; preserve PCMP for tools that expect a standard NCLR.

CPOS is not used by MKDS. The SDK’s only CPOS consumer is an optional character-position accessor returned to the BG loader; that loader asserts `srcPosX == 0` and uses `srcPosY * srcW` as a **source character offset** into the CHAR data. `srcH` is not read by the loader. CPOS is therefore a sub-rectangle start hint, not a destination placement and not a load extent; screen placement always comes from the NSCR. All 337 stock CPOS blocks store x = 0 and y = 0, so even that source offset is zero. The game’s resource wrapper requests only CHAR, PLTT, SCRN, CEBK and ANIM blocks; no checked MKDS call site requests the CPOS block or passes character-position information to the SDK, and the course loader builds its BG transfers directly from the NSCR and CHAR pointers.

The producer rule is the `g2dcvtr` `-cr/XYWH` option. `-cr` defines the input rectangle; the converter ignores X and W (`X = 0`, `W = total character-data width`) and uses the supplied Y and H. That exactly matches the stock values: CPOS width equals the CHAR width in characters (`2`, `10`, `30` or `32`), CPOS height is the supplied H (`1..32`; cup pictures `11`, battle-stage `30`, multi-download `1`), and Y is zero in every file. For 1D mapping the CHAR width/height are `0xFFFF`, so CPOS is the only record of the converter’s total width and requested H. Editing CPOS alone therefore changes nothing at runtime; update CHAR/NSCR when the sheet extent changes.

| CPOS family | Files | CPOS width × height | CHAR dimensions |
|---|---|---|---|
| 1D 32K sprite sheets | 262 | 32 × 1..32 | `0xFFFF` × `0xFFFF` |
| Cup pictures | 32 | 10 × 11 | 10 × 11 tiles |
| Other 2D CPOS sheets | 43 | same as CHAR | real tile dimensions |

### NCER, NANR and NFTR resource usage

Only five NANR files exist, and each pairs by stem with exactly one NCER. The other NCERs have no NANR twin; they are static or are animated by `.bncl`/`.bnll` banks that sit beside them, for example `player_character_L/M`, the character/kart-select cells, and the race/record/result cells.

| NCER + NANR pair | Cells | OAM per cell | Labels / animations | Frames | Frame durations (60 Hz units) |
|---|---|---|---|---|---|
| `Nickname_arc/Keyboard_s_o` | 22 | 1..33 | 4 / 4 | 9 | 4, 9, 24 |
| `Emblem_arc/emblem_camera_s` | 3 | 3..32 | 2 / 2 | 3 | 4, 50 |
| `Emblem_arc/emblem_m` | 24 | 1..13 | 10 / 10 | 55 | 4 |
| `Emblem_arc/emblem_s` | 129 | 0..25 | 75 / 75 | 128 | 4, 8, 12, 24, 250 |
| `Edit_arc/emblem_s` | 90 | 1..25 | 50 / 50 | 87 | 4, 8 |

The `Emblem_arc` and `Edit_arc` `emblem_s` files share a stem but are not interchangeable: 129 cells/75 labels/128 frames versus 90 cells/50 labels/87 frames. The NANR LABL and the paired NCER LABL contain identical strings in identical order in all five pairs, and the animation record at index `i` corresponds to label `i`; each frame’s content offset selects a cell index in the NCER cell array directly. Changing cell order, adding cells, or renaming labels therefore requires rebuilding both files.

NFTR usage is separate from NCGR/NCLR pairing. The three Main2D fonts are loaded into the global font array by `m2d_load`; the Edit/Test `selectFont.NFTR` is a separate font; the six `MBChild_<lang>.NFTR` files are the Download Play child fonts and pair with the same-language `MBChild_<lang>.bmg` text banks.

| Font | Scene / archive | Version / encoding | Line feed | Cell / bpp | Glyphs | Role |
|---|---|---|---|---|---|---|
| `LC_Font_s.NFTR` | `Main2D_arc` | 0x0100 / 1 | 11 | 9×11 / 1 | 438 | Small global UI font |
| `LC_Font_m.NFTR` | `Main2D_arc` | 0x0100 / 1 | 15 | 11×15 / 1 | 438 | Medium global UI font |
| `marioFont.NFTR` | `Main2D_arc` | 0x0100 / 1 | 13 | 12×13 / 2 | 441 | Stylised menu font |
| `LC_Font_l.NFTR` | `Test_arc` | 0x0001 / 0 | 20 | 15×20 / 1 | 462 | Large test font |
| `selectFont.NFTR` | `Edit_arc`, `Test_arc` | 0x0001 / 0 | 13 | 12×13 / 3 | 460 | Emblem-edit font (inferred) |
| `MBChild_us/es/fr.NFTR` | `Static2D_arc` | 0x0100 / 1 | 11 | 7×10 / 1 | 24 each | Download Play child font |
| `MBChild_it.NFTR` | `Static2D_arc` | 0x0100 / 1 | 11 | 7×10 / 1 | 22 | Download Play child font |
| `MBChild_ge.NFTR` | `Static2D_arc` | 0x0100 / 1 | 11 | 7×10 / 1 | 27 | Download Play child font |
| `MBChild_ja.NFTR` | `Static2D_arc` | 0x0100 / 1 | 11 | 9×9 / 1 | 36 | Download Play child font |

### Configuration fields that matter for editing

| Format | Field | Why it matters | Observed MKDS values |
|---|---|---|---|
| NCGR | `color_format` | Selects 4bpp or 8bpp and therefore the matching NCLR format | 3 for most menus, courses and cup pictures; 4 for local course maps and a few scene sprites |
| NCGR | `mapping_type` | 0x10 means 1D 32K; 0 means 2D | 262 files use 0x10; the rest use 0 |
| NCGR | `height` / `width` | Tile-sheet extent; `0xFFFF` means the extent is in CPOS | 1..32 tiles high, 32 tiles wide on 1D sheets |
| NCGR | CPOS x/y | Source sub-rectangle start for the SDK partial-load path; MKDS does not read it | 0/0 in all 337 CPOS files, so any offset is zero |
| NCGR | CPOS width/height | Source extent metadata for 1D sheets; not a runtime load extent | 32×1..32; cup pictures 10×11 |
| NCLR | `palette_format` | Must match NCGR depth and NSCR color mode | 3 in 351 files, 4 in 83 |
| NCLR | extended flag | 1 selects extended-palette VRAM in SDK palette loads; never changes payload size | 1 in the 44 `7680` PCMP files; 0 elsewhere |
| NCLR | actual payload (`block_size - 0x18`) | The declared size is wrong or oversized in 59 PCMP files; the block size gives the payload | 512 bytes normally; 256 or 64 in compact/truncated PCMP cases |
| NCLR | PCMP count/index table | Compressed-palette metadata; MKDS transfers the raw PLTT and ignores it | 1 index `(0)` for local maps; 8 indices for `mini_stage2`; 2 for `multi_download` |
| NSCR | width / height | Pixel dimensions; data size is `width * height / 32` | 256×256 for course globals and menus; 512×512 for course locals |
| NSCR | color mode / screen format | Text vs affine vs affine-extended; selects entry interpretation | course globals 0/0; course locals 2/2; menus mostly 0/0 |
| NCER | cell count and bank attribute | Cell-array stride is 8 or 16 bytes; OAM area starts after it | 1..201 cells; 267 files with bounding boxes, 17 without |
| NCER | OAM count and OAM offsets | OAM offsets are relative to the OAM area and shift when cell count/stride changes | 0..33 OAM entries per cell |
| NCER | cell labels | NANR animation order and `.bncl` bindings use them | 4 labels in Keyboard, 75/50 in `emblem_s`, 10 in `emblem_m` |
| NFTR | `encoding` | Text decoder must match the font | 1 = UTF-16 in all version `0x0100` files; 0 = UTF-8 in all version `0x0001` files |
| NFTR | `line_feed`, cell height | Controls vertical text layout | line feed 11, 13, 15 or 20 |
| NFTR | glyph range and CWDH/CMAP chains | Character-to-glyph mapping and advances; version `0x0001` CWDH entries are 2 bytes | glyph counts 22..462 |
| NANR | animation/frame counts | Must equal the NCER label/cell layout | 2..75 animations, 3..128 frames |
| NANR | animation type and element | Selects the frame payload form; stock files are cell + index only | type 1 / element 0 / play mode 2 in all 141 records |
| NANR | frame content offset | Points to a 16-bit cell index; no fixed stride and `0xCCCC` is alignment padding | `0x00`..`0x12A` across the corpus; 1..31 pad words per file |
| NANR | frame duration | Playback timing in 60 Hz units | 4, 8, 9, 12, 24, 50 and 250 |

### Practical edit guidance

- Replacing an NCGR sheet requires keeping the tile count and color format, or updating every consumer: the NSCR tile indices and palette bits, the NCLR depth/bank count, any NCER cell OAM tile indices, CPOS dimensions, and any NANR frame cell indices. Changing only the NCGR usually produces wrong tiles, wrong colors, or reads past the sheet.
- Replacing an NCLR requires keeping the palette format and the actual PLTT payload/bank order. For course locals that means a 512-byte payload; for 4bpp menu palettes that means 16 banks of 16 colors. Changing the order of banks breaks the NSCR palette field and the `_o` object palettes even when the colors themselves look correct. Do not treat the `7680` declaration as a payload size: the stored payload is `block_size - 0x18` and the 44 extended-flag files still carry one 512-byte bank. No checked MKDS path uses PCMP, so editing it alone changes nothing; preserve it only for tool compatibility.
- Replacing `global.NCGR`/`global.NCLR` changes `global1.NSCR`; replacing `global2.NCGR`/`global2.NCLR` changes `global2.NSCR`. Replacing `local.NCGR`/`local.NCLR` changes both `local2.NSCR` and `local3.NSCR`, because both local maps share the same texture and palette.
- When a course has `global2.NSCR` but no `global2.NCGR/NCLR`, the background screen map is inferred to use the global texture/palette. Do not add a new `global2` pair unless the NSCR is also rebuilt for it; otherwise leave the shared global pair in place.
- Replacing a menu background pair must keep the `_b.NCGR`/`_b.NCLR`/`<stem>.NSCR` stem together. Replacing the object cells must keep `<stem>.nce.ncgr` + `<stem>.nce.ncer` + `<stem>_o.NCLR` together, and preserve the `.bncl`/`.bnll` or NANR animation that indexes those cells. The `_b` and `_o` palettes are both loaded in several menus, so changing only one does not fully recolor the scene.
- Cup pictures are fixed-size assets in the game code: all 32 `_m_b.NCGR` files are 3584 bytes, all `_m_b.NCLR` files are 552 bytes, and all `_m_picture.NSCR` files are 2084 bytes. The `cpic_*` loaders read those exact sizes, so a replacement outside those sizes will be truncated or overflow the fixed buffer.
- Editing an NCER/NANR pair must preserve cell order and labels. NANR frame records address NCER cells by index and are ordered with the label table; adding, removing or reordering cells without rebuilding the NANR produces wrong frames or out-of-range cell indices. For NCERs without a NANR, the same warning applies to the `.bncl`/`.bnll` animation bank.
- Editing an NFTR must preserve the glyph order, CWDH ranges and CMAP mappings, or existing text codes will render the wrong glyphs. Changing line feed, cell height or default advance also shifts every menu layout that uses the font. Version `0x0001` fonts use a 2-byte CWDH entry and store the encoding at FINF+0x0E; do not apply the `0x0100` layout to them. The Main2D fonts are global; the `selectFont` and `MBChild` fonts are scene- or language-specific.
- Localized archives add or override same-named files in the base archive (inferred from the paired base/language archive layout). For text-bearing resources such as `select_character_gp_name_m`, `select_cup_m`, `results_gp_*` and `Keyboard_s_b_*`, edit the base and every language arc that carries the same stem, or some languages will keep the old graphic.
- The 3D emblem palette `emblem_s_b.NCLR` also exists in the `KartModel*` archives and is used for race emblem rendering. Changing the 2D emblem palette without updating the 3D copies leaves the in-race emblem colors inconsistent.
- The Boot `dbgfont` files are legacy (version `0x0001`, BOM `0x0000`) and their declared NCGR size is 8 bytes short. Treat them as boot/debug-only and do not use them as a template for normal menu resources.

### Open questions in the MKDS mapping

- The `global2.NSCR` fallback to `global.NCGR`/`global.NCLR` when the `global2` texture pair is absent is blocked on `m2d_getCourseArcFile` / `sub_02047975` (0x02047975), which is not reconstructed; that wrapper must be reconstructed to prove whether a missing path falls back to the global file.
- `_m`/`_s` are treated as main/sub-screen layouts because paired files are loaded together; exact upper/lower assignment is blocked on `scene/menu/menuGPStates.c`, `menuVSStates.c`, `menuTAStates.c`, `menuMGStates.c` and `menuMRStates.c`, not on the G2D format.
- Full scene usage for the Emblem, Record, ResultDL, WLMenu, Option and Ending archives is blocked on `scene/emblem/emblemScene.c`, `scene/record/recordScene.c`, `scene/result/resultScene.c`, `scene/wlmenu/wlmenuScene.c`, and the corresponding Option/Ending overlay code where no Matching source file exists; the archive/stem mapping is already recorded above.
- NFTR encoding and glyph packing are resolved. Only UTF-8 (`0`) and UTF-16 (`1`) occur in the corpus, so the Shift-JIS (`2`) and CP1252 (`3`) selectors and the five legacy-layout fonts are not exercised by paired text; consumer text-encoding mismatches are outside the G2D format and would require the individual text call sites.
- NANR index-plus-translation and index-plus-SRT payloads are defined by the format but absent from MKDS; no further stock-corpus work is possible without a custom NANR.
- The 44 `7680` NCLR declarations are resolved as the `g2dcvtr -pcm` inverted-size convention (`0x2000 - 0x200`), not a real 15-bank allocation. The remaining question is only which g2dcvtr revision or build flag produced the 14 zero-size variant; the payload and runtime path are the same.
