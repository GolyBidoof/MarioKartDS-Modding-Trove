/* nkm.h — NKM course map. SPDX-License-Identifier: MIT */
#pragma once

#include <stddef.h>
#include <stddef.h>
#include <stdint.h>

#include "nitro/bits.h"
#include "nitro/fx.h"
#include "nitro/mkds/common/ids.h"
#include "nitro/rgb555.h"

#define NKM_MAGIC "NKMD"
#define NKM_SECTION_HEADER_SIZE 8u

typedef enum {
    NKM_VERSION_30 = 30,
    NKM_VERSION_32 = 32,
    NKM_VERSION_34 = 34,
    NKM_VERSION_36 = 36,
    NKM_VERSION_37 = 37
} NkmVersion;

#define NKM_SEC_OBJI "OBJI"
#define NKM_SEC_PATH "PATH"
#define NKM_SEC_POIT "POIT"
#define NKM_SEC_STAG "STAG"
#define NKM_SEC_KTPS "KTPS"
#define NKM_SEC_KTPJ "KTPJ"
#define NKM_SEC_KTP2 "KTP2"
#define NKM_SEC_KTPC "KTPC"
#define NKM_SEC_KTPM "KTPM"
#define NKM_SEC_CPOI "CPOI"
#define NKM_SEC_CPAT "CPAT"
#define NKM_SEC_IPOI "IPOI"
#define NKM_SEC_IPAT "IPAT"
#define NKM_SEC_EPOI "EPOI"
#define NKM_SEC_EPAT "EPAT"
#define NKM_SEC_MEPO "MEPO"
#define NKM_SEC_MEPA "MEPA"
#define NKM_SEC_AREA "AREA"
#define NKM_SEC_CAME "CAME"

typedef struct {
    char     magic[4];
    uint16_t version;
    uint16_t header_size;
} NkmHeader;

_Static_assert(sizeof(NkmHeader) == 8, "NKM header");
_Static_assert(offsetof(NkmHeader, version) == 0x04, "NKM version");
_Static_assert(offsetof(NkmHeader, header_size) == 0x06, "NKM header size");

typedef struct {
    char     magic[4];
    uint32_t entry_count;
} NkmSectionHeader;

_Static_assert(sizeof(NkmSectionHeader) == NKM_SECTION_HEADER_SIZE, "NKM section");

typedef union {
    uint32_t raw;
    struct {
        uint32_t red : 5;
        uint32_t green : 5;
        uint32_t blue : 5;
        uint32_t alpha : 5;
        uint32_t reserved : 12;
    } bits;
} NkmFogColor;

_Static_assert(sizeof(NkmFogColor) == 4, "NKM fog colour");

typedef struct {
    char     magic[4];
    MkdsStageCourseId course_id;
    int16_t  lap_count;
    uint8_t  pole_position;
    uint8_t  fog_enabled;
    uint8_t  fog_table_mode;
    uint8_t  fog_shift;
    uint8_t  unidentified_0C[8]; /* course-specific, no known reader */
    Fx32     fog_offset;
    NkmFogColor fog_color;
    NitroRgb555 kcl_light_color[4];
    Fx32     object_far_clip;
    Fx32     frustum_far;
} NkmStage;

_Static_assert(sizeof(NkmStage) == 44, "STAG record");
_Static_assert(offsetof(NkmStage, course_id) == 0x04, "STAG course id");
_Static_assert(offsetof(NkmStage, fog_offset) == 0x14, "STAG fog offset");
_Static_assert(offsetof(NkmStage, fog_color) == 0x18, "STAG fog colour");
_Static_assert(offsetof(NkmStage, kcl_light_color) == 0x1C,
               "STAG KCL light colours");
_Static_assert(offsetof(NkmStage, object_far_clip) == 0x24,
               "STAG object far clip");
_Static_assert(offsetof(NkmStage, frustum_far) == 0x28, "STAG frustum far");

typedef enum {
    NKM_PATH_ONCE = 0,
    NKM_PATH_LOOP = 1
} NkmPathLoopMode;

typedef struct {
    uint8_t         index;
    uint8_t         loop;
    int16_t         point_count;
} NkmPathEntry;

static inline NkmPathLoopMode nkm_path_loop_mode(const NkmPathEntry *path)
{
    return (NkmPathLoopMode)path->loop;
}

_Static_assert(sizeof(NkmPathEntry) == 4, "PATH record");

typedef struct {
    Fx32    position[3];
    uint8_t index;
    uint8_t translucency_flags;
    int16_t duration;
    int16_t path_parameter;
    int16_t traffic_cosine;
} NkmPointEntry;

_Static_assert(sizeof(NkmPointEntry) == 20, "POIT record");

typedef int16_t NkmObjectSetting;
#define NKM_OBJECT_SETTING_PLAYER_ITEM_LIST 1
#define NKM_OBJECT_SETTING_ENEMY_ITEM_LIST 2

typedef struct {
    Fx32     position[3];
    Fx32     rotation[3];
    Fx32     scale[3];
    MkdsMapObjectId object_id;
    int16_t  path_id;
    NkmObjectSetting settings[7];
    uint16_t visibility;
    uint32_t time_trial_visible;
} NkmObjectEntry;

_Static_assert(sizeof(NkmObjectEntry) == 60, "OBJI record");
_Static_assert(offsetof(NkmObjectEntry, object_id) == 0x24, "OBJI object id");
_Static_assert(offsetof(NkmObjectEntry, settings) == 0x28, "OBJI settings");
_Static_assert(offsetof(NkmObjectEntry, visibility) == 0x36,
               "OBJI visibility");
_Static_assert(offsetof(NkmObjectEntry, time_trial_visible) == 0x38,
               "OBJI Time Trial visibility");

typedef enum {
    NKM_OBJI_CLIP_0_PLACE = 1,
    NKM_OBJI_CLIP_1_PLACE = 10,
    NKM_OBJI_CLIP_2_PLACE = 100,
    NKM_OBJI_CLIP_3_PLACE = 1000,
    NKM_OBJI_INACTIVE_PLACE = 10000
} NkmObjectVisibilityPlace;

#define NKM_OBJI_CLIP_0(v)    ((uint16_t)(((uint16_t)(v) / NKM_OBJI_CLIP_0_PLACE) % 10u))
#define NKM_OBJI_CLIP_1(v)    ((uint16_t)(((uint16_t)(v) / NKM_OBJI_CLIP_1_PLACE) % 10u))
#define NKM_OBJI_CLIP_2(v)    ((uint16_t)(((uint16_t)(v) / NKM_OBJI_CLIP_2_PLACE) % 10u))
#define NKM_OBJI_CLIP_3(v)    ((uint16_t)(((uint16_t)(v) / NKM_OBJI_CLIP_3_PLACE) % 10u))
#define NKM_OBJI_INACTIVE(v)  (((uint16_t)(v) / NKM_OBJI_INACTIVE_PLACE) == 1u)
#define NKM_OBJI_VISIBILITY(c0, c1, c2, c3, inactive) \
    ((uint16_t)(((c0) % 10u) * NKM_OBJI_CLIP_0_PLACE + \
                ((c1) % 10u) * NKM_OBJI_CLIP_1_PLACE + \
                ((c2) % 10u) * NKM_OBJI_CLIP_2_PLACE + \
                ((c3) % 10u) * NKM_OBJI_CLIP_3_PLACE + \
                ((inactive) ? NKM_OBJI_INACTIVE_PLACE : 0u)))

typedef struct {
    Fx32     position[3];
    Fx32     rotation[3];
    uint16_t marker;
    int16_t  index;
} NkmKtpsEntry;

_Static_assert(sizeof(NkmKtpsEntry) == 28, "KTPS record");

typedef struct {
    Fx32    position[3];
    Fx32    rotation[3];
    int16_t enemy_point_id;
    int16_t item_point_id;
    int32_t index;
} NkmKtpjEntry;

_Static_assert(sizeof(NkmKtpjEntry) == 32, "KTPJ record");

typedef struct {
    Fx32     position[3];
    Fx32     rotation[3];
    uint32_t marker;
} NkmKtp2Entry;

_Static_assert(sizeof(NkmKtp2Entry) == 28, "KTP2 record");

typedef struct {
    Fx32    position[3];
    Fx32    rotation[3];
    int16_t next_mepo;
    int16_t index;
} NkmKtpcEntry;

_Static_assert(sizeof(NkmKtpcEntry) == 28, "KTPC record");

typedef struct {
    Fx32     position[3];
    Fx32     rotation[3];
    uint16_t marker;
    int16_t  index;
} NkmKtpmEntry;

_Static_assert(sizeof(NkmKtpmEntry) == 28, "KTPM record");

typedef struct {
    Fx32    point1[2];
    Fx32    point2[2];
    Fx32    sine;
    Fx32    cosine;
    Fx32    distance;
    int16_t goto_section;
    int16_t start_section;
    int16_t key_point_id;
    uint8_t respawn_id;
    uint8_t flags;
} NkmCpoiEntry;

_Static_assert(sizeof(NkmCpoiEntry) == 36, "CPOI record");

typedef struct {
    uint16_t start_index;
    uint16_t length;
    uint8_t  next[3];
    uint8_t  previous[3];
    uint8_t  section_order;
    uint8_t  padding;
} NkmCpatEntry;

_Static_assert(sizeof(NkmCpatEntry) == 12, "CPAT record");

typedef struct {
    Fx32    position[3];
    Fx32    radius;
    uint8_t recalculation_index;
    uint8_t padding[3];
} NkmItemPointEntry;

_Static_assert(sizeof(NkmItemPointEntry) == 20, "IPOI record");

typedef struct {
    int16_t start_index;
    int16_t length;
    uint8_t next[3];
    uint8_t previous[3];
    int16_t section_order;
} NkmPathLinkEntry;

_Static_assert(sizeof(NkmPathLinkEntry) == 12, "IPAT/EPAT record");

typedef struct {
    Fx32    position[3];
    Fx32    radius;
    int16_t drifting;
    int16_t parameter_1;
    int16_t parameter_2;
    int16_t parameter_3;
} NkmEnemyPointEntry;

_Static_assert(sizeof(NkmEnemyPointEntry) == 24, "EPOI record");

typedef struct {
    Fx32     position[3];
    Fx32     radius;
    int16_t  drifting;
    uint8_t  padding_12[2];
    uint32_t settings_word;
} NkmMissionEnemyPointEntry;

_Static_assert(sizeof(NkmMissionEnemyPointEntry) == 24, "MEPO record");

typedef struct {
    int16_t start_index;
    int16_t length;
    uint8_t next[8];
    uint8_t previous[8];
} NkmMissionPathEntry;

_Static_assert(sizeof(NkmMissionPathEntry) == 20, "MEPA record");

typedef struct {
    Fx32    position[3];
    Fx32    length[3];
    Fx32    x_axis[3];
    Fx32    y_axis[3];
    Fx32    z_axis[3];
    int16_t parameter_0;
    int16_t parameter_1;
    int16_t enemy_point_id;
    uint8_t shape;
    uint8_t linked_camera;
    uint8_t area_type;
    uint8_t reserved_45[3];
} NkmAreaEntry;

_Static_assert(sizeof(NkmAreaEntry) == 72, "AREA record");

typedef enum {
    NKM_AREA_SHAPE_BOX = 0,
    NKM_AREA_SHAPE_CYLINDER = 1
} NkmAreaShape;

typedef enum {
    NKM_AREA_TYPE_0 = 0,
    NKM_AREA_TYPE_CAMERA = 1,
    NKM_AREA_TYPE_MISSION_END = 2,
    NKM_AREA_TYPE_CLIP = 3,
    NKM_AREA_TYPE_ENEMY_RECALC = 4,
    NKM_AREA_TYPE_MISSION_RIVAL = 5
} NkmAreaType;

typedef struct {
    Fx32     position[3];
    Fx32     rotation[3];
    Fx32     target_1[3];
    Fx32     target_2[3];
    uint16_t fov_begin;
    Fx16     fov_begin_sine;
    Fx16     fov_begin_cosine;
    uint16_t fov_end;
    Fx16     fov_end_sine;
    Fx16     fov_end_cosine;
    Fx16     fov_speed;
    uint16_t type;
    int16_t  linked_route;
    Fx16     path_speed;
    Fx16     target_speed;
    int16_t  duration;
    int16_t  next_camera;
    uint8_t  first_intro_camera;
    uint8_t  show_award_trail;
} NkmCameEntry;

_Static_assert(sizeof(NkmCameEntry) == 76, "CAME record");

typedef enum {
    NKM_CAMERA_FIXED_LOOK_DRIVER = 0,
    NKM_CAMERA_ROUTE_LOOK_DRIVER = 1,
    NKM_CAMERA_FIXED_LOOK_TARGETS = 2,
    NKM_CAMERA_ROUTE_LOOK_TARGETS = 3,
    NKM_CAMERA_INTRO_BOTTOM = 4,
    NKM_CAMERA_FOLLOW_DRIVER_A = 5,
    NKM_CAMERA_FOLLOW_DRIVER_B = 6,
    NKM_CAMERA_INTRO_MG = 7,
    NKM_CAMERA_MISSION_FINISH = 8
} NkmCameraType;

typedef enum {
    NKM_INTRO_CAMERA_NONE = 0,
    NKM_INTRO_CAMERA_TOP = 1,
    NKM_INTRO_CAMERA_BOTTOM = 2
} NkmIntroCamera;
