# MKDS save image map

> **Project:** Mario Kart DS Modding Trove · **Format:** `.sav`, 256 KiB (0x40000) · **Header:** `include/nitro/mkds/save/save.h` · **CTables:** `tools/ctables/mkds/save_tables.py` · **Licence:** MIT

This is the working map for the game-created flash image. It is deliberately
more explicit than the short format note: the goal is that every byte belongs
to a named region, and every region has a typed representation that can be
edited and rebuilt.

## 1. Image layout

The image has a primary area at 0x00000 and a smaller backup area at 0x30F00.
Unwritten space is `0xFF`. A block with an erased magic is absent.

| Offset | Size | Block | Repetition | Notes |
|---:|---:|---|---|---|
| 0x00000 | 0x100 | NKSY | 1 | identity/settings; first 8 bytes plaintext |
| 0x00100 | 0x300 | NKEM | 1 | player emblem |
| 0x00400 | 0x400 | NKGP | 1 | 4 GP modes × 8 cups |
| 0x00800 | 0x1600 | NKTA | 1 | 6 leaderboard slots × 32 course-order entries |
| 0x01E00 | 0x100 | NKMR | 1 | 63 mission slots |
| 0x01F00 | 0xC00 | NKFL | 1 | 60 friend profiles + DWC records |
| 0x02B00 | 0x3700 | NKFE | 5 × 0xB00 | five emblem slots |
| 0x06200 | 0x4D00 | — | — | erased/reserved in stock images |
| 0x0AF00 | 0x1C000 | NKPG | 32 × 0xE00 | personal ghosts |
| 0x26F00 | 0xA000 | NKDG | 10 × 0x1000 | download ghosts |
| 0x30F00 | 0x100 | NKSY | 1 | backup identity |
| 0x31000 | 0x300 | NKEM | 1 | backup emblem |
| 0x31300 | 0x400 | NKGP | 1 | backup GP |
| 0x31700 | 0x1600 | NKTA | 1 | backup Time Trials |
| 0x32D00 | 0x100 | NKMR | 1 | backup mission ranks |
| 0x32E00 | 0xC00 | NKFL | 1 | backup friends |
| 0x33A00 | 0x3700 | NKFE | 5 × 0xB00 | backup emblem slots |
| 0x37100 | 0x8F00 | — | — | erased in stock images |

The primary/backup pair is selected by the 16-bit timestamp in each footer.
The game prefers the primary when its timestamp is greater than or equal to
the backup timestamp; a primary timestamp of zero beats a backup of 0xFFFF.

## 2. Block envelope

Every block is encrypted as 32-bit little-endian words and ends with a
four-byte footer. NKSY is the exception: bytes 0x00–0x07 are the plaintext
`MKDSSV10` tag and encryption starts at 0x08.

| Offset | Size | Meaning |
|---:|---:|---|
| +0x00 | 4 | decrypted block magic (`NKSY`, `NKEM`, …) |
| … | … | payload |
| end−4 | 2 | timestamp, big-endian |
| end−2 | 2 | CRC16-CCITT, big-endian, over the whole block with the timestamp zeroed |

The header declares `SavBlockFooter`. The CRC is verified by zeroing the
timestamp bytes and requiring a zero result over the full block.

## 3. NKSY — identity and settings (0x100)

| Offset | Size | Field | Representation |
|---:|---:|---|---|
| 0x00 | 8 | `MKDSSV10` | string literal |
| 0x08 | 4 | `NKSY` | magic constant |
| 0x0C | 20 | nickname, 10 UTF-16LE units | `uint16_t[10]` |
| 0x20 | 4 | unlock bits | `uint8_t[4]`; bits 17–19 are the kart unlock levels |
| 0x24 | 2 | ELO/rating | `uint16_t` |
| 0x26 | 4 | personal-ghost present bits | bit set per ghost slot |
| 0x2A | 4 | download-ghost present bits | bit set per download slot |
| 0x2E | 2 | emblem-slot used bits | bit set per `MkdsEmblemSlot` |
| 0x30 | 1 | padding | `{ 0 }` |
| 0x31 | 1 | flags | bitfield union (`SavNksyFlags31`) |
| 0x32 | 1 | padding | `{ 0 }` |
| 0x34 | 4 | aggregate unlock bits | `SavAnyUnlockBits` |
| 0x38 | 1 | max kart unlock level | `sav_kart_unlock_level()` |
| 0x39 | 1 | min kart unlock level | scalar |
| 0x3A | 2 | padding | `{ 0 }` |
| 0x3C | 4 | reserved | cleared at load |
| 0x40 | 4 | reserved | zero in stock |
| 0x44 | 4 | network wins | `uint32_t` |
| 0x48 | 4 | network losses | `uint32_t` |
| 0x4C | 0x40 | Nintendo Wi-Fi user data | opaque DWC record |
| 0x8C | 0x74 | reserved | `{ 0 }` |

## 4. NKEM — player emblem (0x300)

| Offset | Size | Field | Representation |
|---:|---:|---|---|
| 0x00 | 4 | `NKEM` | magic |
| 0x04 | 1 | valid bit | `SavNkemFlags` |
| 0x05 | 3 | padding | `{ 0 }` |
| 0x08 | 0x200 | emblem | `MkdsEmblemBitmap emblem` |
| 0x208 | 0xF8 | reserved | `{ 0 }` |

The emblem is not a string. The CTables emit `MkdsEmblemBitmap.rows` as 32
rows of 16 bytes, and `mkds_emblem_pixel()` reads a nibble without assuming a
host bitfield order.

## 5. NKGP — GP records (0x400)

32 records of 28 bytes, indexed `[mode][cup]`:

| Offset | Size | Field |
|---:|---:|---|
| 0x00 | 4 | `SavGpInfo0`: valid, character, kart, rank points, rank |
| 0x04 | 4 | `SavGpInfo1`: trophy, minutes, seconds, milliseconds |
| 0x08 | 20 | nickname |

`mode` uses `MkdsEngineClassValue` (50/100/150/mirror) and `cup` uses
`MkdsCup` (Mushroom … Lightning). `sav_gp_clock()` and
`sav_gp_milliseconds()` expose the packed time.

## 6. NKTA — Time Trials leaderboard (0x1600)

192 records of 28 bytes, indexed `[place][course_order]`:

| Offset | Size | Field |
|---:|---:|---|
| 0x00 | 4 | valid, character, minutes, seconds, milliseconds |
| 0x04 | 1 | kart id |
| 0x05 | 3 | padding |
| 0x08 | 20 | nickname |

- `place` uses `MkdsTimeTrialsPlace`: slots 0–4 are the top five, slot 5 is
  the best-ghost record.
- `course_order` uses `MkdsCourseOrder` (8 cups × 4 positions), the output of
  the game's course-id-to-order conversion. It is not the race course id.

`sav_ta_clock()` and `sav_ta_milliseconds()` expose the packed time.

## 7. NKMR — mission ranks (0x100)

| Offset | Size | Field |
|---:|---:|---|
| 0x00 | 4 | `NKMR` |
| 0x04 | 63 | one byte per mission menu slot |
| 0x43 | 0xBD | reserved |

Each byte is `SavMissionRankEntry`: bit 0 valid, bits 1–7 best rank. The 63
entries follow `MkdsMissionMenuSlot` (`MKDS_MISSION_MENU_L1_1` …
`MKDS_MISSION_MENU_L7_9`), not the mission id order.

## 8. NKFL — friends (0xC00)

| Offset | Size | Field |
|---:|---:|---|
| 0x00 | 4 | `NKFL` |
| 0x04 | 60 × 36 | friend profiles |
| 0x874 | 720 | 60 DWC friend records, 12 bytes each |
| 0xB44 | 0xBC | reserved |

Each profile is indexed by `MkdsFriendSlot`:

| Offset | Size | Field |
|---:|---:|---|
| 0x00 | 12 | vs wins/losses and battle wins/losses |
| 0x0C | 4 | net wins/losses |
| 0x10 | 2 | date: year−2000 in bits 0–6, month 7–10, day 11–15 |
| 0x12 | 20 | nickname |
| 0x26 | 1 | flags: valid, offline, has emblem, locked |
| 0x27 | 1 | reserved |

## 9. NKFE — emblem slots (5 × 0xB00)

Each slot starts at `SAV_OFF_NKFE + slot * SAV_NKFE_SIZE`:

| Offset | Size | Field |
|---:|---:|---|
| 0x00 | 4 | `NKFE` |
| 0x04 | 1 | used-slot bit mask |
| 0x05 | 3 | padding |
| 0x08 | 0x200 | emblem bitmap |
| 0x208 | 0x8F8 | reserved |

Slots are indexed by `MkdsEmblemSlot`. The CTables emit five
`MkdsEmblemBitmap` values, not a 0xA00-byte string.

## 10. Ghost slots

| Range | Count | Size | Type |
|---|---:|---:|---|
| 0x0AF00 | 32 | 0xE00 | NKPG personal ghost |
| 0x26F00 | 10 | 0x1000 | NKDG download ghost |

The ghost header and input-run record live in `include/nitro/mkds/save/ghost.h`.
The present bits in NKSY must agree with the slots that contain a valid ghost;
a slot with an erased magic is absent.

## 11. CTables representation

`tools/ctables/mkds/save_tables.py` emits one decrypted block per program. The
editable form follows these rules:

- arrays use the enum key, not a numeric index:
  `[MKDS_ENGINE_150CC][MKDS_CUP_STAR]`,
  `[MKDS_TA_PLACE_1][MKDS_COURSE_ORDER_SHELL_3]`,
  `[MKDS_MISSION_MENU_L4_2]`, `[MKDS_FRIEND_SLOT_17]`,
  `[MKDS_EMBLEM_SLOT_3]`;
- emblems are `MkdsEmblemBitmap.rows`, 32 rows of 16 bytes; an all-zero
  emblem collapses to `{ 0 }`;
- all-zero reserved regions collapse to `{ 0 }`, because C zero-initialises
  the rest; non-zero regions keep every byte as an inspectable number;
- ASCII names are string literals; binary payloads are never strings;
- fixed-point values are printed as the shortest decimal that the existing
  `FX32()`/`FX16()` macro maps back to the same raw word (tested exhaustively
  for all 65,536 FX16 words and sampled for FX32).

Example:

```c
static const SavEmblemBlock block = {
    .magic = SAV_MAGIC_NKEM,
    .valid_and_reserved = { .bits = { .valid = 1, .reserved = 0 } },
    .reserved_5 = { 0 },
    .emblem = {
        .rows = {
            { 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF,
              0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF },
            /* ... 31 more rows ... */
        },
    },
    .reserved_208 = { 0 },
};
```

Rebuild a block with:

```sh
python3 tools/ctables/edit.py extract NKEM.bin -o NKEM.c
python3 tools/ctables/edit.py build NKEM.c -o NKEM.bin
```

The encrypted full-image rebuild is out of scope: callers supply a decrypted
block. The plaintext NKSY tag stays in place.
