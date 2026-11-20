/* bncl.h — JNCL cell placement list. SPDX-License-Identifier: MIT */
#pragma once

#include <stdint.h>

#include "nitro/mkds/common/ui_common.h"

#define MKDS_UI_BNCL_MAGIC "JNCL"
#define MKDS_UI_CELL_ELEMENT_SIZE 8u

typedef struct {
    MkdsUiCoord x;
    MkdsUiCoord y;
    MkdsUiCellId cell_id;
} MkdsUiCellElement;

_Static_assert(sizeof(MkdsUiCellElement) == MKDS_UI_CELL_ELEMENT_SIZE,
               "JNCL element");
_Static_assert(offsetof(MkdsUiCellElement, cell_id) == 0x04,
               "JNCL cell id offset");
