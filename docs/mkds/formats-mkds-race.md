# MKDS race and save-adjacent formats

> **Project:** Mario Kart DS Modding Trove · **Licence:** MIT · **Header:** `include/nitro/mkds_race.h` · **Corpus:** stock MKDS extraction, 32 ghost files, 8 PRM files, 1 NKMR, 1 RTT, 1 RPT, 1 ItemSlotList, 18 kart/character parameter files, 1 emblem2, 1 builddate and 2 DWC utility copies.

This document records only what the stock corpus and the game code prove. Every multi-byte integer is little-endian unless a field says otherwise. File paths are the in-game NitroFS paths, not host paths. The header declares the proven structures; formats whose field meanings are unresolved are described here and deliberately left opaque in the header.

### Resolved in this revision

The mission timer and rank target are frame counters at 60 per second; mission tasks 5 and 8–10 are unused in retail data; the mission camera byte selects a two-entry camera table; `mission.mr` has 91 records because 28 are unreachable alternate/boss configurations and only 63 are indexed by `missionTable.mtbl`. The rank-time file uses the normal race course ids in a separate table order (retro cup half first). The rank-point row formulas are confirmed. `ItemSlotList.dat` entries are item weights, not item ids; block 6 is the item-box override table. Ghost dates are offsets from 2000, result bits 2–3 are the system region, and the 0x2F byte is a derived cup-rank tier. PRM is a per-boss block loaded into the boss at `+0xA0`, not a generic mission stream. Staff-time holes are the non-cup course ids. The 148-byte kart physical row is inferred to be the 152-byte row without the drift-compensation word; the 144-byte row is inferred to additionally omit the word at 0x08.

## NKDG ghost files

`/data/Ghost/ghost_000.bin` through `ghost_031.bin` are 32 files of exactly `0x1000` bytes. The first 0x30 bytes are a fixed header, the next 0x200 bytes are an emblem, and the rest is a run-length input stream followed by zero padding. All fields below are proven by cross-checking all 32 files.

| Offset | Size | Field |
|---|---|---|
| 0x00 | 4 | ASCII `NKDG` |
| 0x04 | 4 | identity word: character, kart, course and date |
| 0x08 | 4 | result word: validity, flags and race time |
| 0x0C | 20 | nickname, 10 UTF-16LE code units, not NUL-terminated |
| 0x20 | 15 | five lap slots of 3 bytes each |
| 0x2F | 1 | cup-rank tier in the low 2 bits; 0 in all stock files |
| 0x30 | 0x200 | emblem, 32×32 at 4bpp |
| 0x230 | 4 | byte length of the run stream (`n`) |
| 0x234 | `n` | 2-byte input runs |
| 0x234+n | up to 0x1000 | zero padding |

The identity word is read with the masks in `mkds_race.h`:

| Bits | Width | Field | Observed |
|---|---|---|---|
| 0–3 | 4 | character | 0–11 |
| 4–9 | 6 | kart | 0–35 |
| 10–15 | 6 | course | 1–40 |
| 16–22 | 7 | year offset | 5, or 0 in `ghost_029.bin` |
| 23–26 | 4 | month | 10 |
| 27–31 | 5 | day | 3–5 |

The year is not a full year. It is the RTC year offset from 2000, proven by the save writer: it stores the value returned by the RTC date call, and the RTC fallback in the same code writes 5. Every October 2005 ghost stores 5, so `ghost_000.bin` is character 0, kart 0, course 20 and date 2005-10-03.

The result word packs validity and time:

| Bits | Width | Field | Observed |
|---|---|---|---|
| 0 | 1 | valid | always 1 in the stock set |
| 1 | 1 | custom-emblem flag for a download ghost; written false for a personal ghost | 0 or 1 |
| 2–3 | 2 | system region id | 0 or 2 |
| 4–7 | 4 | written zero when a personal ghost is saved | always 0 |
| 8–14 | 7 | minutes | 0–2 |
| 15–21 | 7 | seconds | 0–59 |
| 22–31 | 10 | milliseconds | 0–999 |

`ghost_000.bin` has result word `0x78520101`: valid, 1 minute, 36 seconds and 481 ms, or 1:36.481. The lap-tick sum is close but not identical, so the header time is not a verbatim copy of one lap field.

The save writer is the direct proof for bits 1–7: it sets bit 1 false, stores the system region in bits 2–3, and clears bits 4–7. The ghost loader reads bits 2–3 as the driver region for personal, download and staff ghosts, and bit 1 as the custom-emblem flag only for a download ghost.

The nickname is a fixed 10-unit UTF-16LE array. Every stock file begins `Nintendo` followed by U+2605 (★) and a staff name; `ghost_000.bin` reads `Nintendo★たなか`. A shorter name is padded with `U+0000` units, so the field is not a lone NUL-terminated string.

Each lap slot is three bytes holding a 24-bit big-endian value. The value packs minutes in bits 17–23, seconds in bits 10–16 and milliseconds in bits 0–9, exactly as the personal-ghost writer stores it. `mkds_ghost_lap_value()`, `mkds_ghost_lap_minutes()`, `mkds_ghost_lap_seconds()` and `mkds_ghost_lap_millis()` decode it. Three-lap ghosts use the first three slots and leave the last two zero. `ghost_023.bin` is the only stock file that uses all five slots. `ghost_023.bin` stores 10.051, 10.267, 10.358, 10.322 and 9.922 seconds, which sums to 50.920 s and matches its header exactly. `ghost_000.bin` stores 31.329, 32.553 and 32.343 seconds, which sums to 96.225 s against the header's 96.481 s; the header and lap sum are close but not guaranteed equal.

The five lap slots are the maximum lap count in the stock courses: `old_baby_gc` declares five laps, and the ghost lap reader accepts lap numbers 1 through 5. Three-lap courses leave slots 4 and 5 zero; `ghost_023.bin` is the five-lap `old_baby_gc` ghost and fills all five.

The emblem is exactly 32×32 at 4 bits per pixel (`0x200` bytes), stored as 32 linear rows of 16 bytes. The record screen copies the bytes verbatim and then converts the linear rows to 8×8 tile order for the texture upload; the file itself is not pre-tiled. Observed nibbles are 0, 1, 5 and 8, and the palette comes from the record archive NCLR.

Unknowns: the label-renderer effect of the 0x2F cup-rank tier; the driver byte is written but no race function reads it, so the visual result remains unproven.

The run stream starts with a little-endian byte count, not a run count. `ghost_000.bin` stores 1272 at 0x230, so bytes 0x234–0x72B are runs. Each run is two bytes: an input key mask and a duration in frames. The mask is the recorder format: bit 0 A, bit 1 B, bit 2 R, bit 3 L-or-X, bit 4 right, bit 5 left, bit 6 down, bit 7 up. The first runs of `ghost_000.bin` are `00 49`, `01 7F` and `29 03`, i.e. no keys for 73 frames, A for 127 frames and right+A for 3 frames. The durations sum to 5880 frames, about 1.5 s more than the 96.481 s race, which is consistent with countdown or idle frames. Counts range from 374 (`ghost_023.bin`) to 2758 (`ghost_021.bin`); the longest ends at 0xCFA, so the `0x1000` file size is not a stream limit. The recorder caps a ghost at 1764 runs, so every stock stream fits.

The 0x2F byte is a derived cup-rank tier, not a random value. The save path calls a helper that scans all eight GP cups and four rank slots, keeps the worst rank, and returns 0 when any cup is incomplete or its rank is below 5; worst rank 5 returns 1, 6 returns 2 and 7 returns 3. The header stores this value in a two-bit field, so only 0–3 can be represented. A download ghost passes the stored value to its driver config; a personal ghost is forced to 0 and a staff ghost to 1, so the saved personal value is not consumed by the race path. The downstream use of the driver byte is not established, so the display effect remains unproven.

## staff_ghost_time.bin

Two copies exist: `/data/Ghost/staff_ghost_time.bin` and `/data/KartModelMainA_arc/staff_ghost_time.bin`. Both are 160 bytes and both are a plain table of 40 little-endian `uint32_t` values with no header.

| Offset | Size | Field |
|---|---|---|
| 0x00 | 160 | 40 thresholds; entry `i` is course id `i + 1` |

The game loads the `/data/Ghost` copy and reads entry `course id - 1`, so the table is indexed by course id minus one. The comparison is `race_total_ms < threshold`, which proves the unit is milliseconds and that the value is an unlock threshold, not the staff ghost's own race time.

Only 32 of the 40 slots are nonzero, exactly the 32 course ids that have ghost files: 1, 9–20 and 22–40. Slots 2–8 and 21 are zero in both copies, so those courses have no threshold. The two copies differ in every nonzero slot. Course 1 is 117496 ms in `/data/Ghost` and 120117 ms in the archive copy; course 9 is 54993 ms and 53068 ms.

The table has 40 slots because it is indexed directly by the 1–40 race course id. The eight holes are the non-cup/test course ids 2–8 and 21 (old_mario_gc, luigi, dokan, test1, donkey, wario, nokonoko and test_circle), which have no staff ghost. The 32 cup courses are exactly the 32 nonzero slots, so there is no missing entry: the zero slots are deliberate “no staff ghost” markers.

## NKMR mission table

`/data/Scene/Menu_arc/mission.mr` is 4012 bytes and begins with `NKMR`. The count at 0x04 is 91, and `8 + 91×44 = 4012`, so the file is a header and 91 fixed entries with no padding.

| Offset | Size | Field | Observed |
|---|---|---|---|
| 0x00 | 4 | `NKMR` | |
| 0x04 | 4 | entry count | 91 |
| 0x08 | 44×91 | mission entries | names `mr01`..`mr91` |

Each entry matches `MkdsMissionEntry`:

| Offset | Size | Field |
|---|---|---|
| 0x00 | 2 | time limit, frames at 60 Hz (counts down) |
| 0x02 | 2 | rank target time, frames at 60 Hz |
| 0x04 | 2 | signed rank tolerance coefficient, not a time |
| 0x06 | 1 | mission id |
| 0x07 | 1 | task (`MkdsMissionTask`) |
| 0x08 | 1 | course id (`MkdsMissionCourseId`) |
| 0x09 | 1 | engine class (`MkdsEngineClass`) |
| 0x0A | 1 | character id (`MkdsCharacterId`) |
| 0x0B | 1 | kart id |
| 0x0C | 1 | menu id |
| 0x0D | 1 | reserved, zero |
| 0x0E | 1 | camera index |
| 0x0F | 1 | target value |
| 0x10 | 2 | win delay |
| 0x12 | 2 | reserved, zero |
| 0x14 | 8 | four object ids |
| 0x1C | 2 | flags (`MkdsMissionFlags`: `.bits.no_forward`, `.bits.no_damage`, `.bits.no_wall_hit`, `.bits.no_respawn`, `.bits.mirror`, `.bits.backwards`) |
| 0x1E | 1 | enemy character, 0xFF when unused |
| 0x1F | 1 | enemy kart, 0xFF when unused |
| 0x20 | 12 | ASCII name, NUL-padded |

Entry 0 reads time limit 1500, target 1500, tolerance 100, mission 1, task 0, course 1, class 1, character 6, kart 18, target value 1 and name `mr01`. Entry 90 reads mission 91, task 6, course 25, class 1, character 7, kart 21, name `mr91`.

The time unit is proven from the mission controller, not from the file. The race frame counter increments once per update, the mission time limit is compared directly with that counter, and the race-time conversion divides the counter by 60. The HUD timer is `time_limit - frameCounter` while the limit is armed. Therefore both `time_limit` and `target_time` are frame counts at 60 frames per second; entry 0 is a 25-second limit and a 25-second rank target. The tolerance field is used only in the mission rank expression `tolerance × (target_time - frameCounter) / 1000`, so it is a point coefficient (0.1 point per frame when 100), not a duration.

The camera byte indexes a two-entry camera parameter table: 0 is the normal race camera (distance 58, elevation 34, maximum target elevation 20, all fx32) and 1 is a wider camera (98, 55, 34). Only record 24 uses 1, and record 24 is not referenced by the menu table. Values above 1 have no bounds check and are invalid.

The menu byte (`menu_index` in the header) is not the `missionTable.mtbl` slot. Over the 63 menu-referenced records its values form a permutation of 0–62, but 23 of those records disagree with the mtbl slot that names the same mission id; every unreferenced record stores 0. No stock consumer reads the field, so `missionTable.mtbl` is the authoritative menu key and the menu index has no proven runtime role.

The CTables key the mission records by `MkdsMission` and the menu table by `MkdsMissionMenuSlot`. The 91 records are one complete configuration table; 63 are reachable through the 7×9 menu table and the remaining 28 are additional configurations that no menu slot names. The race setup receives the selected record pointer from the menu path, so an unreferenced record cannot be reached by normal play. The extras all have menu byte 0; by task they are 11 destroy, 6 coins, 4 laps, 3 gates, 2 power-slide, 1 finish-before and 1 boss. Only six of them repeat a `(course, task)` pair that a menu slot also uses, so they are not simply duplicates.

Tasks 0–7 are the gameplay rules listed below. Task 5 (no task) and tasks 8–10 have no stock record. Task 10 is additionally treated as lap-counted by the lap HUD, but no completion handler exists for 8, 9 or 10; tasks 8–10 are only no-ops in the sound switch and are reserved/unused in retail data. They have no runtime effect in the retail build, so their intended meanings are not recoverable from the shipped code or data.

No game function reads the menu byte, and no stock record sets `reserved_0d` or `reserved_12` to anything but zero. Tasks 8–10 are reserved with no stock data; task 10 is only consulted by the lap-count HUD. A menu/UI meaning for the menu byte, if one exists, would have to come from a scene path outside the race controller.

## PRM mission parameters

`/data/MissionRun/*.prm` contains eight files and no magic:

| File | Size |
|---|---|
| `common.prm` | 128 (all zero) |
| `hanachan.prm` | 308 |
| `bomb_king.prm` | 528 |
| `kuriking.prm` | 536 |
| `boss_donketu.prm` | 580 |
| `king_ice_donketu.prm` | 580 |
| `king_teresa.prm` | 580 |
| `iwante_l.prm` | 720 |

The first little-endian word is 3 in seven files and 1 in `boss_donketu.prm`; `common.prm` is all zero. The remainder is a stream of 32-bit words in which multiples of `0x1000` are common, and after 0x38 a word `0x1000` often repeats every 12 bytes for a stretch. Not all file sizes are multiples of 12, and the same 12-byte cadence does not hold everywhere, so this document does not declare a record table or a field layout.

Examples: `boss_donketu.prm` starts `01 00 00 00`, `00 20 00 00`, `00 A0 01 00`, `00 A0 01 00`; `kuriking.prm` starts `03 00 00 00`, `00 10 00 00`, `00 88 00 00`, `00 F0 00 00`.

PRM is a per-boss parameter block, not a generic mission table. The boss loaders pass the matching filename literal (`bomb_king.prm`, `kuriking.prm`, `hanachan.prm`, `iwante_l.prm`, and the king/boss variants) to the boss initializer, which loads it from the MissionRun folder and stores the pointer at boss `+0xA0`. The boss initializer reads two PRM fields immediately: `+0x04` is copied to the boss model scale X/Y/Z, and `+0x0C` is multiplied by four and passed to the size-X setter. The first word is not read by that initializer, so it is not proven to be a count; it may be a version or type selector.

`common.prm` is all zero and no stock loader references it; it is a shared/default placeholder in this corpus. The rest of the file is boss-specific data. The boss update code reads many offsets from a `+0xA0` pointer, but the 580-byte PRM files cannot cover all of those offsets, so some update-side `+0xA0` accesses belong to sub-objects rather than the PRM block. A complete PRM field map needs the boss initializer and the boss update consumers; the available C stubs are not enough.

`include/nitro/mkds/race/prm.h` therefore declares only the proven prefix: `+0x00` variant, `+0x04` model scale, `+0x08` extent A and `+0x0C` extent B (the initialiser multiplies extent B by four before the size-X setter). The stock extents are whole/half-unit Fx32 values in the same range as the boss collision sizes: hanachan 14.3/15.6, bomb_king 50.0/40.0, king_teresa 0.0/40.0 and iwante_l 20.0/20.0. Everything from `+0x10` stays opaque because the body mixes per-boss scale, timer and 12-byte cadence records without a proven consumer map.

No NKMR field names a PRM. The binding is by boss model/object name and the boss mission that spawns it, which is inferred from the loader literals and boss functions.

## RTT rank-time table

`/data/MainRace_arc/ranktimeGP.rtt` is 284 bytes.

| Offset | Size | Field | Observed |
|---|---|---|---|
| 0x00 | 4 | `NKTT` | |
| 0x04 | 4 | file size | 284 |
| 0x08 | 2 | course count | 32 |
| 0x0A | 2 | time-delta factor | 1000 |
| 0x0C | 2 | first-place factor | 150 |
| 0x0E | 2 | start-boost points | 25 |
| 0x10 | 2 | power-slide points | 2 |
| 0x12 | 2 | item-hit points | 5 |
| 0x14 | 2 | off-road divisor | 3 |
| 0x16 | 2 | wall-hit points | 20 |
| 0x18 | 2 | damage points | 30 |
| 0x1A | 2 | respawn points | 70 |
| 0x1C | 8×32 | course entries | |

Each entry is 8 bytes, not 7: a byte course id, one zero byte, then three 16-bit values. The padding is part of the file.

| Offset | Size | Field |
|---|---|---|
| 0x00 | 1 | course id, the same race `CourseId` value used by `rconf_getCourse()` (1–40; not the NKM STAG course id) |
| 0x01 | 1 | zero |
| 0x02 | 2 | 50cc target frames |
| 0x04 | 2 | 100cc target frames |
| 0x06 | 2 | 150cc target frames |

Entry 0 has course 10 and times 5610, 4620 and 3960. The game compares these values with the frame counter, so they are frame counts at 60 Hz, not milliseconds. Entry 1 has course 11 and 8250, 6600 and 5940.

The 32 keys are the 32 cup courses, not a separate id space. They are stored in a separate table order: table index `i` holds the course at 8×4 cup order index `(i + 16) mod 32`. The first 16 rows are therefore cup order indices 16–31 (the second half of the cup table) and rows 16–31 are cup order indices 0–15. All 32 keys match the cup table exactly; no battle, mission or staff-roll course appears.

The runtime lookup scans `course_count` entries and compares the entry course id with the current `CourseId`, so the file order does not affect lookup. It then selects the 50cc, 100cc or 150cc column from the current engine class.

Unknowns: none about the key mapping or scoring formula; the table order is a fixed historical ordering, and why it starts with the retro half is not recorded in the code.

## RPT rank-point table

`/data/MainRace_arc/rankpoint.rpt` is 168 bytes: an 8-byte header and 20 rows of 8 bytes.

| Offset | Size | Field | Observed |
|---|---|---|---|
| 0x00 | 4 | `NKPT` | |
| 0x04 | 4 | file size | 168 |
| 0x08 | 8×20 | rows | |

Each row is eight unsigned bytes, one point value per finishing place. The observed rows are:

| Row | Values |
|---|---|
| 0 | 10, 8, 6, 4, 3, 2, 1, 0 |
| 1 | 10, 8, 6, 4, 3, 2, 1, 0 |
| 2 | 10, 8, 6, 4, 2, 1, 0, 0 |
| 3 | 10, 8, 6, 3, 1, 0, 0, 0 |
| 4 | 10, 8, 5, 2, 0, 0, 0, 0 |
| 5 | 10, 7, 4, 1, 0, 0, 0, 0 |
| 6 | 10, 7, 4, 0, 0, 0, 0, 0 |
| 7 | 10, 5, 0, 0, 0, 0, 0, 0 |
| 8 | 15, 7, 2, 2, 1, 1, 0, 0 |
| 9 | 15, 7, 3, 1, 1, 0, 0, 0 |
| 10 | 15, 6, 2, 1, 1, 0, 0, 0 |
| 11 | 15, 6, 2, 1, 0, 0, 0, 0 |
| 12 | 15, 6, 2, 0, 0, 0, 0, 0 |
| 13 | 15, 6, 1, 0, 0, 0, 0, 0 |
| 14 | 15, 5, 0, 0, 0, 0, 0, 0 |
| 15 | 15, 12, 9, 6, 4, 2, 1, 0 |
| 16 | 15, 12, 9, 6, 3, 1, 0, 0 |
| 17 | 15, 11, 8, 5, 3, 1, 0, 0 |
| 18 | 15, 11, 8, 3, 1, 0, 0, 0 |
| 19 | 15, 10, 6, 1, 0, 0, 0, 0 |

The row index is not a course or engine class; it is selected by race mode, driver count and team layout, as the call-site formulas below show. The trailing zeros store “no points”, not missing bytes.

## ItemSlotList.dat

`/data/MainRace_arc/Item/ItemSlotList.dat` is 1391 bytes. Byte 0 is 11, the number of blocks. Each block starts at the next byte:

| Offset | Size | Field |
|---|---|---|
| +0 | 1 | slot count (table rows) |
| +1 | 1 | item-config column count; 18 in every block |
| +2 | slots×18 | one weight byte per (item config, slot) pair |

The payload is stored item-config-major: for item config 0, one byte per slot; then item config 1, one byte per slot; and so on. In memory the game transposes it to a slot-major table: each slot row has 18 `uint16_t` weights (one per item config), followed by a `0xFFFF` sentinel row. The 18 columns are the 18 item configurations built by the item initialiser, not characters.

A cell is a weight, not an item id: 0 disables that item for that row, larger values make it more likely, and the item roll picks one column by weighted random selection. Stock weights range from 0 to 200.

The 11 blocks are:

| Block | Offset | Slots | Columns | End |
|---|---|---|---|---|
| 0 | 0x001 | 8 | 18 | 0x093 |
| 1 | 0x093 | 8 | 18 | 0x125 |
| 2 | 0x125 | 8 | 18 | 0x1B7 |
| 3 | 0x1B7 | 8 | 18 | 0x249 |
| 4 | 0x249 | 8 | 18 | 0x2DB |
| 5 | 0x2DB | 8 | 18 | 0x36D |
| 6 | 0x36D | 16 | 18 | 0x48F |
| 7 | 0x48F | 3 | 18 | 0x4C7 |
| 8 | 0x4C7 | 3 | 18 | 0x4FF |
| 9 | 0x4FF | 3 | 18 | 0x537 |
| 10 | 0x537 | 3 | 18 | 0x56F |

The last block ends exactly at the file size, so there is no trailer. Block 0 begins with header `08 12` and payload `2D 19 0F 05 00 00 00 00 00 37 28 19 14 0A 00 00 5A 1E`. Because the payload is config-major, item-config 0 has weights 45, 25, 15, 5, 0, 0, 0, 0 for slots 1–8; item-config 1 has 0, 55, 40, 25, 20, 10, 0, 0; item-config 2 has 90, 30, 15, 5, 0, 0, 0, 0; and so on. `0x00` is a disabled item, not padding.

The item-config column order is the order in which the game builds its 18 item configurations:

| Column | Item |
|---|---|
| 0 | green shell, single |
| 1 | red shell, single |
| 2 | banana, single |
| 3 | fake item box |
| 4 | mushroom, single |
| 5 | mushroom, triple |
| 6 | bomb |
| 7 | blue/spiny shell |
| 8 | lightning |
| 9 | green shell, triple |
| 10 | banana, triple |
| 11 | red shell, triple |
| 12 | star |
| 13 | golden mushroom |
| 14 | Bullet Bill |
| 15 | Blooper |
| 16 | Boo |
| 17 | item box (the rolled-item placeholder) |

The runtime item roll confirms the column order: it reads `row × 0x24 + config × 2`, accumulates the 18 weights, picks one index and stores that index as the item-config id.

Block 6 is the item-box override table. It is the only block referenced by an item box's own settings: `settings[1]` selects the row for a non-enemy driver and `settings[2]` for a CPU driver, using `id − 1`. A zero id means “use the mode/place table”. Stock NKM objects use player ids 1–11 and enemy id 1, so block 6 rows 0–10 are reachable; rows 11–15 are not referenced by any stock NKM object (row 11 still contains one weight, rows 12–15 are zero). 16 is the declared capacity, not a count derived from the corpus. Runtime boxes set both ids to 0.

Blocks 7–10 have three rows because in battle the row is a tier derived from the driver's remaining balloons (balloon battle) or relative shine count (shine runners), clamped to 1–3. The eight-row and sixteen-row blocks are indexed by finishing place (1–8) or by the item-box id.

No functional unknown remains for the table: the 16-row capacity is a declared upper bound, not derived from the corpus, and rows 11–15 are unused by stock NKM objects.

## Kart and character parameter files

The corpus has 18 `.bin` parameter files in four `KartModel*` archives. Sizes and exact divisors are corpus facts; the fields below are decoded where a call site proves them and marked where the map is inferred.

| File | Size | Observed shape |
|---|---|---|
| `KartModelMain_arc/charphysicalparam.bin` | 26 | 13 × 2 |
| `KartModelMainA_arc/charphysicalparam.bin` | 104 | 13 × 8 |
| `KartModelMenu_arc/charmenuparam.bin` | 26 | 13 × 2 |
| `KartModelMenu/charmenuparam.bin` | 26 | 13 × 2 |
| `KartModelMain_arc/kartAIparam.bin` | 5760 | 480 × 12 |
| `KartModelMainA_arc/kartAIparam.bin` | 5760 | 480 × 12 |
| `KartModelMain_arc/kartcrsmat.bin` | 400 | 50 × 8 |
| `KartModelMainA_arc/kartcrsmat.bin` | 432 | 54 × 8 |
| `KartModelMain_arc/kartoffsetdata.bin` | 8288 | 37 × 224 |
| `KartModelMainA_arc/kartoffsetdata.bin` | 8288 | 37 × 224 |
| `KartModelMenu_arc/kartoffsetdata.bin` | 8288 | 37 × 224 |
| `KartModelMenu/kartoffsetdata.bin` | 8288 | 37 × 224 |
| `KartModelMain_arc/kartphysicalparam.bin` | 5328 | 37 × 144 |
| `KartModelMainA_arc/kartphysicalparam.bin` | 7600 | 50 × 152 |
| `KartModelMenu_arc/kartphysicalparam.bin` | 7400 | 50 × 148 |
| `KartModelMenu/kartphysicalparam.bin` | 7600 | 50 × 152 |
| `KartModelMenu_arc/kartmenuparam.bin` | 600 | 50 × 12 |
| `KartModelMenu/kartmenuparam.bin` | 600 | 50 × 12 |

`kartAIparam.bin` is 480 records of 12 bytes. The game indexes it as 12 entries per course slot, with three engine classes and three CPU modes inside each non-GP group; that gives 40 course slots. The index formulas are proven by the loader:

| Mode | Record index |
|---|---|
| GP | `cc_mode + (course − 1) × 12` (uses the 0, 1, 2 slots directly) |
| TA, MG, VS, MR, NT | `(course − 1) × 12 + (cc_mode + 1) × 3 + cpu_offset`, where `cpu_offset` is 0 for easy, 1 for normal and 2 for hard |

The first word is a speed bonus added to a rival CPU's target maximum speed; the resulting sum is clamped to 10. The second is divided by three at setup, then multiplied by the per-place aggression table to decide how strongly a CPU closes up to the pack. The third is an ahead-speed threshold: when a leading CPU's speed exceeds this value times 0.8007, the follower applies an extra 0.98 slowdown. All three are Fx32.

`kartcrsmat.bin` is 50 or 54 records of four 16-bit `GXRgb` colours: diffuse, ambient, specular and emission. The record is indexed by course id, not kart id: the game selects `table[course] - 1`, so the 50/54 records cover the 1-based course space and the values are passed directly to the G3D material setters.

`kartoffsetdata.bin` is 37 records of 0xE0 bytes, indexed by kart id. Each record is a 16-byte tyre name, one fx32 front-tyre scale, four `VecFx32` tyre positions and thirteen `VecFx32` character positions. Record 0 begins with the ASCII name `kart_tire_M`.

`kartmenuparam.bin` is 50 records of six signed 16-bit stat bars, indexed by kart id: speed, acceleration, weight, handling, drift and items. `charmenuparam.bin` is 13 signed 16-bit weight offsets indexed by character id and added to the selected kart's weight stat. The 104-byte `charphysicalparam.bin` is 13 records of two fx32 values: a collision-speed scale and a weight, matching the eight-byte character physical record. The 26-byte `KartModelMain_arc/charphysicalparam.bin` is 13 16-bit values, but `KartModelMain_arc` is not the archive selected by `arc_getKartModelArcFile` for race or menu, so that file has no stock consumer.

`kartphysicalparam.bin` appears with three different record widths, all inferred from exact division and stable leading values:

| Width | Files | Records |
|---|---|---|
| 144 (0x90) | `KartModelMain_arc` | 37 |
| 148 (0x94) | `KartModelMenu_arc` | 50 |
| 152 (0x98) | `KartModelMainA_arc`, `KartModelMenu` | 50 |

Observed first words for the 152-byte path are 0x8000, 0xFFFFE000, 0x9000 and 0x002D0800. Each `kartcrsmat.bin` row starts with four 16-bit values, for example 0x7FFF, 0x294C, 0x0000 and 0x2108.

The 152-byte variant is the only one that matches the game's in-memory kart physical-parameter record. The proven offsets are:

| Offset | Size | Meaning | Status |
|---|---|---|---|
| 0x00 | 4 | collision radius, fx32 | proven by driver collision setup |
| 0x04 | 4 | collision Z offset, signed fx32 | proven by driver collision setup |
| 0x08 | 4 | unused padding, no reader | gap |
| 0x0C | 2 | mass, fx16 | proven by collision pushback |
| 0x0E | 2 | boost duration in frames, s16 | proven by boost code |
| 0x10 | 4 | top speed, fx32 | proven |
| 0x14 | 4 | base acceleration, fx32 | proven |
| 0x18 | 4 | acceleration at the high-speed end of the curve, fx32 | proven |
| 0x1C | 4 | max-speed fraction where the high-speed acceleration applies, fx32 | proven |
| 0x20 | 4 | drift acceleration, fx32 | proven |
| 0x24 | 4 | drift acceleration at the high-speed end, fx32 | proven |
| 0x28 | 4 | drift max-speed fraction, fx32 | proven |
| 0x2C | 4 | deceleration, fx32 | proven |
| 0x30 | 2 | steering, fx16 | proven |
| 0x32 | 2 | drift, fx16 | proven |
| 0x34 | 4 | drift compensation, fx32 | proven |
| 0x38 | 48 | 12 collision velocity-minus-direction fx32 multipliers | proven by driver code |
| 0x68 | 48 | 12 collision speed fx32 multipliers | proven by driver code |

The acceleration curve is proven in `driver_handleAcceleration`: normal driving uses `base_accel`, switches to `accel_high_speed` above `accel_curve_end` (a max-speed fraction) and interpolates between them from 0.5 to that fraction; drifting uses `drift_accel`, `drift_high_speed` and `drift_curve_end` the same way. The 0x08 word is padding with no reader.

The 148-byte variant is the 152-byte layout without the four-byte drift-compensation field at 0x34, so its 12+12 collision multiplier arrays start at 0x34 instead of 0x38. The evidence is exact size arithmetic (`0x94 + 4 = 0x98`), the 0x34 boundary, the 96-byte trailing block, and a byte-identical record-0 tail between `KartModelMenu_arc` and `KartModelMainA_arc`. Other records carry different tuning values, so this is a strong structural inference rather than a call-site proof.

The 144-byte variant is inferred to remove the 152-byte words at 0x08 and 0x34, which puts its mass/boost pair at 0x08, top speed at 0x0C, steering/drift at 0x2C and the 12+12 collision arrays at 0x30. `KartModelMain_arc` is not the archive selected by the stock race or menu path, so no retail call site loads this width; the map remains inferred.

The header declares all three widths. `MkdsKartPhysRow152` is proven; `MkdsKartPhysRow148` and `MkdsKartPhysRow144` carry inferred structural maps and are marked as such.

Unknowns: the provenance of the 144-byte table (no stock race or menu path loads it, so it has no runtime effect).

## emblem2.bin

`/data/Scene/Record_arc/emblem2.bin` is 512 bytes, exactly 32×32 pixels at 4bpp, stored as 32 linear rows of 16 bytes. It has no header and no palette. The first row is `00 55 55 55 55 55 55 55 55 55 55 55 55 55 55 00`; the border and the inner shapes use nibbles 0, 1, 5 and 8. The record screen copies the bytes verbatim and then converts the linear rows to 8×8 tile order for the texture upload. The palette is supplied by the surrounding record archive NCLR; scan order is linear in the file and tiled only at upload.

## builddate.bin

`/data/Boot/builddate.bin` is 30 bytes of ASCII with no NUL terminator: `Build: 2005 10/8(Sat) 23:05:54`. It is a build stamp, not a structured format.

## DWC utility.bin

`/dwc/utility.bin` and `/data/dwc/utility.bin` are byte-identical copies of the standard Nitro DWC Wi-Fi setup utility archive, 1,069,000 bytes each. This is the NARC-less DWC layout documented by GBATEK, not an MKDS invention: a 0x10-byte header with FNT offset, FNT size, FAT offset and FAT size, followed by the FNT and FAT. In this file the FNT starts at 0x10 with size 0x1498, the FAT starts at 0x14C0 with size 0xAB0 (342 entries), and FAT offsets are relative to the start of the file. The FNT lists names such as `char`, `move`, `msg`, `sound` and many `*.nsc.l` files.

Reference: GBATEK, “DS Cartridge NitroROM and NitroARC File Systems”, NARC-less variant, <https://problemkaputt.de/gbatek-ds-cartridge-nitrorom-and-nitroarc-file-systems.htm>; Nintendo DWC utility background, <https://twlsdk.randommeaninglesscharacters.com/docs/nitro/NitroDWC/dwc/base/DWC_StartUtility.html>.

The only MKDS-specific observations are the two identical copies and their paths. The internal file system is standard and is not re-specified here.

## MKDS-specific usage and configuration

This part is deliberately separate from the byte layouts above. It records which game mode or feature consumes each file and which edits depend on each other. Mappings marked inferred are consistent with the corpus and call sites but are not asserted by one direct structure definition.

### Ghost selection, saving and playback

MKDS uses two ghost block types with the same 0x30-byte header but different containers. `NKPG` is the personal ghost written by Time Trials. `NKDG` is the downloaded and staff ghost container and adds the 0x200-byte emblem between the header and the input recording. The corpus supplies only NKDG files; the NKPG size and offsets below come from the game's save code, not from a file in this extraction.

| Container | Magic | Size | Input offset | Emblem | Used by |
|---|---|---|---|---|---|
| Personal ghost | `NKPG` | 0xE00 | 0x30 | none | Time Trials personal ghost, one block per course order index |
| Download/staff ghost | `NKDG` | 0x1000 | 0x234 | 0x30..0x22F | downloaded ghost save slots and the 32 staff ghost files |

The personal ghost area starts at save offset 0xAF00 and has 32 blocks of 0xE00 bytes, indexed by course order index. The download ghost area starts at 0x26F00 and has 10 blocks of 0x1000 bytes, indexed by download slot. The personal and download availability bits live in the `NKSY` save block, not in the ghost block.

The staff ghost file index is the 0-based course order index, not the course id. The order is the 8-cup by 4-course layout used by the cup table. The header's course field stores the course id. The staff ghost time table is indexed by course id minus one, so a ghost edit has three linked keys: file index, header course id and threshold slot. A race total strictly below the threshold is what makes the staff ghost available; the threshold is not the ghost's own time.

| Order index | Staff file | Header course id | `staff_ghost_time` slot |
|---|---|---|---|
| 0 | `ghost_000.bin` | 20 | 19 |
| 1 | `ghost_001.bin` | 22 | 21 |
| 2 | `ghost_002.bin` | 31 | 30 |
| 3 | `ghost_003.bin` | 18 | 17 |
| 4 | `ghost_004.bin` | 27 | 26 |
| 5 | `ghost_005.bin` | 28 | 27 |
| 6 | `ghost_006.bin` | 33 | 32 |
| 7 | `ghost_007.bin` | 24 | 23 |
| 8 | `ghost_008.bin` | 30 | 29 |
| 9 | `ghost_009.bin` | 17 | 16 |
| 10 | `ghost_010.bin` | 25 | 24 |
| 11 | `ghost_011.bin` | 19 | 18 |
| 12 | `ghost_012.bin` | 34 | 33 |
| 13 | `ghost_013.bin` | 26 | 25 |
| 14 | `ghost_014.bin` | 32 | 31 |
| 15 | `ghost_015.bin` | 29 | 28 |
| 16 | `ghost_016.bin` | 10 | 9 |
| 17 | `ghost_017.bin` | 11 | 10 |
| 18 | `ghost_018.bin` | 13 | 12 |
| 19 | `ghost_019.bin` | 14 | 13 |
| 20 | `ghost_020.bin` | 35 | 34 |
| 21 | `ghost_021.bin` | 16 | 15 |
| 22 | `ghost_022.bin` | 12 | 11 |
| 23 | `ghost_023.bin` | 9 | 8 |
| 24 | `ghost_024.bin` | 15 | 14 |
| 25 | `ghost_025.bin` | 36 | 35 |
| 26 | `ghost_026.bin` | 37 | 36 |
| 27 | `ghost_027.bin` | 38 | 37 |
| 28 | `ghost_028.bin` | 39 | 38 |
| 29 | `ghost_029.bin` | 23 | 22 |
| 30 | `ghost_030.bin` | 40 | 39 |
| 31 | `ghost_031.bin` | 1 | 0 |

Header fields have these runtime jobs:

| Field | Runtime use |
|---|---|
| character, kart | spawn the ghost driver with that character/kart |
| course | course check and display; must match the file's order index |
| year/month/day | RTC date captured when a personal ghost is saved |
| valid | if zero, no ghost is offered |
| flag 1 | download ghost custom-emblem flag; false for a personal ghost |
| flag pair (bits 2–3) | system region id for the ghost driver |
| minutes/seconds/milliseconds | displayed total time and comparison against the staff threshold |
| nickname | ten UTF-16LE units shown on the ghost label |
| lap slots | up to five displayed lap times |
| field `0x2F` | derived cup-rank tier 0–3 (worst GP cup rank: below 5 or incomplete → 0, rank 5 → 1, 6 → 2, 7 → 3); download ghosts pass it on, personal/staff use fixed values |

Time Trials loads the personal ghost for the selected course, then loads one of personal, download or staff according to the ghost selector. A download ghost is loaded by download slot id, not by course id. A staff ghost is loaded by course order index through `ghost_%03d.bin`, and the staff threshold comes from the separate course-id-keyed table. If the selected block is invalid, the ghost driver is not added.

Playback copies the whole input recording into the ghost driver's input unit and starts playback. Each run's key mask becomes the DS key state for `duration` frames. The recorded `byte_length` is a byte count, but the playback loop compares it with an entry index, so it runs past the real runs into zero padding; this is a game quirk, not a request to double the stored length. Edit a ghost stream by keeping runs two bytes each, setting `byte_length = 2 × runs`, keeping runs within 1764, and leaving the rest zero.

Linked edits for ghosts: changing the personal ghost's course order index requires moving its 0xE00 block; changing a staff ghost's file index requires moving the file and updating its header course and the threshold at `course - 1`; changing the total time should be reflected in the lap slots and in the staff threshold if the ghost is staff; changing the emblem is NKDG-only and must stay 0x200 bytes.

### Mission records, menu table and PRM sidecars

The 91 `mission.mr` records are not all menu missions. `missionTable.mtbl` is the menu index: magic `NKMT`, `uint16_t` level count 7, `uint16_t` missions per level 9, then 63 bytes of mission ids in row-major level/mission order. The menu slot `(level, mission)` reads the id from this table, maps it to `(level, index)` with a search of the same table, and then uses the `mission.mr` record whose 1-based id matches.

`mission.mr` record fields map as follows: `mission_id` is the 1-based record number; `course_id` selects the course archive; `task` selects the mission rule; `time_limit` is a 60 Hz frame countdown, `target_time` is the 60 Hz rank target and `rank_delta_scale` is the rank point coefficient; `target_value` is the task's counter target (the controller returns 1 when it is zero); `object_ids` are the four object ids used by object-based tasks; `flags` carries the no-forward, no-damage, no-wall-hit, no-respawn, mirror and backwards bits; `character_id`/`kart_id` set the player loadout; `enemy_character`/`enemy_kart` set the rival; `camera_index` selects one of two camera parameter sets (0 normal, 1 wide); `name` is the ASCII `mrNN` stem. The `menu_id` byte is not read by the race code and is not the MTBL position, so the menu table is the authoritative key.

The 63 menu missions pair with course archives as follows. The tool file is `data/Course/<archive>_arc/MissionRun/mrNN_tool.nkm`.

| Level | Mission | Id | Course id | Course archive |
|---|---|---|---|---|
| 1 | 1 | 54 | 20 | cross_course |
| 1 | 2 | 55 | 13 | old_peach_agb |
| 1 | 3 | 12 | 22 | bank_course |
| 1 | 4 | 82 | 31 | beach_course |
| 1 | 5 | 81 | 44 | mini_stage1 |
| 1 | 6 | 14 | 18 | mansion_course |
| 1 | 7 | 6 | 11 | old_momo_64 |
| 1 | 8 | 29 | 10 | old_mario_sfc |
| 1 | 9 | 9 | 48 | MR_stage1 |
| 2 | 1 | 26 | 28 | town_course |
| 2 | 2 | 13 | 20 | cross_course |
| 2 | 3 | 43 | 35 | old_donut_sfc |
| 2 | 4 | 20 | 18 | mansion_course |
| 2 | 5 | 11 | 31 | beach_course |
| 2 | 6 | 41 | 27 | desert_course |
| 2 | 7 | 34 | 14 | old_luigi_gc |
| 2 | 8 | 38 | 9 | old_baby_gc |
| 2 | 9 | 50 | 49 | MR_stage2 |
| 3 | 1 | 75 | 33 | pinball_course |
| 3 | 2 | 47 | 28 | town_course |
| 3 | 3 | 25 | 14 | old_luigi_gc |
| 3 | 4 | 85 | 22 | bank_course |
| 3 | 5 | 76 | 43 | mini_dokan_gc |
| 3 | 6 | 2 | 11 | old_momo_64 |
| 3 | 7 | 62 | 24 | ridge_course |
| 3 | 8 | 80 | 45 | mini_stage2 |
| 3 | 9 | 21 | 9 | old_baby_gc |
| 4 | 1 | 88 | 30 | snow_course |
| 4 | 2 | 39 | 46 | mini_stage3 |
| 4 | 3 | 3 | 24 | ridge_course |
| 4 | 4 | 61 | 27 | desert_course |
| 4 | 5 | 27 | 12 | old_koopa_agb |
| 4 | 6 | 83 | 36 | old_choco_64 |
| 4 | 7 | 70 | 33 | pinball_course |
| 4 | 8 | 66 | 37 | old_luigi_agb |
| 4 | 9 | 51 | 50 | MR_stage3 |
| 5 | 1 | 4 | 26 | garden_course |
| 5 | 2 | 28 | 16 | old_frappe_64 |
| 5 | 3 | 48 | 15 | old_noko_sfc |
| 5 | 4 | 37 | 12 | old_koopa_agb |
| 5 | 5 | 53 | 38 | old_kinoko_gc |
| 5 | 6 | 78 | 47 | mini_stage4 |
| 5 | 7 | 35 | 30 | snow_course |
| 5 | 8 | 91 | 25 | mario_course |
| 5 | 9 | 17 | 49 | MR_stage2 |
| 6 | 1 | 64 | 32 | koopa_course |
| 6 | 2 | 8 | 19 | airship_course |
| 6 | 3 | 15 | 39 | old_choco_sfc |
| 6 | 4 | 79 | 42 | mini_block_64 |
| 6 | 5 | 44 | 40 | old_sky_agb |
| 6 | 6 | 40 | 1 | old_yoshi_gc |
| 6 | 7 | 33 | 17 | clock_course |
| 6 | 8 | 90 | 26 | garden_course |
| 6 | 9 | 10 | 48 | mini_block_course |
| 7 | 1 | 60 | 29 | rainbow_course |
| 7 | 2 | 89 | 32 | koopa_course |
| 7 | 3 | 7 | 17 | clock_course |
| 7 | 4 | 72 | 25 | mario_course |
| 7 | 5 | 84 | 34 | stadium_course |
| 7 | 6 | 77 | 44 | mini_stage1 |
| 7 | 7 | 69 | 19 | airship_course |
| 7 | 8 | 86 | 23 | old_hyudoro_64 |
| 7 | 9 | 49 | 38 | old_kinoko_gc |

Mission 10 also has a duplicate `mr10_tool.nkm` in `MR_stage1`; mission 49 also has one in `MR_stage4`. The table lists the first archive that contains the file. The remaining 28 records are not referenced by `missionTable.mtbl`; they are extra mission/boss configurations and all have `menu_id` 0.

Tasks are encoded as: 0 gates, 1 coins, 2 laps, 3 destroy objects, 4 power slides, 5 none (no stock record), 6 finish before the rival, 7 boss, and 8–10 reserved (no stock record; 10 also counts laps for the HUD but has no completion handler). The corpus counts for the 63 menu missions are 14 gates, 14 coins, 2 laps, 14 destroy, 6 power slides, 9 finish-before and 4 boss; the 91-record file includes the extra records.

Mission rank points use their own hardcoded factors, not `ranktimeGP.rtt`: `tolerance × (target_time - frameCounter) / 1000`, minus 5 per item hit, 5 per wall hit, 10 per damage event and 20 per respawn, clamped to −9999..9999. Mission success is separate: the timer expiring fails the mission, while `target_time` only feeds this rank score.

Mission ranks are not stored in `mission.mr`. The save block `NKMR` has 7×9 one-byte entries, one per level/mission, each `valid` plus a 7-bit best rank. Completing a mission updates the entry only when the new rank is better. Rewards and level unlocks read that save block; the reward table itself is outside these files, and `mission.mr` carries no reward id.

PRM files are sidecars for the boss and special objects in the same folder, named after the model. They are not referenced by an NKMR field; the boss loaders pass the matching filename literal and store the loaded pointer in the boss instance, so the binding is by model name and by the boss mission that spawns it.

| PRM | Model file | Notes |
|---|---|---|
| `boss_donketu.prm` | `boss_donketu.nsbmd` | boss parameter sidecar |
| `king_ice_donketu.prm` | `king_ice_donketu.nsbmd` | boss parameter sidecar |
| `king_teresa.prm` | `king_teresa.nsbmd` | boss parameter sidecar |
| `bomb_king.prm` | `bomb_king.nsbmd` | boss parameter sidecar |
| `iwante_l.prm` | `iwante_l.nsbmd` | boss parameter sidecar |
| `hanachan.prm` | `hanachan.nsbmd` | boss parameter sidecar |
| `kuriking.prm` | `kuriking.nsbmd` | boss parameter sidecar |
| `common.prm` | none | all zero; no loader reference found |

The boss missions in the menu table are 9, 10, 17 and 50; mission 24 is a boss-task record not referenced by the menu table. PRM is selected by boss model literal in the boss loader, not by an NKMR field; which mission spawns that boss follows the mission's `mrNN_tool.nkm`. Changing a boss mission's course or object set requires the matching `mrNN_tool.nkm` and, when the object is a boss, the same-named PRM sidecar.

Linked edits for missions: `missionTable.mtbl` must contain the mission id for every menu slot; `mission.mr` must contain that id with the same course; the course archive must contain `mrNN_tool.nkm`; a changed task must still match the object/target fields; and the save `NKMR` rank entry is keyed by level/mission, not by mission id.

### Rank tables

`ranktimeGP.rtt` is GP-only scoring data. The game searches the 32 entries for the current course id, then selects the 50cc, 100cc or 150cc frame value. Entry order is not course order; course ids in the stock file are 10, 11, 13, 14, 35, 16, 12, 9, 15, 36, 37, 38, 39, 23, 40, 1, 20, 22, 31, 18, 27, 28, 33, 24, 30, 17, 25, 19, 34, 26, 32 and 29.

The factors have these runtime effects in GP scoring. Let `T` be the selected class frame value for the current course, `F` the race frame counter at scoring time, `P` the accumulated first-place frames, `S` the power-slide count, `I` the item-hit count, `O` the off-road frame count, `W` wall hits, `D` damage events and `R` respawns:

| Term | Exact expression |
|---|---|
| time delta | `round(1000 × (T − F) / T)`; the code uses a fixed-point divide, adds `0x800` and shifts by 12 |
| first place | `floor(150 × P / T)`; fixed-point divide, then multiply and shift |
| start boost | 25 if the start boost succeeded, else 0 |
| power slides | `2 × S` |
| item hits | `5 × I` |
| off road | `−floor(O × FX_Inv(3 << 12) / 4096)`; the fixed-point reciprocal makes this approximately `−O / 3`, not an exact integer divide |
| wall hits | `−20 × W` |
| damage | `−30 × D` |
| respawns | `−70 × R` |

The nine terms are summed and clamped to −9999..9999. Mission mode uses its own hardcoded factors and does not read this file.

`rankpoint.rpt` is used by GP, VS and NT, not by mission mode. The row is chosen by mode, driver count and team layout, then the finishing place indexes the eight bytes:

| Mode | Row formula |
|---|---|
| GP | 0 |
| VS, no teams | 9 − driver count |
| VS, teams, 2–3 drivers | 16 − driver count |
| VS, teams, 4+ drivers, one team has ≤1 driver | 16 − driver count |
| VS, teams, 4+ drivers, both teams have ≥2 drivers | 23 − driver count |
| NT | 9 − driver count |

The formulas are confirmed at the call site. They produce these row groups: row 0 for GP; rows 1–7 for no-team VS and for NT with 8 down to 2 drivers; rows 8–14 for VS teams with 2–3 drivers or with 4+ drivers and one team of at most one driver; and rows 15–19 for VS teams with 4+ drivers and at least two drivers per team. Row 0 is GP only, not an eight-player no-team race. The finishing place indexes `place_points[place − 1]`, so only places 1–8 can be read.

Linked edits for ranks: a new course entry must be inserted in `ranktimeGP.rtt` if the course is not already present; the course id and class columns must agree; changing a driver count or team rule can select a different `rankpoint.rpt` row, so both tables should be checked together with the race-mode rules.

### Item slots

`ItemSlotList.dat` is a mode-dependent bundle, not a single table. The loader switches on race mode and loads different blocks into three in-memory slot tables. The byte layout is sequential; there are no offsets, so every block header and payload must stay consistent.

| Race mode | Non-enemy table (6C) | Enemy/CPU table (64) | Item-box override (74) |
|---|---|---|---|
| GP (0), TA (1), MR (4) | block 0 | block 1 | block 6 |
| MG (2), balloon battle | block 5 | block 6 | block 4 |
| MG (2), shine runners | block 7 | block 8 | block 4 |
| VS (3) | block 4 | block 5 | block 6 |
| NT (5) | no case in this loader | no case | no case |

The loader reads the sequential block stream and assigns three pointers in this order: block 0/4/5/7 to the non-enemy table, block 1/6/8/5 to the enemy table, and block 6/4 to the item-box override. The player/enemy roles are proven by the roll path: the selector picks the non-enemy table when the breaking driver is a player, ghost or net driver, and the enemy table when the driver is a CPU. Block 6 is the override in GP/TA/MR/VS and the enemy table in balloon battle; rows 0–7 double as the place table there. Block 4 is the override in battle and the non-enemy table in VS and mission. Block 4 and block 5 are byte-identical in the stock file. In VS, when the CPU mode is “none” (a local all-human race), blocks 4/5 are row-remapped by driver count using a fixed 7×7 table, so N drivers use N chosen rows and the rest are zeroed. Blocks 2, 3, 9 and 10 are not referenced by the switch. NT has no case in this loader and does not reload the tables here.

Item-box objects store two ids in their NKM settings: `settings[1]` is the player list id and `settings[2]` is the enemy list id. Runtime item boxes use id 0, which selects the place/tier table. A nonzero id selects row `id − 1` in block 6. When a box breaks, player, ghost and net drivers use the player id; CPU drivers use the enemy id.

Blocks 4 and 5 are byte-identical in the stock file, so NT's player and enemy tables currently differ only by which block the loader assigns. No block is overwritten; the earlier claim that GP loads block 1 over block 0 was a misreading of the loader and is corrected here.

Linked edits for item slots: if a block gains or loses a slot, rewrite its two-byte header and all `slots × 18` weight bytes; if the number of blocks changes, update byte 0; if an item-box object's `settings[1]` or `settings[2]` is stale, it indexes the wrong table or reads past the loaded row count; and every weight column must match the item-config table used by the race mode.

### Parameter table indices

The physical, AI, offset, material, menu and ghost-time files are indexed by different keys. The table below records the proven index formula or dimension, not a promise that every field is understood.

| File family | Observed dimension | Index/key |
|---|---|---|
| `kartphysicalparam.bin` 152-byte variant | 50 records | kart id |
| `kartphysicalparam.bin` 144-byte variant | 37 records | kart id; inferred 152 map minus two words |
| `kartphysicalparam.bin` 148-byte variant | 50 records | kart id; 152 map minus the 0x34 word |
| `kartAIparam.bin` | 480 records of 12 bytes | GP: `(course - 1) × 12 + class`; other modes: `(course - 1) × 12 + (class + 1) × 3 + cpu mode` |
| `kartcrsmat.bin` | 50 or 54 records of 8 bytes | kart id; four 16-bit material slots |
| `kartoffsetdata.bin` | 37 records of 0xE0 | selected kart/model index |
| `kartmenuparam.bin` | 50 records of 12 bytes | kart id; six signed 16-bit stat bars: speed, acceleration, weight, handling, drift, items |
| `charmenuparam.bin` | 13 values of 2 bytes | character index; signed weight offset added to the selected kart's weight stat |
| `charphysicalparam.bin` | 13 records | character index |
| `staff_ghost_time.bin` | 40 values of 4 bytes | course id - 1 |

The AI index explains why the file is 480 records: 40 course slots times twelve entries. The course slot is `course id - 1` (course ids 1–40), not the 8×4 staff-ghost order index. GP uses the first three entries of each group directly by engine class; the other modes use the three-class by three-CPU-mode offset. All three words are Fx32: rival target-speed bonus, pack closing-response scale and leading-CPU slowdown threshold. The loader divides the middle word by three at setup; the rubber-banding update reads all three.

The `kartcrsmat.bin` kart-id key and the `kartoffsetdata.bin` selected-kart key are inferred from their consumers. The AI, menu, character and 152-byte physical keys are proven by indexing code.

For the 152-byte physical record the proven fields are the collision sphere size and Z offset, the Fx32 extent at 0x08, mass, drift-boost duration, top speed, base and drift acceleration, deceleration, handling, drift, drift-turn compensation, and the two 12-entry collision multiplier arrays. The 148-byte record is the same map without the drift-compensation word; the 144-byte record also omits the 0x08 extent. The 0x08 word is a whole/half-unit Fx32 extent (6.0–14.0 in stock) with no matched reader; it is not padding. The 12 collision entries are indexed by surface: road, road alternate, weak off-road, off-road, heavy off-road, slippery 1, slippery 2, unused 7, boost, cannon, water and loop.

Linked edits for parameter tables: changing a record index requires updating every consumer that uses the same kart/character/course id; `kartAIparam.bin` must keep the 12-record course stride; `kartoffsetdata.bin` must keep the 0xE0 stride and its name/payload boundary; `kartphysicalparam.bin` must not mix the 144/148/152 layouts; and the staff ghost threshold index must stay course id minus one.

### Practical edit checklist

Ghost edit: keep NKDG at 0x1000 and NKPG at 0xE00; keep the personal-ghost block index equal to the course order index and the header course byte equal to the race course id; update lap slots and total time together; set the run byte length correctly and keep runs ≤1764; if staff, update the threshold at `course - 1`; if download, keep the emblem flag and 0x200 emblem consistent; the date year is an offset from 2000 and 0x2F is a 0–3 cup-rank tier.

Mission edit: change `missionTable.mtbl` and the `mission.mr` record together; keep the mission id, course id and `mrNN_tool.nkm` name aligned; update task-specific target/object fields; keep `time_limit` and `target_time` in 60 Hz frames and treat `rank_delta_scale` as a rank coefficient; use camera 0 or 1 only; keep PRM sidecars named after their boss models; remember that mission ranks live in the save `NKMR` block, not in `mission.mr`.

Rank edit: keep `ranktimeGP.rtt` course ids unique and matched to the selected class column; the table order is the retro half of the cup order followed by the nitro half, but the loader searches by id so order is not semantic; check `rankpoint.rpt` row formulas against driver count and team mode; do not expect mission mode to read either table.

Item edit: keep the file block count, each two-byte block header and each payload length consistent; remember the payload is item-config-major and the cells are weights, not item ids; check item-box `settings[1]` and `settings[2]` (row `id − 1` in block 6, 0 = place table). The loader switch proves the block roles: blocks 0/1 are the GP/TA/mission default and alternate tables, block 6 is the shared override (and the balloon-battle enemy table), block 4 is the battle override and VS non-enemy table, block 5 is the balloon-battle non-enemy and VS enemy table, and blocks 7/8 are the three-row shine-battle tables. Blocks 2, 3, 9 and 10 are skipped by every mode.

Parameter edit: keep the record stride and count for the chosen archive; use the AI course/class/CPU index formula; keep the 0xE0 offset stride; use the 152-byte physical struct for the 7600-byte file; the 148-byte row is the 152 map minus the 0x34 word and the 144-byte row is the inferred map minus the 0x08 and 0x34 words.

## Object group profiles (`grpconf.tbl`)

Two stock files share one 16-byte record layout:

| File | Records | Bytes |
|---|---|---|
| `MainRace_arc/MapObj/grpconf.tbl` | 133 | 2128 |
| `Main/MapObj_arc/grpconf.tbl` | 91 | 1456 |

| Offset | Size | Field |
|---|---|---|
| 0x00 | 2 | NKM object id |
| 0x02 | 2 | model kind: 0 none, 1 2D billboard, 2 3D model |
| 0x04 | 2 | near clip, whole world units |
| 0x06 | 2 | far clip, whole world units |
| 0x08 | 2 | collision shape: 0 none, 1 sphere, 2 spheroid, 3 cylinder, 4 box, 5 custom |
| 0x0A | 2 | width, whole world units |
| 0x0C | 2 | height |
| 0x0E | 2 | depth |

The CTables key the rows by `MkdsMapObject`, not by table index. The loader scans the table by object id (not row index) and applies the near/far pair to the visibility path, `model_kind >= 2` to the 3D flag, and the shape/width/height/depth triple to the collision config. `9999` in either distance means "do not clip by distance". Header: `include/nitro/mkds/race/grpconf.h`.

## Kart appearance matrix (`kart_appear.ktbl`)

`Main2D_arc/kart_appear.ktbl` is 487 bytes: a 6-byte `NKKT` header (`u8 kart_count = 37`, `u8 character_count = 13`) followed by one byte per cell, kart-major:

```
level = data[6 + kart_id * 13 + character_id]
```

`0` means the character can never use that kart. A non-zero value is the required kart unlock level: the menu shows the choice when `level <= current_unlock_level`, and the save writer computes the maximum and minimum levels from the connected profiles. Level 1 is the free/default kart, levels 2–4 are progressively later unlocks. Row 36 is the Shy Guy-only kart. Header: `include/nitro/mkds/race/kartappear.h`; helper `mkds_kart_appearance_level()`.

## Emblem editor stamp table (`emblem_s.tbl`)

`Scene/Edit_arc/emblem_s.tbl` is 410 bytes:

| Offset | Size | Field |
|---|---|---|
| 0x00 | 4 | record count (50) |
| 0x04 | 400 | 50 records of 8 bytes |
| 0x194 | 6 | zero trailer |

Each 8-byte record stores `int16 x`, `int16 y`, `u16 kind`, `u16 stamp_id`. Stock rows put `x`/`y` on the 256×192 screen, store kind 1 and number the stamps 1–50. No stock string names this file and no known consumer reads it, so the coordinates and stamp index are inferred from the value shapes; the header marks the kind field as unproven. Header: `include/nitro/mkds/files/emblemtable.h`.

## DWC utility archive (`dwc/utility.bin`)

The file is a NARC-less Nitro archive, not a record table:

| Offset | Size | Field |
|---|---|---|
| 0x00 | 4 | FNT offset (0x10) |
| 0x04 | 4 | FNT size (0x1498) |
| 0x08 | 4 | FAT offset (0x14C0) |
| 0x0C | 4 | FAT size (0x0AB0, 342 entries) |
| 0x10 | … | Nitro FNT |
| 0x14C0 | … | Nitro FAT |

FAT entries are `{u32 start, u32 end}` relative to the file start. The FNT is the normal Nitro directory tree: 8-byte directory heads, sub-tables with `0x80|length` directory entries carrying `F001..FFFF` ids, and plain file entries. Header: `include/nitro/dwc.h`; reader/validator: `tools/dwc_utility.py` (`list`, `verify`, `extract`). The two stock copies are byte-identical.

## Header coverage and remaining gaps

`include/nitro/mkds_race.h` is the umbrella for `include/nitro/mkds/save/ghost.h`, `mission.h`, `prm.h`, `ranktime.h`, `rankpoint.h`, `itemslots.h`, `kartparams.h`, `staffghost.h`, `grpconf.h`, `kartappear.h`, `emblemtable.h`, `misc.h`, `time.h` and `ids.h`. Those headers declare `MkdsGhostHeader`, `MkdsGhostInputRun`, `MkdsGhostInputHeader`, `MkdsMissionHeader`, `MkdsMissionEntry`, `MkdsMissionMenuHeader`, `MkdsBossParamPrefix`, `MkdsRankTimeHeader`, `MkdsRankTimeCourse`, `MkdsRankPointHeader`, `MkdsRankPointRow`, `MkdsItemSlotBlockHeader`, `MkdsStaffGhostTimes`, `MkdsObjectGroupConfig`, `MkdsKartAppearanceHeader`, `MkdsEmblemStampPlacement`, `MkdsKartPhysRow144`, `MkdsKartPhysRow148`, `MkdsKartPhysRow152`, the other kart row types and the emblem/builddate types, with `_Static_assert` guards for every proven size and offset. The DWC archive envelope lives in `include/nitro/dwc.h`.

The largest remaining gaps are the full PRM field map (the block is loaded into the boss at `+0xA0`, but the boss update stubs do not name all offsets) and the label-renderer effect of the 0x2F cup-rank tier. The mission menu byte has no known consumer, and tasks 8–10 have no stock records; task 10 is only checked by the lap-count HUD. Ghost layout, timing, input, staff indexing, mission frame units, rank-time order and formulas, rank-point rows, item weights, item-box override selection, and the 152/148/144 physical relationship are now proven or explicitly marked inferred.
