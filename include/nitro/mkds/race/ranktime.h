/* ranktime.h — NKTT rank-time table. SPDX-License-Identifier: MIT */
#pragma once

#include <stddef.h>
#include <stdint.h>

#include "nitro/mkds/common/ids.h"
#include "nitro/mkds/common/time.h"

#define MKDS_RANK_TIME_MAGIC "NKTT"
#define MKDS_RANK_TIME_HEADER_SIZE 28u
#define MKDS_RANK_TIME_ENTRY_SIZE 8u
#define MKDS_RANK_TIME_COURSE_COUNT 32u
#define MKDS_RANK_TIME_CLASS_COUNT 3u

typedef uint16_t MkdsRankTimePoints;

typedef struct {
    char                magic[4];
    uint32_t            file_size;
    uint16_t            course_count;
    MkdsRankTimePoints  time_delta_factor;
    MkdsRankTimePoints  first_place_factor;
    MkdsRankTimePoints  start_boost_points;
    MkdsRankTimePoints  power_slide_points;
    MkdsRankTimePoints  item_hit_points;
    MkdsRankTimePoints  off_road_time_divisor;
    MkdsRankTimePoints  wall_hit_points;
    MkdsRankTimePoints  damage_points;
    MkdsRankTimePoints  respawn_points;
} MkdsRankTimeHeader; /* rows are in historical table order; lookup is by course_id */

typedef struct {
    MkdsRaceCourseId course_id;
    uint8_t          reserved_01;
    MkdsRaceFrames   target_frames_50cc;
    MkdsRaceFrames   target_frames_100cc;
    MkdsRaceFrames   target_frames_150cc;
} MkdsRankTimeCourse;

_Static_assert(offsetof(MkdsRankTimeHeader, course_count) == 0x08, "rank time count");
_Static_assert(sizeof(MkdsRankTimeHeader) == MKDS_RANK_TIME_HEADER_SIZE, "rank time header");
_Static_assert(offsetof(MkdsRankTimeCourse, target_frames_50cc) == 0x02, "rank time 50cc");
_Static_assert(offsetof(MkdsRankTimeCourse, target_frames_100cc) == 0x04,
               "rank time 100cc");
_Static_assert(offsetof(MkdsRankTimeCourse, target_frames_150cc) == 0x06,
               "rank time 150cc");
_Static_assert(sizeof(MkdsRankTimeCourse) == MKDS_RANK_TIME_ENTRY_SIZE, "rank time entry");
_Static_assert(MKDS_RANK_TIME_COURSE_COUNT == 32u, "rank time course count");
