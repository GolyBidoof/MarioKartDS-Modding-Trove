# MKDS flash save format

> **Project:** Mario Kart DS Modding Trove · **Format:** `.sav` / 2 Mbit flash · **Header:** [`../include/nitro/save.h`](../include/nitro/save.h) · **Licence:** MIT

This note describes the 0x40000-byte save image written by Mario Kart DS. It is a block store with a primary area at 0x00000 and a smaller backup area at 0x30F00. The first eight bytes of the image are the ASCII tag `MKDSSV10`. For the byte-by-byte map and the editable C representation of every block, see [save-file-map.md](save-file-map.md).

The block envelope, footer CRC and record organisation follow the Nitro SDK save-block convention; the game-specific layer is the encryption and the exact block map below. The layout was checked against retail save images and the game's block reader. All multi-byte integers are little-endian unless noted.

## File layout

| Offset | Size | Block | Record |
|---:|---:|---|---|
| 0x00000 | 0x100 | NKSY | identity/header block (also the card header block) |
| 0x00100 | 0x300 | NKEM | player emblem |
| 0x00400 | 0x400 | NKGP | GP records |
| 0x00800 | 0x1600 | NKTA | Time Trials records |
| 0x01E00 | 0x100 | NKMR | mission ranks |
| 0x01F00 | 0xC00 | NKFL | friend profiles |
| 0x02B00 | 5 × 0xB00 | NKFE | emblem slots (0x2B00..0x6200) |
| 0x06200 | 0x4D00 | — | erased/reserved in observed saves |
| 0x0AF00 | 32 × 0xE00 | NKPG | personal ghosts (0xAF00..0x26F00) |
| 0x26F00 | 10 × 0x1000 | NKDG | download ghosts (0x26F00..0x30F00) |
| 0x30F00 | 0x100 | NKSY | backup identity block |
| 0x31000 | 0x300 | NKEM | backup emblem |
| 0x31300 | 0x400 | NKGP | backup GP records |
| 0x31700 | 0x1600 | NKTA | backup Time Trials records |
| 0x32D00 | 0x100 | NKMR | backup mission ranks |
| 0x32E00 | 0xC00 | NKFL | backup friend profiles |
| 0x33A00 | 5 × 0xB00 | NKFE | backup emblem slots (0x33A00..0x37100) |
| 0x37100 | 0x8F00 | — | erased in observed saves |

Erased bytes are `0xFF`. A block that has never been written is not a valid block: the game sees the erased magic and ignores it.

## Block envelope

Every logical block is encrypted and ends with a four-byte footer. The NKSY block is special: its first eight bytes (`MKDSSV10`) stay plaintext, and encryption starts at offset 0x08. All other blocks are encrypted from their first byte.

| Offset | Size | Meaning |
|---:|---:|---|
| 0x00 | 8 | `MKDSSV10` (NKSY only; plaintext) |
| +0x00 | 4 | block magic after decryption (`NKSY`, `NKEM`, ...) |
| ... | ... | block payload |
| end−4 | 2 | 16-bit timestamp, high byte first |
| end−2 | 2 | CRC16, high byte first |

The CRC is CRC16-CCITT with polynomial 0x1021 and initial value 0. To verify a block, zero the two timestamp bytes, calculate the CRC over the whole block including the two CRC bytes, and require the result to be zero. All blocks in the checked saves satisfy this.

The game reads the primary block and its backup, validates both, and prefers the primary when its timestamp is greater than or equal to the backup timestamp. There is one wrap case: when the primary timestamp is zero and the backup timestamp is 0xFFFF, the primary is still selected, treating the backup counter as wrapped.

## Encryption

The payload is encrypted as 32-bit little-endian words. Four 32-bit tables drive a repeating XOR stream; the indices advance independently with periods 0x1D, 0x13, 0x11 and 0xB. The first index (0x00..0x1C) is not stored in the block: the reader tries all 0x1D seeds and accepts the one where the first decrypted word equals the expected block magic. The remaining indices start at zero.

The seed is therefore recoverable from the first encrypted word and the block magic. Blocks that are completely erased (`0xFF`) do not decrypt to a valid magic and are treated as absent.

The tables are implementation data rather than file structure, so they are not duplicated in `save.h`. A reader can carry them in its crypto module and expose only the block-level API.

## NKSY — identity and settings

`save.h` defines `SavIdentityBlock` as the full 0x100-byte block, including the plaintext file tag.

| Offset | Size | Field |
|---:|---:|---|
| 0x00 | 8 | `MKDSSV10` |
| 0x08 | 4 | `NKSY` |
| 0x0C | 20 | nickname, 10 UTF-16LE code units |
| 0x20 | 4 | unlock bits |
| 0x24 | 2 | ELO/rating; the checked save has 5000 |
| 0x26 | 4 | personal-ghost present bits |
| 0x2A | 4 | download-ghost present bits |
| 0x2E | 2 | emblem-slot used bits |
| 0x30 | 1 | reserved |
| 0x31 | 1 | flags: bit0 nickname set, bits1-2 sound output |
| 0x32 | 1 | reserved |
| 0x34 | 16 | four unidentified 32-bit fields |
| 0x44 | 4 | network wins |
| 0x48 | 4 | network losses |
| 0x4C | 0x40 | Nintendo Wi-Fi user data |
| 0x8C | 0x74 | reserved |

## NKEM — player emblem

| Offset | Size | Field |
|---:|---:|---|
| 0x00 | 4 | `NKEM` |
| 0x04 | 1 | bit0: emblem valid |
| 0x05 | 3 | reserved |
| 0x08 | 0x200 | emblem bitmap |
| 0x208 | 0xF8 | reserved |

## NKGP — GP records

NKGP is 32 records of 28 bytes: 4 GP modes × 8 cups. Each record has two packed words followed by the nickname.

| Offset | Size | Field |
|---:|---:|---|
| 0x00 | 4 | flags 0 |
| 0x04 | 4 | flags 1 |
| 0x08 | 20 | nickname, UTF-16LE |

The header exposes these packed words as unions: use `.bits.valid`, `.bits.character`, `.bits.kart`, `.bits.rank_points` and `.bits.rank` on `SavGpInfo0`, and `.bits.trophy`, `.bits.minutes`, `.bits.seconds` and `.bits.milliseconds` on `SavGpInfo1`.

The raw value is still available as `.raw`.

## NKTA — Time Trials records

NKTA is 192 records of 28 bytes: 6 leaderboard slots × 32 course-order entries. Slots 0–4 are the top five times, slot 5 is the best-ghost record. The second index is the 8×4 cup order index, not the race course id.

| Offset | Size | Field |
|---:|---:|---|
| 0x00 | 4 | flags: bit0 valid, bits1-7 character, bits8-14 minutes, bits15-21 seconds, bits22-31 milliseconds |
| 0x04 | 1 | kart |
| 0x05 | 3 | reserved |
| 0x08 | 20 | nickname, UTF-16LE |

## NKMR — mission ranks

NKMR holds 63 one-byte records, one per mission. Bit0 is valid; bits1-7 are the rank.

## NKFL — friend profiles

NKFL starts with 60 profiles of 36 bytes, followed by 60 opaque 12-byte Nintendo Wi-Fi friend records at 0x874.

| Offset | Size | Field |
|---:|---:|---|
| 0x00 | 2 | VS wins |
| 0x02 | 2 | VS losses |
| 0x04 | 2 | battle wins |
| 0x06 | 2 | battle losses |
| 0x08 | 2 | network wins |
| 0x0A | 2 | network losses |
| 0x0C | 2 | date: year 7 bits, month 4 bits, day 5 bits |
| 0x0E | 20 | nickname, UTF-16LE |
| 0x22 | 1 | flags |
| 0x23 | 1 | unidentified |

## NKFE — emblem slot bank

NKFE is 0xB00 bytes per slot, five slots. The first byte after the magic is a slot mask; each slot carries a 0x200-byte emblem at offset 0x08. The rest is reserved.

## Ghost blocks

NKPG (personal) and NKDG (download) share a 0x30-byte header.

| Offset | Size | Field |
|---:|---:|---|
| 0x00 | 4 | `NKPG` or `NKDG` |
| 0x04 | 4 | character, kart, course and date; course uses the ghost table key, see `formats-ids.md` |
| 0x08 | 4 | validity, flags and time |
| 0x0C | 20 | nickname, UTF-16LE |
| 0x20 | 15 | three lap times, five bytes each |
| 0x2F | 1 | low two bits: cup-rank tier (0 = below rank 5, 1 = worst rank 5, 2 = worst rank 6, 3 = worst rank 7); upper bits zero |

Info word 0: character bits0-3, kart bits4-9, course bits10-15, year bits16-22, month bits23-26, day bits27-31. The year is an offset from 2000 (a 2005 ghost stores 5).

Info word 1: valid bit0, flag bit1, region bits2-3, flag bits4-7, minutes bits8-14, seconds bits15-21, milliseconds bits22-31. The rank tier at 0x2F is derived from all 32 GP cup ranks, not stored independently.

NKPG is 0xE00 bytes: header, 0xDCC-byte input recording, four bytes of padding. NKDG is 0x1000 bytes: header, 0x200-byte emblem, 0xDCC-byte input recording, four bytes of padding.

The input recording is 0xDCC bytes: a 32-bit used-entry count followed by 1764 two-byte entries. Each entry is a key mask and a duration in frames. Key bits are A 0x01, B 0x02, R 0x04, L/X 0x08, right 0x10, left 0x20, down 0x40 and up 0x80. The block size is therefore 4 + 1764 × 2 = 0xDCC.

## Implementation map

There is no save model in Mario Kart Toolbox. The C declarations in `include/nitro/save.h` are the shared offset contract for native tools, recomp code and future C# readers. The block encryption tables and CRC routine belong in the reader implementation, not in the header.

## Game usage

| Block | Used by | Written when |
|---|---|---|
| NKSY | player profile, unlocks, ghost flags, network record | profile creation, unlock/ghost/network changes |
| NKEM | active player emblem | emblem editor save |
| NKGP | GP mode records (4 modes × 8 cups) | GP completion |
| NKTA | Time Trials leaderboard (6 slots × 32 course-order entries) | Time Trials completion |
| NKMR | mission ranks (63 missions) | mission completion |
| NKFL | local friend profiles and Wi-Fi friend records | friend list changes |
| NKFE | five emblem slots | emblem slot save/delete |
| NKPG | 32 personal ghosts | Time Trials ghost save |
| NKDG | 10 download ghosts | ghost download/receive |

The first four bytes of the NKSY payload are the player nickname. The unlock bits gate kart/character availability; changing them without the corresponding game-side checks can unlock entries whose models or records are absent. The personal/download ghost bits are presence flags, not a ghost count; a set bit without a valid NKPG/NKDG block is ignored.

NKGP and NKTA records are the only places where the game stores completion times and ranks. NKGP is indexed by engine class and cup; NKTA is indexed by leaderboard place and course-order position. Neither uses the race course ID as an array index, so a course change in the ROM does not reorder them.

## Observed values

A checked retail save image has a UTF-16LE nickname, ELO 5000, no unlock bits, one personal ghost slot marked present, zero download ghosts, 64 network wins and 3827 network losses. NKEM, NKFE, NKPG and NKDG are erased (`0xFF`) until the corresponding feature is used. The backup copies of NKSY through NKFE are present and valid; the areas after the backup NKFE bank are erased.

## Editing notes

A save edit has to preserve the envelope, not just the record. Decrypt the block, change the record bytes, zero the two timestamp bytes, calculate the CRC over the full block including the footer, write the CRC high byte first, restore a timestamp, then encrypt the block again. The NKSY block keeps its first eight bytes plaintext.

Write the same modified block to both the primary and backup offsets when the block has a backup copy, and give the primary a timestamp greater than or equal to the backup. If only the primary is written, the game can still choose the older backup when the primary CRC or timestamp is rejected.

Do not write into an erased block (`0xFF`) unless the whole block is initialized; the magic and footer must both be created. NKPG and NKDG have no backup copies, so a damaged ghost block is simply ignored rather than recovered.
