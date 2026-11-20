/* kcl.h — KCL collision. SPDX-License-Identifier: MIT */
#pragma once

#include <stddef.h>
#include <stdint.h>

#include "nitro/fx.h"

#define KCL_HEADER_SIZE 60u
#define KCL_PRISM_SIZE  16u

typedef uint32_t KclOffset;
typedef uint16_t KclIndex;
typedef uint16_t KclAttribute;

typedef struct {
    Fx32 x;
    Fx32 y;
    Fx32 z;
} KclVecFx32;

typedef struct {
    Fx16 x;
    Fx16 y;
    Fx16 z;
} KclVecFx16;

_Static_assert(sizeof(KclVecFx32) == 12, "KCL FX32 vector");
_Static_assert(sizeof(KclVecFx16) == 6, "KCL FX16 vector");

typedef struct {
    KclOffset position_table;
    KclOffset normal_table;
    KclOffset prism_table_stored;
    KclOffset block_table;
    Fx32     prism_thickness;
    KclVecFx32 area_min;
    uint32_t area_x_mask;
    uint32_t area_y_mask;
    uint32_t area_z_mask;
    uint32_t block_width_shift;
    uint32_t area_x_blocks_shift;
    uint32_t area_xy_blocks_shift;
    Fx32     sphere_radius;
} KclHeader;

_Static_assert(sizeof(KclHeader) == KCL_HEADER_SIZE, "KCL header");
_Static_assert(offsetof(KclHeader, prism_thickness) == 0x10,
               "KCL prism thickness");
_Static_assert(offsetof(KclHeader, area_min) == 0x14, "KCL area minimum");
_Static_assert(offsetof(KclHeader, sphere_radius) == 0x38,
               "KCL sphere radius");

typedef struct {
    Fx32     height;
    KclIndex position_index;
    KclIndex face_normal_index;
    KclIndex edge_normal_index[3];
    KclAttribute attribute;
} KclPrism;

_Static_assert(sizeof(KclPrism) == KCL_PRISM_SIZE, "KCL prism");
