# Debug workflows

> **Project:** Mario Kart DS Modding Trove · **Licence:** MIT

Practical recipes for the debug layers. The generic transports work with the
static recompilation, melonDS, or any GDB RSP target. Input and screenshots
need a backend that provides them.

## Pick the right channel

| Need | Channel |
|---|---|
| Pause/resume, frame wait, input, screenshots, snapshots | recomp text protocol |
| CPU registers, memory, breakpoints, step, call | GDB RSP |
| Keep one target attached across many clients | RSP proxy |
| Ghidra live view | Ghidra GDB agent → proxy or RSP |
| Native host-C stack | lldb/gdb (not either debug port) |

Do not try to inject input or take screenshots over RSP: RSP exposes CPU memory,
not the frontend's composited frame or the input queue.

## Start a target

Set the ports in the target's environment:

```sh
export DBG_PORT=19850        # text protocol
export DBG_GDB_PORT=19851    # ARM9 RSP
export DBG_GDB_PORT7=19852   # ARM7 RSP
```

The aliases `MKDS_DBG_PORT`, `MKDS_GDB_PORT` and `MKDS_GDB_PORT7` are accepted
by the recomp server. A typical launch:

```sh
MKDS_DEBUG=1 \
MKDS_DBG_PORT=19850 \
DBG_GDB_PORT=19851 \
DBG_GDB_PORT7=19852 \
sh linux/play.sh
```

The text server only opens when a text port is set. The RSP listeners only open
when their port variables are set.

## Attach with the trove tools

Read scene/menu state:

```sh
python3 debug/generic/mkds/cli.py --backend recomp --port 19850 status
python3 debug/generic/mkds/cli.py --backend recomp --port 19850 scene
python3 debug/generic/mkds/cli.py --backend recomp --port 19850 menu
```

Keep one RSP attachment and let several clients share it:

```sh
python3 debug/generic/transport/rsp_proxy.py --upstream 19851 --listen 19861
python3 debug/generic/mkds/cli.py --backend rsp --port 19861 status
```

GDB:

```sh
gdb -q \
  -ex 'set architecture armv5te' \
  -ex 'target remote :19861'
```

Ghidra: connect its GDB agent to the proxy port; see
[`generic/ghidra/README.md`](generic/ghidra/README.md).

## Run a scripted flow

`run_scenario.py` launches a recomp with a free text port and runs a Python
scenario:

```sh
python3 debug/recomp/client/run_scenario.py \
  --binary /path/to/recomp/build/stock/mkds \
  --cwd /path/to/recomp \
  --env MKDS_VARIANT=stock \
  --env MKDS_ROM=/path/to/game.nds \
  --env MKDS_RCM_DIR=build/stock \
  --env MKDS_DBG_SYMBOLS=build/stock/dbg_symbols.txt \
  debug/examples/menu_flow.py
```

The scenario imports `Debugger` from `dbg_client` and uses `DBG_PORT`:

```python
from dbg_client import Debugger

with Debugger() as d:
    d.pause()
    d.command("scene 1")
    d.wait(45)
    print(d.command("menu"))
    d.screenshot_both("dbg_mode_select.bmp")
    d.snapshot("mode_select")
```

## Assert on memory, not just screenshots

```python
before = d.read32(0x02000000, 4)
d.press("A", 2)
d.wait(30)
after = d.read32(0x02000000, 4)
assert after != before
```

Snapshots and diffs are useful for side-effect checks:

```python
d.snapshot("before")
# ... run the flow ...
print(d.diff("before"))
```

`screenshot_both()` captures 256×384; `screenshot_upper/lower` capture 256×192.
Use `both` when a menu spans both screens. Keep a control run and compare the
two captures rather than judging one frame in isolation. The generic diff is
`tools.bmp.compare(a, b, threshold=0)`; `tools.bmp.save_diff` writes a red/grey
diff image.

## Find and verify a patch site

Use the shared readers instead of hard-coded addresses:

```python
from tools.arm import thumb_bl_target
from tools.nds import overlay_from_nds

ram, ov = overlay_from_nds("game.nds", 1)

signature = bytes.fromhex("01 28 02 d0 02 28 05 d0")
pos = ov.find(signature)
assert pos >= 0 and ov.find(signature, pos + 1) < 0

site = ram + pos
target = thumb_bl_target(site, ov)
print(f"site {site:#010x} calls {target:#010x}")
```

Then verify the written ROM the same way: re-open the output, read the same
overlay, and assert the patched bytes. `mods/options-cc/` is a worked
example.

## Field notes

- **A proxy attach can pause the target.** Start the RSP proxy only when a
  debugger needs it. If local detach leaves the target paused, resume it through
  the text server or send the resume packet explicitly.
- **Breakpoints stop at function entry.** The recomp executes translated
  functions, not individual instructions. Report the function entry as the
  current PC; do not expect line-level stepping.
- **Wait for animations.** A press that lands during a transition can be
  ignored. Poll the menu state and repeat after 15–90 frames if needed.
- **Do not trust a menu default.** Grid menus can remember the last cursor
  position. Navigate from a known corner to the target row, or read the cursor
  index first.
- **Back is not always `B`.** Touch-screen back arrows are often the reliable
  cancel path.
- **Screenshots are evidence, not proof.** Pair a visual check with a memory
  assertion, and compare against a control run.
- **Keep the target warm.** Build once, attach, and run many scenarios; avoid
  rebuilding or re-translating between ordinary debug iterations.
- **Mid-function resumes are a recompiler gap.** A patch that jumps back into
  the middle of a translated function can stop at “falta código traducido”
  even when the ROM bytes are correct. Test those patches on a real emulator,
  or restructure the hook to resume at a function entry.

## Example

[`examples/menu_flow.py`](examples/menu_flow.py) pauses, skips to the menu,
asserts the mode-select state, captures both screens, and prints the menu after
one navigation step.
