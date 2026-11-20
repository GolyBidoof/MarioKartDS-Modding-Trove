/* spa.h — SPA particle archive. SPDX-License-Identifier: MIT */
#pragma once

#include <stddef.h>
#include <stdint.h>

#include "nitro/bits.h"

#define SPA_MAGIC       "SPA "
#define SPA_TEXTURE_MAGIC "SPT "
#define SPA_VERSION     0x315F3231u
#define SPA_HEADER_SIZE 32u

typedef uint32_t SpaVersion;
typedef uint32_t SpaOffset;
typedef uint32_t SpaSize;
typedef uint16_t SpaCount;

typedef struct {
    char     magic[4];
    SpaVersion version;
    SpaCount emitter_count;
    SpaCount texture_count;
    uint32_t reserved_0C;
    SpaSize  emitter_block_length;
    SpaSize  texture_block_length;
    SpaOffset texture_block_offset;
    uint32_t reserved_20;
} SpaHeader;

_Static_assert(sizeof(SpaHeader) == SPA_HEADER_SIZE, "SPA header");
_Static_assert(offsetof(SpaHeader, version) == 0x04, "SPA version");
_Static_assert(offsetof(SpaHeader, emitter_count) == 0x08,
               "SPA emitter count");
_Static_assert(offsetof(SpaHeader, texture_count) == 0x0A,
               "SPA texture count");
_Static_assert(offsetof(SpaHeader, emitter_block_length) == 0x10,
               "SPA emitter block length");
_Static_assert(offsetof(SpaHeader, texture_block_length) == 0x14,
               "SPA texture block length");
_Static_assert(offsetof(SpaHeader, texture_block_offset) == 0x18,
               "SPA texture block offset");

typedef union {
    uint32_t raw;
    struct {
        uint32_t format : 4;
        uint32_t width : 4;
        uint32_t height : 4;
        uint32_t repeat : 2;
        uint32_t flip : 2;
        uint32_t palette0_clear : 1;
        uint32_t reference : 1;
        uint32_t reference_id : 8;
        uint32_t reserved : 6;
    } bits;
} SpaTextureParams;

_Static_assert(sizeof(SpaTextureParams) == 4, "SPA texture params");

typedef struct {
    char            magic[4];
    SpaTextureParams params;
    SpaSize         texture_size;
    SpaOffset       palette_offset;
    SpaSize         palette_size;
    SpaOffset       palette_index_offset;
    SpaSize         palette_index_size;
    SpaOffset       block_size;
} SpaTextureHeader;

_Static_assert(sizeof(SpaTextureHeader) == 32, "SPA texture header");
_Static_assert(offsetof(SpaTextureHeader, params) == 0x04,
               "SPA texture params");
_Static_assert(offsetof(SpaTextureHeader, texture_size) == 0x08,
               "SPA texture size");
_Static_assert(offsetof(SpaTextureHeader, palette_offset) == 0x0C,
               "SPA palette offset");
_Static_assert(offsetof(SpaTextureHeader, block_size) == 0x1C,
               "SPA next texture offset");
