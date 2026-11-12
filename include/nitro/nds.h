/*
 * Mario Kart DS Modding Trove
 * include/nitro/nds.h — NDS header, FNT/FAT and overlay table
 * SPDX-License-Identifier: MIT
 * Notes: docs/nitro.md
 * References: GBATEK, ndstool; see ../CREDITS.md
 */
#pragma once

#include <stddef.h>
#include <stdint.h>

#define NDS_HEADER_SIZE 0x200u
#define NDS_PREFIX_SIZE 0x20u

typedef struct {
    uint8_t prefix[NDS_PREFIX_SIZE];  /* title, game code, maker, card fields */
    uint32_t arm9_rom_offset;
    uint32_t arm9_entry;
    uint32_t arm9_ram_address;
    uint32_t arm9_size;
    uint32_t arm7_rom_offset;
    uint32_t arm7_entry;
    uint32_t arm7_ram_address;
    uint32_t arm7_size;
    uint32_t fnt_offset;
    uint32_t fnt_size;
    uint32_t fat_offset;
    uint32_t fat_size;
    uint32_t arm9_overlay_offset;
    uint32_t arm9_overlay_size;
    uint32_t arm7_overlay_offset;
    uint32_t arm7_overlay_size;
    uint32_t normal_card_control;
    uint32_t secure_card_control;
    uint32_t icon_banner_offset;
    uint16_t secure_area_crc;
    uint16_t secure_transfer_timeout;
    uint32_t arm9_autoload;
    uint32_t arm7_autoload;
    uint32_t secure_disable;
    uint32_t reserved_7c;
    uint32_t rom_size;
    uint32_t header_size;
    uint8_t reserved[0x178];
} NdsHeader;

_Static_assert(offsetof(NdsHeader, arm9_rom_offset) == 0x20, "ARM9 offset");
_Static_assert(offsetof(NdsHeader, fnt_offset) == 0x40, "FNT offset");
_Static_assert(offsetof(NdsHeader, arm9_overlay_offset) == 0x50, "overlay offset");
_Static_assert(offsetof(NdsHeader, rom_size) == 0x80, "ROM size offset");
_Static_assert(offsetof(NdsHeader, header_size) == 0x84, "header size offset");
_Static_assert(sizeof(NdsHeader) == NDS_HEADER_SIZE, "header size");

#define NDS_FNT_ENTRY_IS_DIR 0x80u
#define NDS_FNT_SUBDIR_BASE 0xF000u

typedef struct {
    uint32_t dir_table_offset;
    uint16_t first_file_id;
    uint16_t dir_count;
} NdsFntRoot;

typedef struct {
    uint32_t name_table_offset;
    uint16_t first_file_id;
    uint16_t parent_id;
} NdsFntDirEntry;

typedef struct {
    uint32_t start;
    uint32_t end;
} NdsFatEntry;

typedef struct {
    uint32_t overlay_id;
    uint32_t ram_address;
    uint32_t ram_size;
    uint32_t bss_size;
    uint32_t sinit_start;
    uint32_t sinit_end;
    uint32_t file_id;
    uint32_t flags;
} NdsOverlayEntry;

_Static_assert(sizeof(NdsFntRoot) == 8, "FNT root");
_Static_assert(sizeof(NdsFntDirEntry) == 8, "FNT dir entry");
_Static_assert(sizeof(NdsFatEntry) == 8, "FAT entry");
_Static_assert(sizeof(NdsOverlayEntry) == 32, "overlay entry");

#define NDS_OVERLAY_COMPRESSED 0x01000000u
