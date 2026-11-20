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

## Dumping every bank

```sh
python3 tools/bmg_dump.py path/to/extracted/root/data -o out/bmg
```

The dumper writes one UTF-8 text file and one JSON file per bank, preserving
the INF1 index:

```text
# Main2D_us_arc/common.bmg
# encoding=2 messages=140
000	"YES"
...
045	"FIGURE-8 CIRCUIT"
```

`out/bmg/index.json` records every source path, encoding and message count.
Non-ASCII text stays readable, so the Japanese, Spanish, French, German and
Italian copies can be compared directly. `out/` is not committed.

MKDS messages contain binary escapes starting with U+001A. Their arguments can
contain U+0000, so a plain NUL-terminated read truncates messages such as
`Drive through all ...`. The reader knows the three stock escape lengths
(`FF08`, `0108`, `0106`) and the dumper renders them as markers:

```text
"Drive through all <1A:FF08:65536>5<1A:FF08:0>\n<1A:FF08:65536>numbered gates<1A:FF08:0> in order!"
```

That keeps the whole message visible without losing the escape positions.

## Generated message-id headers

```sh
python3 tools/bmg_headers.py path/to/extracted/root/data \
    -o include/nitro/mkds/bmg
```

This writes `include/nitro/mkds/bmg/<bank>.h`. A bank with clear semantic
ranges gets one `typedef enum` per domain:

```c
typedef enum {
    MKDS_BMG_COMMON_FRIEND_CODE_REGISTERED = 9, /* 009: ... */
    MKDS_BMG_COMMON_FRIEND_CODE_INCORRECT = 10,
    ...
} MkdsBmgCommonFriendCodeMessage;

typedef enum {
    MKDS_BMG_COMMON_CHARACTER_MARIO = 20,
    ...
} MkdsBmgCommonCharacterMessage;

typedef enum {
    MKDS_BMG_COMMON_COURSE_FIGURE_8_CIRCUIT = 45,
    ...
} MkdsBmgCommonCourseMessage;

typedef enum {
    MKDS_BMG_COMMON_ENGINE_50CC = 110,
    ...
} MkdsBmgCommonEngineMessage;
```

C has no nested enums, so all constants remain at file scope. Numeric values
may overlap between different domains; the domain type and the key prefix say
which space the value belongs to. Every message appears in exactly one block.
Messages that do not belong to a named domain go into a
`MkdsBmg<Bank>MiscMessage` block, so no master enum with duplicate keys is
needed. `MKDS_BMG_<BANK>_COUNT` still counts every message in the bank.

`include/nitro/mkds/bmg_messages.h` includes all banks. The ids are shared
across language copies; the enum keys use the US labels, while
`bmg_dump.py` shows the localized strings. Long messages without a known
reference keep numbered `MSG_nnn` ids so the headers remain a compact message
map rather than a text dump.

## Cross-references in the generated enum keys

A message label often names a value from another identifier space. The enum
key encodes that reference instead of adding a second comment:

```c
MKDS_BMG_COMMON_COURSE_YOSHI_FALLS = 46,
MKDS_BMG_KART_SELECT_KART_STANDARD_MR = 6,
MKDS_BMG_RULE_CPU_EASY = 11,
MKDS_BMG_COMMON_ENGINE_50CC = 110,
```

The semantic key prefixes are `CHARACTER_`, `CUP_`, `COURSE_`, `BATTLE_`,
`ENGINE_`, `KART_`, `MODE_`, `GHOST_`, `CPU_` and `RULE_` inside the bank's
normal `MKDS_BMG_<BANK>_` prefix. Repeated values get a `_2` suffix, such as
the second ghost course list. Messages with no known shared constant keep a
readable text key when it is short enough, otherwise `MSG_nnn`.

The domain blocks are:

| Bank | Indices | Enum type | Key prefix / cross-reference |
|---|---|---|---|
| `common.bmg` | 7–18 | `MkdsBmgCommonFriendCodeMessage` | `FRIEND_CODE_*` |
| `common.bmg` | 0–6, 19, 93–109 | `MkdsBmgCommonUiMessage` | text keys |
| `common.bmg` | 20–32 | `MkdsBmgCommonCharacterMessage` | `CHARACTER_*` → `MKDS_CHARACTER_*` |
| `common.bmg` | 33–34 | `MkdsBmgCommonDuplicateMessage` | duplicate full names |
| `common.bmg` | 35–36 | `MkdsBmgCommonModeMessage` | `MODE_NITRO_GP` / `MODE_RETRO_GP` |
| `common.bmg` | 37–44 | `MkdsBmgCommonCupMessage` | `CUP_*` → `MKDS_CUP_*`, in cup order |
| `common.bmg` | 45–76 | `MkdsBmgCommonCourseMessage` | `COURSE_*` → `MKDS_RACE_COURSE_*` plus the numeric race id |
| `common.bmg` | 77–82 | `MkdsBmgCommonBattleMessage` | `BATTLE_*` → `MKDS_BATTLE_COURSE_*` |
| `common.bmg` | 83–92, 114–139 | `MkdsBmgCommonMiscMessage` | remaining labels |
| `common.bmg` | 110–113 | `MkdsBmgCommonEngineMessage` | `ENGINE_*` → `MKDS_ENGINE_*` |
| `kart_select.bmg` | 0–5 | `MkdsBmgKartSelectStatsMessage` | stat labels |
| `kart_select.bmg` | 6–41 | `MkdsBmgKartSelectKartMessage` | `KART_*` → `MKDS_KART_*`, in roster order |
| `ghost.bmg` | 0–18 | `MkdsBmgGhostUiMessage` | UI/status labels |
| `ghost.bmg` | 19–50 | `MkdsBmgGhostCourseMessage` | `COURSE_*` → `MKDS_RACE_COURSE_*` |
| `ghost.bmg` | 51–82 | `MkdsBmgGhostRepeatedCourseMessage` | `COURSE_*_2` → the same 32 courses |
| `ghost.bmg` | 83–87 | `MkdsBmgGhostMiscMessage` | remaining status labels |
| `menu.bmg` | 0–5 | `MkdsBmgMenuBattleMessage` | `BATTLE_*` → `MKDS_BATTLE_COURSE_*` |
| `menu.bmg` | 6–7 | `MkdsBmgMenuBattleModeMessage` | `MODE_*` battle-mode labels |
| `menu.bmg` | 8–13 | `MkdsBmgMenuGhostMessage` | `GHOST_*` ghost-data-kind labels |
| `menu.bmg` | 14–22 | `MkdsBmgMenuMiscMessage` | remaining labels |
| `rule.bmg` | 0–4 | `MkdsBmgRuleLabelMessage` | rule menu labels |
| `rule.bmg` | 5–8 | `MkdsBmgRuleEngineMessage` | `ENGINE_*` → `MKDS_ENGINE_*` |
| `rule.bmg` | 9–10 | `MkdsBmgRuleToggleMessage` | `ON` / `OFF` |
| `rule.bmg` | 11–13 | `MkdsBmgRuleCpuMessage` | `CPU_*` → `MKDS_CPU_*` |
| `rule.bmg` | 14–16 | `MkdsBmgRuleOrderMessage` | `RULE_*` → `MKDS_RULE_ORDER_*` |
| `rule.bmg` | 17–23 | `MkdsBmgRuleMiscMessage` | remaining labels |

`mission.bmg` is a menu list: slot *i* displays the mission id at
`Main2D_arc/missionTable.mtbl[i]`, and that id is record `id - 1` in
`Scene/Menu_arc/mission.mr`. Missions are one domain, so they stay in a single
`MkdsBmgMissionMessage` enum. The generator resolves both files and names each
key after the mission record and its first task word, so the key identifies the
mission rather than just the message slot:

```c
MKDS_BMG_MISSION_MR80_PERFORM = 25, /* 025 */
/* menu slot 25 -> mission id 80 (mr80), level 3 slot 8 */
```

If the same mission appears in more than one menu slot the later key gets a
`_2` suffix. A mission whose objective has no usable short word falls back to
`MR<id>`.

The mission table is optional. It is found automatically under the source
root, or supplied explicitly:

```sh
python3 tools/bmg_headers.py path/to/extracted/root/data \
    --missions-mtbl path/to/Main2D_arc/missionTable.mtbl \
    -o include/nitro/mkds/bmg
```

If the mission table is absent, generation still succeeds and the enum lines
keep only their message labels.

The same strings also supply the English enum names used by the C tables:
course names (`MKDS_RACE_COURSE_*`), kart names (`MKDS_KART_*`), character
names, cups and battle arenas.

## Reuse

`tools/bmg.py` works on any MKDS `rule.bmg` (and similar MESG/bmg1 banks). `tools/bmgset.py` coordinates several mods that each append labels: it strips all selected labels, pads shorter languages with empty messages, appends them in mod order, and reports the ids each mod received.
