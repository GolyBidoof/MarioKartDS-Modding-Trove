# MKDS/JNLib UI resources

> **Project:** Mario Kart DS Modding Trove · **Licence:** MIT · **Code:** `include/nitro/mkds/ui/*.h` (umbrella `include/nitro/mkds_ui.h`)

MKDS builds its menus from JNLib, a Nintendo menu library that stores one small binary per screen or widget: JNCL cell placements, JNLL label placements and JNBL touch boxes. The keyboard scenes add `.kbd` hit-rect tables and `.kbdmap` character lists, the emblem scene adds `.lld` placement lists, and `data/Boot` ships the multi-boot banner icon as a 4bpp image with its palette in `.nbfc`/`.nbfp`. The first part of this document records the container offsets and the values observed in the stock corpus; it does not describe NCER, NCGR, NCLR or NSCR, which use the standard Nitro layouts documented by GBATEK. The second part, `MKDS usage and configuration`, maps those containers to the actual screens and lists what to edit.

All integers are little-endian and all containers begin at offset 0 of their own file inside the Nitro archive. The C declarations live in `include/nitro/mkds_ui.h` (an umbrella over `include/nitro/mkds/ui/*.h`); names below in `MkdsUi*` form refer to those headers.

## Corpus

The counts below are from the stock extraction (`unpacked/mkds_stock/root`).

| Format | Files | Records | Size range | Typical locations |
|---|---|---|---|---|
| BNCL (JNCL) | 398 | 8930 | 16–792 bytes | `data/Scene/*_arc`, `data/CharacterKartSelect_*_arc`, `data/Main2D_*_arc` |
| BNLL (JNLL) | 237 | 1859 | 38–606 bytes | same, plus `data/Scene/Record_*_arc` |
| BNBL (JNBL) | 211 | 1357 | 8–128 bytes | same |
| KBD | 10 (5 layouts) | 13–59 per file | 104–472 bytes | `data/Scene/Keyboard_arc`, `data/Scene/Nickname_arc` |
| KBDMAP | 28 (14 unique) | 45–55 chars | 92–112 bytes | same two directories |
| LLD | 4 | 2–43 per file | 26–354 bytes | `data/Scene/Emblem_arc` |
| NBFC | 1 | — | 512 bytes | `data/Boot` |
| NBFP | 1 | — | 32 bytes | `data/Boot` |

The corpus contains no BNCL, BNLL or BNBL with a nonzero reserved header halfword. The JNBL files in `data/Scene/Menu_arc/common/cup_mark.bnbl` and `data/Scene/Record_arc/cup_mark.bnbl` are 8-byte headers with count 0.

## Common coordinate word

JNCL, JNLL and JNBL all store positions as the same 16-bit word (`MkdsUiCoord`), not as plain signed pixels.

| Bits | Field | Meaning |
|---|---|---|
| 0–11 | value | signed 12-bit pixel offset |
| 12–13 | origin | 0 = left/top, 1 = centre, 2 = right/bottom, 3 = never observed |
| 14–15 | line alignment | per-line text alignment on JNLL x words: 0 = start, 1 = centre, 2 = end; 3 behaves like 0 |

The 12-bit value is sign-extended: `0x102A` is value 42 with centre origin, and `0x0FF8` is value −8. `mkds_ui_coord_value()`, `mkds_ui_coord_origin()` and `mkds_ui_coord_param()` read the union overlay.

The origin is applied by the renderer, not stored as a bounding box: with centre origin the consumer subtracts half the cell width and the sprite is centred on the coordinate. For JNLL the x origin selects the block alignment inside the label box (left/centre/right) and the y origin the vertical alignment (top/middle/bottom). Bits 14–15 are the per-line alignment handed to the text renderer: 0 leaves each line at the block origin, 1 adds half the difference between the widest line and the current line, 2 adds the full difference (right-aligns each line to the widest line), and 3 has no branch so it behaves like 0. They are not a position, and they do nothing on a single-line label because the widest and current line are equal. The path is proven: the JNLL label routine passes the x-word top two bits at `0x0212428C`, and the line-offset helper at `0x021253AC` applies the difference at the start of each line. They are set on 871 of 1859 JNLL x words (735 value 1, 136 value 2), never on y and never in JNCL/JNBL. The only stock multi-line labels with a nonzero value are the two `WLMenu` `multi_select_NS_s.bnll` strings (value 1); the other 40 multi-line labels use 0. Preserve the value when moving or rewriting a label.

## BNCL

`JNCL` is a cell placement list: each record places one cell from the NCER cell bank that the scene loads alongside it.

| Offset | Field |
|---|---|
| 0x00 | `JNCL` magic (4 bytes) |
| 0x04 | reserved `uint16_t`, 0 |
| 0x06 | record count `uint16_t` |
| 0x08 | first record |

Each record is 8 bytes and matches `MkdsUiCellElement`.

| Offset | Field |
|---|---|
| +0x00 | x coordinate word |
| +0x02 | y coordinate word |
| +0x04 | cell id `uint32_t` |

`cell_id` is an index into the NCER cell bank, not an index into the JNCL. For example `data/CharacterKartSelect_arc/select_character_s.bncl` has 38 records whose cell ids are 0–15, and the matching `select_character_s.nce.ncer` declares 17 cells. The same cell id may appear many times: in that file cell 15 is placed 12 times on a 4×3 grid and cell 12 is placed 12 times on the inner grid, while cells 0–11, 13 and 14 appear once. These are separate placements, not animation frames stored in the BNCL.

Stock counts range from 1 (`data/Scene/Ending_arc/ending_thanks_00.bncl`) to 98 (`data/Scene/WLMenu_us_arc/multi_select_member_s_group.bncl`, 792 bytes = 8 + 98×8). The largest cell id observed anywhere is 57. Coordinates are mostly centre-origin; the observed value range is −16 to 343.

The first record of `data/CharacterKartSelect_arc/select_character_s.bncl` is `2A 10 20 10 0F 00 00 00`: x = 0x102A (42, centre), y = 0x1020 (32, centre), cell 15.

## BNLL

`JNLL` is a label placement list. It has the same 8-byte header as JNCL, then 12-byte records (`MkdsUiLabelElement`), then a pool of NUL-terminated UTF-16LE strings.

| Offset | Field |
|---|---|
| 0x00 | `JNLL` magic (4 bytes) |
| 0x04 | reserved `uint16_t`, 0 |
| 0x06 | record count `uint16_t` |
| 0x08 | first record |
| 0x08 + 12×count | first string |

| Record offset | Field |
|---|---|
| +0x00 | x coordinate word |
| +0x02 | y coordinate word |
| +0x04 | horizontal spacing `int8_t` |
| +0x05 | vertical spacing `int8_t` |
| +0x06 | style `MkdsUiLabelStyle` (16 bits) |
| +0x08 | string offset `uint32_t`, relative to file start |

The style halfword (`MkdsUiLabelStyle`) overlays `color:8, palette:4, font:4` on the raw halfword, low bits first; `style.bits.color`, `style.bits.palette` and `style.bits.font` name the three fields. `color` is the colour index inside the selected 16-colour OBJ palette, `palette` is the OBJ palette bank written into the OAM palette field, and `font` indexes the resident font table (stock value 0 = small UI font, 1 = medium UI font, 2 = Mario font). Observed stock values are colour 1–15, palette 0/14/15 (15 in 1362 of 1859 labels) and font 0/1/2. `h_space` is added after every glyph as an inter-character advance and `v_space` is added to the font height for each line; both are pixel values, not fixed-point. Horizontal spacing is −1, 0 or 1 (1498 ones) and vertical spacing is 0, 2 or 3 (1844 zeroes).

In all 237 files the string pool begins exactly at `8 + 12×count`, all offsets are ascending and distinct, and the last string ends at the end of the file; there is no padding and no BOM. The renderer adds the string at runtime, and stock files use placeholder text that the game overwrites: `data/CharacterKartSelect_ge_arc/select_menu_etc_m.bnll` has 8 records at 0x68, each a 4-character string plus NUL, 10 bytes apart. `data/CharacterKartSelect_ge_arc/select_kart_s.bnll` has 9 records after a 0x74 pool and contains the labels `アイテム`, `ドリフト`, `ハンドリング`, `おもさ`, `かそく` and `スピード`, followed by `OK` and two `Kart_name` entries.

A label record from that file is `07 00 85 20 01 00 0D 00 74 00 00 00`: x = 0x0007 (7, left), y = 0x2085 (133, bottom origin), horizontal spacing 1, vertical spacing 0, style 0x000D (colour 13, palette 0, font 0), string at 0x74. Its neighbour at record 6 has x = 0x5080 (128, centre, line alignment 1), y = 0x10AD (173, centre), style 0x200E (colour 14, palette 0, font 2) and the string `OK`.

`count` ranges from 1 (`data/Scene/Record_es_arc/Record_Gpx_m.bnll`) to 18 (`data/Scene/Ghost_us_arc/TimeAttack_ghost_send_s.bnll`). Strings are 1 to 142 characters; the longest ones are localized menu sentences rather than placeholders.

At load time the JNLL records are appended after the JNCL records, so element indices `0..bnclCount-1` are cells and `bnclCount..` are labels. The two files are loaded as a pair by the scene.

## BNBL

`JNBL` is a flat list of touch rectangles with no id or callback. It has the same 8-byte header, then 6-byte records (`MkdsUiBoxElement`).

| Offset | Field |
|---|---|
| 0x00 | `JNBL` magic (4 bytes) |
| 0x04 | reserved `uint16_t`, 0 |
| 0x06 | record count `uint16_t` |
| 0x08 | first record |

| Record offset | Field |
|---|---|
| +0x00 | x coordinate word |
| +0x02 | y coordinate word |
| +0x04 | width `uint8_t` |
| +0x05 | height `uint8_t` |

A record is `x(2) + y(2) + w(1) + h(1)`. Widths and heights are unsigned, up to 200 in the corpus. Because the format carries no id, the record order is the only ordering information available in the file.

`data/CharacterKartSelect_arc/select_character_s.bnbl` is the cleanest example: 12 records of 40×40 at centre coordinates (39,29), (99,29), (159,29), (219,29), (39,81), … and (219,133). `data/CharacterKartSelect_us_arc/select_kart_s.bnbl` has 3 records: 15×24 at centre (22,21), 15×24 at centre (227,21), and 64×23 at (96,161). Counts range from 0 to 20; the corpus total is 1357 records.

## KBD

`.kbd` is a list of 8-byte keyboard hit rectangles, stored without a header or terminator. The file length divided by 8 is the record count.

| Offset | Field |
|---|---|
| +0x00 | x `uint8_t` |
| +0x01 | y `uint8_t` |
| +0x02 | width `uint8_t` |
| +0x03 | height `uint8_t` |
| +0x04 | rectangle-chain step `int16_t`, 0 in all 10 files |
| +0x06 | key id `uint16_t`, 1-based and sequential |

The ten files cover five layouts, each duplicated in `data/Scene/Keyboard_arc` and `data/Scene/Nickname_arc`. The exception is `10key.kbd`: both copies have the same rectangles and ids but list the 4/5/6 and 10/11/12 rows in the opposite order, so the ids differ.

| File | Records | Bytes | Notes |
|---|---|---|---|
| `ascii.kbd` | 50 | 400 | QWERTY, 45 character keys |
| `euro.kbd` | 55 | 440 | accented Latin, 52 character keys |
| `jp.kbd` | 59 | 472 | hiragana/katakana, 51 character keys |
| `picto.kbd` | 58 | 464 | symbol keyboard, 55 character keys |
| `10key.kbd` | 13 | 104 | 3×4 digit pad |

`ascii.kbd` starts with the non-character keys: `(218,33,31,20)` for backspace, a 1×1 record at `(255,52)`, and `(88,96,99,20)` for the space bar. The character keys begin at record 6 with `(8,12,19,20)` for `1` and continue row-major. `jp.kbd` instead starts with two tall 20×41 keys at `(228,33)` and `(228,75)`, another 1×1 record at `(255,76)`, and then an 11×5 key grid whose first entry is `(8,12,19,20)`. Ids 1–8 are the control block (the first grid column, ids 4–8, is part of it), so the 51 character keys begin at id 9 with `(28,12,19,20)`.

Every file contains exactly one 1×1 record with x = 255 except `10key.kbd`, which has two at `(135,127)` and `(115,127)`. The hit test rejects any entry with width ≤ 1 or height ≤ 1, and the keytop pass skips the same entries, so these are not touch or cursor targets. They keep the 1-based key-id sequence intact for control keys that have no touch rectangle. Id 1 is backspace (code 8) in every layout, including `10key.kbd`; id 2 becomes `0x0A` (newline/confirm) in every layout; id 3 becomes space (`0x20`, or `0x3000` in `jp.kbd`) and is also `0x20` in `10key.kbd`. The alphabetic layouts give space a real rectangle, so only id 2 is 1×1; `10key.kbd` suppresses both the confirm and space rectangles, so ids 2 and 3 are both 1×1. The visible confirm and back buttons are the two bottom BNBL boxes at y = 172, handled by the scene's `jn_ui_checkTouch`, so the KBD table does not need a rectangle for them.

The halfword at +0x04 is not padding. The cursor/selection redraw starts at the selected record, draws its four bytes, then advances the record pointer by the signed halfword at +0x04 times 8 and repeats until it returns to the starting record. Zero therefore draws exactly one rectangle, which is the stock case in all 10 files; a nonzero value would make the same highlight pass visit more records. No stock file uses a nonzero value, so whether those records were meant as extra pieces of one key is unproven. The hit test and the keytop pass do not read +0x04.

## KBDMAP

`.kbdmap` is a byte-order mark followed by UTF-16LE code units, with no count field.

| Offset | Field |
|---|---|
| 0x00 | BOM `0xFFFE` (`FE FF` in file order) |
| 0x02 | UTF-16LE code units to end of file |

`mkds_ui_kbdmap_count()` computes `(size - 2) / 2` and `mkds_ui_kbdmap_char()` reads one unit. The corpus has 14 unique maps (28 files, duplicated per keyboard directory).

| Map | Units | Content |
|---|---|---|
| `ascii.kbdmap` | 45 | ``1234567890-=qwertyuiopasdfghjklzxcvbnm,./;`[]`` |
| `ascii_caps.kbdmap` | 45 | uppercase letters, same digits and punctuation |
| `ascii_shift.kbdmap` | 45 | `!@#$%^&*()_+…<>?:~{}` |
| `hiragana*.kbdmap` | 51 | あいうえお… with dakuten/handaku/small variants |
| `katakana*.kbdmap` | 51 | アイウエオ… with dakuten/handaku/small variants |
| `other1.kbdmap` | 55 | accented Latin (52 characters plus 3 never-read spaces) |
| `other2.kbdmap` | 55 | symbols, punctuation and arrows |
| `other3.kbdmap` | 55 | private-use units `U+E000`–`U+E028` mixed with `+-☆○◇□△▽◎★●◆■▲▼` |

The map lists the characters produced by the character keys of the matching KBD, in the order those keys appear. The page constructor stores a base id in the runtime table (5 for `ascii.kbd`, 8 for `jp.kbd`, 3 for `euro.kbd`, `picto.kbd` and `10key.kbd`), and the character for a key is `map[key_id - base - 1]`. `ascii.kbd` therefore uses its 45 units for ids 6–50, `jp.kbd` uses its 51 units for ids 9–59, `euro.kbd` uses 52 of the 55 `other1` units for ids 4–55, `picto.kbd` uses 55 units for ids 4–58, and `10key.kbd` uses the first 10 `other3` units for ids 4–13, which are `1234567890`. Ids at or below the base are the control keys described in the KBD section, not map characters. The euro table has 52 character ids, so the last three spaces in `other1.kbdmap` are never read. The private-use units `U+E000`–`U+E028` in `other3.kbdmap` are the codes the picto keyboard returns for its symbol glyphs; the glyphs are drawn from the keyboard NCGR/NSCR, not stored in the map.

## LLD

`.lld` files are emblem-screen placement lists. The layout is a 2-byte count, that many 8-byte records, and eight trailing zero bytes that the loader does not read, so `file_size = 2 + 8×count + 8`.

| Offset | Field |
|---|---|
| 0x00 | count `uint16_t` |
| 0x02 | first record |
| 0x02 + 8×count | trailing zeros, not read |

| Record offset | Field |
|---|---|
| +0x00 | id `uint16_t`, NCER cell id and NANR sequence id |
| +0x02 | x `uint16_t` |
| +0x04 | y `uint16_t` |
| +0x06 | flags `uint16_t`, 0 = inactive, nonzero = active; stock only 0/1 |

The loader in overlay9_1 (function at `0x21852F8`) reads the count, allocates one 136-byte runtime element per record, stores `id` at +0, converts `x` and `y` from pixels to 20.12 fixed point (`pixel << 12`) at +4/+8, and stores `flags != 0` as an enable flag at +0x0C. `id` selects a cell in the paired NCER cell bank (the builder's +8 argument) and a sequence in the paired NANR animation bank (+12); `0x2021DB0` is the bounds-checked NANR sequence lookup (16-byte entries, returns NULL when `id` ≥ count). The same sparse id therefore selects the same cell and animation in every file that shares the pair. Record order, not id, is the runtime slot: scenes address elements as `array + slot*136`.

| File | Count | Bytes | Ids observed |
|---|---|---|---|
| `emblem_camera_s.lld` | 2 | 26 | 0, 1 |
| `emblem_m.lld` | 10 | 90 | 0–9 |
| `emblem_s.lld` | 43 | 354 | 0–42 |
| `emblem_template_s.lld` | 32 | 266 | 43–74 |

`emblem_camera_s.lld` is `02 00` then `(0,128,96,1)`, `(1,200,172,1)` and the trailing zeros. `emblem_m.lld` places ids 0–9, for example `(1,197,181,0)`, `(3,216,181,1)` and `(9,128,0,1)`. `emblem_s.lld` is the touch-screen tool layout: ids 6–13 sit at x = 240 with y = 26, 47, … 173 (eight colour swatches), ids 14–20 sit at x = 216 with the same 21-pixel pitch (seven more), ids 21–28 form two columns at x = 14/39 with y = 28, 52, 76 and 104, ids 29–30 sit at (26,137) and (26,170), and ids 0–3 are a 2×2 block at (205,170), (220,170), (205,184), (220,184). `emblem_template_s.lld` places ids 73 and 74 at (13,189) and (29,170), then ids 43–72 in a 6×5 grid with x = 43 + 34·column and y = 22 + 34·row, which is the emblem template chooser.

`flags` is the initial enable state of the element: the builder stores `flags != 0` at +0x0C, the render pass skips any element whose +0x0C is zero, and the animation step at `0x2184FF8` returns `-5` instead of advancing a disabled element. The editor can toggle the same flag at runtime through the command interface at `0x2185018`, so the file value is only the initial state. Values above 1 also set a second state word at +0x34 (`flags > 1`), but no stock record uses more than 1. In `emblem_s.lld` ids 0–5, 31–34, 37–39 and 42 start disabled while 6–30, 35, 36, 40 and 41 start enabled; preserve the value when rewriting. The parser reads exactly `count` records and never consumes the trailing eight zero bytes, so those bytes are padding, not an id-0 record.

## NBFC and NBFP

`data/Boot/mkds_banner02.nbfc` is a 512-byte 4bpp image and `mkds_banner02.nbfp` is its 16-colour palette. These use the standard Nitro 4bpp tile image and RGB555 palette conventions (GBATEK), so only the corpus-specific facts are listed here.

| File | Size | Layout |
|---|---|---|
| NBFC | 512 | 32×32 pixels, 16 8×8 tiles of 32 bytes, tiles row-major |
| NBFP | 32 | 16 little-endian RGB555 halfwords |

The tile data uses colour indices 0–14; index 15 is not referenced. Palette entries are packed as red in bits 0–4, green in bits 5–9 and blue in bits 10–14, with bit 15 zero in all 16 entries. `mkds_ui_rgb555_red()`, `mkds_ui_rgb555_green()` and `mkds_ui_rgb555_blue()` expand a channel to 8 bits.

Observed palette values include index 0 = `0x7E00` (0,128,248), index 4 = `0x7FFF` (white) and index 15 = `0x0000` (black). Index 0 is a solid blue, not a transparent key, so the image is opaque.

Decoding the pair with this layout produces a coherent 32×32 character-in-kart icon, so the two files are an icon and its palette rather than a font sheet. They are global Nitro FS resources, not scene-arc members: the ARM9 `MBGameRegistry` at `0x0215472C` has `romFilePathp` at +0x00 (an empty string), `gameNamep` at +0x04 and `gameIntroductionp` at +0x08 (filled at runtime by `0x204EA14` from message ids 0 and 1), `iconCharPathp` at +0x0C = `/data/boot/mkds_banner02.nbfc`, `iconPalettePathp` at +0x10 = `.nbfp`, `ggid` = `0x25` at +0x14, `maxPlayerNum` = 8 at +0x18, and 32 bytes of `userParam` at +0x1C. `0x204EA3C` calls `MB_GetSegmentLength`, `MB_ReadSegment` and then `MB_RegisterFile(&registry, segment)`, so the consumer is the Nitro multi-boot library, not a game screen. The child's Download Play menu (IPL) is what displays the icon; the game itself never decodes NBFC/NBFP. `data/Boot` is simply where the two registry path strings point.

## Open points and limits

The reserved halfword in the 8-byte JNCL/JNLL/JNBL header at +0x04 is never read by the stock JNLib code; only the count at +0x06 is used. It is runtime padding, and whether the authoring tool stored a version or flags there cannot be recovered from the game. This does not apply to the KBD halfword at the same offset, which the keyboard redraw does read (see `KBD`).

JNCL `cell_id` is bounds-checked by `NNS_G2dGetCellDataByIdx`, but JNLib does not check the result: the SDK lookup returns NULL when `id` ≥ the cell count, and the render, priority and translucency helpers dereference it. An out-of-range id therefore faults instead of drawing nothing. No stock file exercises this: a name-based sweep of all 398 BNCLs found a same-stem or common-arc NCER for every file (including the `_o` art variants and the ending/trophy pairs), and no id is at or above that NCER's cell count. The largest id anywhere is 57 (`select_menu_etc_m.bncl`), against a paired count of 58.

`palette` 15 is an ordinary OBJ palette bank, not a format-level "labels" bank: the label renderer writes `style.bits.palette` into the OAM palette field, the stock menu layout uploads banks 0–12 and 14–15 from the scene NCLR, and most labels select bank 15 (the last 32 bytes of the NCLR). A scene whose NCLR does not upload usable colours into bank 15 will draw label text with the wrong palette.

Repeated JNCL placements (12 copies of cell 15 in `select_character_s.bncl`) are per-slot copies that character select moves by element index. Other screens have not all been checked, but no stock BNCL uses repeats as animation frames stored in the file.

The KBDMAP private-use units `U+E000`–`U+E028` are returned as character codes for the picto symbols, but the code-to-glyph table lives in the keyboard NCGR/NSCR, not in the corpus. Resolving it needs the keyboard NSCR or font mapping.

The LLD element is a cell animation: `NNS_G2dInitCellAnimation` at `0x2022904` binds the NCER cell bank and the NANR sequence selected by `id`, and `0x20220F0` advances it. `flags` 0/1 is proven to be the initial enable state, not a label/text selector. The remaining unknown is the second state word written at +0x34 when `flags > 1`; no stock file uses such a value, so its effect is untested.

NBFC/NBFP are proven to be the multi-boot banner icon and palette registered through `MB_RegisterFile`; only the IPL's own drawing of that icon is outside the game binary.

---

# MKDS usage and configuration

This part is MKDS-specific. It maps the containers to the screens that load them and lists the fields to edit; it is not part of the generic format description. A mapping backed by a game call site is marked verified, a mapping backed by a file name in an overlay or the ARM9 string table is marked strong, and a mapping derived only from geometry or content is marked inferred.

## Screen and resource map

Layouts live in per-language arcs (`Title_*_arc`, `Menu_*_arc`, `Result_*_arc`, and so on). Most are byte-identical across the five language arcs: of 163 duplicated layout names, 35 differ. The differences are concentrated in the `Record_*` group, the two `select_race_rule_*` label files, `select_menu_etc_m.bncl`, `select_menu_etc_download_m.bncl`, the Wi-Fi top/matching files, mission LV/MS layouts, cup and engine select, and `Option_embrem_select_s.bnll`. KBD, KBDMAP, LLD, NBFC and NBFP are not language-split, and the two copies of every KBD and KBDMAP (`Keyboard_arc` and `Nickname_arc`) are identical; the only difference in the whole set is the record order of `10key.kbd` between the two arcs.

| Screen / menu | Arc | BNCL | BNLL | BNBL | Evidence |
|---|---|---|---|---|---|
| Title | `Title_*_arc` | `title_s.bncl` (15) | `title_s.bnll` (2) | `title_s.bnbl` (5) | verified: `title.c` loads all three; the two labels are Options and Records and are replaced from `title.bmg` |
| Main menu, mode select | `Menu_*_arc/common` | `single_play_select_mode_m.bncl` (1), `single_play_select_mode_s.bncl` (15) | — | `single_play_select_mode_s.bnbl` (5) | verified: `menu.c` |
| Game select (single, multi, battle) | `Menu_*_arc/common`, `MenuDL_*_arc/common` | `select_game_m.bncl` (10), `select_game_multi_s.bncl` (9), `select_game_battle_s.bncl` | `select_game_m.bnll` (10) | `select_game_multi_s.bnbl` (3), `select_game_battle_s.bnbl` | verified: `gameSelect.c`; the 10 labels are filled from `menu.bmg` ids through a fixed label table |
| VS rules | `Menu_*_arc/common`, `MenuDL_*_arc/common` | `select_race_rule_s.bncl` (43), `select_race_rule_multi_simple_s.bncl` | `select_race_rule_s.bnll` (15), multi-simple variant | `select_race_rule_s.bnbl` (20), multi-simple variant | strong: ARM9 string table; this is the screen described in `docs/options-class-row.md` |
| Download Play menu | `MenuDL_*_arc/mb` | `select_menu_etc_download_m.bncl` | `select_menu_etc_download_m.bnll` | — | strong: ARM9 string table |
| Cup select | `Menu_*_arc/common` | `select_cup_m.bncl`, `select_cup_s.bncl`, `select_cup_name_m.bncl`, `select_cup_course_ta_m.bncl`, `select_cup_course_vs_m.bncl`, `cup_mark.bncl` (8), `trophy_icon.bncl` (8) | `select_cup_m.bnll` and the two course lists | `select_cup_m.bnbl`, `select_cup_s.bnbl`, `cup_mark.bnbl` | strong: ARM9 string table; 8 cup entries |
| Engine / cc select | `Menu_*_arc/gp` | `select_engine_m.bncl`, `select_engine_A_s.bncl`, `select_engine_B_s.bncl` | — | `select_engine_A_s.bnbl`, `select_engine_B_s.bnbl` | strong: overlay9_1 string table |
| Battle stage select | `Menu_*_arc/mg` | `select_battle_stage_m.bncl`, `select_battle_stage_s.bncl` | `select_battle_stage_m.bnll` | `select_battle_stage_s.bnbl` | strong: overlay9_1 string table |
| Character select | `CharacterKartSelect_arc` + `CharacterKartSelect_*_arc` | `select_character_s.bncl` (38) plus `select_character_gp_m.bncl`, `select_character_gp_title_m.bncl`, `select_character_gp_name_m.bncl`, `select_menu_etc_m.bncl`, `select_menu_etc_title_m.bncl` | `select_menu_etc_m.bnll` (8) | `select_character_s.bnbl` (12) | verified: `charSelect.c`; the `gp_*` files are placeholder layouts filled from their NCER at runtime |
| Kart select | `CharacterKartSelect_arc` + `CharacterKartSelect_*_arc` | `select_kart_s.bncl` (19) plus the same `gp_*` placeholders | `select_kart_s.bnll` (9) | `select_kart_s.bnbl` (3) | verified: `kartSelect.c` |
| Time Trials top and ghost select | `Menu_*_arc/ta`, `Ghost_*_arc` | `TimeAttack_top_menu_s.bncl`, `ta/select_ghost_s.bncl`, `TimeAttack_ghost_get_m/s.bncl`, `TimeAttack_ghost_get_s_sel.bncl`, `TimeAttack_ghost_send_m/s.bncl` | all but the top-menu file | `select_ghost_s.bnbl`, `TimeAttack_ghost_get_s.bnbl`, `_get_s_sel.bnbl`, `_send_s.bnbl` | strong: ARM9 string table |
| Records | `Record_*_arc` | `Record_top_menu_m/s.bncl`, `Record_Gpx_m/s.bncl`, `Record_T_att_m/s.bncl`, `Record_VS_m.bncl`, `Record_VS_m_transient.bncl`, `Record_VS_s.bncl`, `Record_VS_s_erase.bncl`, `Record_trophy_s_o.bncl` | 9 files | 5 files | strong: ARM9 string table; this is the most language-sensitive layout group |
| Wi-Fi | `WiFiMenu_*_arc` | `WiFi_top_menu_s.bncl`, `WiFi_VS_setting.bncl`, `WiFi_VS_matching.bncl`, `WiFi_aikotoba.bncl`, `WiFi_aikotoba_check.bncl`, `WiFi_VS_course_select_m/s.bncl` | setting, matching, course select | setting, aikotoba, top menu, course select | split: overlay9_0 string table (top/setting/matching/aikotoba); verified course select in `wifiMenuTrackSelectScene.c` |
| GP results | `Result_*_arc` | `results_gp_m.bncl` (21), `results_gp_s.bncl` (17), `cup_name_left.bncl` (8) | `results_gp_m.bnll` (1), `results_gp_s.bnll` (16) | — | verified: `gpResult.c` |
| Battle results | `ResultDL_*_arc` | `results_battle_s.bncl`, `Results_battle_VS_m.bncl`, `_draw_m.bncl`, `_lose_m.bncl`, `_victory_m.bncl` | `results_battle_s.bnll`, `_lose_m.bnll`, `_victory_m.bnll` | — | strong: ARM9 string table |
| Options | `Option_*_arc` | `Option_top_menu_s.bncl` (12), `Option_select_menu_m.bncl` (1), `Option_select_menu_s.bncl` (25), `Option_hensyu_menu_s.bncl` (8), `Option_embrem_select_s.bncl` (15) | select m/s, embrem | top menu, select s, hensyu, embrem | strong: overlay9_1 string table |
| Emblem editor | `Option_*_arc`, `Emblem_arc` | `Option_embrem_select_s.bncl`, `Option_hensyu_menu_s.bncl` | `Option_embrem_select_s.bnll` | embrem, hensyu | strong: overlay9_1; the LLD files are listed below |
| Ending and staff roll | `Ending_arc`, `StaffRoll_arc` | `ending_thanks_00.bncl`, `ending_thanks_01.bncl`, `ending_staffRoll.bncl` | both thanks files | — | strong: overlay9_1 and ARM9 string tables |
| Keyboard | `Keyboard_*_arc` | `Keyboard_s.bncl` (37), `Keyboard_s_10key.bncl` (23) | `Keyboard_s.bnll` (12), `Keyboard_s_10key.bnll` (14) | `Keyboard_s.bnbl` (7), `Keyboard_s_10key.bnbl` (2) | verified: ARM9 keyboard scene |
| Wireless member select | `WLMenu_*_arc` | `multi_select_member_s_group.bncl` (98), `multi_select_NS_s.bncl`, `multi_select_member_m.bncl`, `multi_select_member_s_register.bncl` | all four | group, NS, register | strong: ARM9 string table; 98 is the largest BNCL in the corpus |
| Mission select | `Menu_*_arc/mr` | `Mission_run_LVsel_s_6.bncl`, `Mission_run_LVsel_s_7.bncl`, `Mission_run_MSsel_m.bncl`, `Mission_run_MSsel_s.bncl`, `Mission_run_BOSS_icon_s.bncl` | four | three | strong: overlay9_1 and ARM9 string tables |
| Shared wait | `Menu_*_arc/common`, `MenuDL_arc/common` | `wait.bncl` (3) | — | — | verified: `waitIndicator.c`, three animation frames |
| Shared kart icon atlas | `Menu_*_arc/common`, `Ghost_*_arc` | `Kart_icon_all.bncl` (36) | — | — | verified: `kartIcon.c`, 36 kart slots |
| Race 2D portraits | `Main2D_*_arc` | `player_character_M.bncl` (13), `player_character_L.bncl` (13) | — | — | verified: `main2d.c`, medium and large portrait placeholders |
| Search icon | `Static2D_arc` | `search_icon_00.bncl` (11), `search_icon_layout_00.bncl` (2) | — | — | verified load in `static2d.c`; wireless search use is inferred |

`Kart_icon_all.bncl` is the clearest example of a shared atlas: 36 records, one per kart, and the scene picks a record by kart id and a palette from three NCLR files (`Kart_icon_o_A/B/C`) and a palette row. `player_character_M/L.bncl` are pure placeholders: 13 records with cell ids 0–12 and zero coordinates, over which scenes copy a portrait cell at runtime. `wait.bncl` cycles its three records every four updates.

## How BNCL, BNLL and BNBL fit together

BNCL is the drawing list. Each record places one NCER cell, the record index is the element index the scene uses for visibility, affine transforms and runtime movement, and the cell id selects the graphic. A file with no BNLL or BNBL is still a complete visual layout (the title screen uses all three, while `single_play_select_mode_m.bncl` is a single cell and nothing else).

BNLL is a text overlay, not a second drawing list. Its records are appended after the BNCL elements in one heap array, so the global element index of label `i` is `bncl.count + i`; a change to the BNCL count therefore renumbers every label. The BNLL record supplies the anchor position, the origin used for alignment, the spacing, the colour/palette/font and a string; it does not supply the label box size. The scene passes width and height to `jnui_initLabel`, draws the text into a private 16-colour OBJ canvas for that box, and uploads those tiles. The initial string is usually replaced at runtime from a BMG (`gameSelect` maps label `i` to a `menu.bmg` id, `gpResult` builds times and course names, `title.c` uses `title.bmg`).

BNBL is a touch overlay only. Nothing draws from it; `jnui_checkTouch` walks its records in file order, returns the first index whose rectangle contains the touch point, and the scene compares that index with its own button table. Scenes also move boxes at runtime: character select sets each button box to the current grid position and parks unused boxes at `(0x400, 0x400)`, which is outside the screen.

The hierarchy is therefore: BNCL is authoritative for what is drawn and where, BNLL for text defaults and text styling, BNBL for touch. All three are initial state; any screen that animates, fills placeholders or lays out buttons at runtime can override them, so a file edit is only visible if the scene does not overwrite that field.

| Array | Index range | Addressed by |
|---|---|---|
| BNCL cells | `0 .. bncl.count-1` | scene element indices, visibility, affine, movement |
| BNLL labels | `bncl.count .. bncl.count+bnll.count-1` | label index in the scene's label table |
| BNBL boxes | own `0 .. bnbl.count-1` | touch result, button tables, runtime repositioning |

## Keyboard resources

The keyboard scene loads all five KBD tables and all fourteen KBDMAP files at init into one state block; a page selector then chooses which table and map are active. The KBD file supplies the hit rectangles only, the KBDMAP supplies the characters only, and the visible key art comes from the keyboard BG (NSCR/NCGR) in the shared `Keyboard_arc`.

| KBD | Records | Base | Character ids | Maps | Use |
|---|---|---|---|---|---|
| `ascii.kbd` | 50 | 5 | 6–50 | `ascii`, `ascii_shift`, `ascii_caps` | Latin text entry, base/shift/caps |
| `euro.kbd` | 55 | 3 | 4–55 | `other1` | Accented Latin entry |
| `jp.kbd` | 59 | 8 | 9–59 | `hiragana`, `katakana` and their dakuten/handaku/small variants | Japanese entry |
| `picto.kbd` | 58 | 3 | 4–58 | `other2`, `other3` | Two symbol pages |
| `10key.kbd` | 13 | 3 | 4–13 | `other3` | Numeric entry (friend code, password) |

The ARM9 page switch chooses the base map by page value: 1 = `hiragana`, 2 = `ascii`, 3 = `other1`, 4 = `other2`, and 0 or 5 = `other3`. Page 0/5 selects the `10key.kbd` table together with `other3`; the first ten units of `other3` are `1234567890`, which are the keytop characters, so the map is not unused. A second switch handles the ASCII modifier: mode 0 = `ascii`, 4 = `ascii_shift`, 5 = `ascii_caps`; the Japanese page selects hiragana or katakana and then the base, dakuten, handaku or small map. Each page constructor also stores `base = control_count - 1` (5 for ascii, 8 for jp, 3 for euro, picto and 10key), and the character lookup is `map[key_id - base - 1]`; the map pointer is advanced by 2 before use, which matches the 0xFFFE BOM prefix.

The keyboard BNCL is not a key grid: `Keyboard_s.bncl` has 37 cells against the 50 rectangles of `ascii.kbd`, so it most likely places cursor, selection and preview elements over the background keyboard image (inferred from the cell count and the repeated cell ids); the 7 BNBL boxes cover the non-key buttons (inferred from the count against the 50 KBD rectangles). `Keyboard_s_10key.bncl` has 23 cells against 13 KBD rectangles. The KBD control ids 1–5 (ascii), 1–8 (jp) and 1–3 (euro, picto, 10key) are not characters and include the newline/confirm code `0x0A`; the 1×1 entries hold id 2, and id 3 in `10key.kbd`, and are skipped by the hit test. Changing a key rectangle therefore changes only the touch area; changing a character means editing the KBDMAP unit; changing the glyph means editing the NCGR/NSCR.

## Emblem and banner resources

The four LLD files live in `Emblem_arc` and are grouped in overlay9_1 next to the matching cell, animation and screen files; the same overlay contains the four call sites that load them through the shared parser at `0x21852F8`, which fixes their roles. All use the same record shape: id, x, y, flags.

| File | Role | Ids | Evidence |
|---|---|---|---|
| `emblem_m.lld` | Top-screen emblem status/controls | 0–9 | grouped with `emblem_m.NANR`, `emblem_m.NSCR`, `emblem_m_b.NCGR/NCLR` |
| `emblem_s.lld` | Bottom-screen editor tool and palette layout | 0–42 | grouped with `emblem_s.NCER`, `emblem_s.NANR`, `emblem_s_tool.NSCR` |
| `emblem_template_s.lld` | Template chooser, 6×5 icon grid plus two buttons | 43–74 | follows `emblem_s.lld`; ids 43–72 form a 34-pixel grid at x = 43+34·column, y = 22+34·row (a few cells are off by one pixel) |
| `emblem_camera_s.lld` | Camera preview anchors | 0–1 | grouped with `emblem_camera_s.NANR/NCGR`, `emblem_camera_s_DS.NSCR` |

The id split (0–42 tools, 43–72 template icons, 73–74 buttons) is inferred from the geometry and from the fact that the ids are unique across all four files. `flags` is the initial enable state of the element (0 = not drawn or animated, nonzero = active), not a page or palette selector; the editor can toggle the same flag at runtime.

NBFC/NBFP are a 32×32 4bpp image and its 16-colour palette. Decoding them with the documented tile order and RGB555 packing produces a character-in-kart icon on a solid blue field, so the pair is an icon (banner character data and palette), not a font. The two paths are fields of the ARM9 `MBGameRegistry` at `0x0215472C` (+0x0C `.nbfc`, +0x10 `.nbfp`); `0x204EA3C` passes that registry to `MB_RegisterFile`, so the consumer is the Nitro multi-boot library. The child's Download Play menu (IPL), not a game scene, draws the icon.

## Fields that matter when editing

| File | Field | Controls | Notes |
|---|---|---|---|
| BNCL | count at +0x06 | number of cells | Changing it renumbers every BNLL label (labels are at `bncl.count+i`) |
| BNCL | x/y value and origin | cell position and anchor | Origin 1/2 make the coordinate a centre or right/bottom edge, not a top-left corner |
| BNCL | cell id at +0x04 | NCER cell index | The SDK lookup returns NULL when `id` ≥ the paired NCER count and JNLib dereferences it, so an out-of-range id faults. All 398 stock BNCLs are in range (largest id 57). |
| BNCL | record order | element index | Scene tables and `elements[i]` addresses are index-based |
| BNLL | count at +0x06 | number of labels | Scene label tables are usually sized to this count |
| BNLL | x/y and origin | anchor and text alignment | Origin also sets left/centre/right and top/middle/bottom alignment inside the label box |
| BNLL | h_space/v_space | inter-glyph advance / line-height addition | Signed pixel values; −1 tightens, 1 loosens; v_space is added to the font height |
| BNLL | `style.bits.color` / `.palette` / `.font` | colour index / OBJ palette bank / font index | Palette must exist in the scene NCLR; font 0–2 selects the resident small, medium and Mario fonts |
| BNLL | string offset at +0x08 | UTF-16LE string | File-relative, must point at a NUL-terminated string; stock files pack the pool immediately after the records |
| BNLL | `x.bits.param` | per-line text alignment (0 start, 1 centre, 2 end) | Not a position; applies to lines inside the block set by the x origin |
| BNBL | x/y, width/height | touch rectangle | Origin applies exactly as in BNCL |
| BNBL | record order | hit-test priority | The first containing rectangle wins |
| KBD | x/y/w/h | key hit rectangle | Purely hit-test; the key art is elsewhere |
| KBD | key id at +0x06 | record ordinal and map index base | Keep 1-based and sequential; the character is `map[key_id - base - 1]` |
| KBD | chain step at +0x04 | extra highlight rectangles for one key | Signed step in 8-byte records; 0 (all stock files) means one rectangle. The hit test ignores it. |
| KBDMAP | units after the BOM | produced characters | One unit per character key, in KBD order; pad with spaces if needed |
| LLD | count, id, x/y, flags | emblem placement | `id` selects the NCER cell and NANR sequence; `flags` 0 = inactive, nonzero = active; keep the trailing padding |
| NBFC | 512 bytes of tiles | multi-boot banner icon pixels | 16 8×8 4bpp tiles, row-major, no header; registered by `MB_RegisterFile` |
| NBFP | 16 RGB555 halfwords | icon colours | Index 0 is drawn (blue background), not transparent; index 15 is not referenced by the stock tiles |

## Edit recipes

1. Move a drawn element: change the x/y value in the BNCL record and, if needed, the origin bits. Keep the record index, because scene code and visibility tables address `elements[i]`. If the element is a label, edit the BNLL record instead; label position and alignment both come from that record.
2. Move a label without changing its text: change x/y in BNLL. Changing the origin changes alignment, so a label that was left-aligned becomes centred or right-aligned even if the coordinate is unchanged.
3. Change visible text: first check whether the scene writes the label from a BMG. `select_game_m.bnll` labels are overwritten from `menu.bmg`, `results_gp_*` from course/time messages, and `title_s.bnll` from `title.bmg`; editing those BNLL strings alone does nothing. For a label the scene does not overwrite, edit the UTF-16LE string, keep the NUL terminator, and rebuild every later `string_offset` if the length changed.
4. Add a cell: append an 8-byte record, increment the count, and make sure the cell id exists in the NCER and that the scene can address the new index. Inserting in the middle shifts every later element index; appending shifts only the label base, so every scene that hardcodes a label index must be adjusted by the same amount.
5. Add or move a touch box: append or edit a BNBL record. Appending puts the box at the end of the hit-test order, so an existing overlapping box still wins. Scene code may move or disable boxes at runtime, so verify the screen rather than the file.
6. Change a keyboard character: edit the KBDMAP unit at the character-key position; also confirm that the key art still shows the same glyph. Change a key rectangle in the KBD if the hit area is wrong, but leave the key ids sequential.
7. Change an emblem tool position: edit x/y in the LLD record with the matching id. Keep `flags` as it is (0 hides the element, nonzero draws it), keep the eight trailing zero bytes and the count exact; the loader ignores the trailing bytes but the file size must stay consistent with the archive entry.
8. Replace the banner icon: rewrite 512 bytes of 4bpp tiles (16 8×8 tiles, row-major) and/or the 16-colour palette. Palette index 0 is the background; keep the image opaque. The two paths are referenced by the `MBGameRegistry`, so keep the files at `data/Boot` with the same names.

## What breaks when counts or pointers are stale

A stale BNCL count makes the loader read past the last record (the file has no size field; the NARC FAT entry is the only length). A count that is too low silently drops cells and also moves the label base, so labels show the wrong text or blank. A stale BNCL count on a generated layout such as `Kart_icon_all.bncl` shifts the kart-to-element mapping. A cell id at or above the paired NCER count is worse: the SDK cell lookup returns NULL and JNLib dereferences it, so the screen faults on the first use of that element instead of drawing nothing.

A stale BNLL offset points into the middle of a string or into the record array, producing mojibake or a wild pointer; the text renderer then draws from that address and can overrun. A string that grows without rebuilding the following offsets corrupts every later label even though the file still parses.

A BNLL count change is safe only if the scene iterates `bnll.count` (game select does) and does not use a fixed-size label table; otherwise the extra label is never initialised or the table overruns. A BNCL count change is never neutral, because it renumbers the labels.

A stale BNBL count changes the hit-test range; a garbage rectangle can swallow every touch. Reordering BNBL records changes which box wins an overlap. Moving a box outside the screen (the stock trick is `0x400,0x400`) disables it.

A stale KBD length (file size not a multiple of 8) changes the number of hit rectangles; a KBDMAP length that no longer matches the character-key count misaligns every character after the change. `10key.kbd` uses `other3`, but only its ids 4–13 are character keys, so changing the id base or the two 1×1 placeholders shifts the digit mapping.

A stale LLD count reads past the last real record, because the loader trusts the count and the trailing bytes are not records. A palette or font value that no scene initialises draws with the wrong colours or a missing glyph set. Changing an LLD `flags` value from 0 to nonzero makes a hidden element draw at its stored position; changing it to 0 hides a normally visible tool or button.

Finally, the NARC wrapper stores each file's start and end in its FAT section, while the GMIF section holds the payload. Editing a file in place without rebuilding the archive leaves the old size and the next file at the old offset; the game then sees a truncated file or two overlapping files.

## Evidence and confidence

| Claim | Evidence | Confidence |
|---|---|---|
| Title, character select, kart select, game select, GP results, Wi-Fi course select, keyboard, wait, kart icon and portrait files map to those screens | game call sites in the ARM9 and `Matching/src` | verified |
| BNLL labels are appended after BNCL elements (`index = bncl.count + i`) | `jnui_initLabel` and the layout allocation in the JNLib code | verified |
| BNBL is hit-test only and the first matching record wins | `jnui_checkTouch` walks records in order | verified |
| BNLL text is often replaced from BMG at runtime | `gameSelect.c` label table, `gpResult.c`, `title.c` | verified |
| ASCII shift/caps and hiragana/katakana/dakuten map selection | ARM9 keyboard page and modifier switches; the `+2` BOM skip | verified |
| Options, VS rules, mission, ending, Wi-Fi top/matching, emblem and engine-select groups | overlay9_0/overlay9_1 string tables | strong |
| LLD roles (top status, bottom tools, template chooser, camera) | overlay9_1 grouping, file geometry and id ranges | strong (roles) |
| JNLL x bits 14–15 are per-line text alignment (0/1/2) | label renderer passes them to the line-align helper | verified |
| KBD ids 1..base are control keys and 1×1 entries are skipped | page constructors store the base; hit test requires width/height > 1 | verified |
| KBD +0x04 is a signed rectangle-chain step read by the cursor redraw, not padding | keyboard redraw advances by `s16[+0x04] × 8` (`0x020AABD8`); zero in all stock files | verified |
| KBD 1×1 records hold the return key (id 2) and, in 10key, also the space key (id 3) | key-code map id 2 → `0x0A`, id 3 → `0x20`/`0x3000`; hit test and keytop skip width/height ≤ 1 | verified |
| LLD `id` selects the NCER cell and NANR sequence; flags is the initial enable state (0 hidden, nonzero active) | builder `0x21852F8`, NANR lookup `0x2021DB0`, render skip at `0x218516C`, animation step `0x2184FF8` | verified |
| Every stock BNCL cell id is in range for its paired NCER | corpus scan of all 398 BNCLs; largest id 57; out-of-range lookup returns NULL and JNLib dereferences it | verified |
| NBFC/NBFP are the multi-boot banner icon and palette, not a font | decoded image; `MBGameRegistry` at `0x0215472C`; `MB_RegisterFile` call at `0x204EA3C` | verified (content, registry, consumer); IPL drawing outside the game |
| `player_character_M/L` are medium/large portraits | `main2d.c` loads them as `PORTRAIT_MEDIUM`/`PORTRAIT_LARGE` | verified |
| Record and `select_menu_etc_m` layouts differ per language | byte comparison of the five language copies | verified |

The strongest mappings are the ones with call sites: title, character select, kart select, game select, GP results, Wi-Fi course select, keyboard, wait indicator, kart icon atlas and portraits. The weakest are the LLD role names, which rest on overlay grouping and geometry rather than on an executed screen path; the NBFC/NBFP consumer is now proven to be `MB_RegisterFile`, with only the IPL's drawing code outside the game binary.
