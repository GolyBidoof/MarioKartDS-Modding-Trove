/* staffghost.h — staff_ghost_time.bin table. SPDX-License-Identifier: MIT */
#pragma once

#include <stddef.h>
#include <stdint.h>

#include "nitro/mkds/common/ids.h"
#include "nitro/mkds/common/time.h"

#define MKDS_STAFF_TIME_SLOTS 40u
#define MKDS_STAFF_TIME_FILE_SIZE 160u

#define MKDS_STAFF_TIME_SLOT(course_id) ((uint32_t)(course_id) - 1u)

typedef struct {
    MkdsRaceMilliseconds threshold_ms[MKDS_STAFF_TIME_SLOTS];
} MkdsStaffGhostTimes;

static inline MkdsRaceMilliseconds
mkds_staff_ghost_threshold(const MkdsStaffGhostTimes *times,
                           MkdsRaceCourseId course_id)
{
    return times->threshold_ms[MKDS_STAFF_TIME_SLOT(course_id)];
}

_Static_assert(MKDS_STAFF_TIME_SLOTS * sizeof(MkdsRaceMilliseconds) ==
                   MKDS_STAFF_TIME_FILE_SIZE,
               "staff ghost stride");
_Static_assert(sizeof(MkdsStaffGhostTimes) == MKDS_STAFF_TIME_FILE_SIZE,
               "staff ghost file");
