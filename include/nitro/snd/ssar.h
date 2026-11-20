/* ssar.h — SSAR sequence archive. SPDX-License-Identifier: MIT */
#pragma once

#include <stddef.h>
#include <stdint.h>

#include "nitro/snd/common.h"

#define SSAR_MAGIC "SSAR"
#define SSAR_DATA_OFFSET 0x18u
#define SSAR_COUNT_OFFSET 0x1Cu
#define SSAR_ENTRY_OFFSET 0x20u

typedef struct {
    SndDataBlockHeader block;
    uint32_t data_offset;
    uint32_t count;
} SsarDataBlock;

typedef struct {
    uint32_t offset;
    uint16_t bank;
    uint8_t volume;
    uint8_t channel_priority;
    uint8_t player_priority;
    uint8_t player;
    uint16_t reserved;
} SsarEntry;

_Static_assert(sizeof(SsarDataBlock) == 16, "SSAR DATA block");
_Static_assert(sizeof(SsarEntry) == 12, "SSAR entry");
