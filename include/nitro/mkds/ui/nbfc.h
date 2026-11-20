/* nbfc.h — NBFC 4bpp tile image. SPDX-License-Identifier: MIT */
#pragma once

#include <stddef.h>
#include <stdint.h>

#define MKDS_UI_NBFC_SIZE 512u
#define MKDS_UI_NBFC_TILES 16u
#define MKDS_UI_NBFC_WIDTH 32u
#define MKDS_UI_NBFC_HEIGHT 32u
#define MKDS_UI_NBFC_TILE_WIDTH 8u
#define MKDS_UI_NBFC_TILE_HEIGHT 8u
#define MKDS_UI_NBFC_TILE_BYTES 32u

typedef struct {
    uint8_t tiles[MKDS_UI_NBFC_TILES][MKDS_UI_NBFC_TILE_BYTES];
} MkdsUiBannerTileImage;

_Static_assert(MKDS_UI_NBFC_TILES * MKDS_UI_NBFC_TILE_BYTES ==
                   MKDS_UI_NBFC_SIZE,
               "NBFC tile layout");
_Static_assert(sizeof(MkdsUiBannerTileImage) == MKDS_UI_NBFC_SIZE,
               "NBFC image");
