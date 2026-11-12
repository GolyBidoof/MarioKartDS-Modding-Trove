# Mario Kart DS Modding Trove

A public-toolchain framework for Mario Kart DS ROM mods: reusable Nitro/BMG/NCPatcher tools, independent mods, and a ROM-agnostic debug layer. Maintained by [GolyBidoof](https://github.com/GolyBidoof).

```text
tools/        shared framework: ROM readers, BMG repair, NCPatcher driver, mod loader
mods/         self-contained mods
debug/        debug server, RSP transport/proxy, MKDS layer, GDB/Ghidra/native guides
docs/         format and research notes
include/      reusable C format headers
apply.py      one-command entry point
bootstrap.py  first-run tool bootstrap
```

Mods are independent: select any subset and the framework merges them into one NCPatcher pass. It refuses a run where two mods patch the same address or append the same BMG label.

No ROMs or BMG files are stored here. BMG content is read from the input ROM and written back through NCPatcher. Use a ROM you legally own. Mario Kart DS and Nintendo DS are trademarks of Nintendo; this project is not affiliated with or endorsed by Nintendo.

## AI disclosure

This repository was developed with substantial generative-AI involvement. Substantial portions of the framework code, tests, documentation and patch templates were drafted or rewritten with AI assistance, under human direction and review. The patches have been built and structurally verified, but that is not a correctness or fitness guarantee. Review the code and test on an emulator or hardware before using a patched ROM.

AI systems are tools, not authors; the human contributors are named under [Credits](#credits). Contributions made with AI tools are welcome under the same disclosure rule.

## Quick start

You need Python 3.9+ and, on first run, an internet connection. Everything else is fetched or built automatically if missing.

```sh
python3 apply.py /path/to/game.nds
```

The patched ROM is written to `out/`. On macOS you can double-click `run.command`; on Linux, `./run.sh game.nds`; on Windows, `run.bat game.nds`. Run `python3 bootstrap.py --check` to see what was found. The first run builds NCPatcher and downloads a GNU Arm toolchain if `arm-none-eabi-gcc` is not already available.

## Compatibility

The patches apply to any Mario Kart DS version whose Options class row uses the stock layout. Tables and instruction sites are found by pattern, not by a hardcoded build, so EU, US and JP retail images are recognized. They also apply on top of an already-modded `.nds`: if the engine CC switch is already redirected, the engine source is skipped and the Options/BMG patches are applied as a delta, leaving the existing redirect byte-identical.

Apply to the original ROM, not to one of the tool's own outputs. The verifier checks tables, BMG bytes and branch targets; it does not run the game. Test a patched ROM in an emulator or on hardware before distributing it.

## Mods

| id | what it does | screenshot |
|---|---|---|
| `options-cc` | Appends 200cc / 250cc / 300cc to the Options class row and adds localized class names to the ROM's BMGs. See `mods/options-cc/README.md`. | ![VS rules showing 250cc](mods/options-cc/options-250cc-rules.png) |

`options-cc` targets the Options list, not the 2×2 GP class-select tiles. It is the example mod; new mods go under `mods/` and are selected with `--mod` or joined with `--all-mods`. The screenshot shows game content © Nintendo and is included only to document the patch.

## Usage

```sh
python3 apply.py /path/to/game.nds
python3 apply.py --rom-dir /path/to/roms --all-mods --out-dir out
python3 apply.py /path/to/game.nds --mod options-cc --dry-run
```

`--mod` is repeatable and defaults to all mods. Outputs are `<name>_<mod ids>.nds`. Scratch files live under `OUT/.work` and are removed on success; `--keep-work` keeps them.

## Development

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for the module layout, where findings and headers belong, mod conventions, debug-route rules, and the definition of done.

Requirements are Python 3.9+ and `arm-none-eabi-gcc` on `PATH`, via `DEVKITARM`/`DEVKITPRO`, or via `ARM_GCC`/`ARM_TOOLCHAIN`; otherwise the bootstrap downloads xPack. The first run also needs `git`, CMake, a C++20 compiler and internet access unless NCPatcher and the toolchain are already installed. Locations can be overridden with `NCPATCHER`, `NCPATCHER_SDK`, `ARM_GCC`, `ARM_TOOLCHAIN`, `DEVKITARM`/`DEVKITPRO` or `PATH`.

Patch units link into the retail ARM9. Use NCPatcher's `ncp.h`, `<stdint.h>` and the mod's own headers. Do not include libnds/devkitARM headers in patch units: they assume a homebrew runtime, IRQ setup and ABI that the retail game does not provide.

## Documentation

- [Format notes](docs/README.md)
- [Debug layers](debug/README.md)
- [Ghidra GDB bridge](debug/generic/ghidra/README.md)
- [C format headers](include/)
- [Contributing patterns](CONTRIBUTING.md)

## Tests

```sh
python3 -m unittest discover -s tests
```

The tests build a synthetic BMG in code; they never read a game file. CI runs them on Python 3.9 and 3.12.

## Credits

Maintainer: [GolyBidoof](https://github.com/GolyBidoof). Debug-layer origin: [DS-Kart-Recompiled](https://github.com/AlonsoTlol/DS-Kart-Recompiled). Format references, tool authors, licences and full AI disclosure: [CREDITS.md](CREDITS.md).

## Licence

MIT. See `LICENSE`. Third-party notices and the DS-Kart-Recompiled MIT text are in `CREDITS.md` and `LICENSES/`.
