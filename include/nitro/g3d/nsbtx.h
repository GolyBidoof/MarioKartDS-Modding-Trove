/* nsbtx.h — Nitro NSBTX (BTX0) textures and TEX0 blocks. SPDX-License-Identifier: MIT */
#pragma once

#include <stddef.h>
#include <stdint.h>

#include "nitro/g3d/common.h"

#define G3D_TEX0_HEADER_SIZE        8u
#define G3D_TEX_INFO_OFFSET         0x08u
#define G3D_TEX_4X4_INFO_OFFSET     0x18u
#define G3D_TEX_PALETTE_INFO_OFFSET 0x2Cu
#define G3D_TEX_INFO_SIZE           16u
#define G3D_TEX_4X4_INFO_SIZE       20u
#define G3D_TEX_PALETTE_INFO_SIZE   16u

#define G3D_TEX_SIZE_UNIT           8u

_Static_assert(G3D_TEX_SIZE_UNIT == 8u, "G3D texture size unit");

typedef union {
    uint16_t raw;
    struct {
        uint16_t loaded : 1;
        uint16_t reserved : 15;
    } bits;
} G3dTextureFlag;

typedef union {
    uint16_t raw;
    struct {
        uint16_t loaded : 1;
        uint16_t reserved : 14;
        uint16_t four_color : 1;
    } bits;
} G3dPaletteFlag;

typedef union {
    uint16_t raw;
    struct {
        uint16_t four_by_four : 1;
        uint16_t reserved : 15;
    } bits;
} G3dPaletteEntryFlag;

typedef struct {
    uint32_t vram_key;
    uint16_t texture_data_size;
    uint16_t dictionary_offset;
    G3dTextureFlag flag;
    uint16_t reserved;
    uint32_t texture_data_offset;
} G3dTextureInfo;

typedef struct {
    uint32_t vram_key;
    uint16_t texture_data_size;
    uint16_t dictionary_offset;
    G3dTextureFlag flag;
    uint16_t reserved;
    uint32_t texture_data_offset;
    uint32_t palette_index_offset;
} G3dTexture4x4Info;

typedef struct {
    uint32_t vram_key;
    uint16_t palette_data_size;
    G3dPaletteFlag flag;
    uint16_t dictionary_offset;
    uint16_t reserved;
    uint32_t palette_data_offset;
} G3dPaletteInfo;

typedef struct {
    G3dTextureImageParam texture_image_param;
    G3dTextureExtraParam extra_param;
} G3dTextureEntry;

typedef struct {
    uint16_t palette_offset;
    G3dPaletteEntryFlag flag;
} G3dPaletteEntry;

typedef struct {
    G3dBlockHeader block;
    G3dTextureInfo texture_info;
    G3dTexture4x4Info texture4x4_info;
    G3dPaletteInfo palette_info;
} G3dTextureSetHeader;

_Static_assert(sizeof(G3dTextureFlag) == 2, "G3D texture flag");
_Static_assert(sizeof(G3dPaletteFlag) == 2, "G3D palette flag");
_Static_assert(sizeof(G3dPaletteEntryFlag) == 2, "G3D palette entry flag");
_Static_assert(sizeof(G3dTextureInfo) == G3D_TEX_INFO_SIZE, "G3D texture info");
_Static_assert(offsetof(G3dTextureInfo, texture_data_size) == 0x04,
               "G3D texture size");
_Static_assert(offsetof(G3dTextureInfo, dictionary_offset) == 0x06,
               "G3D texture dictionary");
_Static_assert(offsetof(G3dTextureInfo, flag) == 0x08,
               "G3D texture flag");
_Static_assert(offsetof(G3dTextureInfo, reserved) == 0x0A,
               "G3D texture reserved word");
_Static_assert(offsetof(G3dTextureInfo, texture_data_offset) == 0x0C,
               "G3D texture data offset");
_Static_assert(sizeof(G3dTexture4x4Info) == G3D_TEX_4X4_INFO_SIZE,
               "G3D 4x4 texture info");
_Static_assert(offsetof(G3dTexture4x4Info, dictionary_offset) == 0x06,
               "G3D 4x4 dictionary");
_Static_assert(offsetof(G3dTexture4x4Info, palette_index_offset) == 0x10,
               "G3D 4x4 palette index offset");
_Static_assert(sizeof(G3dPaletteInfo) == G3D_TEX_PALETTE_INFO_SIZE,
               "G3D palette info");
_Static_assert(offsetof(G3dPaletteInfo, dictionary_offset) == 0x08,
               "G3D palette dictionary");
_Static_assert(offsetof(G3dPaletteInfo, flag) == 0x06,
               "G3D palette flag");
_Static_assert(offsetof(G3dPaletteInfo, reserved) == 0x0A,
               "G3D palette reserved word");
_Static_assert(sizeof(G3dTextureEntry) == 8, "G3D texture entry");
_Static_assert(sizeof(G3dPaletteEntry) == 4, "G3D palette entry");
_Static_assert(sizeof(G3dTextureSetHeader) == 60, "G3D texture set header");
_Static_assert(offsetof(G3dTextureSetHeader, texture_info) == G3D_TEX_INFO_OFFSET,
               "G3D texture info offset");
_Static_assert(offsetof(G3dTextureSetHeader, texture4x4_info) ==
               G3D_TEX_4X4_INFO_OFFSET, "G3D 4x4 info offset");
_Static_assert(offsetof(G3dTextureSetHeader, palette_info) ==
               G3D_TEX_PALETTE_INFO_OFFSET, "G3D palette info offset");
