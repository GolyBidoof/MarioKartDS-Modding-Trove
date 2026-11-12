# Recomp debug layer

These files are specific to the static recompilation. melonDS does not use them.

They originate in [DS-Kart-Recompiled](https://github.com/AlonsoTlol/DS-Kart-Recompiled).

## Files

| Path | Purpose |
|---|---|
| `src/dbg_server.c` | text protocol + GDB RSP server |
| `include/dbg_host.h` | host adapter callbacks |
| `include/dbg_server.h` | server hooks (`start`, frame, breakpoint) |
| `client/dbg_client.py` | recomp text protocol client |
| `client/run_scenario.py` | launch a recomp and run a Python scenario |
| `mkds/text_backend.py` | recomp-only `RecompBackend` (screenshots + input) |
| `examples/host_example.c` | minimal host adapter template |
| `examples/bmp.c` / `bmp.h` | optional BGRA BMP writer/crop helper |
| `examples/scenario_example.py` | example scenario |
| `native/` | process-level lldb/gdb for recompiled C |
| `Makefile` | compile check |

## Integrate

Add `src/dbg_server.c` to the recomp build, implement `DbgHost`, then:

```c
dbg_server_start(&host);
```

- `dbg_on_frame_boundary(frame)` once per frame.
- `dbg_check_breakpoint(cpu, pc)` before executing a translated function.
- `mkds_dbg_host_frame()` in DS-Kart applies injected input before the frame boundary.

## Ports

| Variable | Meaning |
|---|---|
| `DBG_PORT` / `MKDS_DBG_PORT` | text protocol |
| `DBG_GDB_PORT` / `MKDS_GDB_PORT` | ARM9 GDB RSP |
| `DBG_GDB_PORT7` / `MKDS_GDB_PORT7` | ARM7 GDB RSP |
| `DBG_SYMBOLS` / `MKDS_DBG_SYMBOLS` | fallback symbol file |

The DS-Kart adapter sets `DBG_PORT` and `DBG_GDB_PORT` for the installed server.

## Screenshots

Recomp screenshots are native by default and support upper/lower/both plus full resolution:

```sh
python3 debug/recomp/client/dbg_client.py screenshot upper
python3 debug/generic/mkds/cli.py --backend recomp --port 19850 screenshot upper
```

The `DbgHost.screenshot` callback receives `screen` (`both`/`upper`/`lower`) and `capture` (`native` 256x192 per screen, or `full`).

## Native C debugging

`native/` is the separate lldb/gdb path for the recompiled host C. It does not use either debug port. See [`native/README.md`](native/README.md).

## Build check

```sh
make -C debug/recomp check
```
