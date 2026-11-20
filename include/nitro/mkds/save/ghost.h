/* ghost.h — NKDG/NKPG ghost files and ghost input runs. SPDX-License-Identifier: MIT */
#pragma once

#include <stddef.h>
#include <stdint.h>

#include "nitro/bits.h"
#include "nitro/mkds/common/ids.h"

#define MKDS_GHOST_MAGIC "NKDG"
#define MKDS_PERSONAL_GHOST_MAGIC "NKPG"
#define MKDS_GHOST_FILE_SIZE 4096u
#define MKDS_PERSONAL_GHOST_SIZE 3584u
#define MKDS_GHOST_NAME_UNITS 10u
#define MKDS_GHOST_LAP_SLOTS 5u
#define MKDS_GHOST_LAP_ENTRY_SIZE 3u

typedef enum {
    MKDS_GHOST_SOURCE_MY = 0,
    MKDS_GHOST_SOURCE_DOWNLOADED = 1,
    MKDS_GHOST_SOURCE_STAFF = 2
} MkdsGhostSource;

typedef enum {
    MKDS_GHOST_LAP_1 = 0,
    MKDS_GHOST_LAP_2 = 1,
    MKDS_GHOST_LAP_3 = 2,
    MKDS_GHOST_LAP_4 = 3,
    MKDS_GHOST_LAP_5 = 4
} MkdsGhostLapSlot;

typedef enum {
    MKDS_GHOST_LAP_MINUTES = 0,
    MKDS_GHOST_LAP_SECONDS = 1,
    MKDS_GHOST_LAP_MILLISECONDS = 2
} MkdsGhostLapComponent;

#define MKDS_GHOST_LAP_BYTE(slot, component) \
    ((uint32_t)(slot) * MKDS_GHOST_LAP_ENTRY_SIZE + (uint32_t)(component))
#define MKDS_GHOST_EMBLEM_OFFSET 0x30u
#define MKDS_GHOST_EMBLEM_SIZE 512u
#define MKDS_GHOST_RUN_LENGTH_OFFSET 0x230u
#define MKDS_GHOST_RUN_DATA_OFFSET 0x234u
#define MKDS_PERSONAL_GHOST_RUN_LENGTH_OFFSET 0x30u
#define MKDS_GHOST_RUN_SIZE 2u
#define MKDS_INPUT_MAX_RUNS 1764u

#define MKDS_GHOST_YEAR_BASE 2000u

typedef enum {
    MKDS_GHOST_CUP_TIER_NONE = 0,
    MKDS_GHOST_CUP_TIER_RANK5 = 1,
    MKDS_GHOST_CUP_TIER_RANK6 = 2,
    MKDS_GHOST_CUP_TIER_RANK7 = 3
} MkdsGhostCupTier;

#define MKDS_GHOST_CUP_TIER_MASK 0x03u

typedef union {
    uint32_t raw;
    struct {
        uint32_t character : 4;
        uint32_t kart : 6;
        uint32_t course : 6;
        uint32_t year : 7;
        uint32_t month : 4;
        uint32_t day : 5;
    } bits;
} MkdsGhostIdentity;

#define MKDS_GHOST_IDENTITY_CHARACTER_MASK NITRO_MASK(4, 0)
#define MKDS_GHOST_IDENTITY_KART_MASK NITRO_MASK(6, 4)
#define MKDS_GHOST_IDENTITY_COURSE_MASK NITRO_MASK(6, 10)
#define MKDS_GHOST_IDENTITY_YEAR_MASK NITRO_MASK(7, 16)
#define MKDS_GHOST_IDENTITY_MONTH_MASK NITRO_MASK(4, 23)
#define MKDS_GHOST_IDENTITY_DAY_MASK NITRO_MASK(5, 27)

_Static_assert(sizeof(MkdsGhostIdentity) == 4, "ghost identity word");

typedef union {
    uint32_t raw;
    struct {
        uint32_t valid : 1;
        uint32_t flag_1 : 1;
        uint32_t region : 2;
        uint32_t flags_4_7 : 4;
        uint32_t minutes : 7;
        uint32_t seconds : 7;
        uint32_t milliseconds : 10;
    } bits;
} MkdsGhostResult;

_Static_assert(sizeof(MkdsGhostResult) == 4, "ghost result word");

typedef enum {
    MKDS_GHOST_RESULT_VALID = NITRO_BIT(0),
    MKDS_GHOST_RESULT_CUSTOM_EMBLEM = NITRO_BIT(1),
    MKDS_GHOST_RESULT_REGION_MASK = NITRO_MASK(2, 2),
    MKDS_GHOST_RESULT_FLAGS_MASK = NITRO_MASK(4, 4)
} MkdsGhostResultField;

#define MKDS_GHOST_CUSTOM_EMBLEM MKDS_GHOST_RESULT_CUSTOM_EMBLEM

typedef struct {
    char magic[4];
    MkdsGhostIdentity identity;
    MkdsGhostResult result;
    MkdsNicknameUnit nickname[MKDS_GHOST_NAME_UNITS];
    uint8_t lap_time[MKDS_GHOST_LAP_SLOTS][MKDS_GHOST_LAP_ENTRY_SIZE];
    uint8_t rank_tier_2f;
} MkdsGhostHeader;

_Static_assert(offsetof(MkdsGhostHeader, identity) == 0x04, "ghost identity");
_Static_assert(offsetof(MkdsGhostHeader, result) == 0x08, "ghost result");
_Static_assert(offsetof(MkdsGhostHeader, nickname) == 0x0C, "ghost nickname");
_Static_assert(offsetof(MkdsGhostHeader, lap_time) == 0x20, "ghost lap times");
_Static_assert(offsetof(MkdsGhostHeader, rank_tier_2f) == 0x2F, "ghost +0x2F");
_Static_assert(sizeof(MkdsGhostHeader) == 48, "ghost header");

static inline uint32_t mkds_ghost_lap_value(const uint8_t entry[MKDS_GHOST_LAP_ENTRY_SIZE])
{
    return ((uint32_t)entry[0] << 16) | ((uint32_t)entry[1] << 8) | entry[2];
}

static inline uint8_t mkds_ghost_lap_minutes(uint32_t value)
{
    return (uint8_t)((value >> 17) & 0x7Fu);
}

static inline uint8_t mkds_ghost_lap_seconds(uint32_t value)
{
    return (uint8_t)((value >> 10) & 0x7Fu);
}

static inline uint16_t mkds_ghost_lap_millis(uint32_t value)
{
    return (uint16_t)(value & 0x3FFu);
}

typedef union {
    uint8_t raw;
    struct {
        uint8_t button_a : 1;
        uint8_t button_b : 1;
        uint8_t button_r : 1;
        uint8_t button_lx : 1;
        uint8_t dpad_right : 1;
        uint8_t dpad_left : 1;
        uint8_t dpad_down : 1;
        uint8_t dpad_up : 1;
    } bits;
} MkdsInputButtons;

typedef struct {
    MkdsInputButtons input;
    uint8_t          frames;
} MkdsGhostInputRun;

_Static_assert(sizeof(MkdsInputButtons) == 1, "ghost input buttons");
_Static_assert(sizeof(MkdsGhostInputRun) == MKDS_GHOST_RUN_SIZE, "ghost input run");

typedef struct {
    uint32_t byte_length;
} MkdsGhostInputHeader;

_Static_assert(sizeof(MkdsGhostInputHeader) == 4u, "ghost input header");

typedef enum {
    MKDS_INPUT_A_BIT = 0,
    MKDS_INPUT_B_BIT = 1,
    MKDS_INPUT_R_BIT = 2,
    MKDS_INPUT_LX_BIT = 3,
    MKDS_INPUT_DPAD_RIGHT_BIT = 4,
    MKDS_INPUT_DPAD_LEFT_BIT = 5,
    MKDS_INPUT_DPAD_DOWN_BIT = 6,
    MKDS_INPUT_DPAD_UP_BIT = 7
} MkdsInputButtonBit;

#define MKDS_INPUT_BUTTON_A NITRO_BIT(MKDS_INPUT_A_BIT)
#define MKDS_INPUT_BUTTON_B NITRO_BIT(MKDS_INPUT_B_BIT)
#define MKDS_INPUT_BUTTON_R NITRO_BIT(MKDS_INPUT_R_BIT)
#define MKDS_INPUT_BUTTON_LX NITRO_BIT(MKDS_INPUT_LX_BIT)
#define MKDS_INPUT_DPAD_RIGHT NITRO_BIT(MKDS_INPUT_DPAD_RIGHT_BIT)
#define MKDS_INPUT_DPAD_LEFT NITRO_BIT(MKDS_INPUT_DPAD_LEFT_BIT)
#define MKDS_INPUT_DPAD_DOWN NITRO_BIT(MKDS_INPUT_DPAD_DOWN_BIT)
#define MKDS_INPUT_DPAD_UP NITRO_BIT(MKDS_INPUT_DPAD_UP_BIT)

_Static_assert(MKDS_GHOST_LAP_SLOTS * MKDS_GHOST_LAP_ENTRY_SIZE == 15u,
               "ghost lap slots");
_Static_assert(MKDS_GHOST_RUN_DATA_OFFSET + 4u + (2u * MKDS_INPUT_MAX_RUNS) ==
                   MKDS_GHOST_FILE_SIZE,
               "NKDG input capacity");
_Static_assert(MKDS_PERSONAL_GHOST_RUN_LENGTH_OFFSET + 4u + (2u * MKDS_INPUT_MAX_RUNS) <=
                   MKDS_PERSONAL_GHOST_SIZE,
               "NKPG input capacity");

typedef struct {
    uint32_t magic;
    MkdsGhostIdentity info_0;
    MkdsGhostResult info_1;
    MkdsNicknameUnit nickname[MKDS_GHOST_NAME_UNITS];
    uint8_t  lap_times[15];
    uint8_t  rank_tier_2F;
} SavGhostHeader;

_Static_assert(sizeof(SavGhostHeader) == 48, "ghost header");
_Static_assert(sizeof(SavGhostHeader) == sizeof(MkdsGhostHeader),
               "ghost header layouts agree");
_Static_assert(offsetof(SavGhostHeader, info_0) == 0x04, "ghost info 0");
_Static_assert(offsetof(SavGhostHeader, info_1) == 0x08, "ghost info 1");
_Static_assert(offsetof(SavGhostHeader, nickname) == 0x0C, "ghost nickname");
_Static_assert(offsetof(SavGhostHeader, lap_times) == 0x20, "ghost lap times");
_Static_assert(offsetof(SavGhostHeader, rank_tier_2F) == 0x2F,
               "ghost rank tier");

#define SAV_INPUT_KEYS_A NITRO_BIT(MKDS_INPUT_A_BIT)
#define SAV_INPUT_KEYS_B NITRO_BIT(MKDS_INPUT_B_BIT)
#define SAV_INPUT_KEYS_R NITRO_BIT(MKDS_INPUT_R_BIT)
#define SAV_INPUT_KEYS_LX NITRO_BIT(MKDS_INPUT_LX_BIT)
#define SAV_INPUT_KEYS_RIGHT NITRO_BIT(MKDS_INPUT_DPAD_RIGHT_BIT)
#define SAV_INPUT_KEYS_LEFT NITRO_BIT(MKDS_INPUT_DPAD_LEFT_BIT)
#define SAV_INPUT_KEYS_DOWN NITRO_BIT(MKDS_INPUT_DPAD_DOWN_BIT)
#define SAV_INPUT_KEYS_UP NITRO_BIT(MKDS_INPUT_DPAD_UP_BIT)

typedef struct {
    MkdsInputButtons keys;
    uint8_t          duration;
} SavInputEntry;

_Static_assert(sizeof(SavInputEntry) == 2, "input recording entry");

typedef struct {
    uint32_t data_length;
    SavInputEntry entries[MKDS_INPUT_MAX_RUNS];
} SavInputRecording;

_Static_assert(sizeof(SavInputRecording) == 3532, "input recording");
_Static_assert(offsetof(SavInputRecording, entries) == 0x04, "input entries");

typedef struct {
    SavGhostHeader    header;
    SavInputRecording input;
    uint8_t           reserved_FCC[4];
} SavPersonalGhostBlock;

_Static_assert(sizeof(SavPersonalGhostBlock) == MKDS_PERSONAL_GHOST_SIZE, "NKPG size");

typedef struct {
    SavGhostHeader    header;
    uint8_t           emblem[MKDS_GHOST_EMBLEM_SIZE];
    SavInputRecording input;
    uint8_t           reserved_FFC[4];
} SavDownloadGhostBlock;

_Static_assert(sizeof(SavDownloadGhostBlock) == MKDS_GHOST_FILE_SIZE, "NKDG size");
