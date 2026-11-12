/*
 * Mario Kart DS Modding Trove
 * include/nitro/blz.h — Nitro BLZ trailer
 * SPDX-License-Identifier: MIT
 * Notes: docs/nitro.md, docs/arm9-autoloads.md
 * References: GBATEK; see ../CREDITS.md
 */
#pragma once

#include <stddef.h>
#include <stdint.h>

#define BLZ_TRAILER_SIZE 8u
#define BLZ_NO_COMPRESSION 0u

typedef struct {
    uint32_t header;              /* top byte: header length; low 24: compressed length */
    uint32_t uncompressed_size;   /* bytes the image grows by */
} BlzTrailer;

_Static_assert(sizeof(BlzTrailer) == BLZ_TRAILER_SIZE, "BLZ trailer");

static inline uint8_t blz_header_length(uint32_t header)
{
    return (uint8_t)(header >> 24);
}

static inline uint32_t blz_compressed_length(uint32_t header)
{
    return header & 0xFFFFFFu;
}
