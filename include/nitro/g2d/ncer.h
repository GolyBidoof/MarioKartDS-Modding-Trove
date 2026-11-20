/* ncer.h — Nitro NCER cells (RECN). SPDX-License-Identifier: MIT */
#pragma once

#include <stddef.h>
#include <stdint.h>

#include "nitro/bits.h"
#include "nitro/g2d/common.h"

#define NCER_MAGIC "RECN"
#define NCER_CEBK_MAGIC "KBEC"
#define NCER_LABL_MAGIC "LBAL"
#define NCER_CEBK_HEADER_SIZE 32u
#define NCER_CELL_SIZE 8u
#define NCER_CELL_BBOX_SIZE 16u

typedef union {
    uint16_t raw;
    struct {
        uint16_t bbox : 1;
        uint16_t reserved : 15;
    } bits;
} NcerCebkAttributes;

#define NCER_CEBK_ATTR_BBOX NITRO_BIT(0)

typedef union {
    uint16_t raw;
    struct {
        uint16_t radius : 6;
        uint16_t reserved : 2;
        uint16_t hflip : 1;
        uint16_t vflip : 1;
        uint16_t hvflip : 1;
        uint16_t bbox : 1;
        uint16_t reserved_hi : 4;
    } bits;
} NcerCellAttributes;

#define NCER_CELL_ATTR_RADIUS_MASK NITRO_MASK(6, 0)
#define NCER_CELL_ATTR_HFLIP NITRO_BIT(8)
#define NCER_CELL_ATTR_VFLIP NITRO_BIT(9)
#define NCER_CELL_ATTR_HVFLIP NITRO_BIT(10)
#define NCER_CELL_ATTR_BBOX NITRO_BIT(11)

typedef enum {
    NCER_MAPPING_1D_32K = 0,
    NCER_MAPPING_1D_64K = 1,
    NCER_MAPPING_1D_128K = 2,
    NCER_MAPPING_1D_256K = 3,
    NCER_MAPPING_2D = 4
} NcerMappingMode;

_Static_assert(sizeof(NcerCebkAttributes) == 2, "NCER CEBK attributes");
_Static_assert(sizeof(NcerCellAttributes) == 2, "NCER cell attributes");

static inline NcerCebkAttributes ncer_cebk_attributes(uint16_t raw)
{
    NcerCebkAttributes attributes;
    attributes.raw = raw;
    return attributes;
}

static inline NcerCellAttributes ncer_cell_attributes(uint16_t raw)
{
    NcerCellAttributes attributes;
    attributes.raw = raw;
    return attributes;
}

typedef struct {
    NitroG2dMagic magic;
    NitroG2dSize block_size;
    NitroG2dCellCount cell_count;
    NitroG2dBankAttribute attributes;
    NitroG2dOffset cell_data_offset;
    NitroG2dMappingMode mapping_mode;
    NitroG2dOffset vram_transfer_offset;
    NitroG2dOffset string_bank;
    NitroG2dOffset extended_data;
} NcerCebkHeader;

typedef struct {
    NitroG2dOamCount oam_count;
    NitroG2dCellAttribute attributes;
    NitroG2dOffset oam_offset;
} NcerCell;

typedef struct {
    NitroG2dOamCount oam_count;
    NitroG2dCellAttribute attributes;
    NitroG2dOffset oam_offset;
    int16_t max_x;
    int16_t max_y;
    int16_t min_x;
    int16_t min_y;
} NcerCellBbox;

_Static_assert(sizeof(NcerCebkHeader) == NCER_CEBK_HEADER_SIZE, "NCER CEBK header");
_Static_assert(sizeof(NcerCell) == NCER_CELL_SIZE, "NCER cell");
_Static_assert(sizeof(NcerCellBbox) == NCER_CELL_BBOX_SIZE, "NCER cell with bbox");
_Static_assert(offsetof(NcerCebkHeader, cell_count) == 0x08, "NCER cell count");
_Static_assert(offsetof(NcerCebkHeader, attributes) == 0x0A, "NCER bank attributes");
_Static_assert(offsetof(NcerCebkHeader, cell_data_offset) == 0x0C, "NCER cell data offset");
_Static_assert(offsetof(NcerCebkHeader, mapping_mode) == 0x10, "NCER mapping mode");
_Static_assert(offsetof(NcerCebkHeader, vram_transfer_offset) == 0x14,
               "NCER VRAM transfer offset");
_Static_assert(offsetof(NcerCebkHeader, string_bank) == 0x18,
               "NCER string bank");
_Static_assert(offsetof(NcerCebkHeader, extended_data) == 0x1C,
               "NCER extended data");
_Static_assert(offsetof(NcerCell, attributes) == 0x02, "NCER cell attributes");
_Static_assert(offsetof(NcerCell, oam_offset) == 0x04, "NCER cell OAM offset");
_Static_assert(offsetof(NcerCellBbox, max_x) == 0x08, "NCER cell bbox");
