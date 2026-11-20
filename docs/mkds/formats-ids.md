# Shared MKDS identifier spaces

> **Project:** Mario Kart DS Modding Trove · **Header:** [`../include/nitro/mkds_ids.h`](../include/nitro/mkds_ids.h) · **Licence:** MIT

The same number is not the same course in every file. MKDS uses three course-like key spaces, and they must not be mixed.

| Space | Used by | Header enum |
|---|---|---|
| stage course id | NKM `STAG` | `MkdsStageCourseId` |
| mission course id | `mission.mr` | `MkdsMissionCourseId` |
| race course id | `ranktimeGP.rtt` and staff-ghost tables | `MkdsRaceCourseId` |
| staff-ghost slot | `staff_ghost_time.bin`, ghost headers | race course id − 1 |

## NKM stage course ids

These values are stored in the `STAG` record. They are sparse. Aliases in the archive names share one id.

| Id | Archive |
|---:|---|
| 0 | `StaffRollTrue_arc` |
| 1 | `mini_block_course_arc` |
| 2 | `test_circle_arc` |
| 3 | `luigi_course_arc` |
| 4 | `dokan_course_arc` |
| 5 | `test1_course_arc` |
| 6 | `donkey_course_arc` |
| 7 | `wario_course_arc` |
| 8 | `nokonoko_course_arc` |
| 9 | `mini_stage1_arc` |
| 10 | `mini_stage2_arc` |
| 11 | `mini_stage3_arc` |
| 12 | `mini_stage4_arc` |
| 13 | `mini_block_64_arc` |
| 14 | `mini_dokan_gc_arc` |
| 17 | `old_mario_gc_arc` |
| 18 | `old_yoshi_gc_arc` |
| 19 | `old_mario_sfc_arc` |
| 20 | `old_momo_64_arc`, `old_momo_64D_arc` |
| 21 | `old_baby_gc_arc` |
| 22 | `old_koopa_agb_arc` |
| 23 | `old_peach_agb_arc` |
| 24 | `old_luigi_gc_arc`, `old_luigi_gcD_arc` |
| 25 | `old_choco_64_arc` |
| 26 | `old_choco_sfc_arc` |
| 27 | `old_frappe_64_arc` |
| 28 | `old_hyudoro_64_arc` |
| 29 | `old_donut_sfc_arc` |
| 30 | `old_kinoko_gc_arc`; `MR_stage4_arc` also stores 30 |
| 31 | `old_luigi_agb_arc` |
| 32 | `old_noko_sfc_arc` |
| 33 | `old_sky_agb_arc` |
| 34 | `clock_course_arc` |
| 35 | `mansion_course_arc`, `mansion_courseD_arc` |
| 36 | `airship_course_arc` |
| 37 | `cross_course_arc`, `cross_courseD_arc` |
| 38 | `bank_course_arc` |
| 39 | `ridge_course_arc` |
| 40 | `mario_course_arc` |
| 41 | `garden_course_arc` |
| 42 | `desert_course_arc` |
| 43 | `town_course_arc` |
| 44 | `rainbow_course_arc` |
| 45 | `snow_course_arc` |
| 46 | `beach_course_arc`, `beach_courseD_arc` |
| 47 | `koopa_course_arc` |
| 48 | `stadium_course_arc` |
| 49 | `pinball_course_arc` |
| 53 | `MR_stage1_arc` |
| 54 | `MR_stage2_arc` |
| 55 | `MR_stage3_arc` |
| 57 | `Award_arc` |
| 58 | `StaffRoll_arc` |

Ids 15, 16, 50, 51, 52 and 56 do not occur in the stock NKM corpus.

## Race course ids

`MKDS_RACE_COURSE_*` names come from the English BMG banks, not from the NKM
archive names. `data/Main2D_us_arc/common.bmg` indices 45–76 and
`data/Scene/Ghost_us_arc/ghost.bmg` indices 19–50 list the same 32 cup courses
in cup order. The numeric ids are the race `CourseId` keys stored by
`ranktimeGP.rtt`, staff ghosts and the `kartcrsmat.bin`/`kartAIparam.bin`
course slots.

| Cup | Race 1 | Race 2 | Race 3 | Race 4 |
|---|---|---|---|---|
| Mushroom | 20 Figure-8 Circuit | 22 Yoshi Falls | 31 Cheep Cheep Beach | 18 Luigi's Mansion |
| Flower | 27 Desert Hills | 28 Delfino Square | 33 Waluigi Pinball | 24 Shroom Ridge |
| Star | 30 DK Pass | 17 Tick-Tock Clock | 25 Mario Circuit | 19 Airship Fortress |
| Special | 34 Wario Stadium | 26 Peach Gardens | 32 Bowser Castle | 29 Rainbow Road |
| Shell | 10 SNES Mario Circuit 1 | 11 N64 Moo Moo Farm | 13 GBA Peach Circuit | 14 GCN Luigi Circuit |
| Banana | 35 SNES Donut Plains 1 | 16 N64 Frappe Snowland | 12 GBA Bowser Castle 2 | 9 GCN Baby Park |
| Leaf | 15 SNES Koopa Beach 2 | 36 N64 Choco Mountain | 37 GBA Luigi Circuit | 38 GCN Mushroom Bridge |
| Lightning | 39 SNES Choco Island 2 | 23 N64 Banshee Boardwalk | 40 GBA Sky Garden | 1 GCN Yoshi Circuit |

The `MKDS_RACE_COURSE_MUSHROOM_1`-style names remain as aliases for the cup
position. Non-cup ids 2–8 and 21 have no English course name; they are exposed
as `MKDS_RACE_COURSE_NON_CUP_n`. Ids 41–54 in the 54-row `kartcrsmat.bin`
variant are table slots beyond the named 1–40 space and use
`MKDS_RACE_COURSE_EXTRA_n`.

## Mission course ids

These values are stored in `mission.mr` records. They are a different 1..50 space.

| Id | Archive |
|---:|---|
| 1 | `old_yoshi_gc_arc` |
| 9 | `old_baby_gc_arc` |
| 10 | `old_mario_sfc_arc` |
| 11 | `old_momo_64_arc` |
| 12 | `old_koopa_agb_arc` |
| 13 | `old_peach_agb_arc` |
| 14 | `old_luigi_gc_arc` |
| 15 | `old_noko_sfc_arc` |
| 16 | `old_frappe_64_arc` |
| 17 | `clock_course_arc` |
| 18 | `mansion_course_arc` |
| 19 | `airship_course_arc` |
| 20 | `cross_course_arc` |
| 22 | `bank_course_arc` |
| 23 | `old_hyudoro_64_arc` |
| 24 | `ridge_course_arc` |
| 25 | `mario_course_arc` |
| 26 | `garden_course_arc` |
| 27 | `desert_course_arc` |
| 28 | `town_course_arc` |
| 29 | `rainbow_course_arc` |
| 30 | `snow_course_arc` |
| 31 | `beach_course_arc` |
| 32 | `koopa_course_arc` |
| 33 | `pinball_course_arc` |
| 34 | `stadium_course_arc` |
| 35 | `old_donut_sfc_arc` |
| 36 | `old_choco_64_arc` |
| 37 | `old_luigi_agb_arc` |
| 38 | `old_kinoko_gc_arc` |
| 39 | `old_choco_sfc_arc` |
| 40 | `old_sky_agb_arc` |
| 42 | `mini_block_64_arc` |
| 43 | `mini_dokan_gc_arc` |
| 44 | `mini_stage1_arc` |
| 45 | `mini_stage2_arc` |
| 46 | `mini_stage3_arc` |
| 47 | `mini_stage4_arc` |
| 48 | `mini_block_course_arc`; `MR_stage1_arc` also uses 48 |
| 49 | `MR_stage2_arc` |
| 50 | `MR_stage3_arc` |

Ids 2–8, 21 and 41 do not occur in the menu mission table.

## Characters and cups

| Id | Character |
|---:|---|
| 0 | Mario |
| 1 | Luigi |
| 2 | Peach |
| 3 | Yoshi |
| 4 | Toad |
| 5 | Donkey Kong |
| 6 | Wario |
| 7 | Daisy |
| 8 | Waluigi |
| 9 | Dry Bones |
| 10 | Bowser |
| 11 | R.O.B. |
| 12 | Shy Guy (battle-only slot) |

Cup ids are 0 Mushroom, 1 Flower, 2 Star, 3 Special, 4 Shell, 5 Banana, 6 Leaf and 7 Lightning. They are the `MkdsCupId` enum.

## Karts

`kart_select.bmg` indices 6–41 give the 36 roster karts in `MkdsKart` order.
The names below are the US labels; `MKDS_KART_MARIO_A`-style aliases are kept
only where they still name the correct row.

| Id | Kart | Id | Kart | Id | Kart |
|---:|---|---:|---|---:|---|
| 0 | Standard MR | 12 | Standard TD | 24 | Standard DS |
| 1 | Shooting Star | 13 | Mushmellow | 25 | Light Dancer |
| 2 | B Dasher | 14 | 4-Wheel Cradle | 26 | Power Flower |
| 3 | Standard LG | 15 | Standard DK | 27 | Standard DB |
| 4 | Poltergust 4000 | 16 | Wildlife | 28 | Dry Bomber |
| 5 | Streamliner | 17 | Rambi Rider | 29 | Banisher |
| 6 | Standard PC | 18 | Standard WR | 30 | Standard WL |
| 7 | Light Tripper | 19 | Brute | 31 | Gold Mantis |
| 8 | Royale | 20 | Dragonfly | 32 | Zipper |
| 9 | Standard YS | 21 | Standard BW | 33 | Standard RB |
| 10 | Egg 1 | 22 | Hurricane | 34 | ROB-BLS |
| 11 | Cucumber | 23 | Tyrant | 35 | ROB-LGS |

Ids 36–49 are extra slots used by the 50-row parameter tables.

## Battle arenas

`menu.bmg` indices 0–5 and `common.bmg` indices 77–82 name the six battle
arenas in `MkdsBattleCourse` order: 0 Block Fort, 1 Pipe Plaza, 2 Nintendo DS,
3 Twilight House, 4 Palm Shore, 5 Tart Top.

## Modes and engine classes

Race modes are 0 Grand Prix, 1 Time Trials, 2 Battle, 3 Versus, 4 Mission, 5 Nintendo WFC. The English banks name the two battle modes Balloon Battle and Shine Runners, and the two Grand Prix groups Nitro Grand Prix and Retro Grand Prix. Engine classes are 0 50cc, 1 100cc, 2 150cc and 3 Mirror. CPU difficulty is 0 Easy, 1 Normal, 2 Hard; rule order is 0 In Order, 1 Random, 2 Choose. Ghost provenance is named My Ghost Data, Downloaded Ghost Data and Staff Ghost Data. The mode names, engine classes, rule values and ghost sources come from `menu.bmg`, `common.bmg`, `rule.bmg` and `ghost.bmg`.

## Scene/jingle sequence ids

| Id | Use |
|---:|---|
| 0 | title |
| 1 | menu |
| 2 | wireless menu |
| 3 | Wi-Fi menu |
| 4 | options / emblem / nickname / keyboard |
| 6 | records |
| 13 | menu 2 |
| 43 | battle |
| 45 | mission |
| 63–68 | result variants |
| 69, 70 | staff roll |
| 73 | star/invincibility |
| 75 | logo |

Course sequences use a different range and are listed in `formats-audio.md`.

## Other shared enums

`mkds_ids.h` also declares `MkdsCharacterId`, `MkdsCupId`, `MkdsEngineClass`, `MkdsRaceMode`, `MkdsMissionTask`, `MkdsSequenceId`, `MkdsKart`, `MkdsRaceCourse`, `MkdsBattleCourse`, `MkdsCpuMode`, `MkdsRuleOrder` and the `MKDS_MISSION_FLAG_*` bits. The `*Id` names are narrow typedefs (usually `uint8_t`/`uint16_t`) so packed structures keep their exact layout; the enum constants are the symbolic values. Use those names in new readers and mod sources instead of raw numbers.
