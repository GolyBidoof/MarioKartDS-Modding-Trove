/* prm.h — MissionRun boss parameter files. SPDX-License-Identifier: MIT */
#pragma once

#include <stddef.h>
#include <stdint.h>

#include "nitro/fx.h"

#define MKDS_BOSS_PARAM_PREFIX_SIZE 16u

typedef enum {
    MKDS_BOSS_PARAM_VARIANT_COMMON = 0,
    MKDS_BOSS_PARAM_VARIANT_BOSS_DONKETU = 1,
    MKDS_BOSS_PARAM_VARIANT_DEFAULT = 3
} MkdsBossParamVariant;

typedef struct {
    uint32_t                variant;
    Fx32                    model_scale;
    Fx32                    body_extent_a;
    Fx32                    body_extent_b;
} MkdsBossParamPrefix; /* +0x10..end is opaque per-boss data */

_Static_assert(sizeof(MkdsBossParamPrefix) == MKDS_BOSS_PARAM_PREFIX_SIZE,
               "boss parameter prefix");
_Static_assert(offsetof(MkdsBossParamPrefix, model_scale) == 0x04,
               "boss parameter scale");
_Static_assert(offsetof(MkdsBossParamPrefix, body_extent_b) == 0x0C,
               "boss parameter extent B");
