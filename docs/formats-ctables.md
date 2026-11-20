# Typed C tables and exact rebuilds

> **Project:** Mario Kart DS Modding Trove · **Harness:** `tools/ctables/common/harness.py` · **Licence:** MIT

The C-table work tests a simple question: if a file is represented as ordinary typed C tables and compiled back out, does it reproduce the original bytes exactly?

## Edit / rebuild workflow

```sh
python3 tools/ctables/edit.py list
python3 tools/ctables/edit.py extract path/to/ranktimeGP.rtt -o ranktimeGP.c
# edit the typed initializers in ranktimeGP.c
python3 tools/ctables/edit.py build ranktimeGP.c -o ranktimeGP.rtt
```

`extract` detects the format from the filename, extension or magic, then writes a complete compilable C table. `build` compiles that file and runs its writer. The `.c` file contains the editable typed tables first and a small writer `main()` at the bottom.

Each family module emits a complete C program containing:

- the real headers from `include/nitro/`
- designated initializers for the visible records
- static arrays or raw payload blocks for opaque data
- a `main` that writes the resulting file to `argv[1]`

`tools/ctables/common/harness.py` compiles that program with the host C compiler, runs it, and compares the output byte-for-byte with the source file.

Generated `.c` files and rebuilt binaries stay in temporary directories or `out/` and are not committed. Stock files are only used as local validation input.

## Reading the generated tables

Tables use the public enum names as their keys, not numbered rows:

```c
static const MkdsKartColorRow table[54] = {
    [MKDS_RACE_COURSE_SHELL_1 - 1] = {
        .diffuse = NITRO_RGB555(31, 31, 31),
        .ambient = NITRO_RGB555(12, 10, 10),
        ...
    },
};
```

The same rule applies to kart rows (`MKDS_KART_MARIO_A`), course rows
(`MKDS_RACE_COURSE_MUSHROOM_1`), staff-time slots
(`MKDS_STAFF_TIME_SLOT(MKDS_RACE_COURSE_LIGHTNING_4)`), mission records
(`MKDS_MISSION_COURSE_*`, `MKDS_CHARACTER_*`) and item-slot blocks.

No generated table uses a bare numeric array key when an enum exists. The
current mappings are:

| Table | Array keys |
|---|---|
| `grpconf.tbl` | `MKDS_OBJECT_*` |
| `mission.mr` | `MKDS_MISSION_Lx_y`, `MKDS_MISSION_EXTRA_nn` |
| `missionTable.mtbl` | `MKDS_MISSION_MENU_Lx_y` |
| `ranktimeGP.rtt` | `MKDS_RANK_TIME_SLOT_*` |
| `rankpoint.rpt` | `MKDS_RANK_POINT_ROW_*`, `MKDS_RANK_POINT_PLACE_n` |
| `emblem_s.tbl` | `MKDS_EMBLEM_STAMP_SLOT_nn` |
| `kart_appear.ktbl` | `MKDS_KART_*` × `MKDS_CHARACTER_*` |
| `kartmenuparam.bin` | `MKDS_KART_*` |
| `charmenuparam.bin` | `MKDS_CHARACTER_*` |
| NKTA | `MKDS_TIME_TRIALS_PLACE_*` × `MKDS_COURSE_ORDER_*` |
| NKMR | `MKDS_MISSION_MENU_Lx_y` |
| NKFL | `MKDS_FRIEND_SLOT_n` |
| NKFE | `MKDS_EMBLEM_SLOT_n` |
| NKGP | `MKDS_ENGINE_*` × `MKDS_CUP_*` |

Semantic sub-fields keep their names too. The 12-entry collision multiplier
arrays use the surface enum:

```c
.collision_velocity_multiplier = {
    [MKDS_SURFACE_ROAD] = FX32(1.0),
    [MKDS_SURFACE_OFF_ROAD] = FX32(0.64),
    ...
},
```

Kart menu rows name the six stat bars instead of storing an anonymous array:

```c
[MKDS_KART_STANDARD_MR] = {
    .speed = 62, .acceleration = 71, .weight = 29,
    .handling = 56, .drift = 57, .items = 66,
},
```

Generated comments are limited to notes that the initializer cannot express,
such as a sparse array’s order list or an unresolved field. Offsets, sizes and
time conversions live in the headers and format notes.

Fixed-point fields use compile-time constructors from `include/nitro/fx.h`:

```c
.top_speed = FX32(7.5),
.mass = FX16(0.5),
```

`FX32(1.5)` is exactly `0x1800`. The macro truncates toward zero, so the
formatter emits the **shortest decimal whose truncation reproduces the stored
raw word**:

```c
.collision_speed_scale = FX32(0.93),  /* raw 3809, not 3808/3810 */
.weight = FX32(0.65),                 /* raw 2662 */
```

This keeps the table readable without losing a bit. The property is tested
exhaustively for every one of the 65,536 FX16 words and on a 20,000-word FX32
sample (`tests/test_ctables_fx.py`). RGB555 material colours use
`NITRO_RGB555(r, g, b)` from `include/nitro/rgb555.h`. Packed words keep the
`union { raw; struct { ... } bits; }` form.

`tools/ctables/common/cnames.py` reads the public headers and supplies these enum
names. If a value has no declared enum constant, the emitter keeps the numeric
form rather than inventing a name.

## Why this matters

This is the practical test of whether a header is complete enough to be a codec, not just documentation. A clean round-trip means:

- every field is the right width and signedness
- every padding/reserved byte is accounted for
- array counts and offsets are consistent
- the typed table can replace the binary as the editable source

A failure is useful too: it identifies an unmodelled field, an alignment rule, or a derived field that the writer must recompute.

## Current families

The last full family sweep rebuilt **4,464 stock inputs byte-for-byte**, with no mismatches in the completed families. After the header/generator reorganization, the unit suite and representative stock rebuilds were re-run; re-run the full family sweep before tagging a release.

| Family | Status |
|---|---|
| Small MKDS tables | **13 / 13 stock inputs exact** (11 formats) (`RTT`, `RPT`, `MR`, `MTBL`, item slots, both staff-time copies, both `grpconf.tbl` copies, `kart_appear.ktbl`, `emblem_s.tbl`, `emblem2.bin`, `builddate.bin`) |
| JNLib UI lists | **890 / 890 stock files exact** (BNCL, BNLL, BNBL, KBD, KBDMAP, LLD, NBFP, NBFC) |
| Save, ghosts, kart parameters | **89 / 89 stock inputs exact** (decrypted save blocks, NKDG, input runs, 18 kart/char tables); encrypted `.sav` not implemented |
| Nitro G2D | **1879 / 1879 stock files exact** (NCGR, NCLR, NSCR, NCER, NFTR, NANR) |
| NKM/KCL/SPA | **186 / 186 stock files exact** (124 NKM, 59 KCL, 3 SPA) |
| Nitro G3D | **1407 / 1407 stock files exact** (NSBMD, NSBTX, NSBCA, NSBTP, NSBTA, NSBMA) |
| SDAT audio | emitters in place; sample round-trips exact |

See `tools/ctables/generic/` for generic Nitro emitters and
`tools/ctables/mkds/` for concrete stock-file emitters. Tests live in
`tests/test_ctables_*.py`.
