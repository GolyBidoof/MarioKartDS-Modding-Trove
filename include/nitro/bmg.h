/*
 * Mario Kart DS Modding Trove
 * include/nitro/bmg.h — MESG/bmg1, INF1/DAT1/MID1
 * SPDX-License-Identifier: MIT
 * Notes: docs/bmg.md
 * References: Mario Kart Toolbox; see ../CREDITS.md
 */
#pragma once

#include <stddef.h>
#include <stdint.h>

#define BMG_MAGIC "MESG"
#define BMG_VERSION "bmg1"
#define BMG_HEADER_SIZE 0x20u
#define BMG_SECTION_HEADER_SIZE 0x08u
#define BMG_INF1_HEADER_SIZE 0x10u
#define BMG_DAT1_HEADER_SIZE 0x08u
#define BMG_MID1_HEADER_SIZE 0x10u
#define BMG_INF1_ENTRY_SIZE 4u
#define BMG_DAT1_ALIGNMENT 0x20u
#define BMG_ENCODING_UTF16LE 2u

typedef struct {
    char magic[4];
    char version[4];
    uint32_t file_size;
    uint32_t section_count;
    uint32_t encoding;
    uint8_t reserved[0x0C];
} BmgHeader;

typedef struct {
    char magic[4];
    uint32_t size;
} BmgSectionHeader;

typedef struct {
    char magic[4];
    uint32_t size;
    uint16_t count;
    uint16_t entry_size;
    uint32_t reserved;
} BmgInf1Header;

typedef struct {
    char magic[4];
    uint32_t size;
} BmgDat1Header;

typedef struct {
    char magic[4];
    uint32_t size;
    uint32_t count;
    uint32_t entry_size;
} BmgMid1Header;

_Static_assert(sizeof(BmgHeader) == BMG_HEADER_SIZE, "BMG header");
_Static_assert(sizeof(BmgSectionHeader) == BMG_SECTION_HEADER_SIZE, "BMG section");
_Static_assert(sizeof(BmgInf1Header) == BMG_INF1_HEADER_SIZE, "INF1 header");
_Static_assert(sizeof(BmgDat1Header) == BMG_DAT1_HEADER_SIZE, "DAT1 header");
_Static_assert(sizeof(BmgMid1Header) == BMG_MID1_HEADER_SIZE, "MID1 header");
