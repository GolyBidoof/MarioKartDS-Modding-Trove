/* dwc.h — NARC-less DWC utility archive. SPDX-License-Identifier: MIT */
#pragma once

#include <stddef.h>
#include <stdint.h>

#define MKDS_DWC_HEADER_SIZE 16u
#define MKDS_DWC_FNT_OFFSET 0x10u
#define MKDS_DWC_STOCK_FILE_SIZE 1069000u
#define MKDS_DWC_STOCK_FNT_SIZE 0x1498u
#define MKDS_DWC_STOCK_FAT_SIZE 0x0AB0u
#define MKDS_DWC_STOCK_FILE_COUNT 342u

typedef struct {
    uint32_t fnt_offset;
    uint32_t fnt_size;
    uint32_t fat_offset;
    uint32_t fat_size;
} MkdsDwcArchiveHeader;

typedef struct {
    uint32_t start;
    uint32_t end;
} MkdsDwcFatEntry; /* start/end are relative to the file, not the FAT */

#define MKDS_DWC_FAT_ENTRY_SIZE 8u
#define MKDS_DWC_FNT_MAIN_ENTRY_SIZE 8u

typedef struct {
    uint32_t subtable_offset;
    uint16_t first_file_id;
    uint16_t parent_or_directory_count;
} MkdsDwcFntDirectory;

#define MKDS_DWC_FNT_ROOT_ID 0xF000u
#define MKDS_DWC_FNT_DIRECTORY_MASK 0xF000u
#define MKDS_DWC_FNT_SUBTABLE_END 0x00u
#define MKDS_DWC_FNT_DIRECTORY_FLAG 0x80u

_Static_assert(sizeof(MkdsDwcArchiveHeader) == MKDS_DWC_HEADER_SIZE,
               "DWC archive header");
_Static_assert(sizeof(MkdsDwcFatEntry) == MKDS_DWC_FAT_ENTRY_SIZE,
               "DWC FAT entry");
_Static_assert(sizeof(MkdsDwcFntDirectory) == MKDS_DWC_FNT_MAIN_ENTRY_SIZE,
               "DWC FNT directory entry");
_Static_assert(MKDS_DWC_STOCK_FAT_SIZE / MKDS_DWC_FAT_ENTRY_SIZE ==
                   MKDS_DWC_STOCK_FILE_COUNT,
               "DWC stock file count");
