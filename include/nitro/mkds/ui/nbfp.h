/* nbfp.h — NBFP 16-colour RGB555 palette. SPDX-License-Identifier: MIT */
#pragma once

#include <stdint.h>

#include "nitro/rgb555.h"

#define MKDS_UI_NBFP_COLOR_COUNT 16u
#define MKDS_UI_NBFP_SIZE 32u

typedef union {
    NitroRgb555 raw;
    struct {
        uint16_t red : 5;
        uint16_t green : 5;
        uint16_t blue : 5;
        uint16_t reserved : 1;
    } bits;
} MkdsUiBannerColor;

_Static_assert(sizeof(MkdsUiBannerColor) == 2, "NBFP colour");
_Static_assert(MKDS_UI_NBFP_COLOR_COUNT * sizeof(MkdsUiBannerColor) ==
                   MKDS_UI_NBFP_SIZE,
               "NBFP palette size");

static inline uint8_t mkds_ui_rgb555_red(MkdsUiBannerColor color)
{
    return nitro_rgb555_red8(color.raw);
}

static inline uint8_t mkds_ui_rgb555_green(MkdsUiBannerColor color)
{
    return nitro_rgb555_green8(color.raw);
}

static inline uint8_t mkds_ui_rgb555_blue(MkdsUiBannerColor color)
{
    return nitro_rgb555_blue8(color.raw);
}
