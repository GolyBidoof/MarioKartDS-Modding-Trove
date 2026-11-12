/*
 * Mario Kart DS Modding Trove
 * debug/recomp/examples/bmp.h — optional 32-bit BMP helper for host adapters
 * SPDX-License-Identifier: MIT
 *
 * Pixels are 32-bit BGRA, matching the common DS framebuffer expansion. The
 * host can crop a native 256x384 image (upper + lower) or write a full frame.
 */
#pragma once

#include <stdint.h>

int dbg_bmp_write_bgra8888(const char *path, const uint32_t *pixels,
                           int width, int height, int stride_pixels);

int dbg_bmp_write_region_bgra8888(const char *path, const uint32_t *pixels,
                                  int source_width, int source_height,
                                  int x, int y, int width, int height);
