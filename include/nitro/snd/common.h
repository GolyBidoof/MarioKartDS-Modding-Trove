/* common.h — shared Nitro sound file header and DATA block. SPDX-License-Identifier: MIT */
#pragma once

#include <stddef.h>
#include <stdint.h>

#include "nitro/bits.h"

#define SND_FILE_HEADER_SIZE 16u
#define SND_DATA_HEADER_SIZE 8u
#define SND_DATA_MAGIC "DATA"
#define SND_BOM 0xFEFFu
#define SND_VERSION 0x0100u

#define SND_TIMER_CLOCK 16756991u

typedef struct {
    char magic[4];
    uint16_t bom;
    uint16_t version;
    uint32_t file_size;
    uint16_t header_size;
    uint16_t block_count;
} SndFileHeader;

typedef struct {
    char magic[4];
    uint32_t size;
} SndDataBlockHeader;

_Static_assert(sizeof(SndFileHeader) == SND_FILE_HEADER_SIZE, "sound file header");
_Static_assert(offsetof(SndFileHeader, bom) == 0x04, "sound file BOM");
_Static_assert(offsetof(SndFileHeader, version) == 0x06, "sound file version");
_Static_assert(offsetof(SndFileHeader, file_size) == 0x08, "sound file size");
_Static_assert(offsetof(SndFileHeader, block_count) == 0x0E,
               "sound file block count");
_Static_assert(sizeof(SndDataBlockHeader) == SND_DATA_HEADER_SIZE, "DATA block header");
_Static_assert(offsetof(SndDataBlockHeader, size) == 0x04, "DATA block size");
