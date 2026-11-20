/* sbnk.h — SBNK instrument bank. SPDX-License-Identifier: MIT */
#pragma once

#include <stddef.h>
#include <stdint.h>

#include "nitro/snd/common.h"

#define SBNK_MAGIC "SBNK"
#define SBNK_RESERVED_SIZE 32u
#define SBNK_COUNT_OFFSET 0x38u
#define SBNK_ENTRY_OFFSET 0x3Cu

typedef enum {
    SBNK_INSTRUMENT_NONE = 0,
    SBNK_INSTRUMENT_PCM = 1,
    SBNK_INSTRUMENT_PSG_SQUARE = 2,
    SBNK_INSTRUMENT_PSG_NOISE = 3,
    SBNK_INSTRUMENT_DIRECT_PCM = 4,
    SBNK_INSTRUMENT_NULL = 5,
    SBNK_INSTRUMENT_RANGE = 16,
    SBNK_INSTRUMENT_REGIONAL = 17,
} SbnkInstrumentType;

#define SBNK_REGION_COUNT 8u

typedef struct {
    SndDataBlockHeader block;
    uint8_t reserved[SBNK_RESERVED_SIZE];
    uint32_t instrument_count;
} SbnkDataBlock;

typedef struct {
    uint8_t type;
    uint8_t offset[2];
    uint8_t reserved;
} SbnkInstrumentEntry;

typedef struct {
    uint16_t wave;
    uint16_t wave_archive;
    uint8_t pitch;
    uint8_t attack;
    uint8_t decay;
    uint8_t sustain;
    uint8_t release;
    uint8_t pan;
} SbnkNote;

typedef struct {
    uint8_t type;
    uint8_t reserved;
    SbnkNote note;
} SbnkTypedNote;

typedef struct {
    uint8_t first_key;
    uint8_t last_key;
} SbnkRangeHeader;

typedef struct {
    uint8_t last_key[SBNK_REGION_COUNT];
} SbnkRegionalHeader;

_Static_assert(sizeof(SbnkDataBlock) == 44, "SBNK DATA block");
_Static_assert(offsetof(SbnkDataBlock, reserved) == 0x08, "SBNK reserved");
_Static_assert(offsetof(SbnkDataBlock, instrument_count) == 0x28, "SBNK count");
_Static_assert(sizeof(SbnkInstrumentEntry) == 4, "SBNK instrument entry");
_Static_assert(offsetof(SbnkInstrumentEntry, offset) == 0x01,
               "SBNK instrument offset");
_Static_assert(offsetof(SbnkInstrumentEntry, reserved) == 0x03,
               "SBNK instrument reserved");
_Static_assert(sizeof(SbnkNote) == 10, "SBNK note");
_Static_assert(sizeof(SbnkTypedNote) == 12, "SBNK typed note");
_Static_assert(sizeof(SbnkRangeHeader) == 2, "SBNK range header");
_Static_assert(sizeof(SbnkRegionalHeader) == SBNK_REGION_COUNT, "SBNK regional header");

static inline uint16_t sbnk_entry_offset(const SbnkInstrumentEntry *entry)
{
    return (uint16_t)(entry->offset[0] | ((uint16_t)entry->offset[1] << 8));
}
