/* rankpoint.h — NKPT rank-point table. SPDX-License-Identifier: MIT */
#pragma once

#include <stddef.h>
#include <stdint.h>

#define MKDS_RANK_POINT_MAGIC "NKPT"
#define MKDS_RANK_POINT_HEADER_SIZE 8u
#define MKDS_RANK_POINT_ROW_SIZE 8u
#define MKDS_RANK_POINT_ROW_COUNT 20u
#define MKDS_RANK_POINT_COLUMN_COUNT 8u

typedef uint8_t MkdsRankPoints;

typedef enum {
    MKDS_RANK_POINT_PLACE_1 = 0,
    MKDS_RANK_POINT_PLACE_2 = 1,
    MKDS_RANK_POINT_PLACE_3 = 2,
    MKDS_RANK_POINT_PLACE_4 = 3,
    MKDS_RANK_POINT_PLACE_5 = 4,
    MKDS_RANK_POINT_PLACE_6 = 5,
    MKDS_RANK_POINT_PLACE_7 = 6,
    MKDS_RANK_POINT_PLACE_8 = 7
} MkdsRankPointPlace;

typedef struct {
    char     magic[4];
    uint32_t file_size;
} MkdsRankPointHeader;

#define MKDS_RANK_POINT_ROW_GP 0u
#define MKDS_RANK_POINT_ROW_NO_TEAMS(driver_count) (9u - (driver_count))
#define MKDS_RANK_POINT_ROW_TEAMS_SMALL(driver_count) (16u - (driver_count))
#define MKDS_RANK_POINT_ROW_TEAMS_FULL(driver_count) (23u - (driver_count))

typedef struct {
    MkdsRankPoints place_points[MKDS_RANK_POINT_COLUMN_COUNT];
} MkdsRankPointRow;

_Static_assert(sizeof(MkdsRankPointHeader) == MKDS_RANK_POINT_HEADER_SIZE, "rank point header");
_Static_assert(sizeof(MkdsRankPointRow) == MKDS_RANK_POINT_ROW_SIZE, "rank point row");
_Static_assert(MKDS_RANK_POINT_ROW_SIZE == MKDS_RANK_POINT_COLUMN_COUNT,
               "rank point row columns");
