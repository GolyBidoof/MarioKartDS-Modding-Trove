# melonDS debug layer

melonDS is not the recomp. It has its own GDB stub; the files in `recomp/` are not used here.

## Ports and config

The local melonDS setup uses:

| Core | Port |
|---|---|
| ARM9 | `3333` |
| ARM7 | `3334` |

`~/Library/Preferences/melonDS/melonDS.toml`:

```toml
[Instance0.Gdb]
Enabled = true

[Instance0.Gdb.ARM9]
BreakOnStartup = false
Port = 3333

[Instance0.Gdb.ARM7]
BreakOnStartup = false
Port = 3334
```

The latest source checkout is the local `melonDS/` checkout in the workspace root; the installed app bundle is the one currently used for live attach.

## Single attachment

melonDS accepts one GDB attachment per emulator run. Keep it open with the generic proxy:

```sh
python3 debug/generic/transport/rsp_proxy.py --upstream 3333 --listen 3335
```

Then attach GDB/Ghidra to `:3335`. Local detach/reconnect does not detach melonDS. The custom MKDS layer can use the same proxy:

```sh
python3 debug/generic/mkds/cli.py --backend rsp --port 3335 scene
python3 debug/generic/mkds/cli.py --backend rsp --port 3335 menu
```

## What is available

- CPU registers/memory and function-entry breakpoints through GDB RSP.
- Scene/menu navigation through MKDS memory writes.
- No recomp text protocol.
- No composited-framebuffer screenshots through RSP; use the recomp text backend for screenshots.

GDB itself can attach directly:

```sh
gdb
(gdb) set architecture armv5te
(gdb) target remote :3333
(gdb) info registers
```
