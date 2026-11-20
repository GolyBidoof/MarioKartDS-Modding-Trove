/* misc.h — emblem2.bin and builddate.bin. SPDX-License-Identifier: MIT */
#pragma once

#include <stddef.h>
#include <stdint.h>

#define MKDS_EMBLEM_WIDTH 32u
#define MKDS_EMBLEM_HEIGHT 32u
#define MKDS_EMBLEM_BPP 4u
#define MKDS_EMBLEM_ROW_BYTES 16u
#define MKDS_EMBLEM_PIXELS_PER_BYTE 2u
#define MKDS_EMBLEM_SIZE 512u

typedef struct {
    uint8_t rows[MKDS_EMBLEM_HEIGHT][MKDS_EMBLEM_ROW_BYTES];
} MkdsEmblemBitmap;

/* Low nibble is the left pixel. */
static inline uint8_t mkds_emblem_pixel(const MkdsEmblemBitmap *bitmap,
                                        unsigned x, unsigned y)
{
    uint8_t packed = bitmap->rows[y][x / MKDS_EMBLEM_PIXELS_PER_BYTE];
    return (x & 1u) ? (uint8_t)(packed >> 4) : (uint8_t)(packed & 0x0Fu);
}

_Static_assert(MKDS_EMBLEM_WIDTH * MKDS_EMBLEM_BPP / 8u ==
                   MKDS_EMBLEM_ROW_BYTES,
               "emblem row width");
_Static_assert(MKDS_EMBLEM_HEIGHT * MKDS_EMBLEM_ROW_BYTES ==
                   MKDS_EMBLEM_SIZE,
               "emblem bitmap size");

#define MKDS_BUILD_DATE_SIZE 30u

typedef struct {
    char text[MKDS_BUILD_DATE_SIZE];
} MkdsBuildDate;

_Static_assert(sizeof(MkdsEmblemBitmap) == MKDS_EMBLEM_SIZE, "emblem bitmap");
_Static_assert(sizeof(MkdsBuildDate) == MKDS_BUILD_DATE_SIZE, "build date string");
