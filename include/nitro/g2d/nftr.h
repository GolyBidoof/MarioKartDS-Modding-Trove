/* nftr.h — Nitro NFTR fonts (RTFN). SPDX-License-Identifier: MIT */
#pragma once

#include <stddef.h>
#include <stdint.h>

#include "nitro/g2d/common.h"

#define NFTR_MAGIC "RTFN"
#define NFTR_INFO_MAGIC "FNIF"
#define NFTR_GLYPH_MAGIC "PLGC"
#define NFTR_WIDTH_MAGIC "HDWC"
#define NFTR_CODE_MAP_MAGIC "PAMC"
#define NFTR_INFO_HEADER_SIZE 28
#define NFTR_GLYPH_HEADER_SIZE 16
#define NFTR_WIDTH_HEADER_SIZE 16
#define NFTR_CODE_MAP_HEADER_SIZE 20
#define NFTR_OFFSET_BASE 0x08

typedef enum {
    NFTR_CODE_MAP_DIRECT = 0,
    NFTR_CODE_MAP_TABLE = 1,
    NFTR_CODE_MAP_SCAN = 2
} NftrCodeMapMethod;

typedef enum {
    NFTR_ENCODING_UTF8 = 0,
    NFTR_ENCODING_UTF16 = 1,
    NFTR_ENCODING_SHIFT_JIS = 2,
    NFTR_ENCODING_CP1252 = 3
} NftrEncoding;

typedef enum {
    NFTR_VERSION_0100 = 0x0100,
    NFTR_VERSION_0001 = 0x0001
} NftrVersion;

typedef struct {
    NitroG2dMagic magic;
    NitroG2dSize block_size;
    uint8_t font_type;
    uint8_t line_feed;
    NitroG2dFontGlyphIndex alternate_index;
    int8_t default_left;
    uint8_t default_glyph_width;
    int8_t default_char_width;
    NitroG2dEncoding encoding;
    NitroG2dOffset glyph_offset;
    NitroG2dOffset width_offset;
    NitroG2dOffset code_map_offset;
} NftrInfoBlock;

typedef struct {
    NitroG2dMagic magic;
    NitroG2dSize block_size;
    uint8_t cell_width;
    uint8_t cell_height;
    uint16_t cell_size;
    int8_t baseline;
    uint8_t max_char_width;
    uint8_t bpp;
    uint8_t reserved;
} NftrGlyphBlock;

typedef struct {
    int8_t left;
    uint8_t width;
    int8_t advance;
} NftrCharWidth;

typedef struct {
    int8_t left;
    uint8_t width;
} NftrCharWidthOld;

typedef struct {
    NitroG2dMagic magic;
    NitroG2dSize block_size;
    uint8_t font_type;
    uint8_t line_feed;
    NitroG2dFontGlyphIndex alternate_index;
    int8_t default_left;
    uint8_t default_glyph_width;
    NitroG2dEncoding encoding;
    uint8_t reserved;
    NitroG2dOffset glyph_offset;
    NitroG2dOffset width_offset;
    NitroG2dOffset code_map_offset;
} NftrInfoBlockOld;

typedef struct {
    NitroG2dMagic magic;
    NitroG2dSize block_size;
    NitroG2dFontGlyphIndex index_begin;
    NitroG2dFontGlyphIndex index_end;
    NitroG2dOffset next_offset;
} NftrWidthBlock;

typedef struct {
    NitroG2dMagic magic;
    NitroG2dSize block_size;
    NitroG2dCharacterCode code_begin;
    NitroG2dCharacterCode code_end;
    NitroG2dFontMapping mapping_method;
    uint16_t reserved;
    NitroG2dOffset next_offset;
} NftrCodeMapBlock;

typedef struct {
    NitroG2dCharacterCode character_code;
    NitroG2dFontGlyphIndex glyph_index;
} NftrScanEntry;

_Static_assert(sizeof(NftrInfoBlock) == NFTR_INFO_HEADER_SIZE, "NFTR FINF header");
_Static_assert(sizeof(NftrGlyphBlock) == NFTR_GLYPH_HEADER_SIZE, "NFTR CGLP header");
_Static_assert(sizeof(NftrCharWidth) == 3, "NFTR character width");
_Static_assert(sizeof(NftrCharWidthOld) == 2, "NFTR old character width");
_Static_assert(sizeof(NftrInfoBlockOld) == NFTR_INFO_HEADER_SIZE, "NFTR old FINF header");
_Static_assert(sizeof(NftrWidthBlock) == NFTR_WIDTH_HEADER_SIZE, "NFTR CWDH header");
_Static_assert(sizeof(NftrCodeMapBlock) == NFTR_CODE_MAP_HEADER_SIZE, "NFTR CMAP header");
_Static_assert(sizeof(NftrScanEntry) == 4, "NFTR CMAP scan entry");
_Static_assert(offsetof(NftrInfoBlock, encoding) == 0x0F, "NFTR encoding");
_Static_assert(offsetof(NftrInfoBlockOld, encoding) == 0x0E, "NFTR old encoding");
_Static_assert(offsetof(NftrInfoBlockOld, glyph_offset) == 0x10, "NFTR old glyph offset");
_Static_assert(offsetof(NftrInfoBlock, glyph_offset) == 0x10, "NFTR glyph offset");
_Static_assert(offsetof(NftrGlyphBlock, cell_size) == 0x0A, "NFTR glyph cell size");
_Static_assert(offsetof(NftrGlyphBlock, bpp) == 0x0E, "NFTR glyph bpp");
_Static_assert(offsetof(NftrWidthBlock, next_offset) == 0x0C, "NFTR width next offset");
_Static_assert(offsetof(NftrCodeMapBlock, mapping_method) == 0x0C,
               "NFTR code map method");
_Static_assert(offsetof(NftrCodeMapBlock, next_offset) == 0x10, "NFTR code map next offset");
