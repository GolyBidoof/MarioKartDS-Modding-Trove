# Nitro G3D resources

> **Project:** Mario Kart DS Modding Trove · **Format:** Nitro G3D (NSBMD, NSBTX, NSBCA, NSBTP, NSBTA, NSBMA) · **Header:** [`../include/nitro/g3d.h`](../include/nitro/g3d.h) · **Licence:** MIT

The six G3D containers share one file envelope, one dictionary format and a small set of block types. The envelope and dictionary are the standard Nitro SDK NNS G3D layout; this note records the on-disk offsets, the values observed in the Mario Kart DS stock corpus, and the parts that are not decoded. All multi-byte fields are little-endian.

The structure names below are this repository's neutral names; the same layouts appear in the Nitro SDK headers as `NNSG3dResDataBlockHeader`, `NNSG3dResDict`, `NNSG3dResMdl` and `NNSG3dResTex`, and in Mario Kart Toolbox as `HaroohiePals.Nitro.NitroSystem.G3d.*`. Texture image parameters use the public GX/GBATEK encoding.

The corpus counts are 766 NSBMD, 335 NSBTX, 136 NSBCA, 91 NSBTP, 50 NSBTA and 29 NSBMA under `mkds_stock/root`. Paths in the examples are relative to that root. The generic layout is in the sections above; how MKDS selects, pairs and edits these resources starts at [MKDS usage and configuration](#mkds-usage-and-configuration).

## File envelope

Every file starts with a 0x10-byte header. Block offsets are absolute file offsets, in block-table order, and each block is 4-byte aligned.

| Offset | Size | Field |
|---:|---:|---|
| 0x00 | 4 | signature: `BMD0`, `BTX0`, `BCA0`, `BTP0`, `BTA0` or `BMA0` |
| 0x04 | 2 | byte order, `0xFEFF` |
| 0x06 | 2 | version |
| 0x08 | 4 | file size |
| 0x0C | 2 | header size, `0x10` |
| 0x0E | 2 | block count |
| 0x10 | 4 × count | block offsets |

All 1407 stock files use byte order `0xFEFF` and header size `0x10`. `BMD0` is version 2 and every other container is version 1.

| Container | Files | Version | Observed blocks |
|---|---:|---:|---|
| NSBMD | 766 | 2 | `MDL0` only (408) or `MDL0` + `TEX0` (358) |
| NSBTX | 335 | 1 | `TEX0` |
| NSBCA | 136 | 1 | `JNT0` |
| NSBTP | 91 | 1 | `PAT0` |
| NSBTA | 50 | 1 | `SRT0` |
| NSBMA | 29 | 1 | `MAT0` |

A `BMD0` may embed its own `TEX0`, so texture blocks exist both inside models and as standalone `BTX0` files. The stock corpus contains 693 `TEX0` blocks in total: 335 standalone plus 358 embedded.

Every block starts with an 8-byte block header: a 4-byte magic and a `uint32_t` size that includes the header.

## Dictionaries

`MDL0`, `JNT0`, `PAT0`, `SRT0` and `MAT0` place a dictionary directly at block + 0x08. `TEX0` places three info records first and addresses its dictionaries through their `dictionary_offset` fields. A dictionary has a fixed 8-byte header, `entry_count + 1` four-byte Patricia nodes, an entry header, the entry data and 16-byte names.

| Dictionary offset | Size | Field |
|---:|---:|---|
| 0x00 | 1 | revision, 0 in every stock dictionary |
| 0x01 | 1 | entry count |
| 0x02 | 2 | total dictionary size, including names |
| 0x04 | 2 | reserved, `8` in every stock dictionary |
| 0x06 | 2 | entry-header offset, relative to the dictionary start |
| 0x08 | 4 × (count + 1) | Patricia tree nodes |

| Entry header offset | Size | Field |
|---:|---:|---|
| 0x00 | 2 | entry size in bytes |
| 0x02 | 2 | name-table offset, relative to the entry header |
| 0x04 | entry_size × count | entry data, in entry-index order |
| +name_offset | 16 × count | NUL-padded ASCII names |

An entry's payload offset (for example the model offset in `MDL0`) is relative to the block or animation record that owns the dictionary, not to the dictionary itself. `TEX0` and the animation records use the same rule.

The Patricia nodes are four bytes each: a reference bit, left index, right index and entry index. The reference bit is a bit position in the 16-byte name; left and right are node indices, and the entry index selects the entry data and name. The Nitro lookup compares 16-byte names linearly for dictionaries with fewer than 16 entries and walks the Patricia tree for 16 or more. Course material dictionaries cross that threshold, so a byte-stable writer must preserve the original nodes or rebuild the tree with the same key order. A reader that only walks records can still scan entries by index.

## NSBMD (BMD0) and MDL0

An `MDL0` block is a block header plus a model-set dictionary. The dictionary points at one or more model records; entry offsets are relative to the block start.

| Model offset | Size | Field |
|---:|---:|---|
| 0x00 | 4 | model size |
| 0x04 | 4 | SBC offset, relative to the model record |
| 0x08 | 4 | material-set offset, relative to the model record |
| 0x0C | 4 | shape-set offset, relative to the model record |
| 0x10 | 4 | envelope-matrix offset; equals `size` when absent |
| 0x14 | 0x2C | model info |
| 0x40 | variable | node dictionary |

| Model-info offset | Size | Field |
|---:|---:|---|
| 0x00 | 1 | SBC type, 0 in stock |
| 0x01 | 1 | scaling rule, 0 or 1 |
| 0x02 | 1 | texture-matrix mode, 0 in stock |
| 0x03 | 1 | node count |
| 0x04 | 1 | material count |
| 0x05 | 1 | shape count |
| 0x06 | 1 | first unused matrix-stack id |
| 0x07 | 1 | zero |
| 0x08 | 4 | position scale, fx32 |
| 0x0C | 4 | inverse position scale, fx32 |
| 0x10 | 2 | vertex count |
| 0x12 | 2 | polygon count |
| 0x14 | 2 | triangle count |
| 0x16 | 2 | quad count |
| 0x18 | 12 | bounding box X, Y, Z, W, H, D, each fx16 |
| 0x24 | 4 | box position scale, fx32 |
| 0x28 | 4 | inverse box position scale, fx32 |

Node data starts at the node dictionary base plus each dictionary entry offset. A node begins with `uint16_t` flags and one fx16 matrix element, then optional translation, rotation and scale fields whose presence is selected by the flags. `g3d_node_data_size()` in the header returns the record length for a flag word.

| Node flag | Value | Meaning |
|---|---:|---|
| `G3D_NODE_TRANSLATION_ZERO` | 0x0001 | no translation field |
| `G3D_NODE_ROTATION_ZERO` | 0x0002 | no rotation field |
| `G3D_NODE_SCALE_ONE` | 0x0004 | no scale fields |
| `G3D_NODE_ROTATION_PIVOT` | 0x0008 | two fx16 pivot angles instead of a 3×3 matrix |
| `G3D_NODE_MATRIX_STACK_MASK` | 0xF800 | matrix-stack index, shifted by 11 |

A material set starts with two `uint16_t` lookup offsets, so its dictionary begins at material-set + 4. The two offsets are declared as `G3dMaterialSetHeader`. The fixed material record is 0x2C bytes; texture-matrix values and a 0x40-byte effect matrix follow according to the material flags.

| Material offset | Size | Field |
|---:|---:|---|
| 0x00 | 2 | item tag, 0 in every stock material |
| 0x02 | 2 | record size, including optional blocks |
| 0x04 | 4 | diffuse/ambient |
| 0x08 | 4 | specular/emission |
| 0x0C | 4 | polygon attribute |
| 0x10 | 4 | polygon-attribute mask |
| 0x14 | 4 | texture image parameter |
| 0x18 | 4 | texture-image-parameter mask |
| 0x1C | 2 | texture palette base |
| 0x1E | 2 | material flags |
| 0x20 | 2 | original width |
| 0x22 | 2 | original height |
| 0x24 | 4 | magnitude W, fx32 |
| 0x28 | 4 | magnitude H, fx32 |

Optional material data follows the fixed record in this order, with each block present only when its flag is set:

| Size | Field | Present when |
|---:|---|---|
| 8 | scale S and scale T, two Fx32 | `G3D_MATERIAL_TEX_MTX` set and `G3D_MATERIAL_TEX_MTX_SCALE_ONE` clear |
| 4 | rotation sin and cos, two Fx16 | `G3D_MATERIAL_TEX_MTX` set and `G3D_MATERIAL_TEX_MTX_ROT_ZERO` clear |
| 8 | translation S and T, two Fx32 | `G3D_MATERIAL_TEX_MTX` set and `G3D_MATERIAL_TEX_MTX_TRANS_ZERO` clear |
| 64 | effect matrix, sixteen Fx32 | `G3D_MATERIAL_EFFECT_MTX` set |

The `texture_image_param_mask` marks the bits the material designates; every stock material stores `0xFFFFFFFF`. The runtime bind path ORs the bound texture entry’s parameter and VRAM offset into the material’s `texture_image_param` and does not consult the mask, so the mask is authoring metadata rather than a second parameter. The material’s low address bits and the texture entry’s format/size bits must still agree with the texture that is bound.

A shape set is a dictionary at shape-set + 0. Each shape record is 0x10 bytes: item tag, size, flags, display-list offset (relative to the shape set) and display-list size.

| Shape flag | Value |
|---|---:|
| `G3D_SHAPE_USE_NORMAL` | 0x00000001 |
| `G3D_SHAPE_USE_COLOR` | 0x00000002 |
| `G3D_SHAPE_USE_TEXCOORD` | 0x00000004 |
| `G3D_SHAPE_USE_RESTORE_MTX` | 0x00000008 |

The stock corpus contains 772 model records for 766 files: 764 files have one model, and `data/KartModelMain_arc/dbgprim.nsbmd` plus `data/KartModelMainA_arc/dbgprim.nsbmd` each have four (`sphere`, `Cylinder`, `arrow`, `cube`). Node counts are 1–17, material counts 1–28 and shape counts 1–28; material and shape counts are equal in every stock model.

Every stock model has its envelope-matrix offset equal to the model size, so no envelope matrices are present. When present, the offset points to a table of envelope matrices indexed by model node; the stock corpus has no sample, so the table is not modelled beyond the offset field. Scaling rule is 0 in 730 models and 1 in 42. All 2038 materials have item tag 0 and texture palette base 0.

Material sizes are 0x2C (1606 records), 0x34 (357), 0x6C (64), 0x78 (5), 0x74 (3), 0x70 (2) and 0x3C (1). All 0x2C records use flags 0x1FCE, most 0x34 records use 0x1FCD (346; 11 use 0x1FC7), and the 0x6C group uses 0x3FCF, which is the effect-matrix bit; the remaining variants clear individual texture-matrix bits. Shape flags in the corpus are 0x06, 0x05, 0x01, 0x04 and 0x00.

## NSBTX (BTX0) and TEX0

A `TEX0` block starts with three info records and then the texture and palette dictionaries. The fixed 0x3C-byte prefix is declared as `G3dTextureSetHeader`; `G3dSetHeader` does not apply to this block because the first dictionary is not at +0x08.

| TEX0 offset | Size | Field |
|---:|---:|---|
| 0x00 | 8 | block header |
| 0x08 | 0x10 | texture info |
| 0x18 | 0x14 | 4x4 texture info |
| 0x2C | 0x10 | palette info |
| 0x3C | variable | texture dictionary, then palette dictionary and data |

| Texture-info offset | Size | Field |
|---:|---:|---|
| 0x00 | 4 | VRAM key; 0 on disk, replaced at load with the VRAM address key |
| 0x04 | 2 | texture data size, in 8-byte units |
| 0x06 | 2 | texture dictionary offset, relative to `TEX0` |
| 0x08 | 2 | flag: bit 0 = resident in VRAM; 0 on disk |
| 0x0A | 2 | reserved/padding word, 0 |
| 0x0C | 4 | texture data offset, relative to `TEX0` |

| 4x4-info offset | Size | Field |
|---:|---:|---|
| 0x00 | 4 | VRAM key; 0 on disk |
| 0x04 | 2 | texture data size, in 8-byte units |
| 0x06 | 2 | dictionary offset, relative to `TEX0` |
| 0x08 | 2 | flag: bit 0 = resident in VRAM; 0 on disk |
| 0x0A | 2 | reserved/padding word, 0 |
| 0x0C | 4 | texture data offset, relative to `TEX0` |
| 0x10 | 4 | palette-index data offset, relative to `TEX0` |

| Palette-info offset | Size | Field |
|---:|---:|---|
| 0x00 | 4 | VRAM key; 0 on disk |
| 0x04 | 2 | palette data size, in 8-byte units |
| 0x06 | 2 | flag: bit 0 = resident in VRAM, bit 15 = 4-color palette; 0 or `0x8000` on disk |
| 0x08 | 2 | palette dictionary offset, relative to `TEX0` |
| 0x0A | 2 | reserved/padding word, 0 |
| 0x0C | 4 | palette data offset, relative to `TEX0` |

The three info records share one field pattern: a 32-bit VRAM key, a size in 8-byte units, a dictionary offset, a 16-bit flag word, a 16-bit reserved word and one or two data offsets. The key is not a format selector. In all 693 stock `TEX0` blocks every texture and 4x4 key is 0, every texture and 4x4 flag and reserved word is 0, and every palette key and reserved word is 0. The palette flag is 0 in 629 blocks and `0x8000` in 64; bit 0 is never set on disk. The stock loader clears the key and the resident bit before loading, allocates VRAM, and afterwards uses the key as the texture or palette address. The `+0x0A` word is explicit 2-byte padding, not a count or a second flag.

The 4x4 texture data length is `sizeTex << 3` bytes; its palette-index data length is `sizeTex << 2` bytes. Palette entry bit 0 marks a 4x4 palette entry, and the 16-bit palette offset is stored right-shifted by 3, like the texture address field. In the corpus 63 of 2222 palette entries set bit 0; the rest store 0.

Texture entries are 8 bytes: `texture_image_param` and `extra_param`. The parameter carries a 16-bit address field that is right-shifted by 3, width and height exponents at bits 20 and 23, a 3-bit format at bits 26–28, and a color-0-alpha bit at bit 29; `extra_param` carries original width and height and a same-size bit. Palette entries are 4 bytes: a 16-bit offset in 8-byte units and a 16-bit flag.

The 693 `TEX0` blocks hold 2228 textures and 2222 palettes. The texture and palette dictionary counts are equal in 690 blocks; `data/Course/old_mario_gc_arc/course_model.nsbmd` (23/22), `data/Course/luigi_course_arc/course_model.nsbmd` (9/8) and `data/Course/old_noko_sfcTex_arc/course_model.nsbtx` (20/16) reuse palettes across textures. A palette is bound by name through the material set’s separate texture-to-material and palette-to-material lookup dictionaries, so the counts do not have to match; several textures can share one palette. Editing a shared palette changes every texture bound to it.

Texture formats in the corpus are Comp4x4 (format 5, 1325 entries), Pltt16 (3, 641), Pltt256 (4, 119), Pltt4 (2, 67), A5I3 (6, 51), A3I5 (1, 23) and Direct (7, 2); format 0 does not occur. Texture data sizes range from 0 to 9248 eight-byte units and palette sizes from 2 to 4614. The `0x8000` palette flag appears in 64 blocks.

## NSBCA (BCA0) and JNT0

A `JNT0` block is a block header plus a set dictionary. Each dictionary entry points at a joint animation record, relative to the block start.

| Animation offset | Size | Field |
|---:|---:|---|
| 0x00 | 4 | category header: `J`, revision 0, `AC` |
| 0x04 | 2 | frame count |
| 0x06 | 2 | node count |
| 0x08 | 4 | animation flags |
| 0x0C | 4 | pivot-rotation table offset, relative to the record |
| 0x10 | 4 | matrix-rotation table offset, relative to the record |
| 0x14 | 2 × node_count | per-node record offsets, relative to the record |
| +pad | 0–2 | zero padding to a 4-byte boundary |

Node records use the flag words listed under NSBMD. Translation, rotation, scale and constant values follow the same presence rules; the node’s high byte is the model node index.

Rotation entries are either a 6-byte pivot record (`uint16_t` info, two fx16 values) or a 10-byte packed matrix (`uint16_t[5]`). The pivot bit in a rotation index is `0x8000` and the data index mask is `0x7FFF`. Frame data uses the shared animation info word: interpolation step in bits 30–31, fx16 flag at bit 29 for translation and scale, and the last interpolated frame in bits 16–28.

The corpus has 136 files and 186 animation records. Set dictionaries hold 1 record in 127 files, 5 in four files, and 4, 6, 8, 10 or 11 in one file each. Frame counts are 1–361 and node counts 1–17. Animation flags are 0 (170 records), 3 (12) and 1 (4). `data/MissionRun/boss_donketu.nsbca` is a representative multi-animation file with `walk`, `hit` and `start`.

NSBCA is currently read-only. Writing is not implemented.

## NSBTP (BTP0) and PAT0

A `PAT0` block is a block header plus a set dictionary. Each entry points at a texture-pattern record, relative to the block start.

| Animation offset | Size | Field |
|---:|---:|---|
| 0x00 | 4 | category header: `M`, revision 0, `PT` |
| 0x04 | 2 | frame count |
| 0x06 | 1 | texture-name count |
| 0x07 | 1 | palette-name count |
| 0x08 | 2 | texture-name table offset, relative to the record |
| 0x0A | 2 | palette-name table offset, relative to the record |
| 0x0C | variable | animation dictionary |

Each dictionary entry is 8 bytes: frame-value count, a 16-bit flag, an fx16 ratio, and a frame-value table offset relative to the record. Frame values are 4 bytes: frame number, texture index and palette index.

The corpus has 91 files and 91 animation records, all with a one-entry set dictionary. Frame counts are 2–300 and texture and palette counts reach 15. The entry flag is the texture-pattern option word: bit 0 would mean `no palette animation`, so 0 leaves palette animation enabled. The SDK marks the option as not currently used by the runtime. All 105 stock inner entries store 0, the frame values carry palette indices and the palette-name table is populated. Inner dictionaries hold 1 record (79), 2 (10) or 3 (2).

NSBTP is currently read-only. Writing is not implemented.

## NSBTA (BTA0) and SRT0

An `SRT0` block is a block header plus a set dictionary. Each entry points at a texture-SRT record, relative to the block start.

| Animation offset | Size | Field |
|---:|---:|---|
| 0x00 | 4 | category header: `M`, revision 0, `AT` |
| 0x04 | 2 | frame count |
| 0x06 | 1 | animation flags: bit 0 interpolation, bit 1 end-to-start |
| 0x07 | 1 | texture-matrix mode |
| 0x08 | variable | animation dictionary |

Each dictionary entry is 40 bytes and holds five `(info, data-offset)` pairs in this order: scale S, scale T, rotation, translation S, translation T. The info word uses the shared step bits 30–31, an fx16 bit 28, a constant bit 29, and a 16-bit last-frame field. When the constant bit is clear, the paired value is a table offset relative to the animation record; when it is set, the paired value is the constant itself.

The corpus has 50 files and 52 records: 49 files have one record and `data/MissionRun/kuriking.nsbta` has three (`ts_wait`, `ts_anger`, `ts_down`). Frame counts are 15–4800 and inner dictionaries hold 1–10 records. Animation flags are 0 (17 records), 1 (1) and 3 (34). Texture-matrix mode is 0 in 17 records and 0x10–0x14 in the other 35. The byte is not used for dispatch: the runtime selects the texture-matrix formula from the model’s `texture_matrix_mode` (0 in every stock model), not from the animation record. The low two bits of the stored byte correspond to the four SDK formulas, but the high bits are outside that enum and inert; a writer must preserve the byte.

NSBTA is currently read/write, and 44 of the 50 stock files round-trip byte-for-byte. The other six differ only in element-data layout or count; every record header, dictionary name, SRT info word, constant and parsed keyframe value is identical after the rewrite.

| File that differs | Differing range | Cause |
|---|---|---|
| `data/Course/pinball_course_arc/course_model.nsbta` | 0x217–0x223, 0x2A7–0x2B3, 0x337–0x343 | 2-byte alignment padding before the constant block of `pin_WarpLine`, `pin_WarpMain` and `pin_cannon1` |
| `data/Course/rainbow_course_arc/course_model.nsbta` | nine 6-byte ranges from 0x303–0x58F | the same 2-byte padding before each entry after the first |
| `data/Course/clock_course_arc/course_model.nsbta` | 0x19B–0x1A7, 0x227–0x233 | 2-byte padding before the constant block of `DASH` and `ya2` |
| `data/Course/stadium_course_arc/course_model.nsbta` | 0x1D7–0x1E3 | `dash` translation-T table stores 120 fx16 values; the rewrite emits 121 |
| `data/Course/wario_course_arc/course_model.nsbta` | 0x1D7–0x1E3 | same `dash` translation-T count difference as stadium |
| `data/MissionRun/kuriking.nsbta` | file/block/dictionary sizes at 0x08, 0x18 and 0x3C, then the shifted tail | each record’s translation-T table stores one more fx16 value than the rewrite emits (60/150/16 versus 59/149/15) |

The first three files are pure padding differences: the stock layout starts each entry’s constant block on a 4-byte boundary and pads the preceding table, while the rewrite concatenates the blocks without that pad.

The two `dash` files and `kuriking.nsbta` are stored-count differences, not padding. In `stadium_course` and `wario_course` the original `dash` table has values for frames 0–119, while the rewrite writes 121 values (the extra value is a constant word read back as a keyframe), shifting every following constant by 2 bytes. In `kuriking.nsbta` the three `ts_wait`, `ts_anger` and `ts_down` records each store one more terminal translation-T value than the rewrite emits; the first two record sizes shrink by 2 bytes, the set-dictionary entry offsets move, and the file shrinks from 1548 to 1544 bytes after the final pad.

The stored extent is the rule: a channel table runs from its offset to the next datum (or block end), with 4-byte alignment padding. The runtime needs at most `frame_count` samples from a step-1 table, and fewer for step 2 or 4 after the last interpolated frame, but the stock exporter sometimes stores one more (kuriking) or one fewer (stadium/wario) and leaves the difference as padding. A byte-stable writer must copy the original table extent instead of recomputing it from the info word.

## NSBMA (BMA0) and MAT0

A `MAT0` block is a block header plus a set dictionary. Each entry points at a material-animation record, relative to the block start.

| Animation offset | Size | Field |
|---:|---:|---|
| 0x00 | 4 | category header: `M`, revision 0, `AM` |
| 0x04 | 2 | frame count |
| 0x06 | 2 | options: bit 0 interpolation, bit 1 end-to-start interpolation |
| 0x08 | variable | animation dictionary |

Each material-animation entry is 20 bytes and contains five packed 32-bit elements in this order: diffuse, ambient, specular, emission and polygon alpha. The inner dictionary names are material names.

| Element bits | Field |
|---:|---|
| 31–30 | frame step: 0 = every frame, 1 = every 2nd frame, 2 = every 4th frame |
| 29 | constant: the low 16 bits are the value |
| 28–16 | last interpolated frame |
| 15–0 | data offset relative to the animation record, or the constant value |

For diffuse, ambient, specular and emission, a constant is RGB555 with red in bits 0–4, green in bits 5–9 and blue in bits 10–14. For polygon alpha, a constant is the low 16-bit alpha. When the constant bit is clear, the low 16 bits are an offset to a table of 32-bit values.

The corpus has 29 files and 29 records. Frame counts are 11–175. The option word is 0 in 23 records, 1 in three and 3 in three. Inner dictionaries hold one or two material entries. `data/MissionRun/MissionGate.nsbma` is the one-record example and `data/Course/beach_course_arc/MapObj/water_efct.nsbma` is a two-record example.

NSBMA has runtime hooks but no parser in this repository. The header and dictionary can be walked, and the entry layout is declared in the header; the five color elements and their tables are still left to the consumer.

## MKDS usage and configuration

This part describes how the stock game uses and configures the generic resources above. The generic layouts are not repeated; only the MKDS-specific file roles, pairing rules, object selection and edit consequences are recorded here. Object IDs and loader behaviour come from the stock NKM data and the matching game code. Rows marked inferred are consistent with the evidence but have not been confirmed by a runtime experiment.

### File roles

| Role | Location | Stock count | Texture source |
|---|---|---:|---|
| Course geometry | `data/Course/<course>_arc/course_model.nsbmd` | 59 | embedded `TEX0`, or sibling `*Tex_arc/course_model.nsbtx` |
| Course sky/backdrop (`_V`, inferred) | `<course>_arc/course_model_V.nsbmd` | 50 | embedded `TEX0`, or `*Tex_arc/course_model_V.nsbtx` |
| Course map objects | `<course>_arc/MapObj/*.nsbmd` | 251 | embedded `TEX0`; the 24 exceptions are shadow models |
| Shared map objects | `MainRace_arc/MapObj/`, `Main/MapObj_arc/` | 9 | embedded `TEX0` |
| Kart bodies | `KartModel*_arc/kart/<character>/kart_*.nsbmd` | 104 | same-basename sibling `.nsbtx` |
| Kart tires | `KartModel*_arc/kart/tire/kart_tire_*.nsbmd` | 12 | same-basename sibling `.nsbtx` |
| Kart shadows | `KartModel*_arc/kart/shadow/sh_*.nsbmd` | 100 | none (untextured) |
| Player characters | `KartModelSub_arc/character/<character>/P_*.nsbmd` and menu copies | 38 copies | same-basename sibling `.nsbtx` |
| Enemy characters | `KartModelMain*_arc/character/<character>/E_*.nsbmd` | 26 copies | same-basename sibling `.nsbtx` |
| Mission objects | `data/MissionRun/*.nsbmd` | 16 | embedded `TEX0`; `sh_circle` and `sh_iwante` are untextured |
| Race items | `MainRace_arc/Item/*.nsbmd` | 15 | embedded `TEX0` |
| Race HUD | `Scene/Race*_arc/*.nsbmd` | 47 | embedded `TEX0`; `jg_shadow` is untextured |
| Result trophies | `Scene/Result*_arc/*.nsbmd` | 33 | embedded `TEX0` |
| Cups | `Scene/Menu_arc/common/` | 0 cup-icon models | cup icons, marks and trophy icons are G2D (NCGR/NCLR/NCER/NSCR) |
| Menus | `KartModelMenu/`, `Scene/Menu*` | 66 in the unpacked duplicate; other menu graphics are G2D | same-basename `.nsbtx` |

The four `KartModel*_arc` trees are not identical: `KartModelMain_arc` contains the full enemy-character roster, while `KartModelMainA_arc` and `KartModelMainB_arc` contain disjoint character subsets that together match it. The A/B split is the Download Play packaging: the child overlay loads `KartModelMainA.carc` and `KartModelMainB.carc` together with separate heap budgets, so the two archives reconstruct the full roster over the link. `KartModelMenu_arc` and the unpacked `KartModelMenu/` folder are a duplicate menu copy; the menu scene loads from the folder path `data/KartModelMenu/`, while the race scene loads the packed `KartModelMain*_arc` trees.

The 118 `data/Course/*_arc` directories contain 59 main course models and 50 sky models. The 59 `*Tex_arc` directories hold the external course texture sets where present and the 2D course-select graphics.

### Pairing rules

The texture rule is determined by the model role. Kart bodies, tires and characters use an external texture set with the exact same basename in the same directory: 104 kart-body, 12 tire and 65 character pairs, plus the 55 standalone emblem sets. Course main and sky models use an embedded `TEX0` block when present; otherwise the game opens `data/Course/<course>Tex_arc/<same basename>.nsbtx`. Map objects, items, HUD elements and trophies embed their textures; the only course map objects without `TEX0` are shadow or silhouette models, and those have no external `.nsbtx` either.

Of the 109 course models, 13 embed `TEX0` and 96 use the sibling texture archive. `data/Course/MR_stage3_arc/course_model_V.nsbmd` is the one exception that has both an embedded `TEX0` and `data/Course/MR_stage3Tex_arc/course_model_V.nsbtx`; both contain one texture named `nd_VR_N05`. The course loader opens the external `_V.nsbtx` and passes it to the model texture bind, so the external set is the one bound and the embedded copy is redundant.

Emblems are separate from the character texture set. `character/<character>/P_XX.nsbtx` holds the face and body textures, while `emblem/<XX>_emblem.nsbtx` holds a texture named `emblem`; the kart material `kart_emblem` is the binding point, and the checked character models have no emblem material. `emblemFrame.nsbtx` holds `emblemA` and is the frame/overlay set.

Two effect texture sets, `MainRace_arc/effect/award_track.nsbtx` and `hanegame.nsbtx`, have no same-basename NSBMD. They are the trail-effect textures: the race effect loader opens `award_track.nsbtx` while the display mode is the award scene and `hanegame.nsbtx` otherwise, binds it to a 16×8 trail texture and reuses the main texture/palette slots. They are not model pairs and are intentionally absent from the model table.

Animation pairing is weaker than texture pairing and follows naming conventions:

| Animation | Pairing rule | Stock result |
|---|---|---|
| NSBTA | same basename as the model, same directory | 50 of 50 |
| NSBTP | same basename as the model, same directory | 88 of 91; exceptions are shared `P_faceanim.nsbtp` and the `countD.nsbtp` variant of `count.nsbmd` |
| NSBMA | same basename as the model, or a shared effect model | 24 of 29; the five exceptions are `bk_wave`, `start`, `goal`, `failed` and `complete`, which target a different or shared model |
| NSBCA | same basename, or `<base>_<clip>` for a multi-clip object | 49 exact matches plus 87 suffixed or shared clips |

NSBCA binds by node index, not by node name. Each node record’s flag word carries the target model-node index in bits 24–31, and `node_count` must not exceed the model’s node count. NSBTP, NSBTA and NSBMA bind by material name: their dictionary entry names are looked up in the model’s material dictionary.

The name joins hold in most of the corpus but not all. NSBTP material names match the paired model in 86 of 88 same-basename files; NSBTA material names match in 48 of 50. All four exceptions are orphaned names that occur in no other stock file:

| Animation | Target absent from the paired model | Paired model material(s) |
|---|---|---|
| `data/Course/donkey_course_arc/MapObj/dossun.nsbtp` | `lambert152` | `dosune_ob` (material), `ob_dosune` (texture) |
| `data/Course/old_hyudoro_64_arc/course_model.nsbtp` | `hyu_ike1` | `Mhyu_renga2`, `hyu_StartLine`, `hyu_arrow1`, … |
| `data/Course/mini_stage4_arc/course_model.nsbta` | `LDashJ` | `Dash` (and seven others) |
| `data/Course/town_course_arc/course_model.nsbta` | `tw_sea` | `StartLine`, `tw_MonZo`, `tw_road1`, … |

The `dossun` case is the clearest: the pattern animation also names textures `dossun_cmp4.*` and palettes `dossun_*_pl`, while the model carries texture `ob_dosune` and has no palette names. None of those strings exists anywhere else in the corpus. The other three animations likewise name a material that no stock model defines; `mini_stage4` has a `Dash` material but no `LDashJ`, and `town_course` has no sea material because its water is a separate map object. `dossun.nsbtp` has no loader call site at all; the other three are opened by the course loader and fail the name lookup, so they are inert. Their origin is inferred to be an earlier or alternate model revision whose material was renamed or removed before shipping.

All 24 same-basename NSBMA files match their model materials.

### Selection by object and character

Object IDs are stored in the `OBJI` section of each NKM at record offset +0x24; the format is documented in [`formats-mkds-course.md`](../mkds/formats-mkds-course.md). The stock corpus has 3917 OBJI instances over 112 distinct IDs. An object ID selects a loader, and the loader chooses the model file and any animation set; the ID itself does not index animation dictionaries. One model file can serve several IDs, especially the `_nocol` variants, the fixed/moving Wiggler IDs, and the traffic IDs.

The following table lists the model basenames used by representative IDs. The path is `data/Course/<course>_arc/MapObj/<name>.nsbmd` unless a path is stated. A course arc only ships the objects its NKM uses, so the same ID can be absent from another course.

| Object IDs | Model basename(s) | Animations |
|---|---|---|
| 1, 3, 6, 9, 12 | `beach_waterA/C`, `town_waterA/C`, `yoshi_waterC`, `hyudoro_waterA/C`, `mini_stage3_waterA/C` | none; the water manager animates positions |
| 5, 14, 15 | `water_efct` | `water_efct.nsbca` (wave), `water_efct.nsbma` |
| 13 | `puddle` | none |
| 101, 201 | `MainRace_arc/MapObj/box`, `question` | none |
| 103 | `woodbox1` | none |
| 104 | `data/MissionRun/coin` | `coin.nsbtp` |
| 106 | `shine16` | `shine16.nsbtp` |
| 108 | `balloon` | `balloon.nsbtp` |
| 110 | `data/MissionRun/MissionGate` | `MissionGate.nsbtp`, `.nsbma` |
| 112 | `shine_balloon` | none |
| 202 | `koopa_block` | none |
| 203 | `gear_black`, `gear_white` | none |
| 204 | `bridge` | `bridge.nsbca` |
| 205 | `second_hand` | none |
| 207 | `pendulum`, `pendulum_shadow` | none |
| 208, 209 | `rotary_room`, `rotary_bridge` | none |
| 210 | `dram` | none |
| 301, 302 | `BeachTree1` | none |
| 303 | `earthen_pipe1`, `earthen_pipe2` | none |
| 304 | `opa_tree1` | none |
| 305 | `OlgPipe1` | none |
| 306 | `OlgMush1` | none |
| 307 | `of6yoshi1` | none |
| 308 | `cow` | `cow.nsbtp` |
| 309 | `NsCannon1` | none |
| 310 | `mini_dokan` | none |
| 312, 319 | `GardenTree1` | none |
| 314 | `CrossTree1` | none |
| 315 | `teresa`, `teresa_shadow` | `teresa.nsbtp` |
| 316 | `bakubaku`, `baku_shadow` | none |
| 318 | `Bank_Tree1` | none |
| 320 | `chandelier` | `chandelier.nsbca` |
| 321, 325 | `TownTree1` | none |
| 322 | `MarioTree3` | none |
| 323, 326 | `Snow_Tree1` | none |
| 327, 328 | `DeTree1` | none |
| 329 | `BankEgg1` | none |
| 331, 332 | `KinoHouse1`, `KinoHouse2` | none |
| 333, 334 | `KinoMount1`, `KinoMount2` | none |
| 335 | `olaTree1c` | none |
| 336 | `osaTree1c` | none |
| 337, 338 | `picture1`, `picture2` | `picture1.nsbca`, `picture2.nsbca` |
| 339 | `om6Tree1` | none |
| 340 | `RainStar` | `RainStar.nsbta` |
| 341, 342 | `Of6Tree1` | none |
| 343 | `TownMonte` | `TownMonte.nsbtp` |
| 344 | `airship` | none |
| 345 | `data/MissionRun/StopSign` | none |
| 401 | `kuribo` | `kuribo.nsbtp` |
| 402 | `rock`, `rock_shadow` | none |
| 403 | `dossun`, `dossun_shadow` | `dossun.nsbtp` exists but does not bind |
| 405 | `bus_a`, `bus_a_shadow` | none |
| 406, 421 | `wanwan`, `rock_shadow` | none |
| 407 | `wanwan_chain`, `wanwan_kui` | none |
| 409 | `choropu` | `choropu.nsbtp` |
| 410 | `car_a`, `car_a_shadow` | `car_a.nsbtp` |
| 412 | `truck_a`, `truck_a_shadow` | `truck_a.nsbtp` |
| 413 | `sman_top`, `sman_bottom` | none |
| 414 | `kanoke_64` | `kanoke_64.nsbca` |
| 419 | `move_tree` | `move_tree.nsbca` |
| 422 | `ob_pakkun_sf` | `ob_pakkun_sf.nsbtp` |
| 423 | `poo`, `cover`, `hole` | `poo.nsbtp` |
| 424 | `bound` | `bound.nsbtp` |
| 425 | `flipper` | `flipper.nsbtp`, `flipper.nsbta` |
| 426 | `PakkunMouth`, `PakkunZHead`, `PakkunBody` | `PakkunMouth.nsbca` |
| 428 | `crab`, `crab_hand` | `crab.nsbtp`, `crab_hand.nsbtp` |
| 429 | `sun`, `sun_LOD` | `sun.nsbca` |
| 433 | `rock2`, `rock2_shadow` | none |
| 434 | `sanbo_h`, `sanbo_b` | none |

ID 111 is an item-box variant with a dispatch-table entry, but its definition is a data symbol without source and no model string is associated with it; the shared item-box model is plausible but not confirmed.

IDs 8, 10, 16, 105, 107, 317, 438, 511 and 512 are emitters, controllers or particles and have no corresponding NSBMD in the stock corpus.

Two further IDs never reach an object definition. The dispatch table has 124 populated entries followed by zero-filled slots; lookup is a linear scan over those 124 entries and a miss returns no definition, so the NKM instance is skipped without a default or fallback.

- **109**: 103 instances in seven `data/Course/*/MissionRun/*_tool.nkm` files (`mr54`, `mr80`, `mr15`, `mr53`, `mr43`, `mr86`, `mr83`). Mission mode loads these `_tool.nkm` maps at runtime, so the entries are live. The group-config row for 109 is byte-identical to item box 101: 3D model present, near 15, far 1300, collision type 1, width 10. The instances carry `settings[0]` 2 or 7 and no other non-zero setting, and the mission archive has no dedicated model; the only matching 3D assets are the shared `MainRace_arc/MapObj/box.nsbmd` and `question.nsbmd`. The main dispatch table has no 109 entry, so the mission overlay must install one before lookup. The intended model is therefore the shared item box (inferred from the identical profile and the absence of any other 3D asset); the exact mission overlay initializer remains unresolved.
- **324**: 56 instances, 35 in `data/Course/donkey_course_arc/course_map.nkm` and 21 in `data/Course/luigi_course_arc/course_map.nkm`. The group-config row has 3D model present, near 110, far 2500, collision type 5, width 1 and height 100. The only same-directory models that fit that profile are `pin1.nsbmd` in both courses and `pin_head1.nsbmd` in Luigi; the pinball objects 206, 210, 424 and 425 co-occur in the same maps. The main dispatch table has no 324 entry, so the pinball overlay must install one before lookup. The model association is `pin1` plus the `pin_head1` attachment (inferred from the filenames, materials `ob_pin1`/`ob_pin_head1` and the tall thin profile); the pinball overlay object-table initializer remains unresolved.

Mission-only object IDs use models from `data/MissionRun/` and multi-clip NSBCA sets:

| Object ID | Model | NSBCA clips |
|---|---|---|
| 501 | `boss_donketu` | 4: `walk`, `hit`, `start`, `dead` |
| 502 | `king_ice_donketu` | 5: `walk`, `jump_ed`, `hit`, `wait`, `dead` |
| 503 | `kuriking` | 8, plus `kuriking.nsbta`, `.nsbtp` and `.nsbma` |
| 504 | `bomb_king` | 11, including `walk1`, `throw`, `walk2`, `jump_up`, `jump_down` |
| 507 | `iwante_l` | 10, plus `iwante_l.nsbtp` and the `sh_iwante` shadow |
| 508 | `hanachan` | 6 head clips; `hanachan_1` and `hanachan_2` add 5 body clips each |
| 509 | `king_teresa` | 5: `wait`, `start`, `fright`, `damage`, `happy` |
| 510 | `hanachan_1`..`hanachan_4` | body parts; 1 and 2 are animated, 3 and 4 are static |

Character animation selection is fixed by slot, not by object ID. The four player files are registered in the order drive, spin, win, lose. Slot 0 (`drive`) is non-looping; slots 1–3 loop. Enemy models `E_*` have no NSBCA. The shared `P_faceanim.nsbtp` is registered against every player model and animates a material whose texture names are `P_face.1` and `P_face.2`.

Kart selection is separate from object IDs. The kart body is `kart_MR_a` for the standard kart in every character slot, while the character-specific karts are `kart_XX_b` and `kart_XX_c`. Tires are `kart_tire_L`, `_M` and `_S`. The shadow is `sh_XX_a/b/c` and has no texture. The character/kart menu uses the same names under `KartModelMenu/`.

### Course-specific use

`course_model.nsbmd` is the main course geometry. It is the model used for the normal render pass; collision comes from the separate `course_collision.kcl`. `course_model_V.nsbmd` is loaded separately and rendered by the sky/backdrop path; the `V` suffix and the separate render path both point to a sky variant, but no runtime test in this repository proves the name. The main models average 14.4 materials (848 across 59), while the sky models average 1.5 (74 across 50), which is consistent with a simple backdrop.

Course animations are optional and independent: 26 main models have `course_model.nsbta` and 5 have `course_model.nsbtp`; 16 sky models have `course_model_V.nsbta` and none has a `_V` NSBTP. The game registers exactly one pattern animation and one SRT animation for the main model, and one SRT animation for the sky model, always at set index 0.

A few stock material names are special-cased by the course loader. These are material-dictionary names in `course_model.nsbmd`, not separate files:

| Material name | Course | Runtime effect |
|---|---|---|
| `ShdwOff`, `ShdwOff1`..`ShdwOff5` | all courses that contain them | assigned polygon ID 7 so the material is skipped in the shadow pass |
| `falls_01`, `falls_02` | `bank_course` | depth update disabled |
| `yogan` | `old_koopa_agb` | alpha set to 30 and depth update disabled |

The `*D_arc` course directories are the Download Play variants. This is proven by the archive path branch: it appends `D` (and `DTex`) only when the game is the multiboot child and the selected course has the D-variant flag set; the same course on a normal host uses the unsuffixed arc. The stock flag table sets it for exactly five courses: `beach_course`, `cross_course`, `mansion_course`, `old_luigi_gc` and `old_momo_64`, matching the five `*D_arc` and `*DTex_arc` directories. These arcs carry their own model and map objects, include a sky model only where the normal arc has one, and omit `MissionRun`; `mansion_courseD` has no sky model, so its texture archive has no `course_model_V.nsbtx`. They are not ordinary alternates and the normal and D files are not interchangeable. Their smaller content is consistent with the child receiving the course over the multiboot link.

Water objects use two independently moving layers, `waterA` and `waterC`, plus the shared `water_efct` splash model with its `nsbca` and `nsbma`. `data/Course/nokonoko_course_arc/MapObj/beach_waterB.nsbmd` is a third single-plane model (node `beach_waterB`, material `waterB`, texture `waterB`, one node/material/shape, 1828 bytes, the same size as but different bytes from `beach_waterA.nsbmd`). It is unused: the water state has only A and C slots, every stock water loader requests only `*_waterA` and `*_waterC`, and no string in the checked ARM9 or overlay code contains `waterB`. It is a leftover third layer, not a fallback or an alternate for either loaded layer.

Shadow models are separate untextured files named `*_shadow.nsbmd`, `sh_*.nsbmd`, `*_s.nsbmd` or `sh_circle`/`sh_iwante`. They are loaded through a shadow-specific path, drawn with a per-object polygon ID (7 or 63 in the checked loaders) and have no `.nsbtx`. They are not interchangeable with the textured parent model.

Billboard objects are the single-node, camera-facing models loaded through the billboard helpers: trees, puddle, shine balloon, iron ball, cow, Teresa, Town Monte, crab, Poo, Basabasa and the balloon/shine effects. The `_nocol` IDs (301, 319, 321, 323, 327, 341) reuse the same model as their colliding counterparts; the difference is collision/behaviour, not geometry. This classification is inferred from the loader calls.

Cup content is 2D. Cup marks, cup icons and trophy icons live in `Scene/Menu_arc/common/` as NCGR/NCLR/NCER/NSCR files, and the course/cup select screens are NSCR backgrounds. The only 3D cup assets are the result trophies. The result scene selects one of nine models by cup index: `T_kino` = Mushroom, `T_flow` = Flower, `T_star` = Star, `T_spec` = Special, `T_kora` = Shell, `T_bana` = Banana, `T_kono` = Leaf, `T_thun` = Lightning and `trophy` = the generic/download result. Each cup also has a same-basename `.nsbtp`. The `_a`, `_b` and `_c` models next to each base are not opened by the trophy loader; the loader requests only `T_<cup>.nsbmd` and `T_<cup>.nsbtp`, so the 24 part files are unused retail data.

### Configuration fields that matter for editing

| Editing concern | Field to inspect | Location | Consequence |
|---|---|---|---|
| Joint targets | node dictionary names and order | `MDL0` model node dictionary | NSBCA stores node indices, so reordering nodes retargets clips |
| Material targets | material dictionary names | material set dictionary | NSBTP, NSBTA and NSBMA look up these names |
| Texture identity | texture dictionary names and order | `TEX0` texture dictionary | NSBTP frame values select texture indices; names are resolved through this table |
| Texture encoding | `texture_image_param`, `extra_param` | `TEX0` texture entry | address, width, height, format and transparency |
| Material texture binding | material `texture_image_param` and mask | material record +0x14 and +0x18 | all stock masks are `0xFFFFFFFF`; the low address bits come from the material and the format/size bits from the texture entry |
| Geometry | display-list offset and size | shape record | shape flags, vertex/polygon counts in model info |
| Animation length | `frame_count` | BCA/BTP/BTA/BMA record | loop timing is set by the loader, not by the file |
| Texture pattern targets | frame values and name tables | NSBTP record | texture/palette indices must exist in the bound texture set |
| SRT channels | `scale_*`, `rotation`, `translation_*` info words | NSBTA entry | constant bit versus offset table; the record mode byte is inert and the model’s `texture_matrix_mode` selects the formula |
| Material animation | dictionary name and five packed color elements | NSBMA entry | diffuse, ambient, specular, emission and alpha; binding is by material name |

Model info’s `node_count`, `material_count` and `shape_count` equal the corresponding dictionary counts in every stock model. Keep that invariant; a mismatch is a reliable corruption signal.

### Practical edit guidance

Replacing a model is safe when the replacement keeps the same dictionary names, node order, material order and texture-address layout, or when no animation references the changed names. A model with a different node order silently retargets NSBCA clips; a model with different material names silently disables NSBTP, NSBTA and NSBMA binding; a model with different texture addresses samples the wrong part of the texture set. These failures do not produce a parse error.

Replacing a texture requires more than changing the image bytes. The texture dictionary name and order are the join key for NSBTP, and the material’s `texture_image_param` supplies the low address bits while the NSBTX texture entry supplies the high format/size bits. Keep those fields identical, or update both the NSBTX entry and every referring NSBMD material. The three stock files with fewer palettes than textures (`old_mario_gc` course model 23/22, `luigi_course` course model 9/8, `old_noko_sfc` texture set 20/16) share palettes across textures, so editing one palette changes several textures.

Replacing an animation requires the same binding keys. NSBCA node count must not exceed the model node count, and the high-byte node indices must still name the intended joints. NSBTP and NSBTA dictionary names must exist in the model material dictionary, and NSBTP texture/palette names must exist in the texture set. NSBMA targets material names and its five color elements are decoded, so a replacement must keep the same material names and channel table layout.

The safest whole-file swaps are the ones that keep the filename, format and binding keys: shadow models of the same node count, map objects with embedded `TEX0` and no animations, trophy part models, and a kart body together with its same-basename `.nsbtx`. Swapping only an NSBMD across two objects with different material or node names is unsafe even when both files parse. Swapping only an NSBTX when NSBTP or NSBTA exists is unsafe even when the texture count matches, because the pattern animation resolves texture names, not just indices.

Course edits need both halves of the course model decision. If `course_model.nsbmd` is replaced with a model that embeds `TEX0`, the external `course_model.nsbtx` becomes redundant but is still shipped; if the replacement does not embed `TEX0`, the external file must exist and its material names and addresses must match. The sky model is a separate file with its own optional `_V.nsbtx` and `_V.nsbta`; changing only the main model leaves the old sky in place.

The NSBTA writer is byte-stable for 44 of 50 stock files. The six exceptions are the three padding cases (`pinball_course`, `rainbow_course`, `clock_course`), the two `dash` count cases (`stadium_course`, `wario_course`) and `kuriking.nsbta`. For those, patch the original in place or diff the rewrite; for `stadium_course`/`wario_course` do not trust the rewritten `dash` translation-T table to have the stock length. The same caution applies to any tool that rewrites a dictionary: entry order, 16-byte name padding, 4-byte data-block alignment and block sizes are part of the byte identity.

## Current status

| Format | Read | Write | Corpus note |
|---|---|---|---|
| NSBMD / MDL0 | yes | yes | byte-stable round trip |
| NSBTX / TEX0 | yes | yes | byte-stable round trip |
| NSBCA / JNT0 | yes | no | read-only |
| NSBTP / PAT0 | yes | no | read-only |
| NSBTA / SRT0 | yes | yes | 44/50 byte-stable; six differ in element padding/count |
| NSBMA / MAT0 | header only | no | runtime hooks, no parser |

Byte-stable means the parsed structures can be written back with the same bytes, including dictionary order, names, padding and embedded `TEX0` blocks.

## Known unknowns

- SBC bytecode and shape display-list commands are stored but not decoded here. Decoding them requires the Nitro SBC interpreter, not a file-format reader; the model layout stops at the shape record.
- Object IDs 109 and 324 are absent from the main dispatch table. Their overlay initializers (the mission object table for 109 and the pinball object table for 324) are not in the checked source, so the models are inferred from the matching group-config profiles and co-located files: the shared item box for 109, and `pin1` plus `pin_head1` for 324. The exact attachment role of `pin_head1` is part of that unresolved loader.
- The four orphaned NSBTP/NSBTA files are proven unbindable; which earlier model revision they were authored for is not known. `dossun.nsbtp` has no loader call site; the other three are loaded but fail material-name lookup.

## Header

All structures, flag masks and size constants in this note are declared in the [`../include/nitro/g3d.h`](../include/nitro/g3d.h) umbrella and its [`../include/nitro/g3d/`](../include/nitro/g3d/) subheaders (`common`, `nsbmd`, `nsbtx`, `nsbca`, `nsbtp`, `nsbta`, `nsbma`). The headers compile standalone with a C11 host compiler and contain no game data or MKDS addresses.
