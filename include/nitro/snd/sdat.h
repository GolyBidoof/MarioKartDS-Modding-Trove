/* sdat.h — SDAT archive, SYMB/INFO/FAT/FILE block model. SPDX-License-Identifier: MIT */
#pragma once

#include <stddef.h>
#include <stdint.h>

#include "nitro/bits.h"
#include "nitro/snd/common.h"

#define SDAT_MAGIC "SDAT"
#define SDAT_HEADER_SIZE 64u
#define SDAT_BLOCK_COUNT 4u
#define SDAT_BLOCK_REF_OFFSET 0x10u
#define SDAT_RESERVED_OFFSET 0x30u
#define SDAT_RESERVED_SIZE 16u

typedef enum {
    SDAT_BLOCK_SYMB = 0,
    SDAT_BLOCK_INFO = 1,
    SDAT_BLOCK_FAT = 2,
    SDAT_BLOCK_FILE = 3
} SdatBlockIndex;

typedef struct {
    uint32_t offset;
    uint32_t size;
} SdatBlockRef;

typedef struct {
    char magic[4];
    uint16_t bom;
    uint16_t version;
    uint32_t file_size;
    uint16_t header_size;
    uint16_t block_count;
    SdatBlockRef block[SDAT_BLOCK_COUNT];
    uint8_t reserved[SDAT_RESERVED_SIZE];
} SdatHeader;

_Static_assert(sizeof(SdatBlockRef) == 8, "SDAT block reference");
_Static_assert(sizeof(SdatHeader) == SDAT_HEADER_SIZE, "SDAT header");
_Static_assert(offsetof(SdatHeader, block) == SDAT_BLOCK_REF_OFFSET, "SDAT block table");
_Static_assert(offsetof(SdatHeader, reserved) == SDAT_RESERVED_OFFSET, "SDAT reserved area");

#define SDAT_SYMB_MAGIC "SYMB"
#define SDAT_SYMB_HEADER_SIZE 64u
#define SDAT_SYMB_RECORD_COUNT 8u
#define SDAT_SYMB_RESERVED_OFFSET 0x28u
#define SDAT_SYMB_RESERVED_SIZE 24u

typedef struct {
    char magic[4];
    uint32_t size;
    uint32_t record_offset[SDAT_SYMB_RECORD_COUNT];
    uint8_t reserved[SDAT_SYMB_RESERVED_SIZE];
} SdatSymbHeader;

typedef struct {
    uint32_t count;
} SdatSymbRecord;

typedef struct {
    uint32_t name_offset;
    uint32_t sub_record_offset;
} SdatSymbArchiveEntry;

_Static_assert(sizeof(SdatSymbHeader) == SDAT_SYMB_HEADER_SIZE, "SYMB header");
_Static_assert(offsetof(SdatSymbHeader, record_offset) == 0x08, "SYMB record table");
_Static_assert(sizeof(SdatSymbRecord) == 4, "SYMB record header");
_Static_assert(sizeof(SdatSymbArchiveEntry) == 8, "SYMB archive entry");

#define SDAT_INFO_MAGIC "INFO"
#define SDAT_INFO_HEADER_SIZE 64u
#define SDAT_INFO_SECTION_COUNT 8u
#define SDAT_INFO_RESERVED_OFFSET 0x28u
#define SDAT_INFO_RESERVED_SIZE 24u

typedef enum {
    SDAT_INFO_SEQ = 0,
    SDAT_INFO_SEQ_ARC = 1,
    SDAT_INFO_BANK = 2,
    SDAT_INFO_WAVE_ARC = 3,
    SDAT_INFO_PLAYER = 4,
    SDAT_INFO_GROUP = 5,
    SDAT_INFO_STREAM_PLAYER = 6,
    SDAT_INFO_STREAM = 7
} SdatInfoSection;

typedef struct {
    char magic[4];
    uint32_t size;
    uint32_t section_offset[SDAT_INFO_SECTION_COUNT];
    uint8_t reserved[SDAT_INFO_RESERVED_SIZE];
} SdatInfoHeader;

typedef struct {
    uint32_t count;
} SdatInfoTable;

typedef struct {
    uint32_t file_id;
    uint16_t bank;
    uint8_t volume;
    uint8_t channel_priority;
    uint8_t player_priority;
    uint8_t player;
    uint16_t reserved;
} SdatSeqInfo;

typedef struct {
    uint32_t file_id;
} SdatSeqArcInfo;

typedef struct {
    uint32_t file_id;
    int16_t wave_archive[4];
} SdatBankInfo;

typedef union {
    uint32_t raw;
    struct {
        uint32_t file_id : 24;
        uint32_t load_individually : 1;
        uint32_t reserved : 7;
    } bits;
} SdatWaveArcInfo;

_Static_assert(sizeof(SdatWaveArcInfo) == 4, "SDAT wave archive info");

typedef struct {
    uint16_t max_sequences;
    uint16_t channel_mask;
    uint32_t heap_size;
} SdatPlayerInfo;

typedef enum {
    SDAT_GROUP_SEQ = 0,
    SDAT_GROUP_BANK = 1,
    SDAT_GROUP_WAVE_ARC = 2,
    SDAT_GROUP_SEQ_ARC = 3
} SdatGroupType;

typedef union {
    uint8_t raw;
    struct {
        uint8_t sequence : 1;
        uint8_t bank : 1;
        uint8_t wave_archive : 1;
        uint8_t sequence_archive : 1;
        uint8_t reserved : 4;
    } bits;
} SdatGroupLoadFlags;

typedef struct {
    uint8_t            type;
    SdatGroupLoadFlags load_flags;
    uint16_t           reserved;
    uint32_t           index;
} SdatGroupItem;

_Static_assert(sizeof(SdatGroupLoadFlags) == 1, "SDAT group load flags");

typedef struct {
    uint32_t count;
} SdatGroupInfo;

typedef struct {
    uint8_t channel_count;
    uint8_t channel[16];
} SdatStreamPlayerInfo;

typedef struct {
    uint32_t file_id;
    uint8_t volume;
    uint8_t player_priority;
    uint8_t player;
    uint8_t flags;
    uint8_t reserved[4];
} SdatStreamInfo;

_Static_assert(sizeof(SdatInfoHeader) == SDAT_INFO_HEADER_SIZE, "INFO header");
_Static_assert(sizeof(SdatInfoTable) == 4, "INFO table header");
_Static_assert(sizeof(SdatSeqInfo) == 12, "SEQ info record");
_Static_assert(sizeof(SdatSeqArcInfo) == 4, "SEQARC info record");
_Static_assert(sizeof(SdatBankInfo) == 12, "BANK info record");
_Static_assert(sizeof(SdatWaveArcInfo) == 4, "WAVEARC info record");
_Static_assert(sizeof(SdatPlayerInfo) == 8, "PLAYER info record");
_Static_assert(sizeof(SdatGroupItem) == 8, "group item");
_Static_assert(sizeof(SdatGroupInfo) == 4, "group record header");
_Static_assert(sizeof(SdatStreamPlayerInfo) == 17, "stream player record body");
_Static_assert(sizeof(SdatStreamInfo) == 12, "stream info record");

static inline uint32_t sdat_wave_arc_file_id(SdatWaveArcInfo info)
{
    return info.bits.file_id;
}

static inline uint8_t sdat_wave_arc_load_individually(SdatWaveArcInfo info)
{
    return (uint8_t)info.bits.load_individually;
}

#define SDAT_FAT_MAGIC "FAT "
#define SDAT_FILE_MAGIC "FILE"
#define SDAT_BLOCK_HEADER_SIZE 12u
#define SDAT_FAT_ENTRY_SIZE 16u
#define SDAT_FAT_ENTRY_RESERVED_SIZE 8u
#define SDAT_FILE_ALIGNMENT 32u

typedef struct {
    char magic[4];
    uint32_t size;
    uint32_t count;
} SdatFatHeader;

typedef struct {
    uint32_t offset;
    uint32_t size;
    uint8_t reserved[SDAT_FAT_ENTRY_RESERVED_SIZE];
} SdatFatEntry;

typedef struct {
    char magic[4];
    uint32_t size;
    uint32_t count;
} SdatFileHeader;

_Static_assert(sizeof(SdatFatHeader) == SDAT_BLOCK_HEADER_SIZE, "FAT header");
_Static_assert(sizeof(SdatFatEntry) == SDAT_FAT_ENTRY_SIZE, "FAT entry");
_Static_assert(sizeof(SdatFileHeader) == SDAT_BLOCK_HEADER_SIZE, "FILE header");
