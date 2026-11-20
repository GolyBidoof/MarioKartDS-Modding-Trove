/* nanr.h — Nitro NANR cell animations (RNAN). SPDX-License-Identifier: MIT */
#pragma once

#include <stddef.h>
#include <stdint.h>

#include "nitro/g2d/common.h"

#define NANR_MAGIC "RNAN"
#define NANR_KNBA_MAGIC "KNBA"
#define NANR_LABL_MAGIC "LBAL"
#define NANR_KNBA_HEADER_SIZE 24
#define NANR_ANIMATION_SIZE 16
#define NANR_FRAME_SIZE 8

typedef enum {
    NANR_ANIM_KIND_CELL = 1,
    NANR_ANIM_KIND_MULTICELL = 2
} NanrAnimationKind;

typedef enum {
    NANR_ANIM_ELEMENT_INDEX = 0,
    NANR_ANIM_ELEMENT_INDEX_SRT = 1,
    NANR_ANIM_ELEMENT_INDEX_T = 2
} NanrAnimationElement;

typedef enum {
    NANR_PLAY_FORWARD = 1,
    NANR_PLAY_FORWARD_LOOP = 2,
    NANR_PLAY_REVERSE = 3,
    NANR_PLAY_REVERSE_LOOP = 4
} NanrPlayMode;

typedef struct {
    NitroG2dMagic magic;
    NitroG2dSize block_size;
    NitroG2dAnimationCount animation_count;
    NitroG2dFrameCount frame_count;
    NitroG2dOffset animation_offset;
    NitroG2dOffset frame_offset;
    NitroG2dOffset frame_data_offset;
} NanrKnbaHeader;

typedef union {
    uint32_t raw;
    struct {
        uint32_t element : 16;
        uint32_t kind : 16;
    } bits;
} NanrAnimationType;

_Static_assert(sizeof(NanrAnimationType) == 4, "NANR animation type word");

typedef struct {
    NitroG2dFrameCount frame_count;
    NitroG2dFrameIndex loop_start_frame;
    NanrAnimationType animation_type;
    NitroG2dPlayMode play_mode;
    NitroG2dOffset first_frame_offset;
} NanrAnimation;

typedef struct {
    NitroG2dOffset data_offset;
    NitroG2dFrameDuration duration;
    uint16_t reserved;
} NanrFrame;

_Static_assert(sizeof(NanrKnbaHeader) == NANR_KNBA_HEADER_SIZE, "NANR KNBA header");
_Static_assert(sizeof(NanrAnimation) == NANR_ANIMATION_SIZE, "NANR animation block");
_Static_assert(sizeof(NanrFrame) == NANR_FRAME_SIZE, "NANR frame block");
_Static_assert(offsetof(NanrKnbaHeader, animation_count) == 0x08, "NANR animation count");
_Static_assert(offsetof(NanrKnbaHeader, frame_count) == 0x0A, "NANR frame count");
_Static_assert(offsetof(NanrKnbaHeader, animation_offset) == 0x0C, "NANR animation offset");
_Static_assert(offsetof(NanrKnbaHeader, frame_offset) == 0x10, "NANR frame offset");
_Static_assert(offsetof(NanrKnbaHeader, frame_data_offset) == 0x14, "NANR frame data offset");
_Static_assert(offsetof(NanrAnimation, loop_start_frame) == 0x02, "NANR loop start");
_Static_assert(offsetof(NanrAnimation, animation_type) == 0x04, "NANR animation type");
_Static_assert(offsetof(NanrAnimation, play_mode) == 0x08, "NANR play mode");
_Static_assert(offsetof(NanrAnimation, first_frame_offset) == 0x0C, "NANR first frame");
_Static_assert(offsetof(NanrFrame, duration) == 0x04, "NANR frame duration");
