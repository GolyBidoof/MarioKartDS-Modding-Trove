/* grpconf.h — MapObj/grpconf.tbl object group profiles. SPDX-License-Identifier: MIT */
#pragma once

#include <stddef.h>
#include <stdint.h>

#define MKDS_OBJECT_GROUP_CONFIG_RECORD_SIZE 16u
#define MKDS_OBJECT_GROUP_CONFIG_MAIN_RACE_COUNT 133u
#define MKDS_OBJECT_GROUP_CONFIG_MAIN_COUNT 91u

#define MKDS_OBJECT_GROUP_NO_DISTANCE_CLIP 9999u

typedef uint16_t MkdsWorldUnits;

typedef enum {
    MKDS_OBJECT_MODEL_NONE = 0,
    MKDS_OBJECT_MODEL_BILLBOARD = 1,
    MKDS_OBJECT_MODEL_THREE_D = 2
} MkdsObjectModelKind;

typedef enum {
    MKDS_OBJECT_COLLISION_NONE = 0,
    MKDS_OBJECT_COLLISION_SPHERE = 1,
    MKDS_OBJECT_COLLISION_SPHEROID = 2,
    MKDS_OBJECT_COLLISION_CYLINDER = 3,
    MKDS_OBJECT_COLLISION_BOX = 4,
    MKDS_OBJECT_COLLISION_CUSTOM = 5
} MkdsObjectCollisionShape;

typedef struct {
    uint16_t object_id;
    uint16_t model_kind;
    MkdsWorldUnits near_clip;
    MkdsWorldUnits far_clip;
    uint16_t collision_shape;
    MkdsWorldUnits width;
    MkdsWorldUnits height;
    MkdsWorldUnits depth;
} MkdsObjectGroupConfig;

static inline MkdsObjectModelKind
mkds_object_model_kind(const MkdsObjectGroupConfig *config)
{
    return (MkdsObjectModelKind)config->model_kind;
}

static inline MkdsObjectCollisionShape
mkds_object_collision_shape(const MkdsObjectGroupConfig *config)
{
    return (MkdsObjectCollisionShape)config->collision_shape;
}

_Static_assert(sizeof(MkdsObjectGroupConfig) ==
                   MKDS_OBJECT_GROUP_CONFIG_RECORD_SIZE,
               "object group config record");
_Static_assert(offsetof(MkdsObjectGroupConfig, model_kind) == 0x02,
               "object group model kind");
_Static_assert(offsetof(MkdsObjectGroupConfig, near_clip) == 0x04,
               "object group near clip");
_Static_assert(offsetof(MkdsObjectGroupConfig, collision_shape) == 0x08,
               "object group collision shape");
_Static_assert(offsetof(MkdsObjectGroupConfig, width) == 0x0A,
               "object group width");
_Static_assert(offsetof(MkdsObjectGroupConfig, depth) == 0x0E,
               "object group depth");
