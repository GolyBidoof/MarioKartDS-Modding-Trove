/* nscr.h — Nitro NSCR screen maps (RCSN). SPDX-License-Identifier: MIT */
#pragma once

#include <stddef.h>
#include <stdint.h>

#include "nitro/bits.h"
#include "nitro/g2d/common.h"

#define NSCR_MAGIC "RCSN"
#define NSCR_SCRN_MAGIC "NRCS"
#define NSCR_SCRN_HEADER_SIZE 20u

typedef enum {
    NSCR_COLOR_MODE_16X16 = 0,
    NSCR_COLOR_MODE_256X1 = 1,
    NSCR_COLOR_MODE_256X16 = 2
} NscrColorMode;

typedef enum {
    NSCR_SCREEN_FORMAT_TEXT = 0,
    NSCR_SCREEN_FORMAT_AFFINE = 1,
    NSCR_SCREEN_FORMAT_AFFINE_EXT = 2
} NscrScreenFormat;

typedef union {
    uint16_t raw;
    struct {
        uint16_t tile_index : 10;
        uint16_t hflip : 1;
        uint16_t vflip : 1;
        uint16_t palette : 4;
    } bits;
} NscrTextTile;

#define NSCR_TEXT_TILE_INDEX_MASK NITRO_MASK(10, 0)
#define NSCR_TEXT_TILE_HFLIP NITRO_BIT(10)
#define NSCR_TEXT_TILE_VFLIP NITRO_BIT(11)
#define NSCR_TEXT_TILE_PALETTE_MASK NITRO_MASK(4, 12)

_Static_assert(sizeof(NscrTextTile) == 2, "NSCR text tile");

typedef struct {
    NitroG2dMagic magic;
    NitroG2dSize block_size;
    NitroG2dWidth width;
    NitroG2dHeight height;
    NitroG2dScreenColorMode color_mode;
    NitroG2dScreenFormat screen_format;
    NitroG2dSize data_size;
} NscrScreenBlock;

_Static_assert(sizeof(NscrScreenBlock) == NSCR_SCRN_HEADER_SIZE, "NSCR SCRN header");
_Static_assert(offsetof(NscrScreenBlock, width) == 0x08, "NSCR width");
_Static_assert(offsetof(NscrScreenBlock, height) == 0x0A, "NSCR height");
_Static_assert(offsetof(NscrScreenBlock, color_mode) == 0x0C, "NSCR colour mode");
_Static_assert(offsetof(NscrScreenBlock, screen_format) == 0x0E, "NSCR screen format");
_Static_assert(offsetof(NscrScreenBlock, data_size) == 0x10, "NSCR data size");
