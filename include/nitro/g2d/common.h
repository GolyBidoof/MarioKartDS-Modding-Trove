/* common.h — Nitro G2D resource envelope and vocabulary. SPDX-License-Identifier: MIT */
#pragma once

#include <stddef.h>
#include <stdint.h>

#include "nitro/rgb555.h"

typedef char NitroG2dMagic[4];
typedef uint16_t NitroG2dBom;
typedef uint16_t NitroG2dVersion;
typedef uint16_t NitroG2dHeaderSize;
typedef uint16_t NitroG2dBlockCount;
typedef uint32_t NitroG2dSize;
typedef uint32_t NitroG2dOffset;
typedef uint16_t NitroG2dWidth;
typedef uint16_t NitroG2dHeight;
typedef uint16_t NitroG2dCharacterCount;
typedef uint16_t NitroG2dTileCount;
typedef uint32_t NitroG2dImageFormat;
typedef uint16_t NitroG2dScreenColorMode;
typedef uint16_t NitroG2dScreenFormat;
typedef uint32_t NitroG2dMappingMode;
typedef uint8_t NitroG2dEncoding;
typedef NitroRgb555 NitroG2dPaletteColor;
typedef uint16_t NitroG2dCellCount;
typedef uint16_t NitroG2dOamCount;
typedef uint16_t NitroG2dCellAttribute;
typedef uint16_t NitroG2dBankAttribute;
typedef uint16_t NitroG2dFontGlyphIndex;
typedef uint16_t NitroG2dFontMapping;
typedef uint16_t NitroG2dCharacterCode;
typedef uint16_t NitroG2dPaletteCount;
typedef uint16_t NitroG2dFrameCount;
typedef uint16_t NitroG2dFrameIndex;
typedef uint16_t NitroG2dAnimationCount;
typedef uint16_t NitroG2dFrameDuration;
typedef uint32_t NitroG2dPlayMode;
typedef uint32_t NitroG2dBool;

typedef enum {
    NITRO_G2D_IMAGE_FORMAT_4BPP = 3,
    NITRO_G2D_IMAGE_FORMAT_8BPP = 4
} NitroG2dImageFormatValue;

_Static_assert(sizeof(NitroG2dMagic) == 4, "G2D magic");
_Static_assert(sizeof(NitroG2dBom) == 2, "G2D byte order");
_Static_assert(sizeof(NitroG2dVersion) == 2, "G2D version");
_Static_assert(sizeof(NitroG2dHeaderSize) == 2, "G2D header size");
_Static_assert(sizeof(NitroG2dBlockCount) == 2, "G2D block count");
_Static_assert(sizeof(NitroG2dSize) == 4, "G2D size");
_Static_assert(sizeof(NitroG2dOffset) == 4, "G2D offset");
_Static_assert(sizeof(NitroG2dWidth) == 2, "G2D width");
_Static_assert(sizeof(NitroG2dHeight) == 2, "G2D height");
_Static_assert(sizeof(NitroG2dCharacterCount) == 2, "G2D character count");
_Static_assert(sizeof(NitroG2dTileCount) == 2, "G2D tile count");
_Static_assert(sizeof(NitroG2dImageFormat) == 4, "G2D image format");
_Static_assert(sizeof(NitroG2dScreenColorMode) == 2, "G2D screen colour mode");
_Static_assert(sizeof(NitroG2dScreenFormat) == 2, "G2D screen format");
_Static_assert(sizeof(NitroG2dMappingMode) == 4, "G2D mapping mode");
_Static_assert(sizeof(NitroG2dEncoding) == 1, "G2D encoding");
_Static_assert(sizeof(NitroG2dPaletteColor) == 2, "G2D palette colour");
_Static_assert(sizeof(NitroG2dCellCount) == 2, "G2D cell count");
_Static_assert(sizeof(NitroG2dOamCount) == 2, "G2D OAM count");
_Static_assert(sizeof(NitroG2dCellAttribute) == 2, "G2D cell attributes");
_Static_assert(sizeof(NitroG2dBankAttribute) == 2, "G2D bank attributes");
_Static_assert(sizeof(NitroG2dFontGlyphIndex) == 2, "G2D glyph index");
_Static_assert(sizeof(NitroG2dFontMapping) == 2, "G2D font mapping");
_Static_assert(sizeof(NitroG2dCharacterCode) == 2, "G2D character code");
_Static_assert(sizeof(NitroG2dPaletteCount) == 2, "G2D palette count");
_Static_assert(sizeof(NitroG2dFrameCount) == 2, "G2D frame count");
_Static_assert(sizeof(NitroG2dFrameIndex) == 2, "G2D frame index");
_Static_assert(sizeof(NitroG2dAnimationCount) == 2, "G2D animation count");
_Static_assert(sizeof(NitroG2dFrameDuration) == 2, "G2D frame duration");
_Static_assert(sizeof(NitroG2dPlayMode) == 4, "G2D play mode");
_Static_assert(sizeof(NitroG2dBool) == 4, "G2D boolean");

#define G2D_HEADER_SIZE 16u
#define G2D_BLOCK_HEADER_SIZE 8u
#define G2D_BOM_LITTLE 0xFEFFu
#define G2D_BOM_UNSPECIFIED 0u

typedef struct {
    NitroG2dMagic magic;
    NitroG2dBom byte_order;
    NitroG2dVersion version;
    NitroG2dSize file_size;
    NitroG2dHeaderSize header_size;
    NitroG2dBlockCount block_count;
} G2dFileHeader;

typedef struct {
    NitroG2dMagic magic;
    NitroG2dSize block_size;
} G2dBlockHeader;

_Static_assert(sizeof(G2dFileHeader) == G2D_HEADER_SIZE, "G2D file header");
_Static_assert(sizeof(G2dBlockHeader) == G2D_BLOCK_HEADER_SIZE, "G2D block header");
_Static_assert(offsetof(G2dFileHeader, byte_order) == 0x04, "G2D byte order");
_Static_assert(offsetof(G2dFileHeader, file_size) == 0x08, "G2D file size");
_Static_assert(offsetof(G2dFileHeader, block_count) == 0x0E, "G2D block count");

#define G2D_UEXT_MAGIC "TXEU"
#define G2D_UEXT_SIZE 12u

typedef struct {
    NitroG2dMagic magic;
    NitroG2dSize block_size;
    uint32_t value;
} G2dUextBlock;

_Static_assert(sizeof(G2dUextBlock) == G2D_UEXT_SIZE, "G2D UEXT block");
_Static_assert(offsetof(G2dUextBlock, value) == 0x08, "G2D UEXT value");
