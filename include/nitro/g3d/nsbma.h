/* nsbma.h — Nitro NSBMA (BMA0) material animations and MAT0 blocks. SPDX-License-Identifier: MIT */
#pragma once

#include <stddef.h>
#include <stdint.h>

#include "nitro/g3d/common.h"

#define G3D_BMA_HEADER_SIZE 8u
#define G3D_BMA_ENTRY_SIZE  20u

typedef union {
    uint16_t raw;
    struct {
        uint16_t interpolation : 1;
        uint16_t end_to_start : 1;
        uint16_t reserved : 14;
    } bits;
} G3dMaterialAnimationFlags;

typedef struct {
    G3dAnimationHeader header;
    uint16_t frame_count;
    G3dMaterialAnimationFlags flags;

} G3dMaterialAnimationHeader;

typedef union {
    uint32_t raw;
    struct {
        uint32_t offset_or_constant : 16;
        uint32_t last_interp_frame : 13;
        uint32_t constant : 1;
        uint32_t step : 2;
    } bits;
} G3dMaterialColorElement;

typedef enum {
    G3D_MATCANM_STEP_1 = 0,
    G3D_MATCANM_STEP_2 = 1,
    G3D_MATCANM_STEP_4 = 2
} G3dMaterialAnimStep;

typedef struct {
    G3dMaterialColorElement diffuse;
    G3dMaterialColorElement ambient;
    G3dMaterialColorElement specular;
    G3dMaterialColorElement emission;
    G3dMaterialColorElement polygon_alpha;
} G3dMaterialAnimationEntry;

_Static_assert(sizeof(G3dMaterialAnimationFlags) == 2,
               "G3D material animation flags");
_Static_assert(sizeof(G3dMaterialAnimationHeader) == G3D_BMA_HEADER_SIZE,
               "G3D material animation header");
_Static_assert(offsetof(G3dMaterialAnimationHeader, frame_count) == 0x04,
               "G3D material animation frame count");
_Static_assert(offsetof(G3dMaterialAnimationHeader, flags) == 0x06,
               "G3D material animation flags offset");
_Static_assert(sizeof(G3dMaterialColorElement) == 4,
               "G3D material color element");
_Static_assert(sizeof(G3dMaterialAnimationEntry) == G3D_BMA_ENTRY_SIZE,
               "G3D material animation entry");
_Static_assert(offsetof(G3dMaterialAnimationEntry, polygon_alpha) == 0x10,
               "G3D material animation alpha offset");
