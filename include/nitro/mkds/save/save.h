/* save.h — MKDS flash save container and block records. SPDX-License-Identifier: MIT */
#pragma once

#include <stddef.h>
#include <stdint.h>

#include "nitro/bits.h"
#include "nitro/mkds/save/ghost.h"
#include "nitro/mkds/common/ids.h"
#include "nitro/mkds/files/misc.h"
#include "nitro/mkds/common/time.h"

#define SAV_FILE_SIZE              262144u
#define SAV_BLOCK_ALIGN            256u
#define SAV_BLOCK_HEADER_SIZE      8u
#define SAV_BLOCK_FOOTER_SIZE      4u
#define SAV_ERASED_BYTE            0xFFu
#define SAV_FILE_MAGIC             "MKDSSV10"
#define SAV_NICKNAME_UNITS         10u
#define SAV_PERSONAL_GHOST_COUNT   32u
#define SAV_DOWNLOAD_GHOST_COUNT   10u
#define SAV_EMBLEM_SIZE            512u
#define SAV_EMBLEM_SLOT_COUNT      5u
#define SAV_FRIEND_COUNT           60u
#define SAV_DWC_FRIEND_RECORD_SIZE 12u
#define SAV_GP_MODE_COUNT          4u
#define SAV_CUP_COUNT              8u
#define SAV_TIME_TRIALS_RANK_COUNT          6u
#define SAV_TIME_TRIALS_COURSE_COUNT        32u
#define SAV_MISSION_COUNT          63u
#define SAV_INPUT_ENTRY_COUNT      1764u

_Static_assert(SAV_NICKNAME_UNITS == MKDS_GHOST_NAME_UNITS, "ghost name units");
_Static_assert(SAV_INPUT_ENTRY_COUNT == MKDS_INPUT_MAX_RUNS, "ghost input runs");

#define SAV_BLOCK_MAGIC(a, b, c, d) \
    ((uint32_t)(a) | ((uint32_t)(b) << 8) | ((uint32_t)(c) << 16) | ((uint32_t)(d) << 24))
#define SAV_MAGIC_NKSY SAV_BLOCK_MAGIC('N', 'K', 'S', 'Y')
#define SAV_MAGIC_NKEM SAV_BLOCK_MAGIC('N', 'K', 'E', 'M')
#define SAV_MAGIC_NKGP SAV_BLOCK_MAGIC('N', 'K', 'G', 'P')
#define SAV_MAGIC_NKTA SAV_BLOCK_MAGIC('N', 'K', 'T', 'A')
#define SAV_MAGIC_NKMR SAV_BLOCK_MAGIC('N', 'K', 'M', 'R')
#define SAV_MAGIC_NKFL SAV_BLOCK_MAGIC('N', 'K', 'F', 'L')
#define SAV_MAGIC_NKFE SAV_BLOCK_MAGIC('N', 'K', 'F', 'E')
#define SAV_MAGIC_NKPG SAV_BLOCK_MAGIC('N', 'K', 'P', 'G')
#define SAV_MAGIC_NKDG SAV_BLOCK_MAGIC('N', 'K', 'D', 'G')

#define SAV_OFF_NKSY   0x00000u
#define SAV_OFF_NKEM   0x00100u
#define SAV_OFF_NKGP   0x00400u
#define SAV_OFF_NKTA   0x00800u
#define SAV_OFF_NKMR   0x01E00u
#define SAV_OFF_NKFL   0x01F00u
#define SAV_OFF_NKFE   0x02B00u
#define SAV_OFF_NKPG   0x0AF00u
#define SAV_OFF_NKDG   0x26F00u

#define SAV_BACKUP_OFF_NKSY 0x30F00u
#define SAV_BACKUP_OFF_NKEM 0x31000u
#define SAV_BACKUP_OFF_NKGP 0x31300u
#define SAV_BACKUP_OFF_NKTA 0x31700u
#define SAV_BACKUP_OFF_NKMR 0x32D00u
#define SAV_BACKUP_OFF_NKFL 0x32E00u
#define SAV_BACKUP_OFF_NKFE 0x33A00u

#define SAV_NKSY_SIZE 256u
#define SAV_NKEM_SIZE 768u
#define SAV_NKGP_SIZE 1024u
#define SAV_NKTA_SIZE 5632u
#define SAV_NKMR_SIZE 256u
#define SAV_NKFL_SIZE 3072u
#define SAV_NKFE_SIZE 2816u
#define SAV_NKPG_SIZE 3584u
#define SAV_NKDG_SIZE 4096u

#define SAV_NKFE_SLOT_OFFSET(n) (SAV_OFF_NKFE + (uint32_t)(n) * SAV_NKFE_SIZE)
#define SAV_NKPG_SLOT_OFFSET(n) (SAV_OFF_NKPG + (uint32_t)(n) * SAV_NKPG_SIZE)
#define SAV_NKDG_SLOT_OFFSET(n) (SAV_OFF_NKDG + (uint32_t)(n) * SAV_NKDG_SIZE)

_Static_assert(SAV_NKPG_SIZE == MKDS_PERSONAL_GHOST_SIZE, "NKPG block size");
_Static_assert(SAV_NKDG_SIZE == MKDS_GHOST_FILE_SIZE, "NKDG block size");

typedef struct {
    uint8_t timestamp_hi;
    uint8_t timestamp_lo;
    uint8_t crc_hi;
    uint8_t crc_lo;
} SavBlockFooter;

_Static_assert(sizeof(SavBlockFooter) == SAV_BLOCK_FOOTER_SIZE, "save footer");

typedef union {
    uint8_t raw;
    struct {
        uint8_t nickname_set : 1;
        uint8_t sound : 2;
        uint8_t emblem_deleted : 1;
        uint8_t reserved : 4;
    } bits;
} SavNksyFlags31;

typedef enum {
    SAV_NKSY_FLAG_NICKNAME_SET = NITRO_BIT(0),
    SAV_NKSY_FLAG_SOUND_MASK = NITRO_MASK(2, 1)
} SavNksyFlag;

typedef union {
    uint8_t raw;
    struct {
        uint8_t valid : 1;
        uint8_t reserved : 7;
    } bits;
} SavNkemFlags;

#define SAV_NKEM_FLAG_VALID NITRO_BIT(0)

typedef union {
    uint32_t raw;
    uint8_t  any_unlock_bits[4];
} SavAnyUnlockBits;

typedef struct {
    uint8_t  file_magic[8];
    uint32_t block_magic;
    MkdsNicknameUnit nickname[SAV_NICKNAME_UNITS];
    uint8_t  unlock_bits[4];
    uint16_t elo;
    uint8_t  personal_ghost_bits[4];
    uint8_t  download_ghost_bits[4];
    uint8_t  emblem_used_bits[2];
    uint8_t  padding_30;
    SavNksyFlags31 flags_31;
    uint8_t  padding_32;
    SavAnyUnlockBits any_unlock;
    uint8_t  max_kart_unlock_level;
    uint8_t  min_kart_unlock_level;
    uint8_t  padding_3A[2];
    uint32_t reserved_3C;
    uint32_t reserved_40;
    uint32_t net_wins;
    uint32_t net_losses;
    uint8_t  dwc_user[64];
    uint8_t  reserved_8C[SAV_NKSY_SIZE - 0x8C];
} SavIdentityBlock;

_Static_assert(offsetof(SavIdentityBlock, block_magic) == 0x08, "NKSY magic");
_Static_assert(offsetof(SavIdentityBlock, nickname) == 0x0C, "NKSY nickname");
_Static_assert(offsetof(SavIdentityBlock, unlock_bits) == 0x20, "NKSY unlock bits");
_Static_assert(offsetof(SavIdentityBlock, elo) == 0x24, "NKSY elo");
_Static_assert(offsetof(SavIdentityBlock, personal_ghost_bits) == 0x26, "NKSY personal ghosts");
_Static_assert(offsetof(SavIdentityBlock, download_ghost_bits) == 0x2A, "NKSY download ghosts");
_Static_assert(offsetof(SavIdentityBlock, dwc_user) == 0x4C, "NKSY DWC user");

#define SAV_UNLOCK_BIT_LEVEL_2 17u
#define SAV_UNLOCK_BIT_LEVEL_3 18u
#define SAV_UNLOCK_BIT_LEVEL_4 19u

static inline int sav_unlock_bit(const uint8_t bits[4], unsigned index)
{
    return (bits[index >> 3] >> (index & 7u)) & 1;
}

static inline unsigned sav_kart_unlock_level(const SavIdentityBlock *block)
{
    if (sav_unlock_bit(block->unlock_bits, SAV_UNLOCK_BIT_LEVEL_4))
        return 4u;
    if (sav_unlock_bit(block->unlock_bits, SAV_UNLOCK_BIT_LEVEL_3))
        return 3u;
    if (sav_unlock_bit(block->unlock_bits, SAV_UNLOCK_BIT_LEVEL_2))
        return 2u;
    return 1u;
}

_Static_assert(sizeof(SavIdentityBlock) == SAV_NKSY_SIZE, "NKSY size");

typedef struct {
    uint32_t magic;
    SavNkemFlags valid_and_reserved;
    uint8_t  reserved_5[3];
    MkdsEmblemBitmap emblem;
    uint8_t  reserved_208[SAV_NKEM_SIZE - 0x208];
} SavEmblemBlock;

_Static_assert(sizeof(SavEmblemBlock) == SAV_NKEM_SIZE, "NKEM size");
_Static_assert(offsetof(SavEmblemBlock, emblem) == 0x08, "NKEM emblem");

typedef union {
    uint32_t raw;
    struct {
        uint32_t valid : 1;
        uint32_t character : 7;
        uint32_t kart : 8;
        uint32_t rank_points : 8;
        uint32_t rank : 8;
    } bits;
} SavGpInfo0;

typedef union {
    uint32_t raw;
    struct {
        uint32_t trophy : 8;
        uint32_t minutes : 7;
        uint32_t seconds : 7;
        uint32_t milliseconds : 10;
    } bits;
} SavGpInfo1;

typedef struct {
    SavGpInfo0 info_0;
    SavGpInfo1 info_1;
    MkdsNicknameUnit nickname[SAV_NICKNAME_UNITS];
} SavGpEntry;

_Static_assert(sizeof(SavGpEntry) == 28, "NKGP entry");
_Static_assert(sizeof(SavGpInfo0) == 4, "NKGP info 0");
_Static_assert(sizeof(SavGpInfo1) == 4, "NKGP info 1");

static inline MkdsRaceClock sav_gp_clock(const SavGpInfo1 *info)
{
    MkdsRaceClock clock;
    clock.minutes = (uint8_t)info->bits.minutes;
    clock.seconds = (uint8_t)info->bits.seconds;
    clock.milliseconds = (uint16_t)info->bits.milliseconds;
    return clock;
}

static inline MkdsRaceMilliseconds sav_gp_milliseconds(const SavGpInfo1 *info)
{
    return mkds_clock_to_milliseconds(sav_gp_clock(info));
}

typedef struct {
    uint32_t magic;
    SavGpEntry entries[SAV_GP_MODE_COUNT][SAV_CUP_COUNT];
    uint8_t  reserved_384[SAV_NKGP_SIZE - 0x384];
} SavGpBlock;

_Static_assert(sizeof(SavGpBlock) == SAV_NKGP_SIZE, "NKGP size");

typedef union {
    uint32_t raw;
    struct {
        uint32_t valid : 1;
        uint32_t character : 7;
        uint32_t minutes : 7;
        uint32_t seconds : 7;
        uint32_t milliseconds : 10;
    } bits;
} SavTimeTrialsInfo;

typedef enum {
    MKDS_TIME_TRIALS_PLACE_1 = 0,
    MKDS_TIME_TRIALS_PLACE_2 = 1,
    MKDS_TIME_TRIALS_PLACE_3 = 2,
    MKDS_TIME_TRIALS_PLACE_4 = 3,
    MKDS_TIME_TRIALS_PLACE_5 = 4,
    MKDS_TIME_TRIALS_BEST_TIME = 5
} MkdsTimeTrialsPlace;

typedef struct {
    SavTimeTrialsInfo info_0;
    MkdsKartId kart;
    uint8_t  reserved_5[3];
    MkdsNicknameUnit nickname[SAV_NICKNAME_UNITS];
} SavTimeTrialsEntry;

_Static_assert(sizeof(SavTimeTrialsEntry) == 28, "NKTA entry");
_Static_assert(sizeof(SavTimeTrialsInfo) == 4, "NKTA info 0");

static inline MkdsRaceClock sav_time_trials_clock(const SavTimeTrialsInfo *info)
{
    MkdsRaceClock clock;
    clock.minutes = (uint8_t)info->bits.minutes;
    clock.seconds = (uint8_t)info->bits.seconds;
    clock.milliseconds = (uint16_t)info->bits.milliseconds;
    return clock;
}

static inline MkdsRaceMilliseconds sav_time_trials_milliseconds(const SavTimeTrialsInfo *info)
{
    return mkds_clock_to_milliseconds(sav_time_trials_clock(info));
}

typedef struct {
    uint32_t magic;
    /* second index is 8x4 cup order, not race course id */
    SavTimeTrialsEntry entries[SAV_TIME_TRIALS_RANK_COUNT][SAV_TIME_TRIALS_COURSE_COUNT];
    uint8_t  reserved_1504[SAV_NKTA_SIZE - 0x1504];
} SavTimeTrialsBlock;

_Static_assert(sizeof(SavTimeTrialsBlock) == SAV_NKTA_SIZE, "NKTA size");

typedef union {
    uint8_t raw;
    struct {
        uint8_t valid : 1;
        uint8_t rank : 7;
    } bits;
} SavMissionRankEntry;

_Static_assert(sizeof(SavMissionRankEntry) == 1, "NKMR entry");

typedef struct {
    uint32_t magic;
    /* indexed by mission menu slot, not mission id */
    SavMissionRankEntry entries[SAV_MISSION_COUNT];
    uint8_t  reserved_43[SAV_NKMR_SIZE - 0x43];
} SavMissionRankBlock;

_Static_assert(sizeof(SavMissionRankBlock) == SAV_NKMR_SIZE, "NKMR size");

typedef union {
    uint16_t raw;
    struct {
        uint16_t year : 7;
        uint16_t month : 4;
        uint16_t day : 5;
    } bits;
} SavFriendDate;

typedef union {
    uint8_t raw;
    struct {
        uint8_t valid : 1;
        uint8_t offline : 1;
        uint8_t has_emblem : 1;
        uint8_t locked : 1;
        uint8_t flags : 4;
    } bits;
} SavFriendFlags;

typedef enum {
    MKDS_FRIEND_SLOT_1 = 0,
    MKDS_FRIEND_SLOT_2 = 1,
    MKDS_FRIEND_SLOT_3 = 2,
    MKDS_FRIEND_SLOT_4 = 3,
    MKDS_FRIEND_SLOT_5 = 4,
    MKDS_FRIEND_SLOT_6 = 5,
    MKDS_FRIEND_SLOT_7 = 6,
    MKDS_FRIEND_SLOT_8 = 7,
    MKDS_FRIEND_SLOT_9 = 8,
    MKDS_FRIEND_SLOT_10 = 9,
    MKDS_FRIEND_SLOT_11 = 10,
    MKDS_FRIEND_SLOT_12 = 11,
    MKDS_FRIEND_SLOT_13 = 12,
    MKDS_FRIEND_SLOT_14 = 13,
    MKDS_FRIEND_SLOT_15 = 14,
    MKDS_FRIEND_SLOT_16 = 15,
    MKDS_FRIEND_SLOT_17 = 16,
    MKDS_FRIEND_SLOT_18 = 17,
    MKDS_FRIEND_SLOT_19 = 18,
    MKDS_FRIEND_SLOT_20 = 19,
    MKDS_FRIEND_SLOT_21 = 20,
    MKDS_FRIEND_SLOT_22 = 21,
    MKDS_FRIEND_SLOT_23 = 22,
    MKDS_FRIEND_SLOT_24 = 23,
    MKDS_FRIEND_SLOT_25 = 24,
    MKDS_FRIEND_SLOT_26 = 25,
    MKDS_FRIEND_SLOT_27 = 26,
    MKDS_FRIEND_SLOT_28 = 27,
    MKDS_FRIEND_SLOT_29 = 28,
    MKDS_FRIEND_SLOT_30 = 29,
    MKDS_FRIEND_SLOT_31 = 30,
    MKDS_FRIEND_SLOT_32 = 31,
    MKDS_FRIEND_SLOT_33 = 32,
    MKDS_FRIEND_SLOT_34 = 33,
    MKDS_FRIEND_SLOT_35 = 34,
    MKDS_FRIEND_SLOT_36 = 35,
    MKDS_FRIEND_SLOT_37 = 36,
    MKDS_FRIEND_SLOT_38 = 37,
    MKDS_FRIEND_SLOT_39 = 38,
    MKDS_FRIEND_SLOT_40 = 39,
    MKDS_FRIEND_SLOT_41 = 40,
    MKDS_FRIEND_SLOT_42 = 41,
    MKDS_FRIEND_SLOT_43 = 42,
    MKDS_FRIEND_SLOT_44 = 43,
    MKDS_FRIEND_SLOT_45 = 44,
    MKDS_FRIEND_SLOT_46 = 45,
    MKDS_FRIEND_SLOT_47 = 46,
    MKDS_FRIEND_SLOT_48 = 47,
    MKDS_FRIEND_SLOT_49 = 48,
    MKDS_FRIEND_SLOT_50 = 49,
    MKDS_FRIEND_SLOT_51 = 50,
    MKDS_FRIEND_SLOT_52 = 51,
    MKDS_FRIEND_SLOT_53 = 52,
    MKDS_FRIEND_SLOT_54 = 53,
    MKDS_FRIEND_SLOT_55 = 54,
    MKDS_FRIEND_SLOT_56 = 55,
    MKDS_FRIEND_SLOT_57 = 56,
    MKDS_FRIEND_SLOT_58 = 57,
    MKDS_FRIEND_SLOT_59 = 58,
    MKDS_FRIEND_SLOT_60 = 59,
} MkdsFriendSlot;

typedef struct {
    uint16_t vs_wins;
    uint16_t vs_losses;
    uint16_t battle_wins;
    uint16_t battle_losses;
    uint16_t net_wins;
    uint16_t net_losses;
    SavFriendDate date;
    MkdsNicknameUnit nickname[SAV_NICKNAME_UNITS];
    SavFriendFlags flags;
    uint8_t  reserved_23;
} SavFriendProfile;

_Static_assert(sizeof(SavFriendProfile) == 36, "friend profile");
_Static_assert(sizeof(SavFriendDate) == 2, "friend date");
_Static_assert(sizeof(SavFriendFlags) == 1, "friend flags");

typedef struct {
    uint32_t magic;
    SavFriendProfile profiles[SAV_FRIEND_COUNT];
    uint8_t  dwc_friends[SAV_FRIEND_COUNT * SAV_DWC_FRIEND_RECORD_SIZE];
    uint8_t  reserved_B44[SAV_NKFL_SIZE - 0xB44];
} SavFriendBlock;

_Static_assert(SAV_FRIEND_COUNT * SAV_DWC_FRIEND_RECORD_SIZE == 720u,
               "NKFL DWC friend area");
_Static_assert(offsetof(SavFriendBlock, dwc_friends) == 0x874, "NKFL DWC friends");
_Static_assert(sizeof(SavFriendBlock) == SAV_NKFL_SIZE, "NKFL size");

typedef enum {
    MKDS_EMBLEM_SLOT_1 = 0,
    MKDS_EMBLEM_SLOT_2 = 1,
    MKDS_EMBLEM_SLOT_3 = 2,
    MKDS_EMBLEM_SLOT_4 = 3,
    MKDS_EMBLEM_SLOT_5 = 4
} MkdsEmblemSlot;

typedef struct {
    uint32_t magic;
    uint8_t  emblem_slot_mask;
    uint8_t  reserved_5[3];
    MkdsEmblemBitmap emblems[SAV_EMBLEM_SLOT_COUNT];
    uint8_t  reserved_A08[SAV_NKFE_SIZE - 0xA08];
} SavEmblemBank;

_Static_assert(sizeof(SavEmblemBank) == SAV_NKFE_SIZE, "NKFE size");

#define SAV_NKFE_SLOT_USED(mask, slot) \
    ((uint8_t)(((uint8_t)(mask) >> (slot)) & 0x01u))
