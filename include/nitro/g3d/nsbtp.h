/* nsbtp.h — Nitro NSBTP (BTP0) texture patterns and PAT0 blocks. SPDX-License-Identifier: MIT */
#pragma once

#include <stddef.h>
#include <stdint.h>

#include "nitro/bits.h"
#include "nitro/fx.h"
#include "nitro/g3d/common.h"

#define G3D_BTP_HEADER_SIZE 12u
#define G3D_BTP_ENTRY_SIZE  8u
#define G3D_BTP_FRAME_SIZE  4u

typedef struct {
    G3dAnimationHeader header;
    uint16_t frame_count;
    uint8_t texture_count;
    uint8_t palette_count;
    uint16_t texture_names_offset;
    uint16_t palette_names_offset;

} G3dTexturePatternHeader;

typedef struct {
    uint16_t frame_value_count;
    uint16_t flags;
    Fx16 frame_ratio;
    uint16_t frame_value_offset;
} G3dTexturePatternEntry;

typedef union {
    uint16_t raw;
    struct {
        uint16_t no_palette_animation : 1;
        uint16_t reserved : 15;
    } bits;
} G3dTexturePatternFlags;

#define G3D_BTP_NO_PALETTE_ANIMATION NITRO_BIT(0)

_Static_assert(sizeof(G3dTexturePatternFlags) == 2, "G3D texture pattern flags");

typedef struct {
    uint16_t frame;
    uint8_t texture_index;
    uint8_t palette_index;
} G3dTexturePatternFrame;

_Static_assert(sizeof(G3dTexturePatternHeader) == G3D_BTP_HEADER_SIZE,
               "G3D texture pattern header");
_Static_assert(offsetof(G3dTexturePatternHeader, frame_count) == 0x04,
               "G3D texture pattern frame count");
_Static_assert(offsetof(G3dTexturePatternHeader, texture_names_offset) == 0x08,
               "G3D texture names offset");
_Static_assert(offsetof(G3dTexturePatternHeader, palette_names_offset) == 0x0A,
               "G3D palette names offset");
_Static_assert(sizeof(G3dTexturePatternEntry) == G3D_BTP_ENTRY_SIZE,
               "G3D texture pattern entry");
_Static_assert(offsetof(G3dTexturePatternEntry, flags) == 0x02,
               "G3D texture pattern flags");
_Static_assert(sizeof(G3dTexturePatternFrame) == G3D_BTP_FRAME_SIZE,
               "G3D texture pattern frame");
