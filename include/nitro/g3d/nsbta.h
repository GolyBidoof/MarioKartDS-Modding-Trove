/* nsbta.h — Nitro NSBTA (BTA0) texture SRT animations and SRT0 blocks. SPDX-License-Identifier: MIT */
#pragma once

#include <stddef.h>
#include <stdint.h>

#include "nitro/g3d/common.h"

#define G3D_BTA_HEADER_SIZE     8u
#define G3D_BTA_ENTRY_SIZE      40u

#define G3D_BTA_DATA_ALIGNMENT  4u

typedef union {
    uint32_t raw;
    struct {
        uint32_t last_frame : 16;
        uint32_t reserved : 12;
        uint32_t fx16 : 1;
        uint32_t constant : 1;
        uint32_t step : 2;
    } bits;
} G3dSrtElementInfo;

typedef enum {
    G3D_SRT_STEP_1 = 0,
    G3D_SRT_STEP_2 = 1,
    G3D_SRT_STEP_4 = 2
} G3dSrtStep;

typedef union {
    uint8_t raw;
    struct {
        uint8_t interpolation : 1;
        uint8_t end_to_start : 1;
        uint8_t reserved : 6;
    } bits;
} G3dTextureSrtFlags;

typedef struct {
    G3dAnimationHeader header;
    uint16_t frame_count;
    G3dTextureSrtFlags flags;
    uint8_t texture_matrix_mode;

} G3dTextureSrtHeader;

typedef struct {
    G3dSrtElementInfo scale_s;
    uint32_t scale_s_offset;
    G3dSrtElementInfo scale_t;
    uint32_t scale_t_offset;
    G3dSrtElementInfo rotation;
    uint32_t rotation_offset;
    G3dSrtElementInfo translation_s;
    uint32_t translation_s_offset;
    G3dSrtElementInfo translation_t;
    uint32_t translation_t_offset;
} G3dTextureSrtEntry;

_Static_assert(sizeof(G3dSrtElementInfo) == 4, "G3D SRT element info");
_Static_assert(sizeof(G3dTextureSrtFlags) == 1, "G3D SRT flags");
_Static_assert(sizeof(G3dTextureSrtHeader) == G3D_BTA_HEADER_SIZE,
               "G3D texture SRT header");
_Static_assert(offsetof(G3dTextureSrtHeader, flags) == 0x06,
               "G3D texture SRT flags");
_Static_assert(offsetof(G3dTextureSrtHeader, texture_matrix_mode) == 0x07,
               "G3D texture SRT matrix mode");
_Static_assert(sizeof(G3dTextureSrtEntry) == G3D_BTA_ENTRY_SIZE,
               "G3D texture SRT entry");
_Static_assert(offsetof(G3dTextureSrtEntry, rotation) == 0x10,
               "G3D SRT rotation");
_Static_assert(offsetof(G3dTextureSrtEntry, translation_t_offset) == 0x24,
               "G3D SRT translation T offset");
