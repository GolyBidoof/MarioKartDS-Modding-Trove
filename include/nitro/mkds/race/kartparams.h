/* kartparams.h — kart and character parameter tables. SPDX-License-Identifier: MIT */
#pragma once

#include <stddef.h>
#include <stdint.h>

#include "nitro/fx.h"
#include "nitro/mkds/common/ids.h"
#include "nitro/rgb555.h"

#define MKDS_KART_PHYS_ROW_144 144u
#define MKDS_KART_PHYS_ROW_148 148u
#define MKDS_KART_PHYS_ROW_152 152u
#define MKDS_KART_AI_ROW 12u
#define MKDS_KART_COLOR_ROW 8u
#define MKDS_KART_OFFSET_ROW 224u
#define MKDS_KART_MENU_ROW 12u
#define MKDS_CHAR_PHYS_ROW 8u
#define MKDS_CHAR_MENU_ROW 2u

#define MKDS_AXIS_COUNT 3u
#define MKDS_TIRE_COUNT 4u
#define MKDS_CHARACTER_SLOT_COUNT 13u

#define MKDS_KART_AI_GP_SLOT(engine_class) \
    ((uint32_t)(engine_class))
#define MKDS_KART_AI_OTHER_SLOT(engine_class, cpu_mode) \
    ((((uint32_t)(engine_class) + 1u) * 3u) + (uint32_t)(cpu_mode))

typedef enum {
    MKDS_AXIS_X = 0,
    MKDS_AXIS_Y = 1,
    MKDS_AXIS_Z = 2
} MkdsAxis;

typedef enum {
    MKDS_TIRE_FRONT_POS_X = 0,
    MKDS_TIRE_FRONT_NEG_X = 1,
    MKDS_TIRE_REAR_POS_X = 2,
    MKDS_TIRE_REAR_NEG_X = 3
} MkdsTireSlot;

typedef enum {
    MKDS_SURFACE_ROAD = 0,
    MKDS_SURFACE_ROAD_ALT = 1,
    MKDS_SURFACE_WEAK_OFF_ROAD = 2,
    MKDS_SURFACE_OFF_ROAD = 3,
    MKDS_SURFACE_HEAVY_OFF_ROAD = 4,
    MKDS_SURFACE_SLIPPERY_1 = 5,
    MKDS_SURFACE_SLIPPERY_2 = 6,
    MKDS_SURFACE_UNUSED_7 = 7,
    MKDS_SURFACE_BOOST = 8,
    MKDS_SURFACE_CANNON = 9,
    MKDS_SURFACE_WATER = 10,
    MKDS_SURFACE_LOOP = 11,
    MKDS_SURFACE_COUNT = 12
} MkdsCollisionSurface;

typedef struct {
    Fx32 rival_target_speed_bonus;
    Fx32 pack_closing_response_scale;
    Fx32 leading_cpu_slowdown_threshold;
} MkdsKartAiRow;

typedef struct {
    NitroRgb555 diffuse;
    NitroRgb555 ambient;
    NitroRgb555 specular;
    NitroRgb555 emission;
} MkdsKartColorRow;

typedef struct {
    int16_t speed;
    int16_t acceleration;
    int16_t weight;
    int16_t handling;
    int16_t drift;
    int16_t items;
} MkdsKartMenuRow;

typedef struct {
    Fx32     collision_sphere_size;
    Fx32     collision_sphere_z_offset;
    Fx32     extent_08;
    Fx16     weight;
    int16_t  drift_boost_frames;
    Fx32     max_speed;
    Fx32     base_acceleration;
    Fx32     acceleration_at_curve_end;
    Fx32     acceleration_curve_fraction;
    Fx32     drift_base_acceleration;
    Fx32     drift_acceleration_at_curve_end;
    Fx32     drift_curve_fraction;
    Fx32     deceleration;
    Fx16     handling;
    Fx16     drift;
    Fx32     drift_turn_compensation;
    Fx32     collision_velocity_multiplier[MKDS_SURFACE_COUNT];
    Fx32     collision_speed_multiplier[MKDS_SURFACE_COUNT];
} MkdsKartPhysRow152;

typedef struct {
    Fx32     collision_sphere_size;
    Fx32     collision_sphere_z_offset;
    Fx32     extent_08;
    Fx16     weight;
    int16_t  drift_boost_frames;
    Fx32     max_speed;
    Fx32     base_acceleration;
    Fx32     acceleration_at_curve_end;
    Fx32     acceleration_curve_fraction;
    Fx32     drift_base_acceleration;
    Fx32     drift_acceleration_at_curve_end;
    Fx32     drift_curve_fraction;
    Fx32     deceleration;
    Fx16     handling;
    Fx16     drift;
    Fx32     collision_velocity_multiplier[MKDS_SURFACE_COUNT];
    Fx32     collision_speed_multiplier[MKDS_SURFACE_COUNT];
} MkdsKartPhysRow148;

typedef struct {
    Fx32     collision_sphere_size;
    Fx32     collision_sphere_z_offset;
    Fx16     weight;
    int16_t  drift_boost_frames;
    Fx32     max_speed;
    Fx32     base_acceleration;
    Fx32     acceleration_at_curve_end;
    Fx32     acceleration_curve_fraction;
    Fx32     drift_base_acceleration;
    Fx32     drift_acceleration_at_curve_end;
    Fx32     drift_curve_fraction;
    Fx32     deceleration;
    Fx16     handling;
    Fx16     drift;
    Fx32     collision_velocity_multiplier[MKDS_SURFACE_COUNT];
    Fx32     collision_speed_multiplier[MKDS_SURFACE_COUNT];
} MkdsKartPhysRow144;

typedef struct {
    char tire_name[16];
    Fx32 front_tire_scale;
    Fx32 tire_positions[MKDS_TIRE_COUNT][MKDS_AXIS_COUNT];
    Fx32 character_positions[MKDS_CHARACTER_SLOT_COUNT][MKDS_AXIS_COUNT];
} MkdsKartOffsetRow;

typedef struct {
    Fx32 collision_speed_scale;
    Fx32 weight;
} MkdsCharPhysRow;

typedef struct {
    int16_t weight_offset;
} MkdsCharacterMenuRow;

_Static_assert(sizeof(MkdsKartAiRow) == MKDS_KART_AI_ROW, "kart AI row");
_Static_assert(sizeof(MkdsKartColorRow) == MKDS_KART_COLOR_ROW, "kart color row");
_Static_assert(sizeof(MkdsKartMenuRow) == MKDS_KART_MENU_ROW, "kart menu row");
_Static_assert(sizeof(MkdsKartPhysRow144) == MKDS_KART_PHYS_ROW_144, "kart physical row 144");
_Static_assert(offsetof(MkdsKartPhysRow144, weight) == 0x08, "kart 144 weight");
_Static_assert(offsetof(MkdsKartPhysRow144, max_speed) == 0x0C, "kart 144 max speed");
_Static_assert(offsetof(MkdsKartPhysRow144, acceleration_at_curve_end) == 0x14,
               "kart 144 acceleration curve");
_Static_assert(offsetof(MkdsKartPhysRow144, drift_acceleration_at_curve_end) == 0x20,
               "kart 144 drift curve");
_Static_assert(offsetof(MkdsKartPhysRow144, drift_base_acceleration) == 0x1C,
               "kart 144 drift");
_Static_assert(offsetof(MkdsKartPhysRow144, deceleration) == 0x28,
               "kart 144 deceleration");
_Static_assert(offsetof(MkdsKartPhysRow144, handling) == 0x2C, "kart 144 handling");
_Static_assert(offsetof(MkdsKartPhysRow144, collision_velocity_multiplier) == 0x30,
               "kart 144 collision table");
_Static_assert(sizeof(MkdsKartPhysRow148) == MKDS_KART_PHYS_ROW_148, "kart physical row 148");
_Static_assert(offsetof(MkdsKartPhysRow148, weight) == 0x0C, "kart 148 weight");
_Static_assert(offsetof(MkdsKartPhysRow148, max_speed) == 0x10, "kart 148 max speed");
_Static_assert(offsetof(MkdsKartPhysRow148, acceleration_at_curve_end) == 0x18,
               "kart 148 acceleration curve");
_Static_assert(offsetof(MkdsKartPhysRow148, handling) == 0x30, "kart 148 handling");
_Static_assert(offsetof(MkdsKartPhysRow148, collision_velocity_multiplier) == 0x34,
               "kart 148 collision table");
_Static_assert(offsetof(MkdsKartPhysRow152, weight) == 0x0C, "kart weight");
_Static_assert(offsetof(MkdsKartPhysRow152, max_speed) == 0x10, "kart max speed");
_Static_assert(offsetof(MkdsKartPhysRow152, acceleration_at_curve_end) == 0x18,
               "kart acceleration curve");
_Static_assert(offsetof(MkdsKartPhysRow152, drift_acceleration_at_curve_end) == 0x24,
               "kart drift curve");
_Static_assert(offsetof(MkdsKartPhysRow152, handling) == 0x30, "kart handling");
_Static_assert(offsetof(MkdsKartPhysRow152, collision_velocity_multiplier) == 0x38,
               "kart collision table");
_Static_assert(offsetof(MkdsKartPhysRow152, collision_speed_multiplier) == 0x68,
               "kart collision speed table");
_Static_assert(sizeof(MkdsKartPhysRow152) == MKDS_KART_PHYS_ROW_152, "kart physical row");
_Static_assert(sizeof(MkdsKartOffsetRow) == MKDS_KART_OFFSET_ROW, "kart offset row");
_Static_assert(sizeof(MkdsCharPhysRow) == MKDS_CHAR_PHYS_ROW, "char physical row");
_Static_assert(sizeof(MkdsCharacterMenuRow) == MKDS_CHAR_MENU_ROW,
               "char menu row");
