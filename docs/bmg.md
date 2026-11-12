# BMG message banks

> **Project:** Mario Kart DS Modding Trove · **Licence:** MIT · **Code:** `tools/bmg.py`, `tools/bmgset.py`

MKDS menu text lives in `rule.bmg` files inside `data/Scene/Menu*.carc`. `tools/bmg.py` reads, repairs and rewrites them.

## Header

| Offset | Field |
|---|---|
| 0x00 | `MESG` |
| 0x04 | `bmg1` |
| 0x08 | file size |
| 0x0C | section count (`uint32_t`) |
| 0x10 | text encoding (`uint32_t`; `2` = UTF-16LE) |
| 0x14–0x1F | zero |

Sections follow at 0x20. Each is `magic` (`4`), `size` (`uint32_t`), then its payload. `size` includes the 8-byte header.

## INF1 and DAT1

`INF1` maps message ids to string offsets:

| Offset | Field |
|---|---|
| +0x08 | entry count (`uint16_t`) |
| +0x0A | entry size (`uint16_t`, normally 4) |
| +0x0C | reserved (`uint32_t`) |
| +0x10 | `uint32_t` offsets into DAT1 |

`DAT1` is an 8-byte header followed by NUL-terminated strings. An INF1 offset is relative to `DAT1 + 8`.

The INF1 section is padded so DAT1 starts on a `0x20` boundary. Retail files do this by padding the offset table; rebuilds must preserve it.

## Message ids

`MID1` would give explicit ids, but MKDS `rule.bmg` files do not ship one. The message id is therefore the INF1 index. In the stock Options bank:

| Index | Message |
|---|---|
| 5 | 50cc |
| 6 | 100cc |
| 7 | 150cc |
| 8 | Mirror |

`options-cc` appends `200cc`, `250cc`, `300cc` at indices 24, 25, 26.

## Per-language labels

The stock class labels are localized: Spanish uses `50 cc`, German uses `50 ccm`, while English, French, Italian and Japanese use `50cc`. The Options mod keeps one JSON catalog per language in `mods/options-cc/messages/`; the planner selects it from the archive name (`Menu_es` → `es`, `MenuDL_ja` → `ja`, `Menu` → `default`), using the prefixes declared in the mod's `mod.json`.

The labels are appended at the same ids in every language, so one code table works for all of them.

## The four-byte-short append (and repair)

An older append produced files with `INF1` count 28 but size 124 instead of
128. The last declared offset overlapped DAT1's `DAT1` magic, so the final message was unreadable and the section sizes disagreed.

`tools/bmg.py` repairs this structurally, without trusting the declared count:

- The number of usable offsets is `min(count, (DAT1 - (INF1 + 16)) / 4)`.
- Reading stops at the first offset outside DAT1 or below the previous offset (the old append left a zero in the INF1 padding).
- The file is rebuilt with `INF1 = 16 + 4*count`, padded so DAT1 is `0x20`-aligned, and `DAT1 = 8 + data`, padded to 4.

The rebuild also strips any previous copy of the labels being appended, which makes repeated runs idempotent. Files with an explicit `MID1` table are refused rather than guessed at.

## Reuse

`tools/bmg.py` works on any MKDS `rule.bmg` (and similar MESG/bmg1 banks). `tools/bmgset.py` coordinates several mods that each append labels: it strips all selected labels, pads shorter languages with empty messages, appends them in mod order, and reports the ids each mod received.
