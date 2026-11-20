/* nds.h — NDS header, FNT/FAT and overlay table. SPDX-License-Identifier: MIT */
#pragma once

#include <stddef.h>
#include <stdint.h>

#include "bits.h"

#define NDS_HEADER_SIZE 512u
#define NDS_PREFIX_SIZE 32u
#define NDS_HEADER_RESERVED_SIZE 376u

typedef uint32_t NitroRomOffset;
typedef uint32_t NitroRomSize;
typedef uint32_t NitroRamAddress;
typedef uint32_t NitroRamSize;
typedef uint32_t NitroFileId;
typedef uint32_t NitroOverlayId;
typedef uint32_t NitroFntOffset;
typedef uint32_t NitroCardControl;
typedef uint16_t NitroCrc16;
typedef uint16_t NitroSecureTimeout;

typedef struct {
    uint8_t prefix[NDS_PREFIX_SIZE];
    NitroRomOffset arm9_rom_offset;
    NitroRamAddress arm9_entry;
    NitroRamAddress arm9_ram_address;
    NitroRomSize arm9_size;
    NitroRomOffset arm7_rom_offset;
    NitroRamAddress arm7_entry;
    NitroRamAddress arm7_ram_address;
    NitroRomSize arm7_size;
    NitroRomOffset fnt_offset;
    NitroRomSize fnt_size;
    NitroRomOffset fat_offset;
    NitroRomSize fat_size;
    NitroRomOffset arm9_overlay_offset;
    NitroRomSize arm9_overlay_size;
    NitroRomOffset arm7_overlay_offset;
    NitroRomSize arm7_overlay_size;
    NitroCardControl normal_card_control;
    NitroCardControl secure_card_control;
    NitroRomOffset icon_banner_offset;
    NitroCrc16 secure_area_crc;
    NitroSecureTimeout secure_transfer_timeout;
    NitroRamAddress arm9_autoload;
    NitroRamAddress arm7_autoload;
    uint32_t secure_disable;
    uint32_t reserved_7c;
    NitroRomSize rom_size;
    NitroRomSize header_size;
    uint8_t reserved[NDS_HEADER_RESERVED_SIZE];
} NdsHeader;

_Static_assert(offsetof(NdsHeader, arm9_rom_offset) == 0x20, "ARM9 offset");
_Static_assert(offsetof(NdsHeader, arm9_entry) == 0x24, "ARM9 entry");
_Static_assert(offsetof(NdsHeader, arm9_size) == 0x2C, "ARM9 size");
_Static_assert(offsetof(NdsHeader, arm7_rom_offset) == 0x30, "ARM7 offset");
_Static_assert(offsetof(NdsHeader, fnt_offset) == 0x40, "FNT offset");
_Static_assert(offsetof(NdsHeader, fat_offset) == 0x48, "FAT offset");
_Static_assert(offsetof(NdsHeader, arm9_overlay_offset) == 0x50, "overlay offset");
_Static_assert(offsetof(NdsHeader, normal_card_control) == 0x60,
               "normal card control");
_Static_assert(offsetof(NdsHeader, icon_banner_offset) == 0x68,
               "icon/banner offset");
_Static_assert(offsetof(NdsHeader, secure_area_crc) == 0x6C,
               "secure area CRC");
_Static_assert(offsetof(NdsHeader, arm9_autoload) == 0x70,
               "ARM9 autoload");
_Static_assert(offsetof(NdsHeader, rom_size) == 0x80, "ROM size offset");
_Static_assert(offsetof(NdsHeader, header_size) == 0x84, "header size offset");
_Static_assert(sizeof(NdsHeader) == NDS_HEADER_SIZE, "header size");

#define NDS_FNT_ENTRY_IS_DIR NITRO_BIT(7)
#define NDS_FNT_SUBDIR_BASE NITRO_MASK(4, 12)

typedef struct {
    NitroFntOffset dir_table_offset;
    uint16_t first_file_id;
    uint16_t dir_count;
} NdsFntRoot;

typedef struct {
    NitroFntOffset name_table_offset;
    uint16_t first_file_id;
    uint16_t parent_id;
} NdsFntDirEntry;

typedef struct {
    NitroRomOffset start;
    NitroRomOffset end;
} NdsFatEntry;

typedef union {
    uint32_t raw;
    struct {
        uint32_t reserved : 24;
        uint32_t compressed : 1;
        uint32_t reserved_hi : 7;
    } bits;
} NdsOverlayFlags;

#define NDS_OVERLAY_COMPRESSED NITRO_BIT(24)

typedef struct {
    NitroOverlayId overlay_id;
    NitroRamAddress ram_address;
    NitroRamSize ram_size;
    NitroRamSize bss_size;
    NitroRamAddress sinit_start;
    NitroRamAddress sinit_end;
    NitroFileId file_id;
    NdsOverlayFlags flags;
} NdsOverlayEntry;

_Static_assert(sizeof(NdsFntRoot) == 8, "FNT root");
_Static_assert(offsetof(NdsFntRoot, first_file_id) == 0x04, "FNT first file");
_Static_assert(offsetof(NdsFntRoot, dir_count) == 0x06, "FNT directory count");
_Static_assert(sizeof(NdsFntDirEntry) == 8, "FNT dir entry");
_Static_assert(offsetof(NdsFntDirEntry, parent_id) == 0x06, "FNT parent id");
_Static_assert(sizeof(NdsFatEntry) == 8, "FAT entry");
_Static_assert(sizeof(NdsOverlayFlags) == 4, "overlay flags");
_Static_assert(sizeof(NdsOverlayEntry) == 32, "overlay entry");
_Static_assert(offsetof(NdsOverlayEntry, flags) == 0x1C, "overlay flags offset");
