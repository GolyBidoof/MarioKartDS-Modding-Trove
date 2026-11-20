# MKDS course, collision and particle formats

> **Project:** Mario Kart DS Modding Trove · **Formats:** NKM, KCL, SPA · **Header:** [`../include/nitro/mkds_course.h`](../include/nitro/mkds_course.h) · **Licence:** MIT

These are the three files the course editor reads directly. The stock corpus has 124 `.nkm` files, 59 `.kcl` files and 3 `.spa` files. KCL is the standard Nitro collision layout and SPA is the standard JNLib particle layout; this note only records the MKDS variant, container offsets and observed values. Use GBATEK and Mario Kart Toolbox (`HaroohiePals.KCollision`, `HaroohiePals.Nitro.JNLib.Spl`) as the primary references for the shared parts.

All multi-byte values are little-endian. FX32 is a signed 20.12 fixed-point number; an FX32 value of 0x1000 is 1.0.

## NKM — course map

NKM is the course map container. The file starts with a small header; the rest is a sequence of tagged sections. Section offsets are relative to `header_size`, not to the start of the file.

| Offset | Size | Field |
|---:|---:|---|
| 0x00 | 4 | `NKMD` |
| 0x04 | 2 | version |
| 0x06 | 2 | header size, `8 + 4 * section_count` |
| 0x08 | 4 × n | section offsets |

Observed versions are 30, 32, 34, 36 and 37. Version 37 is the common retail/final version. Older versions omit some fields or sections, notably `KTPC` and `KTPM`.

### Sections

Every section except `STAG` begins with a four-byte tag and a 32-bit entry count. `STAG` is a single 0x2C-byte record including its tag and has no count field.

| Tag | Entries | Record | Purpose |
|---|---|---:|---|
| `OBJI` | objects | 0x3C | map-object instances: position, rotation, scale, object id, path id, settings, clip areas |
| `PATH` | paths | 4 | path index, loop flag and point count |
| `POIT` | points | 0x14 | path points: FX32 position, index, duration, two unknown fields |
| `STAG` | 1 | 0x2C | stage/course settings, laps, fog and lighting |
| `KTPS` | start points | 0x1C | kart start position/rotation and index |
| `KTPJ` | jugem points | 0x20 | respawn point and linked enemy/item points |
| `KTP2` | 2D kart points | 0x1C | position/rotation used by 2D course views |
| `KTPC` | cannon points | 0x1C | cannon position/rotation and next `MEPO` index |
| `KTPM` | mission points | 0x1C | mission start position/rotation and index |
| `CPOI` | checkpoints | 0x24 | checkpoint segment, sin/cos, distance and respawn data |
| `CPAT` | checkpoint paths | 0x0C | checkpoint range and next/previous links |
| `IPOI` | item points | 0x14 | item box position, radius and recalculation index |
| `IPAT` | item paths | 0x0C | item path range and next/previous links |
| `EPOI` | enemy points | 0x18 | enemy position, radius and four int16 settings |
| `EPAT` | enemy paths | 0x0C | enemy path range and next/previous links |
| `MEPO` | mission enemy points | 0x18 | mission enemy position, radius, drifting and one unknown word |
| `MEPA` | mission enemy paths | 0x14 | mission enemy path range and links |
| `AREA` | areas | 0x48 | camera/collision trigger volumes, parameters and camera link |
| `CAME` | cameras | 0x4C | camera position, rotation, targets, FOV, path and timing |

Stock coverage: `OBJI`, `PATH`, `POIT`, `STAG`, `KTPS`, `KTPJ`, `KTP2`, `CPOI`, `CPAT`, `IPOI`, `IPAT`, `AREA` and `CAME` appear in all 124 files; `KTPC` in 120, `EPOI`/`EPAT` in 117, `KTPM` in 114, and `MEPO`/`MEPA` in 7. The missing sections correlate with the older versions.

The header defines the fixed-size records used by the stock sections: `NkmObjectEntry` (OBJI, 0x3C), `NkmPathEntry` (PATH, 4), `NkmPointEntry` (POIT, 0x14), `NkmStage` (STAG, 0x2C), `NkmKtpsEntry` (KTPS, 0x1C), `NkmKtpjEntry` (KTPJ v32+, 0x20), `NkmKtp2Entry` (KTP2, 0x1C), `NkmKtpcEntry` (KTPC, 0x1C), `NkmKtpmEntry` (KTPM, 0x1C), `NkmCpoiEntry` (CPOI, 0x24), `NkmCpatEntry` (CPAT, 0xC), `NkmItemPointEntry` (IPOI v34+, 0x14), `NkmPathLinkEntry` (IPAT/EPAT, 0xC), `NkmEnemyPointEntry` (EPOI, 0x18), `NkmMissionEnemyPointEntry` (MEPO, 0x18), `NkmMissionPathEntry` (MEPA, 0x14), `NkmAreaEntry` (AREA, 0x48) and `NkmCameEntry` (CAME, 0x4C).

The `STAG` record is 0x2C bytes:

| Offset | Size | Field |
|---:|---:|---|
| 0x00 | 4 | `STAG` |
| 0x04 | 2 | course id (`MkdsStageCourseId`) |
| 0x06 | 2 | lap count |
| 0x08 | 1 | pole position |
| 0x09 | 1 | fog enabled |
| 0x0A | 1 | fog table generation mode |
| 0x0B | 1 | fog shift |
| 0x0C | 8 | reserved |
| 0x14 | 4 | fog offset |
| 0x18 | 4 | fog colour: RGB555 in low 15 bits, alpha in bits 15-19 |
| 0x1C | 8 | four RGB555 KCL light colours |
| 0x24 | 4 | map-object far clip, FX32 |
| 0x28 | 4 | frustum far, FX32 |

`PATH` entries are four bytes: index, loop byte, signed 16-bit point count. `POIT` entries are 0x14 bytes: three FX32 coordinates, index, a flag byte, duration and two 16-bit values. The flag byte is read as a truth value by item-box and iron-ball code to make some map icons translucent between adjacent points. Duration is used as a speed multiplier by the path walker and as a wait/behaviour value by several enemies. The low 16-bit value is a wait counter, angle or other path-user value; the high 16-bit value is used as a cosine by traffic paths. These fields are context-dependent, not one global meaning.

Version notes: `KTPJ` has no trailing index before version 32, and `IPOI` has no recalculation index before version 34. The `AREA` record uses five vectors (position, length, X/Y/Z axes); its trailing fields are packed without natural 16-bit alignment and end in three separate bytes at 0x45–0x47. The AREA parameter roles and the EPOI/MEPO settings below are proven by game call sites, not inferred from the Toolbox model.

### Record field maps

`NkmObjectEntry` (OBJI, 0x3C):

| Offset | Size | Field |
|---:|---:|---|
| 0x00 | 12 | position, three FX32 |
| 0x0C | 12 | rotation, three FX32 |
| 0x18 | 12 | scale, three FX32 |
| 0x24 | 2 | object id |
| 0x26 | 2 | path id |
| 0x28 | 14 | seven signed 16-bit settings |
| 0x36 | 2 | visibility: clip-area digits plus inactive flag |
| 0x38 | 4 | Time Trials visibility flag |

`NkmAreaEntry` (AREA, 0x48). The five vectors are position, length, X axis, Y axis and Z axis.

| Offset | Size | Field |
|---:|---:|---|
| 0x00 | 60 | five FX32 vectors |
| 0x3C | 2 | parameter 0 |
| 0x3E | 2 | parameter 1 |
| 0x40 | 2 | linked enemy point |
| 0x42 | 1 | shape: 0 box, 1 cylinder |
| 0x43 | 1 | linked camera |
| 0x44 | 1 | area type |
| 0x45 | 1 | `field_45`, unidentified |
| 0x46 | 1 | `field_46`, unidentified |
| 0x47 | 1 | `field_47`, unidentified |

The AREA parameter meanings below are proven by game call sites:

- type 1 (camera): `linked_camera` selects the linked camera.
- type 2 (mission end): `parameter_0 == 0` means win; nonzero means lose.
- type 3 (clip area): `parameter_0` indexes the clip-area list.
- type 4 (enemy respawn route): `enemy_point_id` selects the enemy or mission-enemy point.
- type 5 (mission rival pass): `parameter_0` is an object id; `parameter_1` is the number of passes before losing.

`NkmCameEntry` (CAME, 0x4C):

| Offset | Size | Field |
|---:|---:|---|
| 0x00 | 48 | position, rotation, target 1, target 2 |
| 0x30 | 2 | start FOV |
| 0x32 | 2 | start FOV sine, FX16 |
| 0x34 | 2 | start FOV cosine, FX16 |
| 0x36 | 2 | end FOV |
| 0x38 | 2 | end FOV sine, FX16 |
| 0x3A | 2 | end FOV cosine, FX16 |
| 0x3C | 2 | FOV speed, FX16 |
| 0x3E | 2 | camera type |
| 0x40 | 2 | linked route |
| 0x42 | 2 | path speed, FX16 |
| 0x44 | 2 | target speed, FX16 |
| 0x46 | 2 | duration |
| 0x48 | 2 | next camera |
| 0x4A | 1 | first intro camera |
| 0x4B | 1 | show award trail |

Kart-point records all start with 24 bytes of position and rotation. Their tails are:

| Record | Size | Tail |
|---|---:|---|
| KTPS | 0x1C | `uint16` padding 0xFFFF, `int16` index |
| KTPJ (v32+) | 0x20 | `int16` enemy point, `int16` item point, `int32` index |
| KTP2 | 0x1C | `uint16` padding 0xFFFF, `uint16` id 0xFFFF |
| KTPC | 0x1C | `int16` next MEPO, `int16` index |
| KTPM | 0x1C | `uint16` unknown, `int16` index |

`NkmCpoiEntry` (CPOI, 0x24): two FX32 2D points at 0x00, then FX32 sine/cosine/distance at 0x10, then `int16` goto/start/key at 0x1C and two bytes at 0x22.

`NkmCpatEntry` (CPAT, 0x0C): `uint16` start, `uint16` length, 3-byte next, 3-byte previous, `uint8` section order at offset 10 and one zero padding byte at offset 11.

`NkmItemPointEntry` (IPOI v34+, 0x14): FX32 position, FX32 radius, one-byte recalculation index, three padding bytes.

`NkmPathLinkEntry` (IPAT/EPAT, 0x0C): `int16` start, `int16` length, 3-byte next, 3-byte previous, two padding bytes.

`NkmEnemyPointEntry` (EPOI, 0x18) and `NkmMissionEnemyPointEntry` (MEPO, 0x18) share an FX32 position and radius. Their remaining fields are proven by game call sites, not inferred:

| Offset | EPOI field |
|---:|---|
| 0x10 | `int16` `drifting` |
| 0x12 | `int16` `field_2` |
| 0x14 | `int16` `field_4` |
| 0x16 | `int16` `field_6` |

| Offset | MEPO field |
|---:|---|
| 0x10 | `int16` `drifting` |
| 0x12 | two padding bytes |
| 0x14 | `uint32` `unknown_1` |

`NkmMissionPathEntry` (MEPA, 0x14): `int16` start, `int16` length, eight-byte next array, eight-byte previous array.

## KCL — collision

KCL starts with a 0x3C-byte header, followed by four tables. All offsets are absolute from the start of the file except `prism_table_stored`, which is stored 0x10 lower than the real offset.

| Offset | Size | Field |
|---:|---:|---|
| 0x00 | 4 | position table offset |
| 0x04 | 4 | normal table offset |
| 0x08 | 4 | prism table offset, stored minus 0x10 |
| 0x0C | 4 | octree block table offset |
| 0x10 | 4 | prism thickness, FX32 |
| 0x14 | 12 | area minimum position, three FX32 values |
| 0x20 | 4 | X area mask |
| 0x24 | 4 | Y area mask |
| 0x28 | 4 | Z area mask |
| 0x2C | 4 | block width shift |
| 0x30 | 4 | X block shift |
| 0x34 | 4 | XY block shift |
| 0x38 | 4 | sphere radius, FX32 |

Positions are FX32 triples. Normals are FX16 triples (three signed 16-bit values). Prisms are 0x10-byte records: one FX32 height, then six 16-bit indices/attributes in the order position, face normal, edge normal 1, edge normal 2, edge normal 3, attribute. The octree table follows the prism table and occupies the rest of the file.

The stock corpus uses only the MKDS little-endian KCL variant. Mario Kart Toolbox's octree rewrite is byte-identical on all 59 files.

## SPA — particle archive

SPA is a JNLib particle archive. It starts with a 0x20-byte header.

| Offset | Size | Field |
|---:|---:|---|
| 0x00 | 4 | `SPA ` |
| 0x04 | 4 | version, `0x315F3231` (`12_1` on disk) |
| 0x08 | 2 | emitter count |
| 0x0A | 2 | texture count |
| 0x0C | 4 | reserved |
| 0x10 | 4 | emitter block length |
| 0x14 | 4 | texture block length |
| 0x18 | 4 | texture block offset |
| 0x1C | 4 | reserved |

The emitter block follows the header and contains the emitter records. The texture block starts at `texture_block_offset` and contains texture descriptors and their image data. The stock files are 0x4740/0xACC8-byte blocks in the largest sample; the parser in `HaroohiePals.Nitro.JNLib.Spl` walks emitters and textures but the Toolbox app does not currently use it.

Each texture starts with a 0x20-byte descriptor:

| Offset | Size | Field |
|---:|---:|---|
| 0x00 | 4 | `SPT ` |
| 0x04 | 4 | packed parameters: format 4 bits, width 4, height 4, repeat 2, flip 2, transparent-palette-0 1, reference 1, reference id 8 |
| 0x08 | 4 | texture data size |
| 0x0C | 4 | palette offset |
| 0x10 | 4 | palette size |
| 0x14 | 4 | palette-index offset |
| 0x18 | 4 | palette-index size |
| 0x1C | 4 | block size / next texture offset |

## Current status

| Format | Read | Write | Stock files |
|---|---|---|---|
| NKM | 124/124 | 123/124 byte-identical | 124 |
| KCL | 59/59 | 59/59 byte-identical | 59 |
| SPA | 3/3 | 0/3 byte-identical, output grows | 3 |

The single NKM rewrite difference is `test_circle_arc/course_map.nkm`. It is a test course with a shorter section layout than the retail courses.

## Implementation map

| Format | C header type | Mario Kart Toolbox |
|---|---|---|
| NKM | `NkmHeader`, `NkmSectionHeader`, section records | `HaroohiePals.NitroKart.MapData.Binary.Nkmd` → `MkdsMapData` |
| KCL | `KclHeader`, `KclPrism` | `HaroohiePals.KCollision.Formats.MkdsKcl` |
| SPA | `SpaHeader`, `SpaTextureHeader` | `HaroohiePals.Nitro.JNLib.Spl.SplArchive` |

The C header is the shared offset contract; the Toolbox classes are the editable object model. The NKM writer recalculates derived checkpoint/camera fields, the KCL writer rebuilds the octree, and the SPA writer is not yet byte-stable.

## Course folder usage

A stock course is split across `data/Course/<course>_course_arc/` and `data/Course/<course>_courseTex_arc/`. The editor opens the `.carc` pair, not individual files.

| File | Role |
|---|---|
| `course_map.nkm` | course layout: stage settings, paths, objects, checkpoints, item/enemy points, cameras, areas |
| `course_collision.kcl` | collision prisms and octree |
| `course_model.nsbmd`, `course_V.nsbmd` | course geometry and variant geometry |
| `course_model.nsbtx`, `course_V.nsbtx` | course textures |
| `course_model.nsbta`, `course_model_V.nsbta` | texture SRT animation |
| `MapObj/*.nsbmd`, `*.nsbtx`, `*.nsbca`, `*.nsbtp`, `*.nsbta`, `*.nsbma` | map-object models and animations |
| `Map2D/global.NCGR`, `global.NCLR`, `global1.NSCR`, `global2.*`, `local.*` | minimap graphics |
| `MissionRun/*.nkm`, `*.prm` | mission-mode map and parameters |

The course arc and its texture arc are separate archives. `course_model.nsbmd` normally contains no texture set; the matching `course_model.nsbtx` is loaded separately. The variant `_V` files are used by the alternate course state, so changing one without the other can make the track look correct in one mode and wrong in another.

## Editing notes

NKM is not a flat text-like format: changing a path point count or a checkpoint range requires updating the `PATH`, `POIT`, `CPAT`, `IPAT`, `EPAT` and `MEPA` records that point at those ranges. The Toolbox writer recalculates checkpoint distances and sin/cos values and camera sin/cos values on save; preserving stale derived fields will make the editor and game disagree.

KCL editing is more constrained than the header suggests. Changing prisms without rebuilding the octree leaves the collision lookup pointing at the old spatial partition. Mario Kart Toolbox rebuilds the octree from the prism list and the result is byte-identical on the stock corpus, so the octree parameters in `MkdsKcl.DefaultOctreeParams` are the reference configuration.

SPA is currently read-only in practice. The parser walks the emitter and texture blocks, but the writer grows the file and is not byte-identical on the three stock samples. Treat SPA as a documentation target first, and only edit it after a byte-stable writer exists.
