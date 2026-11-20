/* sseq.h — SSEQ sequence. SPDX-License-Identifier: MIT */
#pragma once

#include <stddef.h>
#include <stdint.h>

#include "nitro/snd/common.h"

#define SSEQ_MAGIC "SSEQ"
#define SSEQ_DATA_OFFSET 0x18u

typedef struct {
    SndDataBlockHeader block;
    uint32_t data_offset;
} SseqDataBlock;

_Static_assert(sizeof(SseqDataBlock) == 12, "SSEQ DATA block");
_Static_assert(offsetof(SseqDataBlock, data_offset) == 0x08, "SSEQ data offset");
