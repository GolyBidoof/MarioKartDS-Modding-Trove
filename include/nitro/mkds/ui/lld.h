/* lld.h — LLD emblem placement list. SPDX-License-Identifier: MIT */
#pragma once

#include <stddef.h>
#include <stdint.h>

#include "nitro/mkds/common/ui_common.h"

#define MKDS_UI_LLD_ENTRY_SIZE 8u

typedef struct {
    MkdsUiEmblemId id;
    uint16_t x;
    uint16_t y;
    uint16_t flags;
} MkdsUiEmblemEntry;

_Static_assert(sizeof(MkdsUiEmblemEntry) == MKDS_UI_LLD_ENTRY_SIZE,
               "LLD entry");
_Static_assert(offsetof(MkdsUiEmblemEntry, x) == 0x02, "LLD x offset");
_Static_assert(offsetof(MkdsUiEmblemEntry, flags) == 0x06, "LLD flags offset");
