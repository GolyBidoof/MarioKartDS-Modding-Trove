/*
 * Mario Kart DS Modding Trove
 * include/nitro/narc.h — NARC/CARC and Nitro LZ77
 * SPDX-License-Identifier: MIT
 * Notes: docs/nitro.md
 * References: GBATEK, Mario Kart Toolbox; see ../CREDITS.md
 */
#pragma once

#include <stddef.h>
#include <stdint.h>

#include "nds.h"

#define NARC_MAGIC "NARC"
#define NARC_BTAF_MAGIC "BTAF"
#define NARC_BTNF_MAGIC "BTNF"
#define NARC_GMIF_MAGIC "GMIF"
#define NARC_BOM 0xFEFFu
#define NARC_HEADER_SIZE 0x10u
#define NARC_BTAF_OFFSET 0x10u
#define NARC_BTAF_ENTRY_OFFSET 0x0Cu

typedef struct {
    char magic[4];
    uint16_t bom;
    uint16_t version;
    uint32_t file_size;
    uint16_t header_size;
    uint16_t section_count;
} NarcHeader;

typedef struct {
    char magic[4];
    uint32_t size;
    uint16_t count;
    uint16_t reserved;
} NarcBtafHeader;

typedef struct {
    uint32_t start;
    uint32_t end;
} NarcFatEntry;

typedef struct {
    char magic[4];
    uint32_t size;
} NarcBtnfHeader;

typedef struct {
    char magic[4];
    uint32_t size;
} NarcGmifHeader;

typedef NdsFntRoot NarcFntRoot;
typedef NdsFntDirEntry NarcFntDirEntry;

_Static_assert(sizeof(NarcHeader) == NARC_HEADER_SIZE, "NARC header");
_Static_assert(sizeof(NarcBtafHeader) == 12, "BTAF header");
_Static_assert(sizeof(NarcFatEntry) == 8, "NARC FAT entry");
_Static_assert(sizeof(NarcBtnfHeader) == 8, "BTNF header");
_Static_assert(sizeof(NarcGmifHeader) == 8, "GMIF header");

#define NITRO_LZ77_TYPE 0x10u

static inline uint8_t nitro_lz77_type(const uint8_t *data)
{
    return data[0];
}

static inline uint32_t nitro_lz77_size(const uint8_t *data)
{
    return (uint32_t)data[1] | ((uint32_t)data[2] << 8) |
           ((uint32_t)data[3] << 16);
}
