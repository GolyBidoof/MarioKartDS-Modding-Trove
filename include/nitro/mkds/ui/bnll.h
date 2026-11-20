/* bnll.h — JNLL label placement list. SPDX-License-Identifier: MIT */
#pragma once

#include <stdint.h>

#include "nitro/mkds/common/ui_common.h"

#define MKDS_UI_BNLL_MAGIC "JNLL"
#define MKDS_UI_LABEL_ELEMENT_SIZE 12u
#define MKDS_UI_LABEL_POOL_BASE 8u

typedef union {
    uint16_t raw;
    struct {
        uint16_t color : 8;
        uint16_t palette : 4;
        uint16_t font : 4;
    } bits;
} MkdsUiLabelStyle;

_Static_assert(sizeof(MkdsUiLabelStyle) == 2, "JNLL label style");

typedef struct {
    MkdsUiCoord x;
    MkdsUiCoord y;
    int8_t h_space;
    int8_t v_space;
    MkdsUiLabelStyle style;
    MkdsUiStringOffset string_offset;
} MkdsUiLabelElement;

_Static_assert(sizeof(MkdsUiLabelElement) == MKDS_UI_LABEL_ELEMENT_SIZE,
               "JNLL element");
_Static_assert(offsetof(MkdsUiLabelElement, h_space) == 0x04,
               "JNLL h_space offset");
_Static_assert(offsetof(MkdsUiLabelElement, v_space) == 0x05,
               "JNLL v_space offset");
_Static_assert(offsetof(MkdsUiLabelElement, style) == 0x06,
               "JNLL style offset");
_Static_assert(offsetof(MkdsUiLabelElement, string_offset) == 0x08,
               "JNLL string offset");
