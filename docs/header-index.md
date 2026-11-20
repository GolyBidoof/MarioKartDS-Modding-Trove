# Header index

> **Project:** Mario Kart DS Modding Trove · **Licence:** MIT

Every public header, the format or stock file it models, and the codec or guide
that goes with it. Use this table when you have a file and need the matching
type.

Field layouts and size assertions in the headers are authoritative. The C-table
emitters are authoritative for rebuild behaviour. The format notes record stock
observations, unknowns and edit constraints that the types cannot express.

## Containers and shared formats

| Header | Format | Stock files | Codec / guide |
|---|---|---|---|
| `nitro/nds.h` | NDS header, FNT/FAT, overlays | `*.nds` | `tools/nds.py`, `docs/generic/nitro.md` |
| `nitro/narc.h` | NARC / CARC archive | `*.carc` | `docs/generic/nitro.md` |
| `nitro/blz.h` | BLZ-compressed overlay | overlay files | `tools/nds.py`, `docs/generic/nitro.md` |
| `nitro/bmg.h` | BMG message bank | `*.bmg` | `tools/bmg.py`, `docs/mkds/bmg.md` |
| `nitro/bits.h` | bit and mask helpers | — | — |
| `nitro/fx.h` | Fx32/Fx16 fixed point | — | — |
| `nitro/rgb555.h` | RGB555 colour word | — | — |
| `nitro/dwc.h` | NARC-less DWC utility archive | `dwc/utility.bin` | `tools/dwc_utility.py` |

## Nitro G2D

| Header | Format | Stock files | Codec / guide |
|---|---|---|---|
| `nitro/g2d.h` | umbrella | — | `docs/generic/formats-g2d.md` |
| `nitro/g2d/common.h` | shared G2D types | all G2D | `docs/generic/formats-g2d.md` |
| `nitro/g2d/ncgr.h` | character graphics | `*.NCGR` | `tools/g2d_project.py` |
| `nitro/g2d/nclr.h` | palette | `*.NCLR` | `tools/g2d_project.py` |
| `nitro/g2d/nscr.h` | screen tilemap | `*.NSCR` | `tools/g2d_project.py` |
| `nitro/g2d/ncer.h` | cell bank | `*.NCER` | `tools/g2d_asset.py` |
| `nitro/g2d/nftr.h` | font | `*.NFTR` | `tools/g2d_font_anim.py` |
| `nitro/g2d/nanr.h` | cell animation | `*.NANR` | `tools/g2d_font_anim.py` |

## Nitro G3D

| Header | Format | Stock files | Codec / guide |
|---|---|---|---|
| `nitro/g3d.h` | umbrella | — | `docs/generic/formats-g3d.md` |
| `nitro/g3d/common.h` | shared G3D blocks | all G3D | `docs/generic/formats-g3d.md` |
| `nitro/g3d/nsbmd.h` | model | `*.nsbmd` | `tools/ctables/generic/g3d_tables.py` |
| `nitro/g3d/nsbtx.h` | texture/palette | `*.nsbtx` | `tools/ctables/generic/g3d_tables.py` |
| `nitro/g3d/nsbca.h` | node animation | `*.nsbca` | `tools/ctables/generic/g3d_tables.py` |
| `nitro/g3d/nsbtp.h` | texture pattern | `*.nsbtp` | `tools/ctables/generic/g3d_tables.py` |
| `nitro/g3d/nsbta.h` | texture SRT | `*.nsbta` | `tools/ctables/generic/g3d_tables.py` |
| `nitro/g3d/nsbma.h` | material colour | `*.nsbma` | `tools/ctables/generic/g3d_tables.py` |

## Nitro sound

| Header | Format | Stock files | Codec / guide |
|---|---|---|---|
| `nitro/sdat.h`, `nitro/snd/sdat.h` | sound archive | `*.sdat` | `tools/ctables/generic/snd_tables.py` |
| `nitro/snd/sseq.h` | sequence | `SSEQ` | `tools/ctables/generic/snd_tables.py` |
| `nitro/snd/ssar.h` | sequence archive | `SSAR` | `tools/ctables/generic/snd_tables.py` |
| `nitro/snd/sbnk.h` | instrument bank | `SBNK` | `tools/ctables/generic/snd_tables.py` |
| `nitro/snd/swar.h` | wave archive | `SWAR` | `tools/ctables/generic/snd_tables.py` |
| `nitro/snd/swav.h` | wave | `SWAV` | `tools/ctables/generic/snd_tables.py` |
| `nitro/snd/common.h` | shared sound types | all sound | `docs/generic/formats-audio.md` |

## MKDS course files

| Header | Format | Stock files | Codec / guide |
|---|---|---|---|
| `nitro/mkds_course.h` | umbrella | — | `docs/mkds/formats-mkds-course.md` |
| `nitro/mkds/course/nkm.h` | course map | `course_map.nkm`, `*_tool.nkm` | `tools/ctables/mkds/course_tables.py` |
| `nitro/mkds/course/kcl.h` | collision | `*.kcl` | `tools/ctables/mkds/course_tables.py` |
| `nitro/mkds/course/spa.h` | particle archive | `*.spa` | `tools/ctables/mkds/course_tables.py` |

## MKDS UI

| Header | Format | Stock files | Codec / guide |
|---|---|---|---|
| `nitro/mkds_ui.h` | umbrella | — | `docs/mkds/formats-mkds-ui.md` |
| `nitro/mkds/common/ui_common.h` | JNLib header/coordinate | all UI lists | `tools/ctables/mkds/ui_tables.py` |
| `nitro/mkds/ui/bncl.h` | cell placement | `*.bncl` | `tools/ctables/mkds/ui_bncl.py` |
| `nitro/mkds/ui/bnll.h` | label placement | `*.bnll` | `tools/ctables/mkds/ui_bnll.py` |
| `nitro/mkds/ui/bnbl.h` | touch boxes | `*.bnbl` | `tools/ctables/mkds/ui_bnbl.py` |
| `nitro/mkds/ui/kbd.h` | keyboard hit boxes | `*.kbd` | `tools/ctables/mkds/ui_kbd.py` |
| `nitro/mkds/ui/kbdmap.h` | keyboard characters | `*.kbdmap` | `tools/ctables/mkds/ui_kbdmap.py` |
| `nitro/mkds/ui/lld.h` | emblem layout | `*.lld` | `tools/ctables/mkds/ui_lld.py` |
| `nitro/mkds/ui/nbfp.h` | banner palette | `*.nbfp` | `tools/ctables/mkds/ui_nbfp.py` |
| `nitro/mkds/ui/nbfc.h` | banner tile image | `*.nbfc` | `tools/ctables/mkds/ui_nbfc.py` |

## MKDS race, save and small tables

| Header | Format | Stock files | Codec / guide |
|---|---|---|---|
| `nitro/mkds_ids.h` | umbrella for identifiers | — | `docs/mkds/formats-ids.md` |
| `nitro/mkds/common/ids.h` | shared id spaces | — | `tools/ctables/common/cnames.py` |
| `nitro/mkds_race.h` | umbrella for race/save data | — | `docs/mkds/formats-mkds-race.md` |
| `nitro/mkds/common/time.h` | shared clock types | — | `docs/mkds/save-file-map.md` |
| `nitro/mkds/save/ghost.h` | NKDG/NKPG ghosts and inputs | `Ghost/*.bin`, save blocks | `tools/ctables/mkds/save_tables.py` |
| `nitro/mkds/save/save.h` | `.sav` blocks and envelopes | `*.sav` | `docs/mkds/save-file-map.md`, `tools/ctables/mkds/save_tables.py` |
| `nitro/mkds/race/mission.h` | NKMR mission table | `mission.mr`, `missionTable.mtbl` | `tools/ctables/mkds/small_tables.py` |
| `nitro/mkds/race/prm.h` | boss parameter prefix | `MissionRun/*.prm` | `docs/mkds/formats-mkds-race.md` |
| `nitro/mkds/race/ranktime.h` | NKTT rank-time | `ranktimeGP.rtt` | `tools/ctables/mkds/small_tables.py` |
| `nitro/mkds/race/rankpoint.h` | NKPT rank points | `rankpoint.rpt` | `tools/ctables/mkds/small_tables.py` |
| `nitro/mkds/race/itemslots.h` | item-slot weights | `Item/ItemSlotList.dat` | `tools/ctables/mkds/small_tables.py` |
| `nitro/mkds/race/staffghost.h` | staff thresholds | `staff_ghost_time.bin` | `tools/ctables/mkds/small_tables.py` |
| `nitro/mkds/race/grpconf.h` | object render/collision profile | `MapObj/grpconf.tbl` | `tools/ctables/mkds/small_tables.py` |
| `nitro/mkds/race/kartappear.h` | kart/character unlock matrix | `kart_appear.ktbl` | `tools/ctables/mkds/small_tables.py` |
| `nitro/mkds/files/emblemtable.h` | emblem editor placements | `Edit_arc/emblem_s.tbl` | `tools/ctables/mkds/small_tables.py` |
| `nitro/mkds/files/misc.h` | emblem bitmap and build stamp | `emblem2.bin`, `builddate.bin` | `tools/ctables/mkds/small_tables.py` |
| `nitro/mkds/race/kartparams.h` | kart/character parameter tables | `kart*.bin`, `char*.bin` | `tools/ctables/mkds/save_tables.py` |
| `nitro/mkds/bmg_messages.h` | BMG message ids | `*.bmg` | `tools/bmg_headers.py` |
| `nitro/mkds/bmg/*.h` | per-bank message enums | `*.bmg` | `tools/bmg_headers.py` |
| `nitro/mkds/rom/rom.h` | stock ROM header constants | `mkds.nds` | `docs/generic/nitro.md` |

## Search tips

- A stock filename extension usually names the header: `.nkm` → `nkm.h`,
  `.nclr` → `nclr.h`, `.bmg` → `bmg.h`.
- For a save block, search `docs/mkds/save-file-map.md` for the magic (`NKSY`,
  `NKGP`, …) and then the matching `Sav*` type in `save.h`.
- For a table with an enum key, search the enum name from `ids.h`
  (`MkdsMapObject`, `MkdsMission`, `MkdsCourseOrder`, `MkdsTimeTrialsPlace`,
  `MkdsFriendSlot`, `MkdsEmblemSlot`).
