# Debug layers

`debug/` is split by what each piece talks to. The custom MKDS layer is generic because it sits on a backend; screenshots are only available from the recomp text backend.

The recomp debug layer originated in [DS-Kart-Recompiled](https://github.com/AlonsoTlol/DS-Kart-Recompiled).

| Layer | Directory | Used where |
|---|---|---|
| Generic | `generic/` | recomp RSP, melonDS, GDB/Ghidra, scripted clients |
| Recomp | `recomp/` | static recompilation only: text protocol, RSP server, screenshots, native C |
| melonDS | `melonDS/` | melonDS-only ports, config and connection notes |

## What to use where

| Task | Backend |
|---|---|
| Recomp scene/menu/screenshot/input | `recomp/client/dbg_client.py` + `recomp/mkds/text_backend.py` |
| Recomp GDB RSP | `recomp/src/dbg_server.c` on `DBG_GDB_PORT` |
| melonDS GDB RSP | melonDS `:3333`/`:3334` via `generic/transport/rsp.py` |
| Keep melonDS attached across reconnects | `generic/transport/rsp_proxy.py` |
| Ghidra live target | Ghidra GDB agent -> proxy -> melonDS/recomp RSP |
| Native recompiled-C debugging | `recomp/native/` (lldb/gdb) |
| Scene/menu over any backend | `generic/mkds/cli.py` |

## Generic

- `generic/transport/rsp.py` — persistent GDB RSP client.
- `generic/transport/rsp_proxy.py` — one upstream attachment, many local clients; local detach does not detach upstream.
- `generic/mkds/` — MKDS scene/menu/screenshot layer over a backend.
- `generic/ghidra/` — Ghidra GDB-agent installation and connection notes.

See [`generic/README.md`](generic/README.md).

## Recomp

- `recomp/include/`, `recomp/src/` — host adapter API and text + RSP server.
- `recomp/client/` — recomp text client and scenario runner.
- `recomp/mkds/text_backend.py` — recomp-only `RecompBackend`.
- `recomp/examples/` — host adapter and BMP/screenshot templates.
- `recomp/native/` — native lldb/gdb path for recompiled C.
- `recomp/Makefile` — compile check.

See [`recomp/README.md`](recomp/README.md).

## melonDS

- `melonDS/README.md` — ARM9/ARM7 ports, single-attachment behavior, proxy setup, and what is/isn't available over its GDB stub.

See [`melonDS/README.md`](melonDS/README.md).
