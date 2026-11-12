/*
 * Mario Kart DS Modding Trove
 * debug/recomp/examples/bmp.c — optional 32-bit BMP helper
 * SPDX-License-Identifier: MIT
 */
#include "bmp.h"

#include <stdio.h>
#include <string.h>

static void put16(unsigned char *p, uint16_t value)
{
    p[0] = (unsigned char)value;
    p[1] = (unsigned char)(value >> 8);
}

static void put32(unsigned char *p, uint32_t value)
{
    p[0] = (unsigned char)value;
    p[1] = (unsigned char)(value >> 8);
    p[2] = (unsigned char)(value >> 16);
    p[3] = (unsigned char)(value >> 24);
}

static int write_bgra(const char *path, const uint32_t *pixels,
                      int width, int height, int stride_pixels)
{
    if (!path || !pixels || width <= 0 || height <= 0 ||
        stride_pixels < width)
        return -1;

    FILE *file = fopen(path, "wb");
    if (!file)
        return -1;

    unsigned char header[54];
    memset(header, 0, sizeof header);
    header[0] = 'B';
    header[1] = 'M';
    put32(header + 2, 54u + (uint32_t)width * (uint32_t)height * 4u);
    put32(header + 10, 54u);
    put32(header + 14, 40u);
    put32(header + 18, (uint32_t)width);
    put32(header + 22, (uint32_t)(-height)); /* top-down */
    put16(header + 26, 1);
    put16(header + 28, 32);
    put32(header + 34, (uint32_t)width * (uint32_t)height * 4u);

    if (fwrite(header, 1, sizeof header, file) != sizeof header)
    {
        fclose(file);
        return -1;
    }

    for (int row = 0; row < height; row++)
    {
        const uint32_t *source = pixels + (size_t)row * (size_t)stride_pixels;
        if (fwrite(source, 4, (size_t)width, file) != (size_t)width)
        {
            fclose(file);
            return -1;
        }
    }

    fclose(file);
    return 0;
}

int dbg_bmp_write_bgra8888(const char *path, const uint32_t *pixels,
                           int width, int height, int stride_pixels)
{
    return write_bgra(path, pixels, width, height, stride_pixels);
}

int dbg_bmp_write_region_bgra8888(const char *path, const uint32_t *pixels,
                                  int source_width, int source_height,
                                  int x, int y, int width, int height)
{
    if (!pixels || x < 0 || y < 0 || width <= 0 || height <= 0 ||
        x + width > source_width || y + height > source_height)
        return -1;

    FILE *file = fopen(path, "wb");
    if (!file)
        return -1;

    unsigned char header[54];
    memset(header, 0, sizeof header);
    header[0] = 'B';
    header[1] = 'M';
    put32(header + 2, 54u + (uint32_t)width * (uint32_t)height * 4u);
    put32(header + 10, 54u);
    put32(header + 14, 40u);
    put32(header + 18, (uint32_t)width);
    put32(header + 22, (uint32_t)(-height));
    put16(header + 26, 1);
    put16(header + 28, 32);
    put32(header + 34, (uint32_t)width * (uint32_t)height * 4u);

    if (fwrite(header, 1, sizeof header, file) != sizeof header)
    {
        fclose(file);
        return -1;
    }

    for (int row = 0; row < height; row++)
    {
        const uint32_t *source = pixels +
            (size_t)(y + row) * (size_t)source_width + (size_t)x;
        if (fwrite(source, 4, (size_t)width, file) != (size_t)width)
        {
            fclose(file);
            return -1;
        }
    }

    fclose(file);
    return 0;
}
