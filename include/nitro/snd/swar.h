/* swar.h — SWAR wave archive. SPDX-License-Identifier: MIT */
#pragma once

#include <stddef.h>
#include <stdint.h>

#include "nitro/snd/common.h"

#define SWAR_MAGIC "SWAR"
#define SWAR_RESERVED_SIZE 32u
#define SWAR_COUNT_OFFSET 0x38u
#define SWAR_ENTRY_OFFSET 0x3Cu

typedef struct {
    SndDataBlockHeader block;
    uint8_t reserved[SWAR_RESERVED_SIZE];
    uint32_t wave_count;
} SwarDataBlock;

_Static_assert(sizeof(SwarDataBlock) == 44, "SWAR DATA block");
_Static_assert(offsetof(SwarDataBlock, wave_count) == 0x28, "SWAR count");
