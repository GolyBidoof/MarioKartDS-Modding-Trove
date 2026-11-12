# Generic debug layer

These files apply to both the static recompilation and melonDS, or to any GDB RSP target.

## Files

| Path | Applies to | Purpose |
|---|---|---|
| `transport/rsp.py` | both | persistent GDB RSP client (memory, registers, breakpoints) |
| `transport/rsp_proxy.py` | both, especially melonDS | one upstream attachment, many local clients |
| `mkds/client.py` | both | MKDS scene/menu/screenshot logic over a backend |
| `mkds/backends.py` | both | backend protocol + `RspBackend` |
| `mkds/cli.py` | both | CLI; uses the recomp text backend when `--backend recomp` |
| `ghidra/README.md` | both | Ghidra's GDB agent and proxy connection |

## Layer map

- **recomp RSP** → `transport/rsp.py` or the proxy → `RspBackend`.
- **recomp text** → `recomp/mkds/text_backend.py` → `RecompBackend` (recomp-only; adds screenshots/input).
- **melonDS** → `transport/rsp.py` or the proxy → `RspBackend`.
- **Ghidra** → its GDB agent → the proxy or target RSP port.
- **native lldb/gdb** → `recomp/native/` (separate; not this layer).

## Persistent melonDS session

```sh
python3 debug/generic/transport/rsp_proxy.py --upstream 3333 --listen 3335
python3 debug/generic/mkds/cli.py --backend rsp --port 3335 menu
```

Local `D`/`k`/`vKill` are not forwarded upstream, so melonDS stays attached while GDB/Ghidra reconnect.

See [`mkds/README.md`](mkds/README.md) for the custom layer and [`ghidra/README.md`](ghidra/README.md) for Ghidra.
