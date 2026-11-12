# Nitro ROM formats

> **Project:** Mario Kart DS Modding Trove · **Licence:** MIT · **Code:** `tools/nds.py`

The subset used by `tools/nds.py`. All offsets are little-endian.

## NDS header

| Offset | Field |
|---|---|
| 0x20 | ARM9 ROM offset |
| 0x24 | ARM9 entry point |
| 0x28 | ARM9 RAM address |
| 0x2C | ARM9 size in the ROM |
| 0x30 | ARM7 ROM offset |
| 0x34 | ARM7 entry point |
| 0x38 | ARM7 RAM address |
| 0x3C | ARM7 size |
| 0x40 | FNT offset |
| 0x44 | FNT size |
| 0x48 | FAT offset |
| 0x4C | FAT size |
| 0x50 | ARM9 overlay table offset |
| 0x54 | ARM9 overlay table size |
| 0x80 | ROM size |

The ARM9 image pointed to by `0x20` may be BLZ-compressed. The FNT/FAT describe the NitroFS file tree.

## FNT and FAT

The FNT starts with a root entry (`uint32_t` directory-table offset, `uint16_t` first file id, `uint16_t` directory count). Directory entries are 8 bytes: name-table offset, first file id, parent id. Names use bit 7 of the length byte to mark a subdirectory; the following `uint16_t` is the child directory id + `0xF000`. A zero length byte ends a directory.

The FAT is an array of `(start, end)` file offsets; `end` is inclusive.

## BLZ

Nitro's backwards LZ. The last four bytes hold the number of bytes the image grows by when decompressed. The eight bytes before that hold a header whose top byte is the compressed-header length and whose low 24 bits are the encoded length. Bytes before the encoded tail are stored plain; the tail is decoded backwards from the end.

The decompressed ARM9 is recognised by the module-params magic `0xDEC00621 0x2106C0DE`. A plain ARM9 can contain that magic too, so use the module params' `compressed_static_end` field (see [ARM9 autoloads](arm9-autoloads.md)) to decide whether a compressed tail exists.

## NARC

MKDS stores most assets in NARCs:

| Section | Contents |
|---|---|
| `NARC` | 0x10-byte header |
| `BTAF` | allocation table: count at +8, `(start, end)` pairs from +0xC |
| `BTNF` | member names, same layout as a DS FNT |
| `GMIF` | member data; `start`/`end` are relative to `GMIF + 8` |

Member ids are their order in BTAF; the BTNF gives the names.

## `.carc` and LZ77

MKDS names its compressed archives `.carc`, but the wrapper is Nitro LZ77 and the contents are an ordinary NARC. An archive is recognised by decompressing it and checking for `NARC`, never by the extension.

LZ77 (type `0x10`) layout:

- 4-byte header: low byte `0x10`, high 24 bits the uncompressed size.
- One flag byte per eight tokens; bit 7 is the first token.
- Clear bit: one literal byte.
- Set bit: two bytes, `length = high nibble + 3`, `displacement = low 12 bits + 1` (a back-reference into the output).

`tools/nds.py` reads both plain and LZ77-wrapped NARCs. NCPatcher recompresses an edited `.carc` in the same wrapper it arrived in.
