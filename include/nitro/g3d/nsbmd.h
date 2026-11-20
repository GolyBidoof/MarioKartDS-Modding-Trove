/* nsbmd.h — Nitro NSBMD (BMD0) models and MDL0 blocks. SPDX-License-Identifier: MIT */
#pragma once

#include <stddef.h>
#include <stdint.h>

#include "nitro/bits.h"
#include "nitro/fx.h"
#include "nitro/g3d/common.h"

#define G3D_MDL0_HEADER_SIZE         8u
#define G3D_MODEL_HEADER_SIZE        20u
#define G3D_MODEL_INFO_SIZE          44u
#define G3D_NODE_DATA_BASE_SIZE      4u
#define G3D_MATERIAL_BASE_SIZE       44u
#define G3D_SHAPE_HEADER_SIZE        16u
#define G3D_MATERIAL_EFFECT_MTX_SIZE 64u

typedef enum {
    G3D_SBC_TYPE_STOCK = 0
} G3dSbcType;

typedef enum {
    G3D_SCALING_RULE_STOCK = 0,
    G3D_SCALING_RULE_STOCK_ALT = 1
} G3dScalingRule;

typedef struct {
    uint32_t size;
    uint32_t sbc_offset;
    uint32_t material_offset;
    uint32_t shape_offset;
    uint32_t envelope_offset;
} G3dModelHeader;

typedef struct {
    uint8_t sbc_type;
    uint8_t scaling_rule;
    uint8_t texture_matrix_mode;
    uint8_t node_count;
    uint8_t material_count;
    uint8_t shape_count;
    uint8_t first_unused_matrix_stack;
    uint8_t reserved;
    Fx32 position_scale;
    Fx32 inverse_position_scale;
    uint16_t vertex_count;
    uint16_t polygon_count;
    uint16_t triangle_count;
    uint16_t quad_count;
    Fx16 box_x;
    Fx16 box_y;
    Fx16 box_z;
    Fx16 box_w;
    Fx16 box_h;
    Fx16 box_d;
    Fx32 box_position_scale;
    Fx32 box_inverse_position_scale;
} G3dModelInfo;

typedef union {
    uint16_t raw;
    struct {
        uint16_t translation_zero : 1;
        uint16_t rotation_zero : 1;
        uint16_t scale_one : 1;
        uint16_t rotation_pivot : 1;
        uint16_t pivot_index : 4;
        uint16_t pivot_negative : 1;
        uint16_t pivot_sign_reverse_c : 1;
        uint16_t pivot_sign_reverse_d : 1;
        uint16_t matrix_stack : 5;
    } bits;
} G3dNodeFlags;

#define G3D_NODE_TRANSLATION_ZERO NITRO_BIT(0)
#define G3D_NODE_ROTATION_ZERO NITRO_BIT(1)
#define G3D_NODE_SCALE_ONE NITRO_BIT(2)
#define G3D_NODE_ROTATION_PIVOT NITRO_BIT(3)
#define G3D_NODE_PIVOT_INDEX_MASK NITRO_MASK(4, 4)
#define G3D_NODE_PIVOT_NEGATIVE NITRO_BIT(8)
#define G3D_NODE_PIVOT_SIGN_REVERSE_C NITRO_BIT(9)
#define G3D_NODE_PIVOT_SIGN_REVERSE_D NITRO_BIT(10)
#define G3D_NODE_MATRIX_STACK_MASK NITRO_MASK(5, 11)

_Static_assert(sizeof(G3dNodeFlags) == 2, "G3D node flags");

typedef struct {
    uint16_t flags;
    Fx16 rotation_m00;
} G3dNodeDataHeader;

static inline size_t g3d_node_data_size(uint16_t flags)
{
    size_t size = G3D_NODE_DATA_BASE_SIZE;

    if ((flags & G3D_NODE_TRANSLATION_ZERO) == 0)
        size += 12;
    if ((flags & G3D_NODE_ROTATION_ZERO) == 0) {
        if (flags & G3D_NODE_ROTATION_PIVOT)
            size += 4;
        else
            size += 16;
    }
    if ((flags & G3D_NODE_SCALE_ONE) == 0)
        size += 24;
    return size;
}

typedef union {
    uint16_t raw;
    struct {
        uint16_t tex_mtx : 1;
        uint16_t tex_mtx_scale_one : 1;
        uint16_t tex_mtx_rot_zero : 1;
        uint16_t tex_mtx_trans_zero : 1;
        uint16_t orig_wh_same : 1;
        uint16_t wireframe : 1;
        uint16_t diffuse : 1;
        uint16_t ambient : 1;
        uint16_t vertex_color : 1;
        uint16_t specular : 1;
        uint16_t emission : 1;
        uint16_t shininess : 1;
        uint16_t tex_palette_base : 1;
        uint16_t effect_mtx : 1;
        uint16_t reserved : 2;
    } bits;
} G3dMaterialFlags;

#define G3D_MATERIAL_TEX_MTX NITRO_BIT(0)
#define G3D_MATERIAL_TEX_MTX_SCALE_ONE NITRO_BIT(1)
#define G3D_MATERIAL_TEX_MTX_ROT_ZERO NITRO_BIT(2)
#define G3D_MATERIAL_TEX_MTX_TRANS_ZERO NITRO_BIT(3)
#define G3D_MATERIAL_ORIG_WH_SAME NITRO_BIT(4)
#define G3D_MATERIAL_WIREFRAME NITRO_BIT(5)
#define G3D_MATERIAL_DIFFUSE NITRO_BIT(6)
#define G3D_MATERIAL_AMBIENT NITRO_BIT(7)
#define G3D_MATERIAL_VERTEX_COLOR NITRO_BIT(8)
#define G3D_MATERIAL_SPECULAR NITRO_BIT(9)
#define G3D_MATERIAL_EMISSION NITRO_BIT(10)
#define G3D_MATERIAL_SHININESS NITRO_BIT(11)
#define G3D_MATERIAL_TEX_PALETTE_BASE NITRO_BIT(12)
#define G3D_MATERIAL_EFFECT_MTX NITRO_BIT(13)

_Static_assert(sizeof(G3dMaterialFlags) == 2, "G3D material flags");

typedef struct {
    uint16_t texture_to_material_offset;
    uint16_t palette_to_material_offset;
} G3dMaterialSetHeader;

typedef struct {
    uint16_t item_tag;
    uint16_t size;
    uint32_t diffuse_ambient;
    uint32_t specular_emission;
    uint32_t polygon_attribute;
    uint32_t polygon_attribute_mask;
    uint32_t texture_image_param;
    uint32_t texture_image_param_mask;
    uint16_t texture_palette_base;
    uint16_t flags;
    uint16_t original_width;
    uint16_t original_height;
    Fx32 magnitude_s;
    Fx32 magnitude_t;
} G3dMaterialData;

typedef union {
    uint32_t raw;
    struct {
        uint32_t use_normal : 1;
        uint32_t use_color : 1;
        uint32_t use_texcoord : 1;
        uint32_t use_restore_mtx : 1;
        uint32_t reserved : 28;
    } bits;
} G3dShapeFlags;

#define G3D_SHAPE_USE_NORMAL NITRO_BIT(0)
#define G3D_SHAPE_USE_COLOR NITRO_BIT(1)
#define G3D_SHAPE_USE_TEXCOORD NITRO_BIT(2)
#define G3D_SHAPE_USE_RESTORE_MTX NITRO_BIT(3)

_Static_assert(sizeof(G3dShapeFlags) == 4, "G3D shape flags");

typedef struct {
    uint16_t item_tag;
    uint16_t size;
    uint32_t flags;
    uint32_t display_list_offset;
    uint32_t display_list_size;
} G3dShapeData;

_Static_assert(sizeof(G3dModelHeader) == G3D_MODEL_HEADER_SIZE, "G3D model header");
_Static_assert(offsetof(G3dModelHeader, sbc_offset) == 0x04, "G3D SBC offset");
_Static_assert(offsetof(G3dModelHeader, envelope_offset) == 0x10,
               "G3D envelope offset");
_Static_assert(sizeof(G3dModelInfo) == G3D_MODEL_INFO_SIZE, "G3D model info");
_Static_assert(offsetof(G3dModelInfo, node_count) == 0x03, "G3D node count");
_Static_assert(offsetof(G3dModelInfo, material_count) == 0x04,
               "G3D material count");
_Static_assert(offsetof(G3dModelInfo, shape_count) == 0x05, "G3D shape count");
_Static_assert(offsetof(G3dModelInfo, position_scale) == 0x08,
               "G3D position scale");
_Static_assert(offsetof(G3dModelInfo, vertex_count) == 0x10,
               "G3D vertex count");
_Static_assert(offsetof(G3dModelInfo, box_x) == 0x18, "G3D box");
_Static_assert(offsetof(G3dModelInfo, box_position_scale) == 0x24,
               "G3D box scale");
_Static_assert(sizeof(G3dNodeDataHeader) == G3D_NODE_DATA_BASE_SIZE,
               "G3D node data header");
_Static_assert(sizeof(G3dMaterialData) == G3D_MATERIAL_BASE_SIZE,
               "G3D material data");
_Static_assert(sizeof(G3dMaterialSetHeader) == 4, "G3D material set header");
_Static_assert(offsetof(G3dMaterialData, polygon_attribute) == 0x0C,
               "G3D polygon attribute");
_Static_assert(offsetof(G3dMaterialData, flags) == 0x1E, "G3D material flags");
_Static_assert(offsetof(G3dMaterialData, magnitude_s) == 0x24,
               "G3D material magnitude");
_Static_assert(sizeof(G3dShapeData) == G3D_SHAPE_HEADER_SIZE, "G3D shape data");
_Static_assert(offsetof(G3dShapeData, flags) == 0x04, "G3D shape flags");
_Static_assert(offsetof(G3dShapeData, display_list_offset) == 0x08,
               "G3D shape display list");
