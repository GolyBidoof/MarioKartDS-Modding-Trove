/*
 * Mario Kart DS Modding Trove
 * debug/recomp/examples/host_example.c — minimal host adapter template
 * SPDX-License-Identifier: MIT
 *
 * Copy this into your static recompilation, replace the fake CPU/memory with
 * your runtime, and pass the returned table to dbg_server_start().
 */
#include "dbg_host.h"
#include "bmp.h"

#include <stdio.h>
#include <string.h>

#define EXAMPLE_MAIN_BASE 0x02000000u
#define EXAMPLE_MAIN_SIZE 0x00100000u
#define EXAMPLE_SCREEN_WIDTH 256
#define EXAMPLE_SCREEN_HEIGHT 192

typedef struct ExampleHost
{
    DbgCpu cpu9;
    DbgCpu cpu7;
    uint8_t memory[EXAMPLE_MAIN_SIZE];
    uint32_t frames[EXAMPLE_SCREEN_WIDTH * EXAMPLE_SCREEN_HEIGHT * 2];
} ExampleHost;

static ExampleHost g_example;

static uint8_t *example_byte(ExampleHost *host, int cpu, uint32_t address)
{
    (void)cpu;
    if (address < EXAMPLE_MAIN_BASE ||
        address >= EXAMPLE_MAIN_BASE + EXAMPLE_MAIN_SIZE)
        return NULL;
    return &host->memory[address - EXAMPLE_MAIN_BASE];
}

static uint8_t example_read8(void *user, int cpu, uint32_t address)
{
    uint8_t *byte = example_byte(user, cpu, address);
    return byte ? *byte : 0;
}

static uint16_t example_read16(void *user, int cpu, uint32_t address)
{
    return (uint16_t)(example_read8(user, cpu, address) |
                      (uint16_t)(example_read8(user, cpu, address + 1) << 8));
}

static uint32_t example_read32(void *user, int cpu, uint32_t address)
{
    return (uint32_t)example_read8(user, cpu, address) |
           ((uint32_t)example_read8(user, cpu, address + 1) << 8) |
           ((uint32_t)example_read8(user, cpu, address + 2) << 16) |
           ((uint32_t)example_read8(user, cpu, address + 3) << 24);
}

static void example_write8(void *user, int cpu, uint32_t address,
                           uint8_t value)
{
    uint8_t *byte = example_byte(user, cpu, address);
    if (byte)
        *byte = value;
}

static void example_write16(void *user, int cpu, uint32_t address,
                            uint16_t value)
{
    example_write8(user, cpu, address, (uint8_t)value);
    example_write8(user, cpu, address + 1, (uint8_t)(value >> 8));
}

static void example_write32(void *user, int cpu, uint32_t address,
                            uint32_t value)
{
    example_write8(user, cpu, address, (uint8_t)value);
    example_write8(user, cpu, address + 1, (uint8_t)(value >> 8));
    example_write8(user, cpu, address + 2, (uint8_t)(value >> 16));
    example_write8(user, cpu, address + 3, (uint8_t)(value >> 24));
}

static int example_get_regs(void *user, int cpu, DbgCpu *out)
{
    ExampleHost *host = user;
    if (cpu == 7)
        *out = host->cpu7;
    else if (cpu == 9)
        *out = host->cpu9;
    else
        return 0;
    return 1;
}

static int example_set_regs(void *user, int cpu, const DbgCpu *state)
{
    ExampleHost *host = user;
    if (cpu == 7)
        host->cpu7 = *state;
    else if (cpu == 9)
        host->cpu9 = *state;
    else
        return 0;
    return 1;
}

static int example_single_step(void *user, int cpu, DbgCpu *out)
{
    (void)user;
    (void)cpu;
    (void)out;
    return 0; /* wire this to a one-instruction step if available */
}

static int example_call(void *user, int cpu, uint32_t address,
                        const uint32_t arguments[4], DbgCpu *out)
{
    (void)user;
    (void)cpu;
    (void)address;
    (void)arguments;
    (void)out;
    return 0; /* wire this to your translated-call helper */
}

static const struct
{
    uint32_t address;
    uint32_t size;
    const char *name;
} EXAMPLE_SYMBOLS[] = {
    {EXAMPLE_MAIN_BASE, 0x100, "example_entry"},
};

static int example_symbol_at(void *user, uint32_t address, char *name,
                             size_t name_size, uint32_t *offset)
{
    (void)user;
    for (size_t i = 0; i < sizeof EXAMPLE_SYMBOLS / sizeof EXAMPLE_SYMBOLS[0];
         i++)
    {
        uint32_t start = EXAMPLE_SYMBOLS[i].address;
        uint32_t size = EXAMPLE_SYMBOLS[i].size;
        if (address < start || address >= start + size)
            continue;
        snprintf(name, name_size, "%s", EXAMPLE_SYMBOLS[i].name);
        if (offset)
            *offset = address - start;
        return 1;
    }
    return 0;
}

static int example_symbol_address(void *user, const char *name,
                                  uint32_t *address)
{
    (void)user;
    for (size_t i = 0; i < sizeof EXAMPLE_SYMBOLS / sizeof EXAMPLE_SYMBOLS[0];
         i++)
    {
        if (!strcmp(name, EXAMPLE_SYMBOLS[i].name))
        {
            *address = EXAMPLE_SYMBOLS[i].address;
            return 1;
        }
    }
    return 0;
}

static int example_memory_base(void *user, int cpu, uint32_t *base)
{
    (void)user;
    (void)cpu;
    *base = EXAMPLE_MAIN_BASE;
    return 1;
}

static int example_memory_size(void *user, int cpu, uint32_t *size)
{
    (void)user;
    (void)cpu;
    *size = EXAMPLE_MAIN_SIZE;
    return 1;
}

static int example_screenshot(void *user, const char *path, int screen,
                              int capture, int *width, int *height)
{
    ExampleHost *host = user;

    if (capture == DBG_CAPTURE_FULL)
        return -1; /* replace with your full-window capture */

    if (screen == DBG_SCREEN_UPPER)
    {
        *width = EXAMPLE_SCREEN_WIDTH;
        *height = EXAMPLE_SCREEN_HEIGHT;
        return dbg_bmp_write_region_bgra8888(
            path, host->frames, EXAMPLE_SCREEN_WIDTH, EXAMPLE_SCREEN_HEIGHT * 2,
            0, 0, EXAMPLE_SCREEN_WIDTH, EXAMPLE_SCREEN_HEIGHT);
    }

    if (screen == DBG_SCREEN_LOWER)
    {
        *width = EXAMPLE_SCREEN_WIDTH;
        *height = EXAMPLE_SCREEN_HEIGHT;
        return dbg_bmp_write_region_bgra8888(
            path, host->frames, EXAMPLE_SCREEN_WIDTH, EXAMPLE_SCREEN_HEIGHT * 2,
            0, EXAMPLE_SCREEN_HEIGHT, EXAMPLE_SCREEN_WIDTH,
            EXAMPLE_SCREEN_HEIGHT);
    }

    *width = EXAMPLE_SCREEN_WIDTH;
    *height = EXAMPLE_SCREEN_HEIGHT * 2;
    return dbg_bmp_write_bgra8888(
        path, host->frames, EXAMPLE_SCREEN_WIDTH, EXAMPLE_SCREEN_HEIGHT * 2,
        EXAMPLE_SCREEN_WIDTH);
}

static int example_press(void *user, const char *spec, int frames)
{
    (void)user;
    (void)spec;
    (void)frames;
    return 1; /* replace with your input injection */
}

static int example_touch(void *user, int x, int y, int frames)
{
    (void)user;
    (void)x;
    (void)y;
    (void)frames;
    return 1;
}

static void example_release(void *user)
{
    (void)user;
}

static void example_status(void *user, DbgReply *reply)
{
    ExampleHost *host = user;
    reply->line(reply->user, "example cpu9 pc=");
    char line[64];
    snprintf(line, sizeof line, "%08X", host->cpu9.r[15]);
    reply->line(reply->user, line);
}

static int example_hello(void *user, int argc, char **argv, DbgReply *reply)
{
    (void)user;
    (void)argc;
    (void)argv;
    reply->line(reply->user, "hello from the host adapter");
    return DBG_KEEP_CONNECTION;
}

static const DbgCommand EXAMPLE_COMMANDS[] = {
    {"hello", "", 0, 0, example_hello},
};

DbgHost dbg_example_host(void)
{
    DbgHost host;
    memset(&host, 0, sizeof host);
    host.user = &g_example;
    host.name = "host-example";
    host.read8 = example_read8;
    host.read16 = example_read16;
    host.read32 = example_read32;
    host.write8 = example_write8;
    host.write16 = example_write16;
    host.write32 = example_write32;
    host.get_regs = example_get_regs;
    host.set_regs = example_set_regs;
    host.single_step = example_single_step;
    host.call = example_call;
    host.symbol_at = example_symbol_at;
    host.symbol_address = example_symbol_address;
    host.memory_base = example_memory_base;
    host.memory_size = example_memory_size;
    host.screenshot = example_screenshot;
    host.press = example_press;
    host.touch = example_touch;
    host.release = example_release;
    host.status = example_status;
    host.commands = EXAMPLE_COMMANDS;
    host.command_count = sizeof EXAMPLE_COMMANDS / sizeof EXAMPLE_COMMANDS[0];
    return host;
}
