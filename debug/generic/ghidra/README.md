# Ghidra GDB bridge

Ghidra 12.2+ includes the Debugger and the `Debugger-agent-gdb` module. The GDB-side package is `ghidragdb`; it is a Python plugin loaded by a GDB built with Python support.

## CLI

There is no `ghidra-cli` in the Ghidra distribution. `support/analyzeHeadless` is the headless CLI for importing/analyzing programs and running Ghidra scripts. The live Debugger/Trace RMI connection is a GUI tool, so it is not driven by `analyzeHeadless`.

## Requirements

- Ghidra 12.2+ with the Debugger modules (bundled).
- A GDB with Python. Homebrew `gdb` works; the devkitARM `arm-none-eabi-gdb` is built `--without-python` and cannot load `ghidragdb`.
- The `ghidragdb` and `ghidratrace` wheels from Ghidra's modules installed into that GDB's Python environment.

## Install the GDB plugin

The wheels are under the Ghidra installation:

```text
Ghidra/Debug/Debugger-rmi-trace/pypkg/dist/ghidratrace-<version>-py3-none-any.whl
Ghidra/Debug/Debugger-agent-gdb/pypkg/dist/ghidragdb-<version>-py3-none-any.whl
```

Install them with the Python that GDB uses:

```sh
python3 -m pip install \
  Ghidra/Debug/Debugger-rmi-trace/pypkg/dist/ghidratrace-*.whl \
  Ghidra/Debug/Debugger-agent-gdb/pypkg/dist/ghidragdb-*.whl
```

Check it from GDB:

```sh
gdb -q -batch -ex 'python import ghidragdb; print("ok")'
```

## Keep melonDS attached

melonDS accepts one GDB attachment per emulator run. Put the persistent proxy in front of it:

```sh
python3 debug/generic/transport/rsp_proxy.py --upstream 3333 --listen 3335
```

Now Ghidra and the custom layer can both use `localhost:3335`; disconnecting either does not detach melonDS.

## Connect

In Ghidra: **Debugger → Connect → GDB remote**, host `localhost`, port `3335`. Use the GDB binary with Python if the launcher asks for a GDB path.

For the recomp RSP listener, use the same proxy shape:

```sh
python3 debug/generic/transport/rsp_proxy.py --upstream 19851 --listen 19861
```

The custom scene/menu layer can use the proxy independently:

```sh
python3 debug/generic/mkds/cli.py --backend rsp --port 3335 menu
python3 debug/generic/mkds/cli.py --backend rsp --port 3335 scene
```

The proxy does not forward local `D`/`k`/`vKill` upstream, so Ghidra can disconnect and reconnect without losing the melonDS attachment.

## Scope

Ghidra sees the emulated CPU memory and registers through RSP. Composed screenshots are not exposed by the melonDS RSP target; use the recomp text backend for those.
