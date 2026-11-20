/* kartappear.h — NKKT kart appearance/unlock matrix. SPDX-License-Identifier: MIT */
#pragma once

#include <stddef.h>
#include <stdint.h>

#include "nitro/mkds/common/ids.h"

#define MKDS_KART_APPEAR_MAGIC "NKKT"
#define MKDS_KART_APPEAR_HEADER_SIZE 6u
#define MKDS_KART_APPEAR_KART_COUNT 37u
#define MKDS_KART_APPEAR_CHARACTER_COUNT 13u
#define MKDS_KART_APPEAR_FILE_SIZE 487u

typedef enum {
    MKDS_KART_APPEAR_UNAVAILABLE = 0,
    MKDS_KART_APPEAR_DEFAULT = 1,
    MKDS_KART_APPEAR_UNLOCK_2 = 2,
    MKDS_KART_APPEAR_UNLOCK_3 = 3,
    MKDS_KART_APPEAR_UNLOCK_4 = 4
} MkdsKartAppearanceLevel;

typedef struct {
    char    magic[4];
    MkdsKartCount      kart_count;
    MkdsCharacterCount character_count;
} MkdsKartAppearanceHeader;

typedef struct {
    uint8_t character_level[MKDS_KART_APPEAR_CHARACTER_COUNT];
} MkdsKartAppearanceRow;

#define MKDS_KART_APPEAR_INDEX(kart_id, character_id) \
    ((size_t)MKDS_KART_APPEAR_HEADER_SIZE + \
     (size_t)(kart_id) * MKDS_KART_APPEAR_CHARACTER_COUNT + \
     (size_t)(character_id))

static inline MkdsKartAppearanceLevel
mkds_kart_appearance_level(const uint8_t *data, unsigned kart_id,
                           unsigned character_id)
{
    return (MkdsKartAppearanceLevel)
        data[MKDS_KART_APPEAR_INDEX(kart_id, character_id)];
}

static inline int
mkds_kart_appearance_available(const uint8_t *data, unsigned kart_id,
                               unsigned character_id, unsigned unlock_level)
{
    MkdsKartAppearanceLevel level =
        mkds_kart_appearance_level(data, kart_id, character_id);
    return level != MKDS_KART_APPEAR_UNAVAILABLE &&
           (unsigned)level <= unlock_level;
}

_Static_assert(sizeof(MkdsKartAppearanceHeader) ==
                   MKDS_KART_APPEAR_HEADER_SIZE,
               "kart appearance header");
_Static_assert(sizeof(MkdsKartAppearanceRow) ==
                   MKDS_KART_APPEAR_CHARACTER_COUNT,
               "kart appearance row");
_Static_assert(MKDS_KART_APPEAR_HEADER_SIZE +
                   MKDS_KART_APPEAR_KART_COUNT *
                       MKDS_KART_APPEAR_CHARACTER_COUNT ==
                   MKDS_KART_APPEAR_FILE_SIZE,
               "kart appearance file size");
