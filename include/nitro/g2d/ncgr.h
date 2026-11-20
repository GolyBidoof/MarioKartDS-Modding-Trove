/* ncgr.h — Nitro NCGR character graphics (RGCN). SPDX-License-Identifier: MIT */
#pragma once

#include <stddef.h>
#include <stdint.h>

#include "nitro/bits.h"
#include "nitro/g2d/common.h"

#define NCGR_MAGIC "RGCN"
#define NCGR_CHAR_MAGIC "RAHC"
#define NCGR_CPOS_MAGIC "SOPC"
#define NCGR_CHAR_HEADER_SIZE 32
#define NCGR_CPOS_HEADER_SIZE 16
#define NCGR_COLOR_FORMAT_4BPP NITRO_G2D_IMAGE_FORMAT_4BPP
#define NCGR_COLOR_FORMAT_8BPP NITRO_G2D_IMAGE_FORMAT_8BPP

typedef union {
    uint32_t raw;
    struct {
        uint32_t type : 8;
        uint32_t vram_transfer : 1;
        uint32_t reserved : 23;
    } bits;
} NcgrCharacterFormat;

typedef enum {
    NCGR_CHAR_FORMAT_TILED = 0,
    NCGR_CHAR_FORMAT_BITMAP = 1
} NcgrCharacterType;

_Static_assert(sizeof(NcgrCharacterFormat) == 4, "NCGR character format word");

typedef enum {
    NCGR_MAPPING_2D = 0x00000000,
    NCGR_MAPPING_1D_32K = 0x00000010,
    NCGR_MAPPING_1D_64K = 0x00100010,
    NCGR_MAPPING_1D_128K = 0x00200010,
    NCGR_MAPPING_1D_256K = 0x00300010
} NcgrMappingType;

typedef struct {
    NitroG2dMagic magic;
    NitroG2dSize block_size;
    NitroG2dTileCount height;
    NitroG2dTileCount width;
    NitroG2dImageFormat color_format;
    NitroG2dMappingMode mapping_type;
    NcgrCharacterFormat character_format;
    NitroG2dSize data_size;
    NitroG2dOffset data_offset;
} NcgrCharBlock;

typedef struct {
    NitroG2dMagic magic;
    NitroG2dSize block_size;
    NitroG2dTileCount x;
    NitroG2dTileCount y;
    NitroG2dTileCount width;
    NitroG2dTileCount height;
} NcgrCposBlock;

_Static_assert(sizeof(NcgrCharBlock) == NCGR_CHAR_HEADER_SIZE, "NCGR CHAR block header");
_Static_assert(sizeof(NcgrCposBlock) == NCGR_CPOS_HEADER_SIZE, "NCGR CPOS block");
_Static_assert(offsetof(NcgrCharBlock, height) == 0x08, "NCGR CHAR height");
_Static_assert(offsetof(NcgrCharBlock, color_format) == 0x0C, "NCGR CHAR colour format");
_Static_assert(offsetof(NcgrCharBlock, mapping_type) == 0x10, "NCGR CHAR mapping type");
_Static_assert(offsetof(NcgrCharBlock, character_format) == 0x14, "NCGR CHAR character format");
_Static_assert(offsetof(NcgrCharBlock, data_size) == 0x18, "NCGR CHAR data size");
_Static_assert(offsetof(NcgrCharBlock, data_offset) == 0x1C, "NCGR CHAR data offset");
_Static_assert(offsetof(NcgrCposBlock, width) == 0x0C, "NCGR CPOS width");
_Static_assert(offsetof(NcgrCposBlock, height) == 0x0E, "NCGR CPOS height");
