/* nclr.h — Nitro NCLR palettes (RLCN, legacy RPCN). SPDX-License-Identifier: MIT */
#pragma once

#include <stddef.h>
#include <stdint.h>

#include "nitro/g2d/common.h"

#define NCLR_MAGIC "RLCN"
#define NCLR_LEGACY_MAGIC "RPCN"
#define NCLR_PLTT_MAGIC "TTLP"
#define NCLR_PCMP_MAGIC "PMCP"
#define NCLR_PLTT_HEADER_SIZE 24
#define NCLR_PCMP_HEADER_SIZE 16
#define NCLR_PCMP_RESERVED 0xBEEFu
#define NCLR_PALETTE_FORMAT_4BPP NITRO_G2D_IMAGE_FORMAT_4BPP
#define NCLR_PALETTE_FORMAT_8BPP NITRO_G2D_IMAGE_FORMAT_8BPP
typedef enum {
    NCLR_EXTENDED_NONE = 0,
    NCLR_EXTENDED_PALETTE = 1
} NclrExtendedMode;

typedef struct {
    NitroG2dMagic magic;
    NitroG2dSize block_size;
    NitroG2dImageFormat palette_format;
    NitroG2dBool extended;
    NitroG2dSize data_size;
    NitroG2dOffset data_offset;
} NclrPlttBlock;

typedef struct {
    NitroG2dMagic magic;
    NitroG2dSize block_size;
    NitroG2dPaletteCount palette_count;
    uint16_t reserved;
    NitroG2dOffset index_offset;
} NclrPcmpBlock;

_Static_assert(sizeof(NclrPlttBlock) == NCLR_PLTT_HEADER_SIZE, "NCLR PLTT header");
_Static_assert(sizeof(NclrPcmpBlock) == NCLR_PCMP_HEADER_SIZE, "NCLR PCMP header");
_Static_assert(offsetof(NclrPlttBlock, palette_format) == 0x08, "NCLR palette format");
_Static_assert(offsetof(NclrPlttBlock, extended) == 0x0C, "NCLR extended flag");
_Static_assert(offsetof(NclrPlttBlock, data_size) == 0x10, "NCLR palette data size");
_Static_assert(offsetof(NclrPlttBlock, data_offset) == 0x14, "NCLR palette data offset");
_Static_assert(offsetof(NclrPcmpBlock, palette_count) == 0x08, "NCLR PCMP count");
_Static_assert(offsetof(NclrPcmpBlock, reserved) == 0x0A, "NCLR PCMP reserved");
_Static_assert(offsetof(NclrPcmpBlock, index_offset) == 0x0C, "NCLR PCMP index offset");
