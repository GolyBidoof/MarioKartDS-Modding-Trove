/* bits.h — readable bit positions and field masks. SPDX-License-Identifier: MIT */
#pragma once

#include <stdint.h>

#define NITRO_BIT(bit)                 (1u << (bit))
#define NITRO_MASK(width, shift)       (((1u << (width)) - 1u) << (shift))
#define NITRO_FIELD_GET(word, width, shift) \
    (((uint32_t)(word) & NITRO_MASK((width), (shift))) >> (shift))
#define NITRO_FIELD_SET(word, width, shift, value) \
    (((uint32_t)(word) & ~NITRO_MASK((width), (shift))) | \
     (((uint32_t)(value) << (shift)) & NITRO_MASK((width), (shift))))
