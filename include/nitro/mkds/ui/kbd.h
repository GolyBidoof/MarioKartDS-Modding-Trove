/* kbd.h — KBD keyboard hit rectangles. SPDX-License-Identifier: MIT */
#pragma once

#include <stddef.h>
#include <stdint.h>

#include "nitro/mkds/common/ui_common.h"

#define MKDS_UI_KBD_ENTRY_SIZE 8u

typedef struct {
    uint8_t x;
    uint8_t y;
    uint8_t width;
    uint8_t height;
    int16_t chain_step;
    MkdsUiKeyId key_id;
} MkdsUiKeyEntry;

_Static_assert(sizeof(MkdsUiKeyEntry) == MKDS_UI_KBD_ENTRY_SIZE, "KBD entry");
_Static_assert(offsetof(MkdsUiKeyEntry, chain_step) == 0x04, "KBD chain step");
_Static_assert(offsetof(MkdsUiKeyEntry, key_id) == 0x06, "KBD key id");
