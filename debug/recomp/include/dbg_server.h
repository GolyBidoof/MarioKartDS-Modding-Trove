/*
 * Mario Kart DS Modding Trove
 * debug/recomp/include/dbg_server.h — generic recomp debug server API
 * SPDX-License-Identifier: MIT
 */
#pragma once

#include "dbg_host.h"

/* Returns 1 if the server started, 0 if DBG_PORT is unset, -1 on error. */
int dbg_server_start(const DbgHost *host);
void dbg_server_stop(void);
int dbg_server_running(void);

/* Call from the emulation/frame loop. */
void dbg_on_frame_boundary(uint64_t frame);

/* Call before executing a translated function. cpu is 9 or 7. */
void dbg_check_breakpoint(int cpu, uint32_t address);
