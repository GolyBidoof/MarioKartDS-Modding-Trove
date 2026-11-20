/* common.h — shared G3D envelope, dictionary and animation header. SPDX-License-Identifier: MIT */
#pragma once

#include <stddef.h>
#include <stdint.h>

#include "nitro/bits.h"

#define G3D_HEADER_SIZE          16u
#define G3D_BYTE_ORDER           0xFEFFu
#define G3D_BLOCK_ALIGNMENT      4u
#define G3D_MAX_BLOCKS           2u
#define G3D_NAME_SIZE            16u
#define G3D_FILE_VERSION_BMD0    2u
#define G3D_FILE_VERSION_OTHER   1u

#define G3D_MAGIC(a, b, c, d) \
    ((uint32_t)(a) | ((uint32_t)(b) << 8) | ((uint32_t)(c) << 16) | \
     ((uint32_t)(d) << 24))

#define G3D_MAGIC_BMD0 G3D_MAGIC('B', 'M', 'D', '0')
#define G3D_MAGIC_BTX0 G3D_MAGIC('B', 'T', 'X', '0')
#define G3D_MAGIC_BCA0 G3D_MAGIC('B', 'C', 'A', '0')
#define G3D_MAGIC_BTP0 G3D_MAGIC('B', 'T', 'P', '0')
#define G3D_MAGIC_BTA0 G3D_MAGIC('B', 'T', 'A', '0')
#define G3D_MAGIC_BMA0 G3D_MAGIC('B', 'M', 'A', '0')

#define G3D_MAGIC_MDL0 G3D_MAGIC('M', 'D', 'L', '0')
#define G3D_MAGIC_TEX0 G3D_MAGIC('T', 'E', 'X', '0')
#define G3D_MAGIC_JNT0 G3D_MAGIC('J', 'N', 'T', '0')
#define G3D_MAGIC_PAT0 G3D_MAGIC('P', 'A', 'T', '0')
#define G3D_MAGIC_SRT0 G3D_MAGIC('S', 'R', 'T', '0')
#define G3D_MAGIC_MAT0 G3D_MAGIC('M', 'A', 'T', '0')

typedef enum {
    G3D_BLOCK_SLOT_MODEL = 0,
    G3D_BLOCK_SLOT_TEXTURE = 1
} G3dBlockSlot;

typedef struct {
    char signature[4];
    uint16_t byte_order;
    uint16_t version;
    uint32_t file_size;
    uint16_t header_size;
    uint16_t block_count;
} G3dFileHeader;

typedef struct {
    G3dFileHeader header;
    uint32_t block_offset[G3D_MAX_BLOCKS];
} G3dFileTable;

typedef struct {
    char magic[4];
    uint32_t size;
} G3dBlockHeader;

typedef struct {
    uint8_t revision;
    uint8_t entry_count;
    uint16_t size;
    uint16_t reserved;
    uint16_t entry_header_offset;
} G3dDictHeader;

typedef struct {
    uint8_t reference_bit;
    uint8_t left_index;
    uint8_t right_index;
    uint8_t entry_index;
} G3dDictNode;

typedef struct {
    uint16_t entry_size;
    uint16_t name_offset;
} G3dDictEntryHeader;

typedef struct {
    G3dBlockHeader block;
    G3dDictHeader dictionary;
} G3dSetHeader;

#define G3D_ANIM_CATEGORY_JOINT       'J'
#define G3D_ANIM_CATEGORY_MATERIAL    'M'
#define G3D_ANIM_KIND_JOINT           "AC"
#define G3D_ANIM_KIND_TEXTURE_PATTERN "PT"
#define G3D_ANIM_KIND_TEXTURE_SRT     "AT"
#define G3D_ANIM_KIND_MATERIAL        "AM"

typedef struct {
    char category0;
    uint8_t revision;
    char category1[2];
} G3dAnimationHeader;

typedef union {
    uint32_t raw;
    struct {
        uint32_t address : 16;
        uint32_t reserved : 4;
        uint32_t width : 3;
        uint32_t height : 3;
        uint32_t format : 3;
        uint32_t color0_alpha : 1;
        uint32_t reserved_hi : 2;
    } bits;
} G3dTextureImageParam;

typedef union {
    uint32_t raw;
    struct {
        uint32_t orig_width : 11;
        uint32_t orig_height : 11;
        uint32_t reserved : 9;
        uint32_t same_size : 1;
    } bits;
} G3dTextureExtraParam;

_Static_assert(sizeof(G3dTextureImageParam) == 4,
               "G3D texture image parameter");
_Static_assert(sizeof(G3dTextureExtraParam) == 4,
               "G3D texture extra parameter");

typedef enum {
    G3D_TEX_FORMAT_NONE = 0,
    G3D_TEX_FORMAT_A3I5 = 1,
    G3D_TEX_FORMAT_PLTT4 = 2,
    G3D_TEX_FORMAT_PLTT16 = 3,
    G3D_TEX_FORMAT_PLTT256 = 4,
    G3D_TEX_FORMAT_COMP4X4 = 5,
    G3D_TEX_FORMAT_A5I3 = 6,
    G3D_TEX_FORMAT_DIRECT = 7
} G3dTextureFormat;

typedef union {
    uint32_t raw;
    struct {
        uint32_t reserved : 16;
        uint32_t last_frame : 13;
        uint32_t fx16 : 1;
        uint32_t step : 2;
    } bits;
} G3dAnimationInfoWord;

#define G3D_ANM_INFO_STEP_MASK NITRO_MASK(2, 30)
#define G3D_ANM_INFO_FX16 NITRO_BIT(29)
#define G3D_ANM_INFO_LAST_FRAME_MASK NITRO_MASK(13, 16)

_Static_assert(sizeof(G3dAnimationInfoWord) == 4, "G3D animation info word");

_Static_assert(sizeof(G3dFileHeader) == G3D_HEADER_SIZE, "G3D file header");
_Static_assert(offsetof(G3dFileHeader, byte_order) == 0x04, "G3D byte order");
_Static_assert(offsetof(G3dFileHeader, version) == 0x06, "G3D version");
_Static_assert(offsetof(G3dFileHeader, file_size) == 0x08, "G3D file size");
_Static_assert(offsetof(G3dFileHeader, header_size) == 0x0C, "G3D header size");
_Static_assert(offsetof(G3dFileHeader, block_count) == 0x0E, "G3D block count");
_Static_assert(offsetof(G3dFileTable, block_offset) == 0x10, "G3D block table");
_Static_assert(sizeof(G3dFileTable) == 24, "G3D file table");
_Static_assert(sizeof(G3dBlockHeader) == 8, "G3D block header");
_Static_assert(offsetof(G3dBlockHeader, size) == 0x04, "G3D block size");
_Static_assert(sizeof(G3dDictHeader) == 8, "G3D dictionary header");
_Static_assert(offsetof(G3dDictHeader, size) == 0x02, "G3D dictionary size");
_Static_assert(offsetof(G3dDictHeader, entry_header_offset) == 0x06,
               "G3D dictionary entry header");
_Static_assert(sizeof(G3dDictNode) == 4, "G3D dictionary node");
_Static_assert(sizeof(G3dDictEntryHeader) == 4, "G3D dictionary entry");
_Static_assert(sizeof(G3dSetHeader) == 16, "G3D set header");
_Static_assert(offsetof(G3dSetHeader, dictionary) == 0x08, "G3D set dictionary");
_Static_assert(sizeof(G3dAnimationHeader) == 4, "G3D animation header");
_Static_assert(offsetof(G3dAnimationHeader, category1) == 0x02,
               "G3D animation category");
