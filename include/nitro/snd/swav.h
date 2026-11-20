/* swav.h — SWAV wave parameter and samples. SPDX-License-Identifier: MIT */
#pragma once

#include <stddef.h>
#include <stdint.h>

#include "nitro/snd/common.h"

#define SWAV_MAGIC "SWAV"
#define SWAV_PARAM_SIZE 12u
#define SWAV_DATA_OFFSET 0x24u

typedef enum {
    SWAV_FORMAT_PCM8 = 0,
    SWAV_FORMAT_PCM16 = 1,
    SWAV_FORMAT_ADPCM = 2
} SwavFormat;

typedef struct {
    uint8_t format;
    uint8_t loop;
    uint16_t sample_rate;
    uint16_t time;
    uint16_t loop_start;
    uint32_t loop_length;
} SwavParam;

typedef struct {
    SndDataBlockHeader block;
    SwavParam param;
} SwavDataBlock;

_Static_assert(sizeof(SwavParam) == SWAV_PARAM_SIZE, "SWAV parameter");
_Static_assert(offsetof(SwavParam, sample_rate) == 0x02, "SWAV sample rate");
_Static_assert(offsetof(SwavParam, time) == 0x04, "SWAV time");
_Static_assert(offsetof(SwavParam, loop_start) == 0x06, "SWAV loop start");
_Static_assert(offsetof(SwavParam, loop_length) == 0x08, "SWAV loop length");
_Static_assert(sizeof(SwavDataBlock) == 20, "SWAV DATA block");
_Static_assert(offsetof(SwavDataBlock, param) == 0x08, "SWAV parameter at 0x18");

static inline uint32_t swav_sample_bytes(const SwavParam *param)
{
    return ((uint32_t)param->loop_start + param->loop_length) * 4u;
}

static inline uint32_t swav_time_from_rate(uint16_t sample_rate)
{
    return sample_rate ? SND_TIMER_CLOCK / sample_rate : 0u;
}
