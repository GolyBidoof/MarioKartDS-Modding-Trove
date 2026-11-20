/* bnbl.h — JNBL touch-box list. SPDX-License-Identifier: MIT */
#pragma once

#include <stdint.h>

#include "nitro/mkds/common/ui_common.h"

#define MKDS_UI_BNBL_MAGIC "JNBL"
#define MKDS_UI_BOX_ELEMENT_SIZE 6u

typedef struct {
    MkdsUiCoord x;
    MkdsUiCoord y;
    uint8_t width;
    uint8_t height;
} MkdsUiBoxElement;

_Static_assert(sizeof(MkdsUiBoxElement) == MKDS_UI_BOX_ELEMENT_SIZE,
               "JNBL element");
_Static_assert(offsetof(MkdsUiBoxElement, width) == 0x04,
               "JNBL width offset");
