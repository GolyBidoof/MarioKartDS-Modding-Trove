# MKDS custom layer

This package contains only Mario Kart DS knowledge: scene/menu addresses, menu names, and screenshot convenience methods. The transports underneath are generic.

```
debug/generic/mkds/          custom: scene, menu, screenshot API (both backends)
debug/generic/transport/     generic: GDB RSP client and persistent proxy
debug/recomp/client/         recomp: text protocol client and scenarios
debug/recomp/mkds/           recomp: text/screenshot backend
debug/recomp/src/            recomp: RSP/text server and host adapter
debug/recomp/native/         recomp: process-level lldb/gdb
```

## Backend matrix

| Backend | Scene navigation | Screenshots | Input injection |
|---|---|---|---|
| recomp text (`DBG_PORT`) | yes | yes, native/full | yes |
| recomp RSP (`DBG_GDB_PORT`) | yes | no | no |
| melonDS RSP (`:3333` / `:3334`) | yes | no | no |
| recomp/melonDS via `rsp_proxy.py` | yes | no | no |
| Ghidra GDB agent | yes (memory view) | no | no |

Scene/menu navigation is just memory reads/writes, so it works anywhere the backend exposes CPU memory. Screenshots require the emulator/recomp host to provide a composited framebuffer; RSP only exposes CPU memory, not the frontend's final frame. Screenshot methods therefore report `Unsupported` on RSP/melonDS/Ghidra instead of pretending.

## Persistent sessions

The generic RSP client keeps one connection open for its lifetime. The `rsp_proxy.py` layer is the important one for melonDS, whose GDB stub accepts a single attachment per emulator run:

```sh
# one upstream attachment to melonDS ARM9
python3 debug/generic/transport/rsp_proxy.py --upstream 3333 --listen 3335

# keep using this session; do not detach melonDS
python3 debug/generic/mkds/cli.py --backend rsp --port 3335 status
python3 debug/generic/mkds/cli.py --backend rsp --port 3335 scene
```

Local `D`, `k`, and `vKill` packets are answered by the proxy and are **not** forwarded upstream, so GDB/Ghidra can disconnect and reconnect without re-attaching melonDS. Multiple local clients share the one upstream connection. The same proxy works in front of the recomp RSP listener.

## Scene/menu navigation

Defaults (overridable from the CLI):

```text
sSceneManager   0x021653B8
gMenuSceneState 0x0217B43C
```

```sh
python3 debug/generic/mkds/cli.py --backend rsp --port 3335 scene
python3 debug/generic/mkds/cli.py --backend rsp --port 3335 scene 1
python3 debug/generic/mkds/cli.py --backend rsp --port 3335 menu
python3 debug/generic/mkds/cli.py --backend rsp --port 3335 menu_state 5
```

From Python:

```python
from mkds import MkdsClient, RspBackend

with MkdsClient(RspBackend(port=3335)) as client:
    print(client.scene())
    print(client.menu())
    client.set_menu_state(5)
    print(client.scene_info())
```

For recomp text, use `RecompBackend(port=19850)`; it adds screenshots and input while keeping the same `MkdsClient` calls.

## Screenshots

Recomp supports the native/full screenshot methods:

For static-recomp screenshots, use the text backend:

```sh
python3 debug/generic/mkds/cli.py --backend recomp --port 19850 screenshot upper
python3 debug/generic/mkds/cli.py --backend recomp --port 19850 screenshot lower
python3 debug/generic/mkds/cli.py --backend recomp --port 19850 screenshot both
python3 debug/generic/mkds/cli.py --backend recomp --port 19850 screenshot both full
```

```python
client.screenshot_upper("dbg_upper.bmp")   # 256x192
client.screenshot_lower("dbg_lower.bmp")   # 256x192
client.screenshot_both("dbg_both.bmp")     # 256x384 native
client.screenshot_full("dbg_full.bmp")     # host full resolution
```

For a custom backend, implement `screenshot(path, screen, native)` and expose the `"screenshot"` capability. The existing recomp host callback is documented in the parent `debug/README.md`.

## Ghidra

Ghidra 12.2's built-in GDB agent (`ghidragdb`) can connect to the proxy port. Use a GDB built with Python; `arm-none-eabi-gdb` from devkitARM is built `--without-python`, so use Homebrew/GDB with Python for the Ghidra agent.

Recommended path:

```sh
# keep melonDS attached once
python3 debug/generic/transport/rsp_proxy.py --upstream 3333 --listen 3335

# Ghidra: Debugger -> Connect -> GDB remote, localhost:3335
# custom layer: same proxy, separate local client
python3 debug/generic/mkds/cli.py --backend rsp --port 3335 menu
```

The custom layer and Ghidra can both use `localhost:3335`; the proxy serializes requests and keeps melonDS's single upstream attachment alive. Scene writes from the custom layer become visible in Ghidra's memory view.

Screenshots remain unavailable through Ghidra's GDB agent for the same reason as melonDS: the RSP target does not expose the composited framebuffer.

## Menu input routes

Observed navigation timings, retry behavior and the VS-rules -> 250cc route are in [`NAVIGATION.md`](NAVIGATION.md). The same route is machine-readable in [`routes.json`](routes.json).

Useful defaults: `scene 1` + `wait 45` skips the title; mode select uses two `DOWN` presses then `A` for VS; kart select uses `A`, then `A` again with a 90-frame wait for the longer confirmation animation; VS rules starts at `50cc`, so four `RIGHT` presses with 15-frame waits select `250cc`.
