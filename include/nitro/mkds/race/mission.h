/* mission.h — NKMR mission table, mission menu and PRM prefix. SPDX-License-Identifier: MIT */
#pragma once

#include <stddef.h>
#include <stdint.h>

#include "nitro/mkds/common/ids.h"
#include "nitro/mkds/common/time.h"

#define MKDS_MISSION_MAGIC "NKMR"
#define MKDS_MISSION_HEADER_SIZE 8u
#define MKDS_MISSION_ENTRY_SIZE 44u
#define MKDS_MISSION_NAME_SIZE 12u

#define MKDS_MISSION_TIME_HZ 60u

#define MKDS_MISSION_CAMERA_COUNT 2u

typedef enum {
    MKDS_MISSION_CAMERA_NORMAL = 0,
    MKDS_MISSION_CAMERA_WIDE = 1
} MkdsMissionCamera;

#define MKDS_MISSION_MENU_LEVELS 7u
#define MKDS_MISSION_MENU_PER_LEVEL 9u

typedef struct {
    char magic[4];
    uint32_t entry_count;
} MkdsMissionHeader;

typedef union {
    uint16_t raw;
    struct {
        uint16_t no_forward : 1;
        uint16_t no_damage : 1;
        uint16_t no_wall_hit : 1;
        uint16_t no_respawn : 1;
        uint16_t mirror : 1;
        uint16_t backwards : 1;
        uint16_t reserved : 10;
    } bits;
} MkdsMissionFlags;

typedef struct {
    MkdsRaceFrames    time_limit;
    MkdsRaceFrames    target_time;
    int16_t           rank_delta_scale;
    MkdsMissionId     mission_id;
    MkdsMissionTask   task;
    MkdsMissionCourseId course_id;
    MkdsEngineClass   engine_class;
    MkdsCharacterId   character_id;
    MkdsKartId        kart_id;
    uint8_t           menu_index;
    uint8_t           reserved_0d;
    uint8_t           camera_index;
    uint8_t           target_value;
    MkdsRaceFrames    win_delay;
    uint16_t          reserved_12;
    MkdsMapObjectId   object_ids[4];
    MkdsMissionFlags  flags;
    MkdsCharacterId   enemy_character;
    MkdsKartId        enemy_kart;
    char              name[MKDS_MISSION_NAME_SIZE];
} MkdsMissionEntry;

_Static_assert(offsetof(MkdsMissionHeader, entry_count) == 0x04, "mission count");
_Static_assert(sizeof(MkdsMissionHeader) == MKDS_MISSION_HEADER_SIZE, "mission header");
_Static_assert(offsetof(MkdsMissionEntry, name) == 0x20, "mission name");
_Static_assert(offsetof(MkdsMissionEntry, flags) == 0x1C, "mission flags");
_Static_assert(sizeof(MkdsMissionEntry) == MKDS_MISSION_ENTRY_SIZE, "mission entry");
_Static_assert(sizeof(MkdsMissionFlags) == 2, "mission flags");
_Static_assert(MKDS_MISSION_CAMERA_COUNT == 2u, "mission camera count");

#define MKDS_MISSION_MENU_MAGIC "NKMT"
#define MKDS_MISSION_MENU_HEADER_SIZE 8u

typedef struct {
    char magic[4];
    uint16_t level_count;
    uint16_t missions_per_level;
} MkdsMissionMenuHeader;

_Static_assert(sizeof(MkdsMissionMenuHeader) == MKDS_MISSION_MENU_HEADER_SIZE,
               "mission menu header");
