/* kbdmap.h — KBDMAP character list. SPDX-License-Identifier: MIT */
#pragma once

#include <stddef.h>
#include <stdint.h>

#define MKDS_UI_KBDMAP_BOM 0xFFFEu
#define MKDS_UI_KBDMAP_PREFIX_SIZE 2u

static inline uint16_t mkds_ui_kbdmap_bom(const uint8_t *data)
{
    return (uint16_t)((uint16_t)data[0] | ((uint16_t)data[1] << 8));
}

static inline size_t mkds_ui_kbdmap_count(size_t size)
{
    return size >= MKDS_UI_KBDMAP_PREFIX_SIZE
               ? (size - MKDS_UI_KBDMAP_PREFIX_SIZE) / 2u
               : 0u;
}

static inline uint16_t mkds_ui_kbdmap_char(const uint8_t *data, size_t index)
{
    const uint8_t *unit = data + MKDS_UI_KBDMAP_PREFIX_SIZE + index * 2u;
    return (uint16_t)((uint16_t)unit[0] | ((uint16_t)unit[1] << 8));
}
