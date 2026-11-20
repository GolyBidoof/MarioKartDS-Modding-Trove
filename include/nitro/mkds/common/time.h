/* time.h — race clock units used by the stock tables. SPDX-License-Identifier: MIT */
#pragma once

#include <stdint.h>

#define MKDS_RACE_FRAME_HZ 60u

typedef uint16_t MkdsRaceFrames;
typedef uint32_t MkdsRaceFrames32;

typedef uint32_t MkdsRaceMilliseconds;

typedef struct {
    uint8_t minutes;
    uint8_t seconds;
    uint16_t milliseconds;
} MkdsRaceClock;

static inline MkdsRaceMilliseconds mkds_frames_to_milliseconds(uint32_t frames)
{
    return (frames * 1000u + MKDS_RACE_FRAME_HZ / 2u) / MKDS_RACE_FRAME_HZ;
}

static inline uint32_t mkds_milliseconds_to_frames(MkdsRaceMilliseconds ms)
{
    return (ms * MKDS_RACE_FRAME_HZ + 500u) / 1000u;
}

static inline MkdsRaceClock mkds_clock_from_milliseconds(MkdsRaceMilliseconds ms)
{
    MkdsRaceClock clock;
    clock.minutes = (uint8_t)(ms / 60000u);
    ms %= 60000u;
    clock.seconds = (uint8_t)(ms / 1000u);
    clock.milliseconds = (uint16_t)(ms % 1000u);
    return clock;
}

static inline MkdsRaceMilliseconds mkds_clock_to_milliseconds(MkdsRaceClock clock)
{
    return (MkdsRaceMilliseconds)clock.minutes * 60000u
         + (MkdsRaceMilliseconds)clock.seconds * 1000u
         + clock.milliseconds;
}
