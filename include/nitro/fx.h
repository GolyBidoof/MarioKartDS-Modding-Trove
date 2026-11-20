/* fx.h — Nitro fixed-point values. SPDX-License-Identifier: MIT */
#pragma once

#include <stdint.h>

#define FX_SHIFT 12
#define FX_ONE 4096
#define FX_HALF 2048

typedef int32_t Fx32;
typedef int16_t Fx16;

#define FX32(value) ((Fx32)((double)(value) * (double)FX_ONE))
#define FX16(value) ((Fx16)((double)(value) * (double)FX_ONE))

_Static_assert(sizeof(Fx32) == 4, "Fx32 is a 32-bit fixed-point value");
_Static_assert(sizeof(Fx16) == 2, "Fx16 is a 16-bit fixed-point value");

static inline double fx32_to_double(Fx32 value)
{
    return (double)value / (double)FX_ONE;
}

static inline Fx32 fx32_from_double(double value)
{
    return (Fx32)(value * (double)FX_ONE);
}

static inline double fx16_to_double(Fx16 value)
{
    return (double)value / (double)FX_ONE;
}

static inline Fx16 fx16_from_double(double value)
{
    return (Fx16)(value * (double)FX_ONE);
}
