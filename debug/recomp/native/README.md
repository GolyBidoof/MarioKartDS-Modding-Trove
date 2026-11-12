# Native C debugging

This is the process-level debugger path. It is deliberately separate from the emulated ARM GDB stub:

| Path | What it debugs | How to attach |
|---|---|---|
| `debug/recomp/native/` | the recompiled host C code | lldb/gdb on the process |
| `debug/recomp/src/` (RSP) | ARM9/ARM7 instructions | `arm-none-eabi-gdb` / IDA / Ghidra on `DBG_GDB_PORT` |
| `debug/recomp/client/` | scripted high-level control | Python client / scenarios |

You can use both at once, but they pause different things: lldb stops the host process, while the RSP stub stops the emulated CPU. Do not expect one to resume the other.

## Build with debug information

Build the recompilation with host debug info (`-g`, preferably `-O0` for the generated C). The exact flag varies by build system; the important part is that the generated `d_<function>` symbols and source line information survive.

## Open the native debugger

```sh
debug/recomp/native/debug.sh ./build/myrecomp
debug/recomp/native/debug.sh ./build/myrecomp anim_initManager
```

Inside lldb:

```text
(lldb) br s -n d_anim_initManager
(lldb) run
(lldb) bt
(lldb) frame variable
(lldb) p *c
```

Inside gdb:

```text
(gdb) break d_anim_initManager
(gdb) run
(gdb) bt
(gdb) info locals
(gdb) p *c
```

Native breakpoints are host-C breakpoints. They do not use the emulated instruction stream and do not require `DBG_PORT`/`DBG_GDB_PORT`.

## Emulated instruction debugging

For ARM9/ARM7 instructions, use the RSP server in the parent `debug/` folder:

```sh
DBG_GDB_PORT=19851 ./build/myrecomp       # ARM9
DBG_GDB_PORT7=19852 ./build/myrecomp      # ARM7
arm-none-eabi-gdb
(gdb) target remote :19851
```

The two interfaces are intentionally separate: native lldb/gdb is best for C control flow and host data, while the RSP stub is best for emulated registers, memory, translated-function breakpoints and instruction-level state.

## Optional native helpers

The original `DS-Kart-Recompiled` tree also had helpers such as `dbg_regs`, `dbg_stack`, `dbg_mem`, and a generated symbol table. Those are recompilation-specific; copy them from that runtime if you want them. They are not required for native lldb/gdb, which can inspect the host C variables directly.
