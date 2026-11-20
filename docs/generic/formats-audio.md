# Nitro sound containers (SDAT family)

> **Project:** Mario Kart DS Modding Trove · **Licence:** MIT · **Code:** `include/nitro/sdat.h`

The stock MKDS sound archive is `data/Sound/sound_data.sdat`: a 3,321,568-byte SDAT containing 76 SSEQ, 5 SSAR, 99 SBNK and 104 SWAR files, plus 10 player and 2 group INFO records. There is no SYMB block. This note records the block map, field offsets and corpus counts needed to walk that archive, and marks the parts that the corpus never exercises.

The container, sound-file header and the SSEQ/SSAR/SBNK/SWAR/SWAV record layouts are the standard Nitro layout: see GBATEK "DS Sound Files - SDAT", the ndspy `soundArchive`/`soundBank`/`soundWaveArchive`/`soundWave` modules, and the Mario Kart Toolbox `HaroohiePals.Nitro.NitroSystem.Snd` classes. Those references agree on every offset below. The MKDS-specific observations are called out per section; the reusable declarations are in `include/nitro/sdat.h`.

All fields are little-endian. Every Nitro sound file starts with the same 0x10 header (`SndFileHeader`): `magic` (`4`), BOM `0xFEFF` (`uint16_t`), version `0x0100` (`uint16_t`), file size (`uint32_t`), header size `0x10` (`uint16_t`), block count (`uint16_t`). SSEQ, SSAR, SBNK, SWAR and SWAV each carry exactly one `DATA` block, whose 8-byte header (`SndDataBlockHeader`) is `magic` (`4`) plus a size that includes the header.

## SDAT container

| Offset | Field |
|---|---|
| 0x00 | `SDAT` |
| 0x04 | BOM `0xFEFF` (`uint16_t`) |
| 0x06 | version `0x0100` (`uint16_t`) |
| 0x08 | file size (`uint32_t`) |
| 0x0C | header size `0x40` (`uint16_t`) |
| 0x0E | block count (`uint16_t`; 3 without SYMB, 4 with) |
| 0x10 | four `(offset, size)` pairs (`SdatBlockRef`, 8 bytes each) |
| 0x30–0x3F | zero; the block table ends at 0x30 but the header declares 0x40 |

The four pairs are SYMB, INFO, FAT and FILE in that order (`SDAT_BLOCK_*`). In the stock file:

| Block | Offset | Size |
|---|---|---|
| SYMB | 0 | 0 |
| INFO | 0x40 | 0xFB0 |
| FAT | 0xFF0 | 0x11CC |
| FILE | 0x21BC | 0x328D24 |

INFO and FAT are contiguous; FILE follows FAT without padding. The FILE block's own size runs to end of file (0x21BC + 0x328D24 = 0x32AEE0).

## SYMB block

Also called the symbol block: eight string tables, one per INFO section, offsets relative to the SYMB block. The header (`SdatSymbHeader`) is `SYMB` (`4`), size (`4`), eight record offsets (`uint32_t`), then 0x18 reserved bytes, so it is 0x40 bytes. A record (`SdatSymbRecord`) is a `uint32_t` count followed by `count` `uint32_t` string offsets; offset 0 means the entry is unnamed. Record 1 (SEQARC) instead stores `count` pairs of `(name offset, sub-record offset)` (`SdatSymbArchiveEntry`), where the sub-record is a normal record for the sequences inside that archive.

The stock archive has no SYMB block, so nothing above is exercised here. This is why MKDS sequence and bank names do not appear in the file; tools that need names must invent them from the FAT order, as the extracted tree does (`seq_0000`, `bank_0000`, `waveArc_0000`).

## INFO block

Header (`SdatInfoHeader`): `INFO` (`4`), size (`4`), eight `uint32_t` section offsets, then 0x18 zero bytes. Section and record offsets are relative to the start of the INFO block, not to the file, and the first section normally starts at 0x40. A section (`SdatInfoTable`) is a `uint32_t` count followed by `count` `uint32_t` record offsets; a zero record offset means the slot is absent.

| Section | Index | Stock offset | Stock count |
|---|---|---|---|
| SEQ | 0 | 0x40 | 76 |
| SEQARC | 1 | 0x504 | 5 |
| BANK | 2 | 0x530 | 99 |
| WAVEARC | 3 | 0xB64 | 104 |
| PLAYER | 4 | 0xEA8 | 10 |
| GROUP | 5 | 0xF24 | 2 |
| STREAM PLAYER | 6 | 0xFA8 | 0 |
| STREAM | 7 | 0xFAC | 0 |

### SEQ record

`SdatSeqInfo`, 12 bytes: file id (`uint32_t`), bank (`uint16_t`), volume (`uint8_t`), channel priority (`uint8_t`), player priority (`uint8_t`), player (`uint8_t`), reserved (`uint16_t`). ndspy splits the leading dword into file id (`uint16_t`) plus an unknown `uint16_t`; the high half is zero in all 76 stock records, so treat it as a 32-bit file id.

Observed: bank ids 49–98, volumes 75–127, channel and player priority both 64 in every record, player 8 in 72 records and 9 in the other 4.

### SEQARC record

`SdatSeqArcInfo`, 4 bytes: the file id of the SSAR. Per-sequence data lives inside the archive, not here.

### BANK record

`SdatBankInfo`, 12 bytes: file id (`uint32_t`) plus four `int16_t` wave archive slots, `-1` for unused. The slots are indices into the WAVEARC section, not FAT file ids: stock values run 0–103 with 104 wave archives, while the files themselves are ids 180–283.

### WAVEARC record

`SdatWaveArcInfo`, 4 bytes: the low 24 bits are the file id (`sdat_wave_arc_file_id`), the high byte is a "load individually" flag (`sdat_wave_arc_load_individually`). All 104 stock records have the flag clear and file ids 180–283.

### PLAYER record

`SdatPlayerInfo`, 8 bytes: max sequences (`uint16_t`), channel allocation mask (`uint16_t`), heap size (`uint32_t`). Mask 0 means "allocate channels automatically". Stock: ten records with max sequences 1–3, mask 0 and heap 0 everywhere. Archive setup copies the first two fields into the runtime player slots, so records 8 and 9 configure the two dedicated players (see "Player, volume and priority path").

### GROUP record

`SdatGroupInfo` (a `uint32_t` count) followed by `count` `SdatGroupItem` entries of type (`uint8_t`), load flags (`uint8_t`), reserved (`uint16_t`) and index (`uint32_t`). Types are 0 = SSEQ, 1 = SBNK, 2 = SWAR, 3 = SSAR; the load flags bit `1 << type` requests that kind of member.

Stock group 0 has 6 items and group 1 has 8. Group 0: SSAR 2 (flags 8), SSEQ 73 and 62 (flags 7), SBNK 45, 46, 47 (flags 6). Group 1 adds SSEQ 1 and SBNK 1. This is consistent with the flag model — a sequence entry asks for its bank and waves, a bank entry asks for its waves, and the SSAR entry asks only for itself. Type 2 never appears.

### STREAM PLAYER and STREAM records

Both tables are empty in the stock archive. For completeness: a stream player record begins with a `uint8_t` channel count and a 16-byte channel list (`SdatStreamPlayerInfo`, 17 bytes of fields, then padding); a stream record is 12 bytes (`SdatStreamInfo`) — file id (`uint32_t`), volume, player priority, player, flags, then 4 reserved bytes. Proven: because INFO records are addressed by the section's offset table, no record has a required stride; the 17-byte body and the 12-byte record are the fixed parts. No stream is created in this build, so the field order is unexercised.

## FAT and FILE blocks

The FAT header (`SdatFatHeader`) is `"FAT "` (`4`, trailing space), size (`4`), count (`4`). Each entry (`SdatFatEntry`) is 16 bytes: offset (`uint32_t`), size (`uint32_t`), 8 reserved bytes. The FILE block header (`SdatFileHeader`) has the same 0x0C layout (`FILE`, size, count) and its file data starts at the next 0x20 boundary after the header.

Stock: 284 entries (ids 0–75 SSEQ, 76–80 SSAR, 81–179 SBNK, 180–283 SWAR), first file at 0x21E0 (FILE + 0x24 after alignment), every offset 0x20-aligned, and each entry's size is the unpadded file size — the next offset minus this offset is the size rounded up to 0x20. The last file ends at 0x32AEC4 with 0x1C bytes of trailing padding to end of file. This matches the ndspy default of 0x20 alignment with sizes that exclude padding.

## SSEQ sequence

| Offset | Field |
|---|---|
| 0x00 | `SndFileHeader` (`SSEQ`, `0xFEFF`, `0x0100`, size, `0x10`, 1) |
| 0x10 | `DATA` + block size (`SndDataBlockHeader`) |
| 0x18 | data offset (`uint32_t`, `SseqDataBlock`) |
| 0x1C | SMFT command stream, to end of file |

All 76 stock sequences have data offset 0x1C and a DATA size of file size minus 0x10, so the stream runs to EOF with no trailing block. The stream itself is the standard SMFT event format and is not decoded in this note.

## SSAR sequence archive

| Offset | Field |
|---|---|
| 0x00 | `SndFileHeader` (`SSAR`, …) |
| 0x10 | `DATA` + block size |
| 0x18 | data offset, relative to the file (`uint32_t`, `SsarDataBlock`) |
| 0x1C | entry count (`uint32_t`) |
| 0x20 | entries, 12 bytes each (`SsarEntry`) |

An entry is offset (`uint32_t`, relative to the data offset), bank (`uint16_t`), volume, channel priority, player priority, player (four `uint8_t`) and 2 reserved bytes. The entry table always ends exactly at the data offset, so the archived streams fill the rest of the file.

Stock: five archives with 596, 346, 182, 24 and 8 entries (1156 total), data offsets 0x1C10, 0x1058, 0x8A8, 0x140 and 0x80, and 1043 distinct offsets — 113 entries alias an earlier stream (58, 45 and 10 in the first three archives). Entry banks span 0–48. The archived payloads are bare SMFT streams with no SSEQ header, which is why the extracted tree has to synthesise one.

Known gap: entry lengths are not stored. A reader must terminate on the SMFT end-of-track token (`0xFF`) or bound the read by the next-higher entry offset.

## SBNK instrument bank

| Offset | Field |
|---|---|
| 0x00 | `SndFileHeader` (`SBNK`, …) |
| 0x10 | `DATA` + block size |
| 0x18–0x37 | 0x20 zero bytes; the runtime wave-archive link is not serialised |
| 0x38 | instrument count (`uint32_t`, `SbnkDataBlock`) |
| 0x3C | instrument entries, 4 bytes each (`SbnkInstrumentEntry`) |

An entry is type (`uint8_t`), payload offset (`uint16_t` stored at +1, unaligned, read it with `sbnk_entry_offset`), 1 reserved byte. The offset is an absolute file offset: in every stock bank the first payload begins exactly at the end of the entry table, and payloads are packed back to back.

Payloads, addressed by the entry type:

| Type | Payload |
|---|---|
| 0 | none (empty slot, offset 0) |
| 1–15 | `SbnkNote`, 10 bytes: wave (`uint16_t`), wave archive slot (`uint16_t`), pitch, attack, decay, sustain, release, pan (six `uint8_t`) |
| 0x10 | `SbnkRangeHeader` (first key, last key) then `last - first + 1` `SbnkTypedNote` (12 bytes: type, 1 reserved, `SbnkNote`) |
| 0x11 | `SbnkRegionalHeader` (8 last-key bytes) then one `SbnkTypedNote` per non-zero key byte |

The second `uint16_t` of a note is a slot 0–3 into the bank's INFO wave archive list, not a global archive id; the first `uint16_t` is the SWAV index inside that archive. Types 1–15 share one layout; 2 and 3 are the PSG square and noise variants.

Stock: 99 banks and 6378 slots — 5553 empty, 718 type 1 (PCM), 1 type 2 (PSG square), 43 type 0x10 and 63 type 0x11. The 1766 notes inside the range and regional instruments are all type 1. Payload areas end 0–3 bytes before EOF (4-byte padding). Types 3, 4 and 5 never appear.

## SWAR wave archive

| Offset | Field |
|---|---|
| 0x00 | `SndFileHeader` (`SWAR`, …) |
| 0x10 | `DATA` + block size |
| 0x18–0x37 | 0x20 zero bytes, same reserved area as SBNK |
| 0x38 | wave count (`uint32_t`, `SwarDataBlock`) |
| 0x3C | absolute file offsets, `uint32_t` per wave |

Each offset points at a 12-byte SWAV parameter followed immediately by that wave's samples; waves are packed contiguously, so the next offset is the current parameter plus 0x0C plus the sample byte count. In 103 of the 104 stock archives the first wave starts exactly at the end of the offset table; the remaining archive has zero waves.

Stock: 104 archives holding 864 waves, between 0 and 90 per archive. As with SBNK, the offsets are absolute file offsets, not relative to the DATA block.

## SWAV wave

| Offset | Field |
|---|---|
| 0x00 | format (`uint8_t`) |
| 0x01 | loop flag (`uint8_t`) |
| 0x02 | sample rate in Hz (`uint16_t`) |
| 0x04 | sample-timer period (`uint16_t`, ticks at 16,756,991 Hz) |
| 0x06 | loop start (`uint16_t`, 4-byte units) |
| 0x08 | loop length (`uint32_t`, 4-byte units) |
| 0x0C | samples |

`SwavParam` is this 12-byte structure. Sample bytes are `(loop_start + loop_length) * 4` (`swav_sample_bytes`). `loop_start > 0` even in unlooped waves, so it is always the offset of the loop point and the total sample count is always loop start plus loop length. Formats are 0 = PCM8, 1 = PCM16, 2 = IMA-ADPCM.

A standalone SWAV file wraps the same structure: file header at 0x00, `DATA` at 0x10, parameter at 0x18, samples at 0x24 (`SwavDataBlock`), DATA size 0x14 + sample bytes. The stock SDAT stores no standalone SWAV entries; the extracted tree writes one per wave with a synthesised wrapper.

Stock: all 864 waves are ADPCM (format 2), 421 looped and 443 unlooped, with 169 distinct sample rates — most commonly 8000 (129), 16000 (106), 32000 (100) and 11025 (60) Hz, but also values such as 22000 and 32301 Hz. `time` equals `16756991 / sample_rate` rounded down in 861 waves. The normal rule, proven for 861 waves, is truncation, not rounding to nearest: 8000 Hz stores 2094 (not 2095), 32000 Hz stores 523 (not 524) and 22050 Hz stores 759 (not 760). The three exceptions are stale values rather than a second rounding rule: wave 84 of archives 0 and 97 at 11053 Hz store 1515, and wave 0 of archive 21 at 16004 Hz stores 1046. The 16004 Hz rate occurs six times, five with 1047 and one with 1046, so the same rate field maps to two timers and `time` is not a deterministic function of `sample_rate`. Their stored timers (1046 and 1515) imply rates of about 16020 and 11061 Hz, so the rate was edited after the timer was written. No single clock reproduces all three (a 16745000 clock explains the 16004 Hz wave but not the two 11053 Hz ones), and the only copy of the 16756991 constant in the ARM9 is a pool word in a playback-timer path at `0x212D034`, so no ARM9 code recomputes a wave timer from its rate and the stored value reaches the driver unchanged. No PCM8 or PCM16 wave exists in the archive, so the non-ADPCM paths are untested here.

## MKDS usage and configuration

This part is specific to the stock AMCP build (`rom/mkds_stock.nds`). Sequence numbers here are INFO SEQ indices (0–75), not FAT ids; for SSEQ the two happen to coincide because the sequences occupy FAT ids 0–75, while SSAR entries (the mission and result jingles) are indexed inside their archive instead. Bank numbers are INFO BANK indices; the bank file id is `81 + index`. Wave archive numbers are INFO WAVEARC indices; the SWAR file id is `180 + index`.

Two ARM9 tables drive playback. The 53-record sequence table lives in rodata at `0x0215316C`; each record is four bytes:

| Offset | Field |
|---:|---|
| 0 | start policy (`2` = start as soon as the scene installs the BGM context, `0xFF` = do not start yet) |
| 1 | sequence id (`0xFF` = none) |
| 2 | preload bank A (`0xFF` = none) |
| 3 | preload bank B (`0xFF` = none) |

The two preload bytes name extra banks that the game's preload helper loads next to the sequence, so a record names one sequence plus up to two banks to keep resident; in this build the preload banks are always small sound-effect banks (0–48), never a music bank (49–98). The policy byte `3` is tested by the player-start helpers but no stock record uses it.

The second table is the start-fanfare/result set at `0x0216CBD8`: six 24-byte records of six sequence ids, addressed by race mode, plus one special record at `0x0216CBC0`.

### Scene → sequence

`scene_getMusicData` resolves the current scene to a sequence-table record; a separate per-scene override can replace or add a sequence.

| Scene id | Scene | Table index | Sequence | Notes |
|---:|---|---:|---:|---|
| 0 | title | 51 | none | override supplies sequence 0 |
| 1 | menu | 50 | 1 | the menu scene owns a target field with mode, character, course, mission and ghost select values, so those screens stay in this scene and keep sequence 1 |
| 2 | race | — | see course table | depends on display mode |
| 3 | emblem | 48 | 4 | |
| 4 | menu 2 | 5 | 13 | |
| 5 | test | 42 | 66 | unused in retail |
| 6 | wireless menu | 46 | 2 | a boot-state halfword selects "none" instead |
| 7 | options | 48 | 4 | |
| 8 | records | 47 | 6 | |
| 9 | logo | 49 | 75 | 188-byte jingle, stopped at frame 93 |
| 10 | result | 41 | 63 | sequence replaced by the rank-dependent id below |
| 11 | nickname | 48 | 4 | |
| 12 | Wi-Fi menu | 45 | 3 | preloads bank 36 |
| 13 | ghost | 46 | 2 | |
| 14 | keyboard | 48 | 4 | |
| 15 | ending | 51 | none | staff roll runs as a race display mode instead |

The per-scene override (`scene_getSceneMusicOverride`) forces sequence 4 for options and nickname, sequence 0 for title, and sequence 69 or 70 for the staff-roll display mode. Mission select (menu target 3) is the one menu sub-screen that suppresses the menu theme: it sets the start policy to `0xFF` so sequence 1 is not started.

### Course → sequence

For a race in the default or replay display mode the course id selects a record through `GetSequenceTableIndexAndData`. The table below lists every course id the resolver knows; `Preload` is the record's two bank bytes, `Wave archives` are the sequence's INFO BANK slots as `index → SWAR file id`, `INFO vol` is the SDAT SEQ volume and `Runtime vol` is the value the game actually passes to the player (see the volume note below).

| Course | Seq | Bank | Preload | Wave archives | INFO vol | Runtime vol | Player |
|---:|---:|---:|---|---|---:|---:|---:|
| 1 | 33 | 50 | 26 | 50→230, 80→260 | 98 | 105 | 8 |
| 9 | 34 | 56 | — | 56→236, 80→260 | 127 | 105 | 8 |
| 10 | 22 | 69 | 26 | 68→248, 80→260 | 127 | 106 | 8 |
| 11 | 30 | 57 | 31 | 57→237, 80→260 | 127 | 110 | 8 |
| 12 | 27 | 74 | — | 73→253, 80→260 | 112 | 105 | 8 |
| 13 | 26 | 73 | — | 72→252, 80→260 | 125 | 118 | 8 |
| 14 | 33 | 50 | 29 | 50→230, 80→260 | 98 | 105 | 8 |
| 15 | 23 | 70 | 18 | 69→249, 80→260 | 92 | 105 | 8 |
| 16 | 31 | 58 | 24 | 58→238, 80→260 | 127 | 105 | 8 |
| 17 | 39 | 83 | 25 | 82→262, 80→260 | 85 | 105 | 8 |
| 18 | 21 | 68 | 19 | 67→247, 80→260 | 92 | 105 | 8 |
| 19 | 18 | 62 | 27 | 60→240, 80→260 | 120 | 105 | 8 |
| 20 | 74 | 49 | 16 | 49→229, 80→260 | 106 | 105 | 8 |
| 22 | 16 | 55 | 17 | 55→235 | 127 | 105 | 8 |
| 23 | 32 | 79 | 32 | 77→257, 80→260 | 90 | 105 | 8 |
| 24 | 36 | 77 | 23 | 75→255, 80→260 | 107 | 105 | 8 |
| 25 | 74 | 49 | 26 | 49→229, 80→260 | 106 | 105 | 8 |
| 26 | 20 | 67 | 29 | 66→246, 80→260 | 94 | 105 | 8 |
| 27 | 38 | 82 | 20 | 81→261, 80→260 | 110 | 105 | 8 |
| 28 | 17 | 59 | 21 | 59→239, 80→260 | 105 | 105 | 8 |
| 29 | 41 | 85 | 48 | 84→264, 80→260 | 108 | 105 | 8 |
| 30 | 37 | 81 | 24 | 79→259, 80→260 | 75 | 105 | 8 |
| 31 | 15 | 51 | 18 | 51→231, 80→260 | 127 | 127 | 8 |
| 32 | 40 | 84 | 30 | 83→263, 80→260 | 113 | 105 | 8 |
| 33 | 19 | 65 | 22 | 64→244, 80→260 | 110 | 105 | 8 |
| 34 | 19 | 65 | 28 | 64→244, 80→260 | 110 | 105 | 8 |
| 35 | 24 | 71 | 26 | 70→250, 80→260 | 127 | 110 | 8 |
| 36 | 29 | 78 | 24 | 76→256, 80→260 | 125 | 105 | 8 |
| 37 | 26 | 73 | 33 | 72→252, 80→260 | 125 | 118 | 8 |
| 38 | 35 | 66 | 23 | 65→245, 80→260 | 127 | 105 | 8 |
| 39 | 25 | 72 | 26 | 71→251, 80→260 | 100 | 105 | 8 |
| 40 | 28 | 75 | — | 74→254, 80→260 | 115 | 105 | 8 |
| 41–47 | 43 | 89 | 43, 34 | 88→268, 80→260 | 112 | 105 | 8 |
| 48–51 | 45 | 88 | 34 | 87→267, 80→260 | 115 | 105 | 8 |
| 52 | 66 | 94 | — | 93→273, 80→260 | 112 | 105 | 8 |

Course ids 41–47 are the battle arenas and all share sequence 43; 48–51 are the mission stages and share sequence 45; 52 is the award cutscene and uses sequence 66. Ids 53 and 54 (staff roll) are not usable through this table: 53 maps to the empty record 51 and 54 falls through to the out-of-range default; the scene override supplies 69/70 instead. Ids 2–8 and 21 are absent from the resolver; they are unused course slots, which matches the 32 ghost-bearing ids (1, 9–20, 22–40).

Four themes are shared: sequence 33 by courses 1 and 14, sequence 19 by 33 and 34, sequence 26 by 13 and 37, and sequence 74 by 20 and 25. Every other race course has its own sequence. All race sequences use player 8, player priority 64 and channel priority 64.

Proven: one stock sequence is unreachable. Sequence 5 (bank 91, 1880 bytes) appears in no scene record, course record or fanfare record; the sequence ids the game writes as immediates are 0, 4, 42, 44, 62, 69, 70, 71, 72 and 73; and the only group that names a sequence names 73, 62 and 1. It is unused data, not a mapping that has been missed.

### Display-mode and race-mode variants

The race scene keys on the display mode, not only on the course:

| Display mode | Value | Sequence |
|---|---:|---|
| default, replay | 0, 2 | course table |
| title/demo | 1 | none |
| course intro | 3 | 8, 9, 10 or 14 (by course class) with the course's preload bank |
| battle intro | 4 | 13 |
| award | 5 | 66 |
| staff roll | 6 | none; override supplies 69 or 70 |

The course-intro fanfare is chosen by course id: 14, 20, 25 and 33 use sequence 8, course 34 uses sequence 10, a boss battle uses sequence 14, and every other course uses sequence 9. The intro record is then patched with the course record's byte 2 in place of its own preload bank, which is why the intro record and the course record have to be edited together if the intro's instrumentation is changed.

Mission races override the main sequence through the mission record: mission id 4 selects sequence 42, otherwise mission task 2 (laps) selects sequence 44, and specific mission ids add a preload bank (9/10 → 37, 17 → 41, 21 → 39, 50 → 38, 51 → 40, with bank 34 as the second preload). Both branches are live in retail data: the 91-record mission table (`data/Scene/Menu_arc/mission.mr`) has id 4 with task 6 and menu slot 37, and six records with task 2 (ids 7, 18, 30, 45, 46, 53), so sequences 42 and 44 are both reachable in normal play. Mission events then play SSAR 0 entries rather than SSEQ files: 471 for the coin target, 475/476 for gates, 477/478 for power slides or destroy targets, 480/481 for a boss, and 255 for "no jingle". Completing a coin mission additionally plays entry 478.

Two sequences are started globally rather than per course: sequence 62 replaces the BGM on the final lap, and sequence 73 is the star/invincibility theme, played on a second handle while every track of the main BGM is muted. Sequence 71 and 72 are the two "secret" jingles, started from a dedicated handler after reloading the sound heap.

### Goal, result and start-fanfare sets

The six records at `0x0216CBD8` are indexed by race mode (0 GP, 1 TA, 2 battle, 3 VS, 4 mission, 5 Wi-Fi) and hold six sequence ids each; the record index is the race-mode field. Every slot has a call site, so the roles are proven rather than inferred: the finish-line handler asks the race code for an outcome code (0, 1 or 2) and starts slot 0, 1 or 2; the result handler starts slot 3 for outcomes 0 and 1 and slot 4 for outcome 2; the start-fanfare accessor returns slot 5, and its single caller starts it from the race-start path. Courses 20, 25 and 34 additionally start a course-specific SSAR 0 entry at the finish (261/262, 413/414 and 445/446 respectively, split by outcome).

| Race mode | Slots 0–2 | Slots 3–4 | Slot 5 |
|---:|---|---|---:|
| 0 GP | 46, 47, 48 | 56, 57 | 7 |
| 1 TA | 54, 53, 49 | 60, 61 | 11 |
| 2 battle | 50, —, 49 | 58, 61 | 12 |
| 3 VS | 50, 51, 49 | 58, 61 | 11 |
| 4 mission | 52, —, 49 | 59, 61 | 12 |
| 5 Wi-Fi | 50, 51, 49 | 58, 61 | 11 |
| mission id 9 special | 55, —, 49 | 59, 61 | 12 |

The result scene selects its own sequence from an eight-entry table instead: index 0 → 67, 1 → 68, 2 → 63, 3 → 65, 4 → 64, 5 → 63, 6 → 65, 7 → 64. The GP result screen also plays SSAR 0 entries 30, 31 and 32 for the last three ranks and entry 5 for one menu action.

### Bank and wave-archive wiring

A sequence's INFO record names its bank. That bank's INFO record has four slot fields holding wave-archive indices; each note in the bank's SBNK then selects a slot (0–3) and a wave index inside that archive. Stock music banks use only slots 0 and 1: slot 0 is the bank's own archive and slot 1 is the shared archive 80 (file id 260, 38 waves), which 48 of the 50 music banks reference. All 2485 notes in the 99 banks resolve to a valid wave, which confirms the slot interpretation end to end.

Proven: the bank load is implicit in the sequence loader: it reads the bank word at SEQ record +0x04 and calls the bank loader before it reads the SSEQ payload (`0x0212E708` → `0x0212E538`). The bank loader then walks the bank's four INFO slot words, skips `-1` and loads each referenced SWAR (`0x0212E538` → `0x0212E490`). A sequence load therefore always brings its own bank and that bank's wave archives.

The game's preload bytes are a separate, extra load. The scene path (`0x0210E888`) passes {sequence, bank A, bank B} to the three-field loader at `0x0210E33C`; that loader calls the sequence loader above, then calls the bank loader for A and for B explicitly unless the byte is `0xFF`. That is why no preload field ever names a music bank (49–98) and every BGM still plays: the music bank is already implied by the SEQ record, and the preload fields only add resident sound-effect banks.

A few banks are worth knowing when reading the table: the final-lap sequence 62 (bank 61) and the star sequence 73 (bank 76) use archive 80 only, the logo jingle 75 (bank 98) uses archive 101 only, and the staff-roll sequences 69/70 share bank 96 with archive 95 plus 80. The 50 music banks produce 47 distinct slot patterns, so there is no single "bank n uses archive n" rule; the course table above gives the exact pairs.

Sequence player numbers split the load: every music, menu and jingle sequence uses player 8 except the four fanfare/star sequences 7, 11, 12 and 73, which use player 9. This is what lets the star theme and the start fanfares play without stopping the main BGM.

### Player, volume and priority path

The sequence record's player byte is a sequence-player index. The sound library keeps 32 player slots of 36 bytes each (`0x0217D89C` in this build), and the start routine picks the slot from that byte and links the new handle into the slot's list. The per-player fields the start routine reads are at record offsets +0x06 (sequence volume), +0x07 (channel priority), +0x08 (player priority) and +0x09 (player); the bank at +0x04 is loaded first.

Players 8 and 9 exist like any other slot: the library's init loop clears all 32 and sets each slot's volume byte (+0x20) to 127, max-sequences (+0x18) to 1 and channel mask (+0x1C) to 0. The archive's INFO PLAYER records then override max-sequences and the mask for the records that exist: records 0–9 carry max-sequences of 1–3 with mask and heap size 0, so players 8 and 9 end up with one sequence each.

The game's global BGM-volume call is the only runtime writer of a slot's volume. It walks slots 1–7 only; the state-driven branch uses masks 0xFF and 0x7F, and the other branches pass 0xFFFF, but the loop bound excludes players 8 and 9 in every case. Slot 0 is also outside the loop, but no stock sequence names player 0.

Proven from the call site: the per-frame mix at `0x0212C19C` still includes them. For every sequence player it sums the owning slot's volume (+0x20), the sequence initial volume (+0x40), the game's per-sequence volume (+0x41) and the fader (+0x1C) through the 128-entry signed-decibel table at `0x02152CE4` (0 → -723, 127 → 0), clamps to [-723, 0] and sends the result to the ARM7 driver as that player's volume (`0x02020D80`). There is no player-number filter. Because the 8/9 slot term is 0 dB, their audible level is the handle volume — the INFO volume at start, then the 105+delta value the game sets immediately — but the mixer does apply the player term; the two are summed, not exclusive. The ARM7 image contains the matching clamp and dB-to-gain conversion at `0x0238429C`.

This also explains why the star theme does not fight the BGM for a player: it runs on player 9, the BGM on player 8, and the game mutes the BGM tracks instead of stopping them. The game watches the star through its handle (a non-null owning player means it is still playing), not through the player-volume path.

### Editing guidance

Replacing a course's music means changing the sequence id in the course record at `0x0215316C` and making sure the new sequence's INFO bank and wave archives can be resident. Replacing the SSEQ bytes at the same FAT id is simpler if the substitute already uses the same bank.

Volume: the INFO volume is copied into the handle at start (the `+0x40` term), and the race path then sets a second per-sequence volume with `min(105 + bonus, 127)` (the `+0x41` term, where the bonus is 1 for course 10, 5 for 11 and 35, 13 for 13 and 37 and 23 for 31, clamped). Both terms reach the mixer together with the player-slot term, so the INFO volume is still a live input: a replacement that must match the stock loudness has to keep the same pair, and lowering only the INFO value trims the level without cancelling the game's term. Non-race sequences started through the same helper also receive the 105 value, and the archive-wide player volume is forced to 127 for non-race scenes.

Priority: the INFO player priority and channel priority (64 everywhere) are applied by the start call and are not overridden by the game. When the chosen player already holds its maximum number of sequences, the acquire routine compares the new player priority with the incumbent's, refuses the new sequence if it is lower, and otherwise stops the incumbent and takes the slot — so a replacement that must beat another sequence on the same player needs a higher value. The star theme avoids that contest by running on player 9 and muting the BGM tracks.

Instruments: a sequence only sounds correct with the bank named in its own INFO record, and that bank only sounds correct with the wave archives in its own INFO record. Changing a sequence's INFO bank without changing its notes and the bank's archive slots produces the wrong instruments or silence; changing a bank's archive slot without moving the waves breaks the note references. If a replacement SWAR grows, the SDAT FAT padding, the file alignment (0x20) and the sound heap budget all change, so the sequence and its banks may fail to load rather than merely sound wrong.

What breaks if only one side changes: swapping a course's sequence id but not the intro fanfare leaves the course intro playing the old fanfare; swapping the sequence but not its bank leaves the preload table pointing at the old sound-effect bank; editing the INFO volume alone changes only one of the two volume terms, so it cannot make a replacement match a neighbour that also has the game's 105+delta value; and editing the shared archive 80 affects every bank that references it, not just one course.

### MKDS open questions

- The STREAM and STREAM PLAYER records are never instantiated. The only stream start path (`0x0212CCD4`, state at `0x0217DDD0`) receives its channel count and channel list as caller arguments; no function in the image indexes records through the INFO section 6/7 offsets at INFO+0x20/+0x24. The serialised field order is therefore unexercised, even though the 17-byte body is known.
- The mission-music rule keys on mission id 4 rather than on the mission task, while the second rule keys on task 2. A rebuilt mission table therefore changes the mission theme if that one id is moved; the reason id 4 is special is not recoverable from the code.

## Known unknowns

- No SYMB block exists in the stock archive; its layout is taken from the format specification and ndspy, not from MKDS data.
- The STREAM PLAYER and STREAM INFO tables are empty and the FAT has no STRM entry, so no stream is ever created. INFO records are addressed through the section's offset table, so no record has a required stride; a writer may space them freely. The stream-player body is 17 bytes (1 channel count + 16 channel bytes); the 24-byte spacing used by readers is a writer convention, not a ROM constant.
- Group type 2 (SWAR) is never used and load-flag values above 8 never appear, so only the sequence/bank/SSAR cases are confirmed.
- SSAR entries have no length field, and 113 of 1156 entries share a payload with an earlier entry. 62 of those aliases repeat the same bank, volume and priority (plain deduplication) while 51 differ in volume or player, so the builder reuses one stream with per-entry playback parameters; which entries alias is a content decision, not a format rule.
- SBNK types 3, 4 and 5 (PSG noise, direct PCM, null) and the empty-slot payload rules are unobserved; only types 0, 1, 2, 0x10 and 0x11 occur.
- The 0x20 reserved areas in SBNK and SWAR are zero on disk; their meaning (runtime wave-archive linkage) comes from the sound player, not from any serialised field.
