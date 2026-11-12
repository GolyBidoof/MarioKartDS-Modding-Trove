/*
 * Mario Kart DS Modding Trove
 * debug/recomp/src/dbg_server.c — ROM-agnostic recomp debug server
 * SPDX-License-Identifier: MIT
 *
 * The server speaks a small line protocol over 127.0.0.1. It knows nothing
 * about the game or the ROM: CPU, memory, symbols, input and screenshots come
 * from the DbgHost adapter supplied by the static recompilation.
 */
#include "dbg_server.h"
#include "dbg_host.h"

#include <ctype.h>
#include <stdarg.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#ifdef _WIN32
#include <windows.h>
#include <winsock2.h>
#include <ws2tcpip.h>
typedef SOCKET dbg_socket;
#define DBG_INVALID_SOCKET INVALID_SOCKET
#define dbg_close_socket closesocket
#define strtok_r strtok_s
#define strcasecmp _stricmp
#define strncasecmp _strnicmp
static void dbg_sleep_ms(int ms) { Sleep((DWORD)ms); }
#else
#include <arpa/inet.h>
#include <netinet/in.h>
#include <pthread.h>
#include <strings.h>
#include <sys/select.h>
#include <sys/socket.h>
#include <sys/time.h>
#include <time.h>
#include <unistd.h>
typedef int dbg_socket;
#define DBG_INVALID_SOCKET (-1)
#define dbg_close_socket close
static void dbg_sleep_ms(int ms)
{
    struct timespec ts;
    ts.tv_sec = ms / 1000;
    ts.tv_nsec = (long)(ms % 1000) * 1000000L;
    nanosleep(&ts, NULL);
}
#endif

enum
{
    DBG_DEFAULT_PORT = 19850,
    DBG_GDB_DEFAULT_PORT = 19851,
    DBG_GDB_PACKET_MAX = 8192,
    DBG_COMMAND_LINE_MAX = 4096,
    DBG_REPLY_MAX = 4096,
    DBG_MAX_ARGUMENTS = 8,
    DBG_MAX_BREAKPOINTS = 32,
    DBG_MAX_READ_BYTES = 0x10000,
    DBG_MAX_DIFF_RANGES = 40,
    DBG_MAX_FIND_MATCHES = 64,
    DBG_PAUSE_POLL_MS = 5000,
    DBG_COMMAND_POLL_MS = 30000,
    DBG_SYMBOL_NAME_MAX = 64,
    DBG_SNAPSHOT_NAME_MAX = 64,
    DBG_READ_ROW_BYTES = 16,
    DBG_WORD_BYTES = 4,
};

enum
{
    DBG_ARG_ANY = -1,
};

typedef struct
{
    uint32_t address;
    uint32_t size;
    char name[DBG_SYMBOL_NAME_MAX];
} DbgRuntimeSymbol;

typedef int (*DbgCommandHandler)(dbg_socket socket, int argument_count, char **arguments);

typedef struct
{
    const char *name;
    const char *usage;
    int minimum_arguments;
    int maximum_arguments;
    DbgCommandHandler run;
} DbgServerCommand;

static DbgHost g_host;
static volatile int g_active;
static volatile int g_stop;
static volatile int g_paused;
static volatile int g_at_pause;
static volatile int g_step_frames;
static volatile int g_wait_frames;
static uint64_t g_frame;
static dbg_socket g_listen_socket = DBG_INVALID_SOCKET;

static volatile int g_stop_reason;
static volatile int g_stop_cpu;
static volatile int g_gdb_step;
static volatile int g_gdb_step_cpu;
static int g_gdb_no_ack;
static dbg_socket g_gdb_listen_socket[2] = {
    DBG_INVALID_SOCKET, DBG_INVALID_SOCKET};

static uint32_t g_breakpoints[DBG_MAX_BREAKPOINTS];
static int g_breakpoint_count;
static uint32_t g_breakpoint_hit;

static DbgRuntimeSymbol *g_runtime_symbols;
static size_t g_runtime_symbol_count;

static uint8_t *g_snapshot;
static size_t g_snapshot_size;
static uint32_t g_snapshot_base;
static char g_snapshot_name[DBG_SNAPSHOT_NAME_MAX];

static void dbg_send_all(dbg_socket socket, const char *text);
static void dbg_reply(dbg_socket socket, const char *format, ...);
static void dbg_end_reply(dbg_socket socket);
static void dbg_pause_and_wait(void);
static void dbg_wait_until_paused(uint64_t start_frame);
static int gdb_start_thread(int port, int cpu, int slot);

static int dbg_handle_help(dbg_socket socket, int count, char **arguments);
static int dbg_handle_status(dbg_socket socket, int count, char **arguments);
static int dbg_handle_pause(dbg_socket socket, int count, char **arguments);
static int dbg_handle_resume(dbg_socket socket, int count, char **arguments);
static int dbg_handle_step(dbg_socket socket, int count, char **arguments);
static int dbg_handle_wait(dbg_socket socket, int count, char **arguments);
static int dbg_handle_wait_pause(dbg_socket socket, int count, char **arguments);
static int dbg_handle_read(dbg_socket socket, int count, char **arguments);
static int dbg_handle_read32(dbg_socket socket, int count, char **arguments);
static int dbg_handle_write(dbg_socket socket, int count, char **arguments);
static int dbg_handle_registers(dbg_socket socket, int count, char **arguments);
static int dbg_handle_symbol(dbg_socket socket, int count, char **arguments);
static int dbg_handle_breakpoint_add(dbg_socket socket, int count, char **arguments);
static int dbg_handle_breakpoint_list(dbg_socket socket, int count, char **arguments);
static int dbg_handle_breakpoint_clear(dbg_socket socket, int count, char **arguments);
static int dbg_handle_press(dbg_socket socket, int count, char **arguments);
static int dbg_handle_touch(dbg_socket socket, int count, char **arguments);
static int dbg_handle_release(dbg_socket socket, int count, char **arguments);
static int dbg_handle_screenshot(dbg_socket socket, int count, char **arguments);
static int dbg_handle_call(dbg_socket socket, int count, char **arguments);
static int dbg_handle_snapshot(dbg_socket socket, int count, char **arguments);
static int dbg_handle_diff(dbg_socket socket, int count, char **arguments);
static int dbg_handle_find(dbg_socket socket, int count, char **arguments);
static int dbg_handle_quit(dbg_socket socket, int count, char **arguments);

static const DbgServerCommand DBG_COMMANDS[] = {
    {"help", "", 0, 0, dbg_handle_help},
    {"status", "", 0, 0, dbg_handle_status},
    {"pause", "", 0, 0, dbg_handle_pause},
    {"resume", "", 0, 0, dbg_handle_resume},
    {"step", "[frames]", 0, 1, dbg_handle_step},
    {"wait", "frames", 1, 1, dbg_handle_wait},
    {"waitpause", "", 0, 0, dbg_handle_wait_pause},
    {"read", "address length [9|7]", 2, 3, dbg_handle_read},
    {"read32", "address [count] [9|7]", 1, 3, dbg_handle_read32},
    {"write", "address hex-bytes [9|7]", 2, 3, dbg_handle_write},
    {"regs", "[9|7]", 0, 1, dbg_handle_registers},
    {"sym", "name|address", 1, 1, dbg_handle_symbol},
    {"bp", "name|address", 1, 1, dbg_handle_breakpoint_add},
    {"bplist", "", 0, 0, dbg_handle_breakpoint_list},
    {"bpclear", "", 0, 0, dbg_handle_breakpoint_clear},
    {"press", "spec [frames]", 1, 2, dbg_handle_press},
    {"touch", "x y [frames]", 2, 3, dbg_handle_touch},
    {"release", "", 0, 0, dbg_handle_release},
    {"screenshot", "[both|upper|lower] [full|native] [path.bmp]", 0, 3, dbg_handle_screenshot},
    {"call", "address [r0] [r1] [r2] [r3]", 1, 5, dbg_handle_call},
    {"snapshot", "name", 1, 1, dbg_handle_snapshot},
    {"diff", "name", 1, 1, dbg_handle_diff},
    {"find", "value [start] [length]", 1, 3, dbg_handle_find},
    {"quit", "", 0, 0, dbg_handle_quit},
    {"detach", "", 0, 0, dbg_handle_quit},
};

static const size_t DBG_COMMAND_COUNT = sizeof DBG_COMMANDS / sizeof DBG_COMMANDS[0];

static void dbg_send_all(dbg_socket socket, const char *text)
{
    size_t remaining = strlen(text);
    while (remaining)
    {
        int written = send(socket, text, (int)remaining, 0);
        if (written <= 0)
            return;
        text += written;
        remaining -= (size_t)written;
    }
}

static void dbg_reply(dbg_socket socket, const char *format, ...)
{
    char buffer[DBG_REPLY_MAX];
    va_list arguments;
    va_start(arguments, format);
    vsnprintf(buffer, sizeof buffer, format, arguments);
    va_end(arguments);
    dbg_send_all(socket, buffer);
}

static void dbg_reply_line(void *user, const char *text)
{
    dbg_socket socket = (dbg_socket)(intptr_t)user;
    dbg_send_all(socket, text);
    dbg_send_all(socket, "\n");
}

static void dbg_end_reply(dbg_socket socket)
{
    dbg_send_all(socket, "END\n");
}

static uint32_t dbg_parse_uint(const char *value)
{
    return (uint32_t)strtoul(value, NULL, 0);
}

static int dbg_parse_cpu(const char *value)
{
    return value && atoi(value) == 7 ? 7 : 9;
}

static uint8_t dbg_read8(int cpu, uint32_t address)
{
    return g_host.read8 ? g_host.read8(g_host.user, cpu, address) : 0;
}

static uint32_t dbg_read32(int cpu, uint32_t address)
{
    if (g_host.read32)
        return g_host.read32(g_host.user, cpu, address);
    return (uint32_t)dbg_read8(cpu, address) |
           ((uint32_t)dbg_read8(cpu, address + 1) << 8) |
           ((uint32_t)dbg_read8(cpu, address + 2) << 16) |
           ((uint32_t)dbg_read8(cpu, address + 3) << 24);
}

static void dbg_write8(int cpu, uint32_t address, uint8_t value)
{
    if (g_host.write8)
        g_host.write8(g_host.user, cpu, address, value);
}

static const DbgRuntimeSymbol *dbg_find_runtime_symbol(uint32_t address)
{
    const DbgRuntimeSymbol *best = NULL;
    for (size_t i = 0; i < g_runtime_symbol_count; i++)
    {
        const DbgRuntimeSymbol *symbol = &g_runtime_symbols[i];
        uint32_t size = symbol->size ? symbol->size : 1;
        if (address < symbol->address || address >= symbol->address + size)
            continue;
        if (!best || symbol->address > best->address)
            best = symbol;
    }
    return best;
}

static int dbg_symbol_at(uint32_t address, char *name, size_t name_size,
                         uint32_t *offset)
{
    uint32_t found_offset = 0;
    if (g_host.symbol_at &&
        g_host.symbol_at(g_host.user, address, name, name_size, &found_offset))
    {
        if (offset)
            *offset = found_offset;
        return 1;
    }

    const DbgRuntimeSymbol *symbol = dbg_find_runtime_symbol(address);
    if (!symbol)
        return 0;
    snprintf(name, name_size, "%s", symbol->name);
    if (offset)
        *offset = address - symbol->address;
    return 1;
}

static uint32_t dbg_symbol_address(const char *name)
{
    uint32_t address = 0;
    if (g_host.symbol_address &&
        g_host.symbol_address(g_host.user, name, &address))
        return address;
    for (size_t i = 0; i < g_runtime_symbol_count; i++)
        if (!strcmp(g_runtime_symbols[i].name, name))
            return g_runtime_symbols[i].address;
    return 0;
}

static uint32_t dbg_parse_address_or_symbol(const char *value)
{
    char *end = NULL;
    uint32_t address = (uint32_t)strtoul(value, &end, 16);
    if (end && *end)
        address = dbg_symbol_address(value);
    return address;
}

static void dbg_load_symbols(void)
{
    const char *path = getenv("DBG_SYMBOLS");
    if (!path || !*path)
        path = getenv("MKDS_DBG_SYMBOLS");
    if (!path || !*path)
        path = "dbg_symbols.txt";

    FILE *file = fopen(path, "r");
    if (!file)
        return;

    char line[512];
    while (fgets(line, sizeof line, file))
    {
        if (line[0] == '#' || line[0] == '\n' || line[0] == '\r')
            continue;
        unsigned address;
        unsigned size;
        char name[DBG_SYMBOL_NAME_MAX];
        if (sscanf(line, "%x %x %63s", &address, &size, name) != 3)
            continue;
        DbgRuntimeSymbol *grown = realloc(
            g_runtime_symbols,
            (g_runtime_symbol_count + 1) * sizeof *grown);
        if (!grown)
            break;
        g_runtime_symbols = grown;
        g_runtime_symbols[g_runtime_symbol_count].address = address;
        g_runtime_symbols[g_runtime_symbol_count].size = size;
        snprintf(g_runtime_symbols[g_runtime_symbol_count].name,
                 sizeof g_runtime_symbols[g_runtime_symbol_count].name,
                 "%s", name);
        g_runtime_symbol_count++;
    }
    fclose(file);
    fprintf(stderr, "[dbg] %zu symbols from %s\n", g_runtime_symbol_count, path);
}

static void dbg_pause_and_wait(void)
{
    g_paused = 1;
    for (int i = 0; i < DBG_PAUSE_POLL_MS && !g_at_pause && !g_stop; i++)
        dbg_sleep_ms(1);
}

static void dbg_wait_until_paused(uint64_t start_frame)
{
    for (int i = 0; i < DBG_COMMAND_POLL_MS && !g_stop; i++)
    {
        if (g_frame > start_frame && g_at_pause)
            break;
        dbg_sleep_ms(1);
    }
}

static int dbg_memory_range(int cpu, uint32_t *base, uint32_t *size)
{
    if (!g_host.memory_base || !g_host.memory_size)
        return 0;
    if (!g_host.memory_base(g_host.user, cpu, base) ||
        !g_host.memory_size(g_host.user, cpu, size))
        return 0;
    return *size != 0;
}

static void dbg_dump_memory(dbg_socket socket, uint32_t address,
                            uint32_t length, int cpu)
{
    if (length > DBG_MAX_READ_BYTES)
        length = DBG_MAX_READ_BYTES;

    for (uint32_t offset = 0; offset < length; offset += DBG_READ_ROW_BYTES)
    {
        char line[128];
        int written = snprintf(line, sizeof line, "%08X ",
                               address + offset);
        for (uint32_t byte = 0;
             byte < DBG_READ_ROW_BYTES && offset + byte < length;
             byte++)
        {
            uint32_t current = address + offset + byte;
            uint8_t value = dbg_read8(cpu, current);
            written += snprintf(line + written,
                                sizeof line - (size_t)written,
                                "%02X", value);
        }
        snprintf(line + written, sizeof line - (size_t)written, "\n");
        dbg_send_all(socket, line);
    }
}

static int dbg_snapshot_path(const char *name, char *path, size_t size)
{
    const char *directory = getenv("DBG_SNAPSHOT_DIR");
    if (!directory || !*directory)
        directory = ".";

    for (const char *cursor = name; *cursor; cursor++)
        if (!isalnum((unsigned char)*cursor) &&
            *cursor != '_' && *cursor != '-')
            return 0;

    snprintf(path, size, "%s/dbg_%s.bin", directory, name);
    return 1;
}

static void dbg_store_snapshot(const char *name)
{
    uint32_t base;
    uint32_t size;
    if (!dbg_memory_range(9, &base, &size))
        return;

    free(g_snapshot);
    g_snapshot = malloc(size);
    if (!g_snapshot)
        return;

    for (uint32_t i = 0; i < size; i++)
        g_snapshot[i] = dbg_read8(9, base + i);

    g_snapshot_size = size;
    g_snapshot_base = base;
    snprintf(g_snapshot_name, sizeof g_snapshot_name, "%s", name);

    char path[512];
    if (!dbg_snapshot_path(name, path, sizeof path))
        return;
    FILE *file = fopen(path, "wb");
    if (!file)
        return;
    fwrite(g_snapshot, 1, g_snapshot_size, file);
    fclose(file);
}

static int dbg_load_snapshot(const char *name, uint8_t **out, size_t *length)
{
    if (g_snapshot && !strcmp(name, g_snapshot_name))
    {
        *out = g_snapshot;
        *length = g_snapshot_size;
        return 1;
    }

    char path[512];
    if (!dbg_snapshot_path(name, path, sizeof path))
        return 0;

    FILE *file = fopen(path, "rb");
    if (!file)
        return 0;

    fseek(file, 0, SEEK_END);
    long size = ftell(file);
    fseek(file, 0, SEEK_SET);
    if (size <= 0)
    {
        fclose(file);
        return 0;
    }

    uint8_t *data = malloc((size_t)size);
    if (!data || fread(data, 1, (size_t)size, file) != (size_t)size)
    {
        free(data);
        fclose(file);
        return 0;
    }

    fclose(file);
    *out = data;
    *length = (size_t)size;
    return 2;
}

static int dbg_handle_help(dbg_socket socket, int count, char **arguments)
{
    (void)count;
    (void)arguments;
    for (size_t i = 0; i < DBG_COMMAND_COUNT; i++)
    {
        if (DBG_COMMANDS[i].usage[0])
            dbg_reply(socket, "%s %s\n", DBG_COMMANDS[i].name,
                      DBG_COMMANDS[i].usage);
        else
            dbg_reply(socket, "%s\n", DBG_COMMANDS[i].name);
    }
    for (size_t i = 0; i < g_host.command_count; i++)
    {
        const DbgCommand *command = &g_host.commands[i];
        if (command->usage && command->usage[0])
            dbg_reply(socket, "%s %s\n", command->name, command->usage);
        else
            dbg_reply(socket, "%s\n", command->name);
    }
    dbg_end_reply(socket);
    return DBG_KEEP_CONNECTION;
}

static int dbg_handle_status(dbg_socket socket, int count, char **arguments)
{
    (void)count;
    (void)arguments;
    dbg_reply(socket, "host %s\n", g_host.name ? g_host.name : "?");
    dbg_reply(socket, "frame %llu paused %d at %s\n",
              (unsigned long long)g_frame, g_paused,
              g_at_pause ? "boundary" : "running");
    if (g_breakpoint_hit)
        dbg_reply(socket, "breakpoint %08X\n", g_breakpoint_hit);
    if (g_host.status)
    {
        DbgReply reply = {(void *)(intptr_t)socket, dbg_reply_line};
        g_host.status(g_host.user, &reply);
    }
    dbg_end_reply(socket);
    return DBG_KEEP_CONNECTION;
}

static int dbg_handle_pause(dbg_socket socket, int count, char **arguments)
{
    (void)count;
    (void)arguments;
    dbg_pause_and_wait();
    dbg_reply(socket, "paused at frame %llu\n", (unsigned long long)g_frame);
    dbg_end_reply(socket);
    return DBG_KEEP_CONNECTION;
}

static int dbg_handle_resume(dbg_socket socket, int count, char **arguments)
{
    (void)count;
    (void)arguments;
    g_paused = 0;
    dbg_reply(socket, "resumed\n");
    dbg_end_reply(socket);
    return DBG_KEEP_CONNECTION;
}

static int dbg_handle_step(dbg_socket socket, int count, char **arguments)
{
    int frames = count ? atoi(arguments[0]) : 1;
    g_step_frames = frames > 0 ? frames : 1;
    uint64_t start_frame = g_frame;
    g_paused = 0;
    dbg_wait_until_paused(start_frame);
    dbg_reply(socket, "paused at frame %llu\n", (unsigned long long)g_frame);
    dbg_end_reply(socket);
    return DBG_KEEP_CONNECTION;
}

static int dbg_handle_wait(dbg_socket socket, int count, char **arguments)
{
    int frames = count ? atoi(arguments[0]) : 1;
    g_wait_frames = frames > 0 ? frames : 1;
    uint64_t start_frame = g_frame;
    g_paused = 0;
    dbg_wait_until_paused(start_frame);
    dbg_reply(socket, "paused at frame %llu\n", (unsigned long long)g_frame);
    dbg_end_reply(socket);
    return DBG_KEEP_CONNECTION;
}

static int dbg_handle_wait_pause(dbg_socket socket, int count, char **arguments)
{
    (void)count;
    (void)arguments;
    for (int i = 0; i < DBG_PAUSE_POLL_MS && !g_at_pause && !g_stop; i++)
        dbg_sleep_ms(1);
    dbg_reply(socket, "frame %llu paused %d\n",
              (unsigned long long)g_frame, g_paused);
    dbg_end_reply(socket);
    return DBG_KEEP_CONNECTION;
}

static int dbg_handle_read(dbg_socket socket, int count, char **arguments)
{
    int cpu = count > 2 ? dbg_parse_cpu(arguments[2]) : 9;
    dbg_pause_and_wait();
    dbg_dump_memory(socket, dbg_parse_uint(arguments[0]),
                    dbg_parse_uint(arguments[1]), cpu);
    dbg_end_reply(socket);
    return DBG_KEEP_CONNECTION;
}

static int dbg_handle_read32(dbg_socket socket, int count, char **arguments)
{
    uint32_t address = dbg_parse_uint(arguments[0]);
    int words = count > 1 ? atoi(arguments[1]) : 1;
    int cpu = count > 2 ? dbg_parse_cpu(arguments[2]) : 9;
    dbg_pause_and_wait();
    for (int i = 0; i < words; i++)
        dbg_reply(socket, "%08X %08X\n",
                  address + (uint32_t)i * DBG_WORD_BYTES,
                  dbg_read32(cpu, address + (uint32_t)i * DBG_WORD_BYTES));
    dbg_end_reply(socket);
    return DBG_KEEP_CONNECTION;
}

static int dbg_handle_write(dbg_socket socket, int count, char **arguments)
{
    uint32_t address = dbg_parse_uint(arguments[0]);
    const char *hex = arguments[1];
    int cpu = count > 2 ? dbg_parse_cpu(arguments[2]) : 9;
    uint32_t written = 0;
    dbg_pause_and_wait();

    while (hex[0] && hex[1])
    {
        char byte_text[3] = {hex[0], hex[1], 0};
        dbg_write8(cpu, address + written,
                   (uint8_t)strtoul(byte_text, NULL, 16));
        written++;
        hex += 2;
    }

    dbg_reply(socket, "wrote %u bytes at %08X\n", written, address);
    dbg_end_reply(socket);
    return DBG_KEEP_CONNECTION;
}

static int dbg_handle_registers(dbg_socket socket, int count, char **arguments)
{
    int cpu = count > 0 ? dbg_parse_cpu(arguments[0]) : 9;
    dbg_pause_and_wait();
    DbgCpu state;
    if (!g_host.get_regs || !g_host.get_regs(g_host.user, cpu, &state))
    {
        dbg_reply(socket, "cpu %d not available\n", cpu);
        dbg_end_reply(socket);
        return DBG_KEEP_CONNECTION;
    }
    dbg_reply(socket, "cpu %d r0 %08X r1 %08X r2 %08X r3 %08X\n",
              cpu, state.r[0], state.r[1], state.r[2], state.r[3]);
    dbg_reply(socket, "r4 %08X r5 %08X r6 %08X r7 %08X\n",
              state.r[4], state.r[5], state.r[6], state.r[7]);
    dbg_reply(socket, "r8 %08X r9 %08X r10 %08X r11 %08X\n",
              state.r[8], state.r[9], state.r[10], state.r[11]);
    dbg_reply(socket, "r12 %08X sp %08X lr %08X pc %08X\n",
              state.r[12], state.r[13], state.r[14], state.r[15]);
    char name[DBG_SYMBOL_NAME_MAX];
    uint32_t offset = 0;
    if (dbg_symbol_at(state.func & ~1u, name, sizeof name, &offset))
        dbg_reply(socket, "cpsr %08X func %08X %s+0x%X\n",
                  state.cpsr, state.func & ~1u, name, offset);
    else
        dbg_reply(socket, "cpsr %08X func %08X ?\n",
                  state.cpsr, state.func & ~1u);
    dbg_end_reply(socket);
    return DBG_KEEP_CONNECTION;
}

static int dbg_handle_symbol(dbg_socket socket, int count, char **arguments)
{
    (void)count;
    const char *value = arguments[0];
    char *end = NULL;
    uint32_t address = (uint32_t)strtoul(value, &end, 16);
    bool looks_like_address = end && *end == 0 &&
                              (isdigit((unsigned char)value[0]) ||
                               value[0] == '0');

    if (looks_like_address)
    {
        char name[DBG_SYMBOL_NAME_MAX];
        uint32_t offset = 0;
        if (dbg_symbol_at(address, name, sizeof name, &offset))
            dbg_reply(socket, "%08X %s+0x%X\n", address, name, offset);
        else
            dbg_reply(socket, "%08X ?\n", address);
    }
    else
    {
        uint32_t resolved = dbg_symbol_address(value);
        if (resolved)
            dbg_reply(socket, "%s %08X\n", value, resolved);
        else
            dbg_reply(socket, "%s not found\n", value);
    }

    dbg_end_reply(socket);
    return DBG_KEEP_CONNECTION;
}

static int dbg_handle_breakpoint_add(dbg_socket socket, int count,
                                     char **arguments)
{
    (void)count;
    if (g_breakpoint_count >= DBG_MAX_BREAKPOINTS)
    {
        dbg_reply(socket, "cannot add breakpoint\n");
        dbg_end_reply(socket);
        return DBG_KEEP_CONNECTION;
    }

    uint32_t address = dbg_parse_address_or_symbol(arguments[0]);
    if (!address)
    {
        dbg_reply(socket, "not found\n");
        dbg_end_reply(socket);
        return DBG_KEEP_CONNECTION;
    }

    g_breakpoints[g_breakpoint_count] = address & ~1u;
    g_breakpoint_count++;
    dbg_reply(socket, "breakpoint %d at %08X\n",
              g_breakpoint_count - 1, address & ~1u);
    dbg_end_reply(socket);
    return DBG_KEEP_CONNECTION;
}

static int dbg_handle_breakpoint_list(dbg_socket socket, int count,
                                      char **arguments)
{
    (void)count;
    (void)arguments;
    for (int i = 0; i < g_breakpoint_count; i++)
    {
        char name[DBG_SYMBOL_NAME_MAX];
        uint32_t offset = 0;
        if (dbg_symbol_at(g_breakpoints[i], name, sizeof name, &offset))
            dbg_reply(socket, "%d %08X %s+0x%X\n",
                      i, g_breakpoints[i], name, offset);
        else
            dbg_reply(socket, "%d %08X ?\n", i, g_breakpoints[i]);
    }
    dbg_end_reply(socket);
    return DBG_KEEP_CONNECTION;
}

static int dbg_handle_breakpoint_clear(dbg_socket socket, int count,
                                       char **arguments)
{
    (void)count;
    (void)arguments;
    g_breakpoint_count = 0;
    g_breakpoint_hit = 0;
    dbg_reply(socket, "cleared\n");
    dbg_end_reply(socket);
    return DBG_KEEP_CONNECTION;
}

static int dbg_handle_press(dbg_socket socket, int count, char **arguments)
{
    int frames = count > 1 ? atoi(arguments[1]) : 2;
    if (!g_host.press)
    {
        dbg_reply(socket, "press not supported\n");
    }
    else if (g_host.press(g_host.user, arguments[0], frames) != 0)
    {
        dbg_reply(socket, "press %s for %d frames\n", arguments[0],
                  frames > 0 ? frames : 2);
    }
    else
    {
        dbg_reply(socket, "press failed\n");
    }
    dbg_end_reply(socket);
    return DBG_KEEP_CONNECTION;
}

static int dbg_handle_touch(dbg_socket socket, int count, char **arguments)
{
    int frames = count > 2 ? atoi(arguments[2]) : 2;
    if (!g_host.touch)
    {
        dbg_reply(socket, "touch not supported\n");
    }
    else if (g_host.touch(g_host.user, atoi(arguments[0]), atoi(arguments[1]),
                          frames) != 0)
    {
        dbg_reply(socket, "touch %s,%s for %d frames\n", arguments[0],
                  arguments[1], frames > 0 ? frames : 2);
    }
    else
    {
        dbg_reply(socket, "touch failed\n");
    }
    dbg_end_reply(socket);
    return DBG_KEEP_CONNECTION;
}

static int dbg_handle_release(dbg_socket socket, int count, char **arguments)
{
    (void)count;
    (void)arguments;
    if (g_host.release)
        g_host.release(g_host.user);
    dbg_reply(socket, "released\n");
    dbg_end_reply(socket);
    return DBG_KEEP_CONNECTION;
}

static const char *dbg_screen_name(int screen)
{
    switch (screen)
    {
    case DBG_SCREEN_UPPER: return "upper";
    case DBG_SCREEN_LOWER: return "lower";
    default: return "both";
    }
}

static const char *dbg_capture_name(int capture)
{
    return capture == DBG_CAPTURE_NATIVE ? "native" : "full";
}

static int dbg_handle_screenshot(dbg_socket socket, int count, char **arguments)
{
    int screen = DBG_SCREEN_BOTH;
    int capture = -1;
    const char *path = NULL;

    for (int i = 0; i < count; i++)
    {
        if (!strcasecmp(arguments[i], "both"))
            screen = DBG_SCREEN_BOTH;
        else if (!strcasecmp(arguments[i], "upper"))
            screen = DBG_SCREEN_UPPER;
        else if (!strcasecmp(arguments[i], "lower"))
            screen = DBG_SCREEN_LOWER;
        else if (!strcasecmp(arguments[i], "full"))
            capture = DBG_CAPTURE_FULL;
        else if (!strcasecmp(arguments[i], "native"))
            capture = DBG_CAPTURE_NATIVE;
        else
            path = arguments[i];
    }

    if (capture < 0)
        capture = DBG_CAPTURE_NATIVE;

    char default_path[512];
    if (!path)
    {
        snprintf(default_path, sizeof default_path,
                 "dbg_screenshot_%llu_%s_%s.bmp",
                 (unsigned long long)g_frame, dbg_screen_name(screen),
                 dbg_capture_name(capture));
        path = default_path;
    }

    if (!g_host.screenshot)
    {
        dbg_reply(socket, "screenshot not supported\n");
    }
    else
    {
        int width = 0;
        int height = 0;
        if (g_host.screenshot(g_host.user, path, screen, capture,
                              &width, &height) == 0)
            dbg_reply(socket, "screenshot %s %dx%d\n", path, width, height);
        else
            dbg_reply(socket, "screenshot failed\n");
    }
    dbg_end_reply(socket);
    return DBG_KEEP_CONNECTION;
}

static int dbg_handle_call(dbg_socket socket, int count, char **arguments)
{
    uint32_t address = dbg_parse_uint(arguments[0]);
    uint32_t registers[4] = {0, 0, 0, 0};
    for (int i = 1; i < count && i <= 4; i++)
        registers[i - 1] = dbg_parse_uint(arguments[i]);

    if (!g_host.call)
    {
        dbg_reply(socket, "call not supported\n");
        dbg_end_reply(socket);
        return DBG_KEEP_CONNECTION;
    }

    dbg_pause_and_wait();
    DbgCpu out;
    memset(&out, 0, sizeof out);
    int ok = g_host.call(g_host.user, 9, address, registers, &out);
    dbg_reply(socket, "call %08X %s r0=%08X r1=%08X\n",
              address, ok ? "ok" : "not translated", out.r[0], out.r[1]);
    dbg_end_reply(socket);
    return DBG_KEEP_CONNECTION;
}

static int dbg_handle_snapshot(dbg_socket socket, int count, char **arguments)
{
    (void)count;
    dbg_pause_and_wait();
    dbg_store_snapshot(arguments[0]);
    if (!g_snapshot)
    {
        dbg_reply(socket, "snapshot failed (host has no memory range)\n");
        dbg_end_reply(socket);
        return DBG_KEEP_CONNECTION;
    }

    dbg_reply(socket, "snapshot %s (%zu bytes) base %08X frame %llu\n",
              arguments[0], g_snapshot_size, g_snapshot_base,
              (unsigned long long)g_frame);
    dbg_end_reply(socket);
    return DBG_KEEP_CONNECTION;
}

static int dbg_handle_diff(dbg_socket socket, int count, char **arguments)
{
    (void)count;
    dbg_pause_and_wait();

    uint32_t base;
    uint32_t size;
    if (!dbg_memory_range(9, &base, &size))
    {
        dbg_reply(socket, "host has no memory range\n");
        dbg_end_reply(socket);
        return DBG_KEEP_CONNECTION;
    }

    uint8_t *old = NULL;
    size_t length = 0;
    int ownership = dbg_load_snapshot(arguments[0], &old, &length);
    if (!ownership)
    {
        dbg_reply(socket, "no snapshot %s\n", arguments[0]);
        dbg_end_reply(socket);
        return DBG_KEEP_CONNECTION;
    }
    if (length != size)
    {
        dbg_reply(socket, "snapshot size %zu != memory size %u\n",
                  length, size);
        if (ownership == 2)
            free(old);
        dbg_end_reply(socket);
        return DBG_KEEP_CONNECTION;
    }

    uint32_t ranges = 0;
    uint32_t total_bytes = 0;
    for (uint32_t i = 0; i < size;)
    {
        if (old[i] == dbg_read8(9, base + i))
        {
            i++;
            continue;
        }

        uint32_t start = i;
        while (i < size && old[i] != dbg_read8(9, base + i))
            i++;
        uint32_t range_length = i - start;
        char name[DBG_SYMBOL_NAME_MAX];
        uint32_t offset = 0;
        if (dbg_symbol_at(base + start, name, sizeof name, &offset))
            dbg_reply(socket, "%08X %5u %s+0x%X\n",
                      base + start, range_length, name, offset);
        else
            dbg_reply(socket, "%08X %5u ?\n", base + start, range_length);

        total_bytes += range_length;
        if (++ranges >= DBG_MAX_DIFF_RANGES)
            break;
    }

    if (!ranges)
        dbg_reply(socket, "no changes\n");
    else
        dbg_reply(socket, "%u ranges, %u bytes changed\n", ranges, total_bytes);
    if (ownership == 2)
        free(old);
    dbg_end_reply(socket);
    return DBG_KEEP_CONNECTION;
}

static int dbg_handle_find(dbg_socket socket, int count, char **arguments)
{
    uint32_t value = dbg_parse_uint(arguments[0]);
    uint32_t start = count > 1 ? dbg_parse_uint(arguments[1]) : 0;
    uint32_t length = count > 2 ? dbg_parse_uint(arguments[2]) : 0;

    uint32_t base;
    uint32_t size;
    if (!dbg_memory_range(9, &base, &size))
    {
        dbg_reply(socket, "host has no memory range\n");
        dbg_end_reply(socket);
        return DBG_KEEP_CONNECTION;
    }

    if (!length)
        length = size;
    uint32_t end = start + length;
    if (end > size)
        end = size;

    dbg_pause_and_wait();
    int matches = 0;
    for (uint32_t offset = start;
         offset + DBG_WORD_BYTES <= end;
         offset += DBG_WORD_BYTES)
    {
        if (dbg_read32(9, base + offset) != value)
            continue;
        dbg_reply(socket, "%08X\n", base + offset);
        if (++matches >= DBG_MAX_FIND_MATCHES)
            break;
    }

    dbg_reply(socket, "%d matches\n", matches);
    dbg_end_reply(socket);
    return DBG_KEEP_CONNECTION;
}

static int dbg_handle_quit(dbg_socket socket, int count, char **arguments)
{
    (void)count;
    (void)arguments;
    dbg_reply(socket, "bye\n");
    dbg_end_reply(socket);
    return DBG_CLOSE_CONNECTION;
}

static const DbgServerCommand *dbg_find_command(const char *name)
{
    for (size_t i = 0; i < DBG_COMMAND_COUNT; i++)
        if (!strcmp(name, DBG_COMMANDS[i].name))
            return &DBG_COMMANDS[i];
    return NULL;
}

static const DbgCommand *dbg_find_host_command(const char *name)
{
    for (size_t i = 0; i < g_host.command_count; i++)
        if (!strcmp(name, g_host.commands[i].name))
            return &g_host.commands[i];
    return NULL;
}

static int dbg_handle_line(dbg_socket socket, char *line)
{
    char *arguments[DBG_MAX_ARGUMENTS];
    int argument_count = 0;
    char *save = NULL;

    for (char *token = strtok_r(line, " \t\r\n", &save);
         token && argument_count < DBG_MAX_ARGUMENTS;
         token = strtok_r(NULL, " \t\r\n", &save))
    {
        arguments[argument_count++] = token;
    }

    if (!argument_count)
    {
        dbg_end_reply(socket);
        return DBG_KEEP_CONNECTION;
    }

    const DbgServerCommand *command = dbg_find_command(arguments[0]);
    if (command)
    {
        int supplied = argument_count - 1;
        if (supplied < command->minimum_arguments ||
            (command->maximum_arguments != DBG_ARG_ANY &&
             supplied > command->maximum_arguments))
        {
            dbg_reply(socket, "usage: %s %s\n", command->name,
                      command->usage);
            dbg_end_reply(socket);
            return DBG_KEEP_CONNECTION;
        }
        return command->run(socket, supplied, arguments + 1);
    }

    const DbgCommand *host_command = dbg_find_host_command(arguments[0]);
    if (host_command)
    {
        int supplied = argument_count - 1;
        if (supplied < host_command->minimum_arguments ||
            (host_command->maximum_arguments != DBG_ARG_ANY &&
             supplied > host_command->maximum_arguments))
        {
            dbg_reply(socket, "usage: %s %s\n", host_command->name,
                      host_command->usage ? host_command->usage : "");
            dbg_end_reply(socket);
            return DBG_KEEP_CONNECTION;
        }
        DbgReply reply = {(void *)(intptr_t)socket, dbg_reply_line};
        int keep = host_command->run(g_host.user, supplied, arguments + 1,
                                     &reply);
        dbg_end_reply(socket);
        return keep;
    }

    dbg_reply(socket, "unknown command %s\n", arguments[0]);
    dbg_end_reply(socket);
    return DBG_KEEP_CONNECTION;
}

#ifdef _WIN32
static DWORD WINAPI dbg_server_thread(LPVOID argument)
#else
static void *dbg_server_thread(void *argument)
#endif
{
    int port = (int)(intptr_t)argument;
#ifdef _WIN32
    WSADATA wsa;
    WSAStartup(MAKEWORD(2, 2), &wsa);
#endif

    dbg_socket server = socket(AF_INET, SOCK_STREAM, 0);
    if (server == DBG_INVALID_SOCKET)
        goto done;

    int reuse = 1;
    setsockopt(server, SOL_SOCKET, SO_REUSEADDR,
               (const char *)&reuse, sizeof reuse);

    struct sockaddr_in address;
    memset(&address, 0, sizeof address);
    address.sin_family = AF_INET;
    address.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
    address.sin_port = htons((uint16_t)port);

    if (bind(server, (struct sockaddr *)&address, sizeof address) < 0)
    {
        fprintf(stderr, "[dbg] cannot bind 127.0.0.1:%d\n", port);
        dbg_close_socket(server);
        goto done;
    }

    listen(server, 1);
    g_listen_socket = server;
    fprintf(stderr, "[dbg] listening on 127.0.0.1:%d\n", port);

    char line[DBG_COMMAND_LINE_MAX];
    while (!g_stop)
    {
        dbg_socket client = accept(server, NULL, NULL);
        if (client == DBG_INVALID_SOCKET)
            break;

        size_t used = 0;
        int close_client = 0;
        while (!close_client && !g_stop)
        {
            int received = recv(client, line + used,
                                (int)(sizeof line - used - 1), 0);
            if (received <= 0)
                break;

            used += (size_t)received;
            line[used] = 0;

            char *newline;
            while ((newline = strchr(line, '\n')) != NULL)
            {
                *newline = 0;
                if (newline > line && !dbg_handle_line(client, line))
                {
                    close_client = 1;
                    break;
                }
                memmove(line, newline + 1, strlen(newline + 1) + 1);
                used = strlen(line);
            }

            if (used >= sizeof line - 1)
                used = 0;
        }

        dbg_close_socket(client);
    }

    dbg_close_socket(server);
    g_listen_socket = DBG_INVALID_SOCKET;

done:
#ifdef _WIN32
    WSACleanup();
    return 0;
#else
    return NULL;
#endif
}

int dbg_server_start(const DbgHost *host)
{
    if (!host || !host->read8 || !host->write8)
        return -1;

    const char *text_port = getenv("DBG_PORT");
    const char *gdb9_port = getenv("DBG_GDB_PORT");
    const char *gdb7_port = getenv("DBG_GDB_PORT7");
    if (!text_port || !*text_port)
        text_port = getenv("MKDS_DBG_PORT");
    if (!gdb9_port || !*gdb9_port)
        gdb9_port = getenv("MKDS_GDB_PORT");
    if (!gdb7_port || !*gdb7_port)
        gdb7_port = getenv("MKDS_GDB_PORT7");
    int has_text = text_port && *text_port;
    int has_gdb9 = gdb9_port && *gdb9_port;
    int has_gdb7 = gdb7_port && *gdb7_port;
    if (!has_text && !has_gdb9 && !has_gdb7)
        return 0;

    g_host = *host;
    g_stop = 0;
    g_paused = 0;
    g_at_pause = 0;
    g_stop_reason = 0;
    g_stop_cpu = 0;
    g_active = 1;
    dbg_load_symbols();

    int started = 0;

    if (has_text)
    {
        int port = atoi(text_port);
        if (port <= 0)
            port = DBG_DEFAULT_PORT;
#ifdef _WIN32
        HANDLE thread = CreateThread(NULL, 0, dbg_server_thread,
                                     (void *)(intptr_t)port, 0, NULL);
        if (thread)
        {
            CloseHandle(thread);
            started = 1;
        }
#else
        pthread_t thread;
        if (pthread_create(&thread, NULL, dbg_server_thread,
                           (void *)(intptr_t)port) == 0)
        {
            pthread_detach(thread);
            started = 1;
        }
#endif
    }

    if (has_gdb9)
    {
        int port = atoi(gdb9_port);
        if (port <= 0)
            port = DBG_GDB_DEFAULT_PORT;
        if (gdb_start_thread(port, 9, 0) == 0)
            started = 1;
    }

    if (has_gdb7)
    {
        int port = atoi(gdb7_port);
        if (port <= 0)
            port = DBG_GDB_DEFAULT_PORT + 1;
        if (gdb_start_thread(port, 7, 1) == 0)
            started = 1;
    }

    if (!started)
    {
        g_active = 0;
        return -1;
    }
    return 1;
}

void dbg_server_stop(void)
{
    g_active = 0;
    g_paused = 0;
    g_stop = 1;
    if (g_listen_socket != DBG_INVALID_SOCKET)
    {
        dbg_close_socket(g_listen_socket);
        g_listen_socket = DBG_INVALID_SOCKET;
    }
    for (int i = 0; i < 2; i++)
    {
        if (g_gdb_listen_socket[i] != DBG_INVALID_SOCKET)
        {
            dbg_close_socket(g_gdb_listen_socket[i]);
            g_gdb_listen_socket[i] = DBG_INVALID_SOCKET;
        }
    }
}

int dbg_server_running(void)
{
    return g_active;
}

void dbg_on_frame_boundary(uint64_t frame)
{
    if (!g_active)
        return;

    g_frame = frame;
    if (g_step_frames > 0 && --g_step_frames == 0)
    {
        g_paused = 1;
        if (g_gdb_step)
        {
            g_stop_reason = 5;
            g_stop_cpu = g_gdb_step_cpu;
            g_gdb_step = 0;
        }
    }
    if (g_wait_frames > 0 && --g_wait_frames == 0)
        g_paused = 1;

    if (g_paused)
    {
        g_at_pause = 1;
        while (g_paused && !g_stop)
            dbg_sleep_ms(1);
        g_at_pause = 0;
    }
}

void dbg_check_breakpoint(int cpu, uint32_t address)
{
    (void)cpu;
    if (!g_active || !g_breakpoint_count)
        return;

    uint32_t aligned = address & ~1u;
    for (int i = 0; i < g_breakpoint_count; i++)
    {
        if (g_breakpoints[i] != aligned)
            continue;
        g_breakpoint_hit = aligned;
        g_stop_reason = 5;
        g_stop_cpu = cpu;
        g_gdb_step = 0;
        if (!g_paused)
        {
            g_paused = 1;
            g_at_pause = 1;
            while (g_paused && !g_stop)
                dbg_sleep_ms(1);
            g_at_pause = 0;
        }
        return;
    }
}

/* ---- GDB Remote Serial Protocol ---------------------------------------- */

enum
{
    GDB_REG_COUNT = 39,
    GDB_SIGNAL_INT = 2,
    GDB_SIGNAL_TRAP = 5,
};

#define GDB_CORE_XML \
    "<reg name=\"r0\" bitsize=\"32\" type=\"uint32\"/>" \
    "<reg name=\"r1\" bitsize=\"32\" type=\"uint32\"/>" \
    "<reg name=\"r2\" bitsize=\"32\" type=\"uint32\"/>" \
    "<reg name=\"r3\" bitsize=\"32\" type=\"uint32\"/>" \
    "<reg name=\"r4\" bitsize=\"32\" type=\"uint32\"/>" \
    "<reg name=\"r5\" bitsize=\"32\" type=\"uint32\"/>" \
    "<reg name=\"r6\" bitsize=\"32\" type=\"uint32\"/>" \
    "<reg name=\"r7\" bitsize=\"32\" type=\"uint32\"/>" \
    "<reg name=\"r8\" bitsize=\"32\" type=\"uint32\"/>" \
    "<reg name=\"r9\" bitsize=\"32\" type=\"uint32\"/>" \
    "<reg name=\"r10\" bitsize=\"32\" type=\"uint32\"/>" \
    "<reg name=\"r11\" bitsize=\"32\" type=\"uint32\"/>" \
    "<reg name=\"r12\" bitsize=\"32\" type=\"uint32\"/>" \
    "<reg name=\"sp\" bitsize=\"32\" type=\"data_ptr\"/>" \
    "<reg name=\"lr\" bitsize=\"32\" type=\"code_ptr\"/>" \
    "<reg name=\"pc\" bitsize=\"32\" type=\"code_ptr\"/>"

#define GDB_MODE_XML \
    "<reg name=\"cpsr\" bitsize=\"32\" regnum=\"25\"/>" \
    "<reg name=\"sp_usr\" bitsize=\"32\" regnum=\"26\" type=\"data_ptr\"/>" \
    "<reg name=\"lr_usr\" bitsize=\"32\" regnum=\"27\" type=\"code_ptr\"/>" \
    "<reg name=\"r8_fiq\" bitsize=\"32\" regnum=\"28\" type=\"uint32\"/>" \
    "<reg name=\"r9_fiq\" bitsize=\"32\" regnum=\"29\" type=\"uint32\"/>" \
    "<reg name=\"r10_fiq\" bitsize=\"32\" regnum=\"30\" type=\"uint32\"/>" \
    "<reg name=\"r11_fiq\" bitsize=\"32\" regnum=\"31\" type=\"uint32\"/>" \
    "<reg name=\"r12_fiq\" bitsize=\"32\" regnum=\"32\" type=\"uint32\"/>" \
    "<reg name=\"sp_fiq\" bitsize=\"32\" regnum=\"33\" type=\"data_ptr\"/>" \
    "<reg name=\"lr_fiq\" bitsize=\"32\" regnum=\"34\" type=\"code_ptr\"/>" \
    "<reg name=\"sp_irq\" bitsize=\"32\" regnum=\"35\" type=\"data_ptr\"/>" \
    "<reg name=\"lr_irq\" bitsize=\"32\" regnum=\"36\" type=\"code_ptr\"/>" \
    "<reg name=\"sp_svc\" bitsize=\"32\" regnum=\"37\" type=\"data_ptr\"/>" \
    "<reg name=\"lr_svc\" bitsize=\"32\" regnum=\"38\" type=\"code_ptr\"/>" \
    "<reg name=\"sp_abt\" bitsize=\"32\" regnum=\"39\" type=\"data_ptr\"/>" \
    "<reg name=\"lr_abt\" bitsize=\"32\" regnum=\"40\" type=\"code_ptr\"/>" \
    "<reg name=\"sp_und\" bitsize=\"32\" regnum=\"41\" type=\"data_ptr\"/>" \
    "<reg name=\"lr_und\" bitsize=\"32\" regnum=\"42\" type=\"code_ptr\"/>" \
    "<reg name=\"spsr_fiq\" bitsize=\"32\" regnum=\"43\"/>" \
    "<reg name=\"spsr_irq\" bitsize=\"32\" regnum=\"44\"/>" \
    "<reg name=\"spsr_svc\" bitsize=\"32\" regnum=\"45\"/>" \
    "<reg name=\"spsr_abt\" bitsize=\"32\" regnum=\"46\"/>" \
    "<reg name=\"spsr_und\" bitsize=\"32\" regnum=\"47\"/>"

static const char GDB_TARGET_XML_ARM7[] =
    "<target version=\"1.0\"><architecture>armv4t</architecture>"
    "<osabi>none</osabi><feature name=\"org.gnu.gdb.arm.core\">"
    GDB_CORE_XML GDB_MODE_XML "</feature></target>";

static const char GDB_TARGET_XML_ARM9[] =
    "<target version=\"1.0\"><architecture>armv5te</architecture>"
    "<osabi>none</osabi><feature name=\"org.gnu.gdb.arm.core\">"
    GDB_CORE_XML GDB_MODE_XML "</feature></target>";

static const char GDB_TARGET_INFO_ARM7[] =
    "cputype:12;cpusubtype:5;triple:arm-none-eabi;ostype:none;"
    "vendor:none;endian:little;ptrsize:4;";

static const char GDB_TARGET_INFO_ARM9[] =
    "cputype:12;cpusubtype:7;triple:arm-none-eabi;ostype:none;"
    "vendor:none;endian:little;ptrsize:4;";

static int gdb_send_raw(dbg_socket socket, const char *data, size_t length)
{
    while (length)
    {
        int written = send(socket, data, (int)length, 0);
        if (written <= 0)
            return -1;
        data += written;
        length -= (size_t)written;
    }
    return 0;
}

static int gdb_wait_readable(dbg_socket socket, int milliseconds)
{
    fd_set set;
    FD_ZERO(&set);
    FD_SET(socket, &set);
    struct timeval timeout;
    timeout.tv_sec = milliseconds / 1000;
    timeout.tv_usec = (milliseconds % 1000) * 1000;
    return select((int)socket + 1, &set, NULL, NULL, &timeout);
}

static int gdb_send_packet(dbg_socket socket, const char *data, size_t length)
{
    char frame[DBG_GDB_PACKET_MAX + 8];
    if (length > DBG_GDB_PACKET_MAX - 5)
        return 0;

    unsigned char checksum = 0;
    frame[0] = '$';
    for (size_t i = 0; i < length; i++)
    {
        frame[i + 1] = data[i];
        checksum = (unsigned char)(checksum + (unsigned char)data[i]);
    }
    size_t end = length + 1;
    char hex[] = "0123456789abcdef";
    frame[end++] = '#';
    frame[end++] = hex[checksum >> 4];
    frame[end++] = hex[checksum & 15];

    for (int attempt = 0; attempt < 3; attempt++)
    {
        if (gdb_send_raw(socket, frame, end) != 0)
            return 0;
        if (g_gdb_no_ack)
            return 1;
        int wr = gdb_wait_readable(socket, 2000);
        if (wr <= 0)
            return 0;
        char ack;
        int received = recv(socket, &ack, 1, 0);
        if (received <= 0)
            return 0;
        if (ack == '+')
            return 1;
        if (ack != '-')
            return 1;
    }
    return 0;
}

static int gdb_send_text(dbg_socket socket, const char *text)
{
    return gdb_send_packet(socket, text, strlen(text));
}

static int gdb_send_empty(dbg_socket socket)
{
    return gdb_send_packet(socket, "", 0);
}

static int gdb_send_error(dbg_socket socket, const char *error)
{
    return gdb_send_text(socket, error);
}

/*
 * Returns 1 for a packet, 2 for Ctrl-C, 0 for disconnect.
 * The caller handles the packet text in buffer.
 */
static int gdb_recv_packet(dbg_socket socket, char *buffer, size_t capacity)
{
    for (;;)
    {
        char ch;
        int received = recv(socket, &ch, 1, 0);
        if (received <= 0)
            return 0;
        if (ch == 0x03)
            return 2;
        if (ch == '+' || ch == '-')
            continue;
        if (ch != '$')
            continue;

        size_t length = 0;
        unsigned char checksum = 0;
        for (;;)
        {
            received = recv(socket, &ch, 1, 0);
            if (received <= 0)
                return 0;
            if (ch == '#')
                break;
            if (length + 1 >= capacity)
                return 0;
            buffer[length++] = ch;
            checksum = (unsigned char)(checksum + (unsigned char)ch);
        }

        char high;
        char low;
        if (recv(socket, &high, 1, 0) != 1 ||
            recv(socket, &low, 1, 0) != 1)
            return 0;
        char hex[] = "0123456789abcdef";
        unsigned char expected = 0;
        for (int i = 0; i < 16; i++)
        {
            if (hex[i] == high)
                expected = (unsigned char)(i << 4);
        }
        for (int i = 0; i < 16; i++)
        {
            if (hex[i] == low)
                expected = (unsigned char)(expected | i);
        }

        if (expected != checksum)
        {
            if (!g_gdb_no_ack)
                gdb_send_raw(socket, "-", 1);
            continue;
        }

        buffer[length] = 0;
        if (!g_gdb_no_ack)
            gdb_send_raw(socket, "+", 1);
        return 1;
    }
}

static int gdb_poll_interrupt(dbg_socket socket)
{
    if (gdb_wait_readable(socket, 0) <= 0)
        return 0;
    char ch;
    if (recv(socket, &ch, 1, 0) != 1)
        return 0;
    return ch == 0x03;
}

static void gdb_put_hex32(char *out, uint32_t value)
{
    static const char hex[] = "0123456789abcdef";
    for (int i = 0; i < 4; i++)
    {
        unsigned char byte = (unsigned char)(value >> (i * 8));
        out[i * 2] = hex[byte >> 4];
        out[i * 2 + 1] = hex[byte & 15];
    }
}

static int gdb_get_hex32(const char *text, uint32_t *out)
{
    uint32_t value = 0;
    for (int byte = 0; byte < 4; byte++)
    {
        unsigned digits = 0;
        for (int nibble = 0; nibble < 2; nibble++)
        {
            char ch = text[byte * 2 + nibble];
            unsigned digit;
            if (ch >= '0' && ch <= '9')
                digit = (unsigned)(ch - '0');
            else if (ch >= 'a' && ch <= 'f')
                digit = (unsigned)(ch - 'a' + 10);
            else if (ch >= 'A' && ch <= 'F')
                digit = (unsigned)(ch - 'A' + 10);
            else
                return 0;
            digits = (digits << 4) | digit;
        }
        value |= (uint32_t)digits << (byte * 8);
    }
    *out = value;
    return 1;
}

static uint32_t gdb_get_reg(const DbgCpu *state, int reg)
{
    if (reg >= 0 && reg < 16)
        return state->r[reg];
    if (reg == 16 || reg == 25)
        return state->cpsr;
    if (reg >= 17 && reg <= 38)
        return state->mode[reg - 17];
    if (reg >= 26 && reg <= 47)
        return state->mode[reg - 26];
    return 0;
}

static void gdb_set_reg(DbgCpu *state, int reg, uint32_t value)
{
    if (reg >= 0 && reg < 16)
        state->r[reg] = value;
    else if (reg == 16 || reg == 25)
        state->cpsr = value;
    else if (reg >= 17 && reg <= 38)
        state->mode[reg - 17] = value;
    else if (reg >= 26 && reg <= 47)
        state->mode[reg - 26] = value;
}

static int gdb_encode_regs(dbg_socket socket, const DbgCpu *state)
{
    char data[GDB_REG_COUNT * 8 + 1];
    for (int i = 0; i < GDB_REG_COUNT; i++)
        gdb_put_hex32(data + i * 8, gdb_get_reg(state, i));
    data[GDB_REG_COUNT * 8] = 0;
    return gdb_send_packet(socket, data, GDB_REG_COUNT * 8);
}

static int gdb_decode_regs(const char *data, size_t length, DbgCpu *state)
{
    if (length != GDB_REG_COUNT * 8)
        return 0;
    for (int i = 0; i < GDB_REG_COUNT; i++)
    {
        uint32_t value;
        if (!gdb_get_hex32(data + i * 8, &value))
            return 0;
        gdb_set_reg(state, i, value);
    }
    return 1;
}

static int gdb_get_state(int cpu, DbgCpu *state)
{
    return g_host.get_regs &&
           g_host.get_regs(g_host.user, cpu, state);
}

static int gdb_set_state(int cpu, const DbgCpu *state)
{
    return g_host.set_regs &&
           g_host.set_regs(g_host.user, cpu, state);
}

static const char *gdb_target_xml(int cpu)
{
    return cpu == 7 ? GDB_TARGET_XML_ARM7 : GDB_TARGET_XML_ARM9;
}

static const char *gdb_target_info(int cpu)
{
    return cpu == 7 ? GDB_TARGET_INFO_ARM7 : GDB_TARGET_INFO_ARM9;
}

static int gdb_send_xfer(dbg_socket socket, const char *data,
                         size_t length, size_t offset, size_t requested)
{
    if (offset >= length)
        return gdb_send_text(socket, "l");

    if (requested > DBG_GDB_PACKET_MAX - 4)
        requested = DBG_GDB_PACKET_MAX - 4;
    size_t available = length - offset;
    size_t count = requested < available ? requested : available;

    char *packet = malloc(count + 2);
    if (!packet)
        return 0;
    packet[0] = (offset + count < length) ? 'm' : 'l';
    memcpy(packet + 1, data + offset, count);
    int result = gdb_send_packet(socket, packet, count + 1);
    free(packet);
    return result;
}

static void gdb_send_stop(dbg_socket socket)
{
    if (g_stop_reason == GDB_SIGNAL_INT)
        gdb_send_text(socket, "S02");
    else
        gdb_send_text(socket, "S05");
}

static void gdb_wait_for_stop(dbg_socket socket, int cpu)
{
    while (!g_stop_reason && !g_stop)
    {
        if (gdb_poll_interrupt(socket))
        {
            g_stop_reason = GDB_SIGNAL_INT;
            g_stop_cpu = cpu;
            g_paused = 1;
            break;
        }
        dbg_sleep_ms(1);
    }

    for (int i = 0; i < DBG_PAUSE_POLL_MS && !g_at_pause && !g_stop; i++)
        dbg_sleep_ms(1);
}

static int gdb_continue(dbg_socket socket, int cpu, int step,
                        const char *address_text)
{
    if (address_text && *address_text)
    {
        DbgCpu state;
        uint32_t address = dbg_parse_uint(address_text);
        if (!gdb_get_state(cpu, &state))
            return gdb_send_error(socket, "E01");
        state.r[15] = address;
        state.func = address;
        if (!gdb_set_state(cpu, &state))
            return gdb_send_error(socket, "E01");
    }

    if (step && g_host.single_step)
    {
        DbgCpu state;
        if (gdb_get_state(cpu, &state) &&
            g_host.single_step(g_host.user, cpu, &state))
        {
            g_stop_reason = GDB_SIGNAL_TRAP;
            g_stop_cpu = cpu;
            gdb_send_stop(socket);
            return 0;
        }
    }

    g_stop_reason = 0;
    g_gdb_step_cpu = cpu;
    g_gdb_step = step ? 1 : 0;
    g_step_frames = step ? 1 : 0;
    g_paused = 0;
    g_at_pause = 0;
    gdb_wait_for_stop(socket, cpu);
    gdb_send_stop(socket);
    return 1;
}

static int gdb_handle_z(dbg_socket socket, const char *text, int add)
{
    int type;
    unsigned address;
    unsigned kind;
    if (sscanf(text, "%d,%x,%u", &type, &address, &kind) != 3)
        return gdb_send_error(socket, "E01");

    if (type == 0 || type == 1)
    {
        uint32_t aligned = address & ~1u;
        if (add)
        {
            if (g_breakpoint_count < DBG_MAX_BREAKPOINTS)
            {
                int exists = 0;
                for (int i = 0; i < g_breakpoint_count; i++)
                    if (g_breakpoints[i] == aligned)
                        exists = 1;
                if (!exists)
                    g_breakpoints[g_breakpoint_count++] = aligned;
            }
        }
        else
        {
            for (int i = 0; i < g_breakpoint_count; i++)
            {
                if (g_breakpoints[i] != aligned)
                    continue;
                memmove(&g_breakpoints[i], &g_breakpoints[i + 1],
                        (size_t)(g_breakpoint_count - i - 1) *
                        sizeof g_breakpoints[0]);
                g_breakpoint_count--;
                break;
            }
        }
        return gdb_send_text(socket, "OK");
    }

    return gdb_send_error(socket, "E01");
}

static int gdb_handle_m(dbg_socket socket, const char *text, int cpu)
{
    unsigned address;
    unsigned length;
    if (sscanf(text, "%x,%x", &address, &length) != 2)
        return gdb_send_error(socket, "E01");
    if (length > (DBG_GDB_PACKET_MAX - 5) / 2)
        return gdb_send_error(socket, "E02");

    char *data = malloc((size_t)length * 2 + 1);
    if (!data)
        return gdb_send_error(socket, "E01");
    static const char hex[] = "0123456789abcdef";
    for (unsigned i = 0; i < length; i++)
    {
        uint8_t byte = dbg_read8(cpu, address + i);
        data[i * 2] = hex[byte >> 4];
        data[i * 2 + 1] = hex[byte & 15];
    }
    data[length * 2] = 0;
    int result = gdb_send_packet(socket, data, (size_t)length * 2);
    free(data);
    return result;
}

static int gdb_handle_M(dbg_socket socket, const char *text, int cpu)
{
    unsigned address;
    unsigned length;
    int offset = 0;
    if (sscanf(text, "%x,%x:%n", &address, &length, &offset) != 2 ||
        offset <= 0)
        return gdb_send_error(socket, "E01");
    if (length > (DBG_GDB_PACKET_MAX - 5) / 2)
        return gdb_send_error(socket, "E02");

    const char *data = text + offset;

    for (unsigned i = 0; i < length; i++)
    {
        char pair[3] = {data[i * 2], data[i * 2 + 1], 0};
        dbg_write8(cpu, address + i,
                   (uint8_t)strtoul(pair, NULL, 16));
    }
    return gdb_send_text(socket, "OK");
}

static int gdb_handle_X(dbg_socket socket, const char *text, int cpu)
{
    unsigned address;
    unsigned length;
    int offset = 0;
    if (sscanf(text, "%x,%x:%n", &address, &length, &offset) != 2 ||
        offset <= 0)
        return gdb_send_error(socket, "E01");
    if (length > DBG_GDB_PACKET_MAX - 5)
        return gdb_send_error(socket, "E02");

    const unsigned char *data = (const unsigned char *)text + offset;
    for (unsigned i = 0; i < length; i++)
        dbg_write8(cpu, address + i, data[i]);
    return gdb_send_text(socket, "OK");
}

static int gdb_handle_question(dbg_socket socket)
{
    if (!g_stop_reason)
        g_stop_reason = GDB_SIGNAL_TRAP;
    if (!g_stop_cpu)
        g_stop_cpu = 9;
    gdb_send_stop(socket);
    return 1;
}

static int gdb_handle_xfer(dbg_socket socket, const char *packet, int cpu)
{
    const char *object = packet + 6; /* after qXfer: */
    const char *object_end = strchr(object, ':');
    if (!object_end)
        return gdb_send_error(socket, "E01");
    const char *operation = object_end + 1;
    const char *operation_end = strchr(operation, ':');
    if (!operation_end)
        return gdb_send_error(socket, "E01");
    const char *annex = operation_end + 1;
    const char *range = strrchr(annex, ':');
    if (!range)
        return gdb_send_error(socket, "E01");

    size_t object_length = (size_t)(object_end - object);
    size_t operation_length = (size_t)(operation_end - operation);
    size_t annex_length = (size_t)(range - annex);

    if (operation_length != 4 || strncmp(operation, "read", 4) != 0)
        return gdb_send_error(socket, "E01");

    size_t offset = 0;
    size_t length = 0;
    if (sscanf(range + 1, "%zx,%zx", &offset, &length) != 2)
        return gdb_send_error(socket, "E01");

    if (object_length == 8 && !strncmp(object, "features", 8) &&
        annex_length == 10 && !strncmp(annex, "target.xml", 10))
    {
        const char *xml = gdb_target_xml(cpu);
        return gdb_send_xfer(socket, xml, strlen(xml), offset, length);
    }

    return gdb_send_text(socket, "l");
}

static uint32_t gdb_crc32(uint32_t address, uint32_t length, int cpu)
{
    uint32_t crc = 0xFFFFFFFFu;
    for (uint32_t i = 0; i < length; i++)
    {
        crc ^= dbg_read8(cpu, address + i);
        for (int bit = 0; bit < 8; bit++)
            crc = (crc >> 1) ^ (0xEDB88320u & (uint32_t)-(int32_t)(crc & 1));
    }
    return crc ^ 0xFFFFFFFFu;
}

static int gdb_handle_packet(dbg_socket socket, char *packet, int cpu)
{
    if (!strcmp(packet, "?"))
        return gdb_handle_question(socket);

    if (!strncmp(packet, "qSupported", 10))
        return gdb_send_text(socket,
            "PacketSize=1000;qXfer:features:read+;swbreak-;hwbreak+;"
            "QStartNoAckMode+");
    if (!strcmp(packet, "qHostInfo") || !strcmp(packet, "qProcessInfo"))
        return gdb_send_text(socket, gdb_target_info(cpu));
    if (!strncmp(packet, "qXfer:", 6))
        return gdb_handle_xfer(socket, packet, cpu);
    if (!strcmp(packet, "qAttached"))
        return gdb_send_text(socket, "1");
    if (!strcmp(packet, "qC"))
        return gdb_send_text(socket, "QC1");
    if (!strcmp(packet, "qfThreadInfo"))
        return gdb_send_text(socket, "m1");
    if (!strcmp(packet, "qsThreadInfo"))
        return gdb_send_text(socket, "l");
    if (!strcmp(packet, "QStartNoAckMode"))
    {
        int result = gdb_send_text(socket, "OK");
        g_gdb_no_ack = 1;
        return result;
    }

    if (packet[0] == 'g')
    {
        DbgCpu state;
        if (!gdb_get_state(cpu, &state))
            return gdb_send_error(socket, "E01");
        return gdb_encode_regs(socket, &state);
    }
    if (packet[0] == 'G')
    {
        DbgCpu state;
        if (!gdb_get_state(cpu, &state) ||
            !gdb_decode_regs(packet + 1, strlen(packet + 1), &state) ||
            !gdb_set_state(cpu, &state))
            return gdb_send_error(socket, "E01");
        return gdb_send_text(socket, "OK");
    }
    if (packet[0] == 'p')
    {
        int reg = 0;
        if (sscanf(packet + 1, "%x", &reg) != 1)
            return gdb_send_error(socket, "E01");
        DbgCpu state;
        if (!gdb_get_state(cpu, &state))
            return gdb_send_error(socket, "E01");
        char data[9];
        gdb_put_hex32(data, gdb_get_reg(&state, reg));
        data[8] = 0;
        return gdb_send_text(socket, data);
    }
    if (packet[0] == 'P')
    {
        int reg = 0;
        int offset = 0;
        if (sscanf(packet + 1, "%x=%n", &reg, &offset) != 1 ||
            offset <= 0)
            return gdb_send_error(socket, "E01");
        uint32_t value;
        if (!gdb_get_hex32(packet + 1 + offset, &value))
            return gdb_send_error(socket, "E01");
        DbgCpu state;
        if (!gdb_get_state(cpu, &state))
            return gdb_send_error(socket, "E01");
        gdb_set_reg(&state, reg, value);
        if (!gdb_set_state(cpu, &state))
            return gdb_send_error(socket, "E01");
        return gdb_send_text(socket, "OK");
    }

    if (packet[0] == 'm')
        return gdb_handle_m(socket, packet + 1, cpu);
    if (packet[0] == 'M')
        return gdb_handle_M(socket, packet + 1, cpu);
    if (packet[0] == 'X')
        return gdb_handle_X(socket, packet + 1, cpu);

    if (packet[0] == 'H')
    {
        int thread = atoi(packet + 2);
        return gdb_send_text(socket, thread <= 1 ? "OK" : "E01");
    }
    if (packet[0] == 'T')
        return gdb_send_text(socket, "OK");

    if (packet[0] == 'c' || packet[0] == 'C')
        return gdb_continue(socket, cpu, 0, packet + 1);
    if (packet[0] == 's' || packet[0] == 'S')
        return gdb_continue(socket, cpu, 1, packet + 1);

    if (packet[0] == 'Z')
        return gdb_handle_z(socket, packet + 1, 1);
    if (packet[0] == 'z')
        return gdb_handle_z(socket, packet + 1, 0);

    if (!strcmp(packet, "vCont?"))
        return gdb_send_text(socket, "vCont;c;s;t");
    if (!strncmp(packet, "vCont;", 6))
    {
        if (packet[6] == 'c')
        {
            if (!gdb_send_text(socket, "OK"))
                return 0;
            return gdb_continue(socket, cpu, 0, "");
        }
        if (packet[6] == 's')
        {
            if (!gdb_send_text(socket, "OK"))
                return 0;
            return gdb_continue(socket, cpu, 1, "");
        }
        g_paused = 1;
        g_stop_reason = GDB_SIGNAL_INT;
        g_stop_cpu = cpu;
        gdb_send_stop(socket);
        return 1;
    }

    if (!strcmp(packet, "vAttach"))
    {
        g_paused = 1;
        g_stop_reason = GDB_SIGNAL_TRAP;
        g_stop_cpu = cpu;
        return gdb_send_text(socket, "T05thread:1;");
    }
    if (!strncmp(packet, "vKill", 5))
    {
        gdb_send_text(socket, "OK");
        return 0;
    }
    if (!strncmp(packet, "vRun", 4))
        return gdb_send_text(socket, "OK");
    if (!strcmp(packet, "vStopped"))
        return gdb_send_text(socket, "OK");
    if (!strcmp(packet, "vMustReplyEmpty"))
        return gdb_send_empty(socket);

    if (packet[0] == '!')
        return gdb_send_text(socket, "OK");
    if (packet[0] == 'D')
    {
        gdb_send_text(socket, "OK");
        g_paused = 0;
        return 0;
    }
    if (packet[0] == 'k')
        return 0;
    if (packet[0] == 'r' || packet[0] == 'R')
        return gdb_send_text(socket, "OK");

    if (!strncmp(packet, "qCRC:", 5))
    {
        unsigned address;
        unsigned length;
        if (sscanf(packet + 5, "%x,%x", &address, &length) != 2)
            return gdb_send_error(socket, "E01");
        char data[32];
        snprintf(data, sizeof data, "C%x",
                 gdb_crc32(address, length, cpu));
        return gdb_send_text(socket, data);
    }
    if (!strncmp(packet, "qRcmd,", 6))
        return gdb_send_error(socket, "E01");

    if (packet[0] == 'q' || packet[0] == 'v')
        return gdb_send_empty(socket);

    return gdb_send_empty(socket);
}

typedef struct
{
    int port;
    int cpu;
    int slot;
} GdbListener;

static GdbListener g_gdb_listeners[2];

static void gdb_client_loop(dbg_socket socket, int cpu)
{
    g_gdb_no_ack = 0;
    g_paused = 1;
    g_stop_reason = GDB_SIGNAL_TRAP;
    g_stop_cpu = cpu;
    for (int i = 0; i < DBG_PAUSE_POLL_MS && !g_at_pause && !g_stop; i++)
        dbg_sleep_ms(1);

    char packet[DBG_GDB_PACKET_MAX];
    for (;;)
    {
        int result = gdb_recv_packet(socket, packet, sizeof packet);
        if (result == 0)
            break;
        if (result == 2)
        {
            g_stop_reason = GDB_SIGNAL_INT;
            g_stop_cpu = cpu;
            g_paused = 1;
            gdb_send_stop(socket);
            continue;
        }
        if (!gdb_handle_packet(socket, packet, cpu))
            break;
    }

    g_paused = 0;
    g_at_pause = 0;
}

#ifdef _WIN32
static DWORD WINAPI gdb_server_thread(LPVOID argument)
#else
static void *gdb_server_thread(void *argument)
#endif
{
    GdbListener *listener = argument;
#ifdef _WIN32
    WSADATA wsa;
    WSAStartup(MAKEWORD(2, 2), &wsa);
#endif

    dbg_socket server = socket(AF_INET, SOCK_STREAM, 0);
    if (server == DBG_INVALID_SOCKET)
        goto done;

    int reuse = 1;
    setsockopt(server, SOL_SOCKET, SO_REUSEADDR,
               (const char *)&reuse, sizeof reuse);

    struct sockaddr_in address;
    memset(&address, 0, sizeof address);
    address.sin_family = AF_INET;
    address.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
    address.sin_port = htons((uint16_t)listener->port);

    if (bind(server, (struct sockaddr *)&address, sizeof address) < 0)
    {
        fprintf(stderr, "[dbg] GDB cannot bind 127.0.0.1:%d\n", listener->port);
        dbg_close_socket(server);
        goto done;
    }

    listen(server, 5);
    g_gdb_listen_socket[listener->slot] = server;
    fprintf(stderr, "[dbg] GDB CPU%d listening on 127.0.0.1:%d\n",
            listener->cpu, listener->port);

    while (!g_stop)
    {
        dbg_socket client = accept(server, NULL, NULL);
        if (client == DBG_INVALID_SOCKET)
            break;
        gdb_client_loop(client, listener->cpu);
        dbg_close_socket(client);
    }

    dbg_close_socket(server);
    g_gdb_listen_socket[listener->slot] = DBG_INVALID_SOCKET;

done:
#ifdef _WIN32
    WSACleanup();
    return 0;
#else
    return NULL;
#endif
}

static int gdb_start_thread(int port, int cpu, int slot)
{
    if (port <= 0)
        return -1;
    if (slot < 0 || slot > 1)
        return -1;

    g_gdb_listeners[slot].port = port;
    g_gdb_listeners[slot].cpu = cpu;
    g_gdb_listeners[slot].slot = slot;
    g_gdb_no_ack = 0;

#ifdef _WIN32
    HANDLE thread = CreateThread(NULL, 0, gdb_server_thread,
                                 &g_gdb_listeners[slot], 0, NULL);
    if (!thread)
        return -1;
    CloseHandle(thread);
#else
    pthread_t thread;
    if (pthread_create(&thread, NULL, gdb_server_thread,
                       &g_gdb_listeners[slot]) != 0)
        return -1;
    pthread_detach(thread);
#endif
    return 0;
}
