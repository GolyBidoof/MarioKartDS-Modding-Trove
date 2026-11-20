/* ui_common.h — shared JNLib list and coordinate helpers. SPDX-License-Identifier: MIT */
#pragma once

#include <stddef.h>
#include <stdint.h>

#define MKDS_UI_LIST_HEADER_SIZE 8u

typedef uint16_t MkdsUiElementCount;
typedef uint32_t MkdsUiCellId;
typedef uint32_t MkdsUiStringOffset;
typedef uint16_t MkdsUiKeyId;
typedef uint16_t MkdsUiEmblemId;

typedef struct {
    char magic[4];
    uint16_t reserved;
    MkdsUiElementCount count;
} MkdsUiListHeader;

_Static_assert(sizeof(MkdsUiListHeader) == MKDS_UI_LIST_HEADER_SIZE,
               "JNLib list header");
_Static_assert(sizeof(MkdsUiElementCount) == 2, "JNLib element count");
_Static_assert(sizeof(MkdsUiCellId) == 4, "JNLib cell id");
_Static_assert(sizeof(MkdsUiStringOffset) == 4, "JNLib string offset");
_Static_assert(sizeof(MkdsUiKeyId) == 2, "JNLib key id");
_Static_assert(sizeof(MkdsUiEmblemId) == 2, "JNLib emblem id");
_Static_assert(offsetof(MkdsUiListHeader, count) == 0x06,
               "JNLib list count offset");

typedef enum {
    MKDS_UI_ORIGIN_START = 0,
    MKDS_UI_ORIGIN_CENTER = 1,
    MKDS_UI_ORIGIN_END = 2
} MkdsUiOrigin;

typedef enum {
    MKDS_UI_LINE_ALIGN_START = 0,
    MKDS_UI_LINE_ALIGN_CENTER = 1,
    MKDS_UI_LINE_ALIGN_END = 2
} MkdsUiLineAlign;

typedef union {
    uint16_t raw;
    struct {
        int16_t value : 12;
        uint16_t origin : 2;
        uint16_t param : 2;
    } bits;
} MkdsUiCoord;

_Static_assert(sizeof(MkdsUiCoord) == 2, "JNLib coordinate word");

static inline int16_t mkds_ui_coord_value(MkdsUiCoord coord)
{
    return coord.bits.value;
}

static inline uint8_t mkds_ui_coord_origin(MkdsUiCoord coord)
{
    return (uint8_t)coord.bits.origin;
}

static inline uint8_t mkds_ui_coord_param(MkdsUiCoord coord)
{
    return (uint8_t)coord.bits.param;
}
