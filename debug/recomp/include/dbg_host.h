/*
 * Mario Kart DS Modding Trove
 * debug/recomp/include/dbg_host.h — host adapter for the generic recomp debug server
 * SPDX-License-Identifier: MIT
 *
 * The debug server never reads a ROM and never assumes a memory map. The
 * static recompilation supplies this table; every callback is optional except
 * read8 and write8, which the server uses to implement all memory access.
 */
#pragma once

#include <stddef.h>
#include <stdint.h>

typedef struct DbgCpu {
    uint32_t r[16];
    uint32_t cpsr;
    uint32_t func;
    /*
     * melonDS/GDB register order after cpsr: sp_usr, lr_usr, r8_fiq..r12_fiq,
     * sp_fiq, lr_fiq, sp_irq, lr_irq, sp_svc, lr_svc, sp_abt, lr_abt,
     * sp_und, lr_und, spsr_fiq, spsr_irq, spsr_svc, spsr_abt, spsr_und.
     * Hosts that do not expose banked registers can leave these zero.
     */
    uint32_t mode[22];
} DbgCpu;

typedef struct DbgReply {
    void *user;
    void (*line)(void *user, const char *text);
} DbgReply;

enum {
    DBG_SCREEN_BOTH = 0,
    DBG_SCREEN_UPPER = 1,
    DBG_SCREEN_LOWER = 2,
};

enum {
    DBG_CAPTURE_FULL = 0,
    DBG_CAPTURE_NATIVE = 1,
};

enum {
    DBG_KEEP_CONNECTION = 1,
    DBG_CLOSE_CONNECTION = 0,
};

/*
 * A host command is how game-specific commands (scene, menu, ...) stay out
 * of the generic server. Register them in DbgHost.commands.
 */
typedef struct DbgCommand {
    const char *name;
    const char *usage;
    int minimum_arguments;
    int maximum_arguments; /* -1 = unlimited */
    int (*run)(void *user, int argc, char **argv, DbgReply *reply);
} DbgCommand;

typedef struct DbgHost {
    void *user;
    const char *name; /* optional; shown by "status" */

    uint8_t (*read8)(void *user, int cpu, uint32_t address);
    uint16_t (*read16)(void *user, int cpu, uint32_t address);
    uint32_t (*read32)(void *user, int cpu, uint32_t address);
    void (*write8)(void *user, int cpu, uint32_t address, uint8_t value);
    void (*write16)(void *user, int cpu, uint32_t address, uint16_t value);
    void (*write32)(void *user, int cpu, uint32_t address, uint32_t value);

    int (*get_regs)(void *user, int cpu, DbgCpu *out);
    int (*set_regs)(void *user, int cpu, const DbgCpu *state);
    int (*single_step)(void *user, int cpu, DbgCpu *out);
    int (*call)(void *user, int cpu, uint32_t address,
                const uint32_t arguments[4], DbgCpu *out);

    int (*symbol_at)(void *user, uint32_t address, char *name,
                     size_t name_size, uint32_t *offset);
    int (*symbol_address)(void *user, const char *name, uint32_t *address);

    int (*memory_base)(void *user, int cpu, uint32_t *base);
    int (*memory_size)(void *user, int cpu, uint32_t *size);

    /*
     * screen: DBG_SCREEN_BOTH / UPPER / LOWER.
     * capture: DBG_CAPTURE_FULL (host's normal resolution) or
     *          DBG_CAPTURE_NATIVE (256x192 per screen).
     * width/height: filled by the host when non-NULL.
     * Return 0 on success.
     */
    int (*screenshot)(void *user, const char *path, int screen, int capture,
                      int *width, int *height);

    int (*press)(void *user, const char *spec, int frames);
    int (*touch)(void *user, int x, int y, int frames);
    void (*release)(void *user);

    void (*status)(void *user, DbgReply *reply);

    const DbgCommand *commands;
    size_t command_count;
} DbgHost;
