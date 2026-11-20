/* blz.h — Nitro BLZ trailer. SPDX-License-Identifier: MIT */
#pragma once

#include <stddef.h>
#include <stdint.h>

#include "bits.h"

#define BLZ_TRAILER_SIZE 8u
#define BLZ_NO_COMPRESSION 0u

typedef union {
    uint32_t raw;
    struct {
        uint32_t compressed_length : 24;
        uint32_t header_length : 8;
    } bits;
} BlzHeaderWord;

typedef struct {
    BlzHeaderWord header;
    uint32_t uncompressed_size;
} BlzTrailer;

_Static_assert(sizeof(BlzHeaderWord) == 4, "BLZ header word");
_Static_assert(sizeof(BlzTrailer) == BLZ_TRAILER_SIZE, "BLZ trailer");
_Static_assert(offsetof(BlzTrailer, uncompressed_size) == 0x04,
               "BLZ uncompressed size");

static inline uint8_t blz_header_length(uint32_t header)
{
    return (uint8_t)(header >> 24);
}

static inline uint32_t blz_compressed_length(uint32_t header)
{
    return header & NITRO_MASK(24, 0);
}
