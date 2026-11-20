/* nsbca.h — Nitro NSBCA (BCA0) joint animations and JNT0 blocks. SPDX-License-Identifier: MIT */
#pragma once

#include <stddef.h>
#include <stdint.h>

#include "nitro/bits.h"
#include "nitro/fx.h"
#include "nitro/g3d/common.h"

#define G3D_BCA_HEADER_SIZE 20u

typedef union {
    uint32_t raw;
    struct {
        uint32_t interpolation : 1;
        uint32_t end_to_start : 1;
        uint32_t reserved : 30;
    } bits;
} G3dBcaFlags;

#define G3D_BCA_FLAG_INTERPOLATION NITRO_BIT(0)
#define G3D_BCA_FLAG_END_TO_START NITRO_BIT(1)

typedef union {
    uint32_t raw;
    struct {
        uint32_t identity : 1;
        uint32_t identity_translation : 1;
        uint32_t base_translation : 1;
        uint32_t const_translation_x : 1;
        uint32_t const_translation_y : 1;
        uint32_t const_translation_z : 1;
        uint32_t identity_rotation : 1;
        uint32_t base_rotation : 1;
        uint32_t const_rotation : 1;
        uint32_t identity_scale : 1;
        uint32_t base_scale : 1;
        uint32_t const_scale_x : 1;
        uint32_t const_scale_y : 1;
        uint32_t const_scale_z : 1;
        uint32_t reserved : 10;
        uint32_t node_index : 8;
    } bits;
} G3dBcaNodeFlags;

#define G3D_BCA_NODE_IDENTITY NITRO_BIT(0)
#define G3D_BCA_NODE_IDENTITY_TRANSLATION NITRO_BIT(1)
#define G3D_BCA_NODE_BASE_TRANSLATION NITRO_BIT(2)
#define G3D_BCA_NODE_CONST_TRANSLATION_X NITRO_BIT(3)
#define G3D_BCA_NODE_CONST_TRANSLATION_Y NITRO_BIT(4)
#define G3D_BCA_NODE_CONST_TRANSLATION_Z NITRO_BIT(5)
#define G3D_BCA_NODE_IDENTITY_ROTATION NITRO_BIT(6)
#define G3D_BCA_NODE_BASE_ROTATION NITRO_BIT(7)
#define G3D_BCA_NODE_CONST_ROTATION NITRO_BIT(8)
#define G3D_BCA_NODE_IDENTITY_SCALE NITRO_BIT(9)
#define G3D_BCA_NODE_BASE_SCALE NITRO_BIT(10)
#define G3D_BCA_NODE_CONST_SCALE_X NITRO_BIT(11)
#define G3D_BCA_NODE_CONST_SCALE_Y NITRO_BIT(12)
#define G3D_BCA_NODE_CONST_SCALE_Z NITRO_BIT(13)
#define G3D_BCA_NODE_INDEX_MASK NITRO_MASK(8, 24)

_Static_assert(sizeof(G3dBcaFlags) == 4, "G3D BCA flags");
_Static_assert(sizeof(G3dBcaNodeFlags) == 4, "G3D BCA node flags");

typedef union {
    uint16_t raw;
    struct {
        uint16_t index : 15;
        uint16_t pivot : 1;
    } bits;
} G3dBcaRotationIndex;

#define G3D_BCA_ROTATION_INDEX_PIVOT NITRO_BIT(15)
#define G3D_BCA_ROTATION_INDEX_MASK NITRO_MASK(15, 0)

_Static_assert(sizeof(G3dBcaRotationIndex) == 2, "G3D BCA rotation index");

typedef struct {
    G3dAnimationHeader header;
    uint16_t frame_count;
    uint16_t node_count;
    uint32_t flags;
    uint32_t pivot_rotation_offset;
    uint32_t matrix_rotation_offset;

} G3dJointAnimationHeader;

typedef struct {
    uint16_t info;
    Fx16 a;
    Fx16 b;
} G3dJointPivotRotation;

typedef struct {
    uint16_t data[5];
} G3dJointMatrixRotation;

_Static_assert(sizeof(G3dJointAnimationHeader) == G3D_BCA_HEADER_SIZE,
               "G3D joint animation header");
_Static_assert(offsetof(G3dJointAnimationHeader, frame_count) == 0x04,
               "G3D joint frame count");
_Static_assert(offsetof(G3dJointAnimationHeader, node_count) == 0x06,
               "G3D joint node count");
_Static_assert(offsetof(G3dJointAnimationHeader, flags) == 0x08,
               "G3D joint flags");
_Static_assert(offsetof(G3dJointAnimationHeader, pivot_rotation_offset) == 0x0C,
               "G3D pivot rotation offset");
_Static_assert(offsetof(G3dJointAnimationHeader, matrix_rotation_offset) == 0x10,
               "G3D matrix rotation offset");
_Static_assert(sizeof(G3dJointPivotRotation) == 6, "G3D pivot rotation");
_Static_assert(sizeof(G3dJointMatrixRotation) == 10, "G3D matrix rotation");
