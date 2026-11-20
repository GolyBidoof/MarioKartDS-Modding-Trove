/* rgb555.h — Nitro RGB555 colour words. SPDX-License-Identifier: MIT */
#pragma once

#include <stdint.h>

#define NITRO_RGB555_RED_BITS 5u
#define NITRO_RGB555_GREEN_BITS 5u
#define NITRO_RGB555_BLUE_BITS 5u
#define NITRO_RGB555_COMPONENT_MAX 31u

#define NITRO_RGB555_RED_MASK \
    ((NitroRgb555)NITRO_RGB555_COMPONENT_MAX)
#define NITRO_RGB555_GREEN_MASK \
    ((NitroRgb555)(NITRO_RGB555_COMPONENT_MAX << 5))
#define NITRO_RGB555_BLUE_MASK \
    ((NitroRgb555)(NITRO_RGB555_COMPONENT_MAX << 10))

typedef uint16_t NitroRgb555;

#define NITRO_RGB555(r, g, b) \
    ((NitroRgb555)((((NitroRgb555)(r) & NITRO_RGB555_COMPONENT_MAX) << 0) | \
                   (((NitroRgb555)(g) & NITRO_RGB555_COMPONENT_MAX) << 5) | \
                   (((NitroRgb555)(b) & NITRO_RGB555_COMPONENT_MAX) << 10)))

static inline uint8_t nitro_rgb555_red(NitroRgb555 color)
{
    return (uint8_t)(color & NITRO_RGB555_COMPONENT_MAX);
}

static inline uint8_t nitro_rgb555_green(NitroRgb555 color)
{
    return (uint8_t)((color >> 5) & NITRO_RGB555_COMPONENT_MAX);
}

static inline uint8_t nitro_rgb555_blue(NitroRgb555 color)
{
    return (uint8_t)((color >> 10) & NITRO_RGB555_COMPONENT_MAX);
}

static inline uint8_t nitro_rgb555_red8(NitroRgb555 color)
{
    uint8_t value = nitro_rgb555_red(color);
    return (uint8_t)((value << 3) | (value >> 2));
}

static inline uint8_t nitro_rgb555_green8(NitroRgb555 color)
{
    uint8_t value = nitro_rgb555_green(color);
    return (uint8_t)((value << 3) | (value >> 2));
}

static inline uint8_t nitro_rgb555_blue8(NitroRgb555 color)
{
    uint8_t value = nitro_rgb555_blue(color);
    return (uint8_t)((value << 3) | (value >> 2));
}

_Static_assert(sizeof(NitroRgb555) == 2, "Nitro RGB555 is a 16-bit word");
_Static_assert(NITRO_RGB555(31u, 0u, 0u) == 0x001Fu, "RGB555 red field");
_Static_assert(NITRO_RGB555(0u, 31u, 0u) == 0x03E0u, "RGB555 green field");
_Static_assert(NITRO_RGB555(0u, 0u, 31u) == 0x7C00u, "RGB555 blue field");
