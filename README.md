# Mario Kart DS Modding Trove

A public-toolchain framework for Mario Kart DS ROM mods. It ships **reusable tools** and **independent mods**:

Maintained by [GolyBidoof](https://github.com/GolyBidoof).

```
tools/     shared framework (ROM readers, BMG repair, NCPatcher driver,
           mod loader)
mods/      self-contained mods
debug/     ROM-agnostic debug server, persistent RSP proxy, MKDS custom layer,
           GDB/Ghidra/native guides
docs/      reverse-engineered format and research notes
apply.py      one-command entry point
bootstrap.py  first-run tool bootstrap
```

Mods are independent: select any subset and the framework merges them into one NCPatcher pass. It refuses a run where two mods patch the same address or append the same BMG label.

No ROMs or BMG files are stored here: BMG content is read from the input ROM and written back through NCPatcher. Use a ROM you legally own. Mario Kart DS and Nintendo DS are trademarks of Nintendo; this project is not affiliated with or endorsed by Nintendo.

## AI disclosure

This repository was developed with substantial generative-AI involvement. Substantial portions of the framework code, tests, documentation and patch templates were drafted or rewritten by **DeepSeek v4.1 Flash** through the **Command Code** coding agent, under human direction and review. The patches have been built and structurally verified, but that is not a correctness or fitness guarantee. Review the code and test on an emulator or hardware before using a patched ROM.

AI systems are tools, not authors; the human contributors are named under [Credits](#credits). Contributions made with AI tools are welcome under the same disclosure rule.

## Quick start

You need Python 3.9+ and, on first run, an internet connection. Everything else is fetched or built automatically if it is missing.

```sh
python3 apply.py /path/to/game.nds
```

The patched ROM is written to `out/`. On macOS you can also double-click `run.command`; on Linux, `./run.sh game.nds`; on Windows, `run.bat game.nds`.

The first run builds NCPatcher from the latest `ncp_v2` branch and downloads the latest GNU Arm toolchain if `arm-none-eabi-gcc` is not already available. Run `python3 bootstrap.py --check` to see what was found.

## Compatibility

The patches apply to **any Mario Kart DS version** whose Options class row uses the stock layout. The tables and instruction sites are found by pattern, not by a hardcoded build, so EU, US and JP retail images are recognized. They also apply on top of an **already-modded `.nds`**: if the engine CC switch is already redirected, the engine source is skipped and the Options/BMG patches are applied as a delta, leaving the existing redirect byte-identical.

Apply to the original ROM, not to one of the tool's own outputs: profile detection expects the vanilla Options layout. An already-modded input is supported as long as it still has that layout.

The verifier checks tables, BMG bytes and branch targets; it does not run the game. Test a patched ROM in an emulator or on hardware before distributing it.

## Mods

| id | what it does | screenshot |
|---|---|---|
| `options-cc` | Appends 200cc / 250cc / 300cc to the Options class row and adds the localized class names to the ROM's BMGs. See `mods/options-cc/README.md`. | ![VS rules showing 250cc](mods/options-cc/options-250cc-rules.png) |

`options-cc` targets the Options list, not the 2×2 GP class-select tiles. It is the included example mod; new mods go under `mods/` and are selected with `--mod` or applied together with `--all-mods`.

The screenshot shows game content © Nintendo and is included only to document the patch.

## Tools

These are the reusable pieces. They work on the data structures documented in `docs/`, so they can be used outside this repository.

| Module | What it does | Data |
|---|---|---|
| `tools/nds.py` | NDS header/FNT/FAT, BLZ, NARC/CARC, LZ77 | Nitro ROM assets |
| `tools/bmg.py` | BMG reader, repair and label append | MESG/bmg1 `rule.bmg` |
| `tools/bmgset.py` | Per-language label planning and id allocation | BMG message banks |
| `tools/patch.py` | NCPatcher project, conflict checks, autoload-aware verification | ARM9 + archives |
| `tools/mods.py` | Mod discovery, selection and metadata | `mods/*/mod.json` |
| `tools/verify.py` | Small check helpers for mod verifiers | — |
| `debug/` | Recomp debug server: text protocol, GDB RSP (ARM9/ARM7), persistent RSP proxy, MKDS scene/screenshot layer, Ghidra and native guides | static recompilations |

Game-specific detection lives with the mod that needs it, e.g. `mods/options-cc/profile.py`; the generic tools do not encode any MKDS addresses.

If you are building a different MKDS tool, the NDS/NARC/BMG readers, the ARM9 autoload reader and the mod loader are the parts most likely to be reusable. The format notes are in `docs/`; matching generic C headers are in `include/`.

## Documentation

- [Nitro ROM formats](docs/nitro.md)
- [BMG message banks](docs/bmg.md)
- [ARM9 autoloads](docs/arm9-autoloads.md)
- [Options class row](docs/options-class-row.md)
- [Debug layers](debug/README.md) — generic, recomp and melonDS split
- [Recomp debug layer](debug/recomp/README.md) — text protocol, GDB RSP, screenshots and native C debugging
- [melonDS debug layer](debug/melonDS/README.md) — ports, single-attachment behavior and proxy
- [MKDS custom layer](debug/generic/mkds/README.md) — scene/menu navigation and recomp screenshots over the generic transports
- [Ghidra GDB bridge](debug/generic/ghidra/README.md) — `ghidragdb` setup, proxy connection
- C format headers: [`include/`](include/) — generic NDS/FNT/FAT, NARC/CARC/LZ77, BMG and BLZ headers. Mod-specific headers live with the mod, e.g. `mods/options-cc/source/options_class_row.h.tmpl`.

## External tools

The bootstrap uses the newest available upstream versions; no tool version is pinned here.

| Tool | Use | Licence |
|---|---|---|
| [NCPatcher](https://github.com/TheGameratorT/NCPatcher) (`ncp_v2`) | compile/link patches, patch the ROM and archive members | GPL-3.0 |
| [xPack GNU Arm Embedded GCC](https://github.com/xpack-dev-tools/arm-none-eabi-gcc-xpack) | portable `arm-none-eabi-gcc` if none is installed (latest release) | GPL-3.0 with GCC exception |
| [Arm GNU Toolchain](https://developer.arm.com/downloads/-/arm-gnu-toolchain-downloads) | upstream toolchain family | GPL-3.0 with GCC exception |
| [Python](https://www.python.org/) | run the framework | PSF-2.0 |

`Mario Kart Toolbox` is optional: the default pipeline reads Nitro archives directly, so `.NET` is not required. It remains useful for inspecting ROMs. Full links, licences and build-only tools are in [CREDITS.md](CREDITS.md).

## Usage

```sh
python3 apply.py /path/to/game.nds
python3 apply.py --rom-dir /path/to/roms --all-mods --out-dir out
python3 apply.py /path/to/game.nds --mod options-cc --dry-run
python3 bootstrap.py --check
```

`--mod` is repeatable and defaults to all mods. Outputs are `<name>_<mod ids>.nds`. Scratch files live under `OUT/.work` and are removed on success; `--keep-work` keeps the rendered sources and intermediates.

## Writing a mod

A mod is a directory under `mods/`:

```
mods/my-mod/
  mod.json
  profile.py
  source/
    mymod.h.tmpl
    mymod.c.tmpl
    engine.s.tmpl      # optional
  messages/
    default.json
    es.json
  verify.py
  README.md
```

`.tmpl` files are templates: `{{placeholders}}` are replaced by `tools/patch.py` and the result is compiled as a normal `.c` or `.s` file. The renderer writes each mod to its own `source/<mod id>/` directory, so a local header can be included by name (`#include "mymod.h"`). This keeps the patch readable and avoids generated source in the repo.

`profile.py` must expose `detect(arm9, base)` and return a dataclass or dict. Its fields become `{{profile.<field>}}` placeholders; the flat `<field>` form is also available for `when` conditions. This is where game-specific address searching belongs.

`messages/` holds the BMG labels. `default.json` is required; other files are selected by the archive language (`es.json` for `Menu_es`, `ja.json` for `Menu_ja`, and so on). Each file is `{"labels": ["..."]}`.

`mod.json`:

```json
{
  "id": "my-mod",
  "name": "My mod",
  "description": "One line.",
  "profile": "profile.py",
  "sources": [
    {"file": "source/mymod.h.tmpl"},
    {"file": "source/mymod.c.tmpl"},
    {"file": "source/engine.s.tmpl", "when": {"engine_mode": "patch"}}
  ],
  "bmg": {
    "archives": "data/Scene/Menu*.carc",
    "member": "rule.bmg",
    "messages": "messages",
    "language_prefixes": ["MenuDL_", "Menu_"]
  },
  "verify": "verify.py"
}
```

The BMG step reads the input ROM's own archives, strips any previous copy of the labels, and appends them at the next ids through NCPatcher. No BMG file is stored in the repo.

Available `{{profile.*}}` placeholders come from the mod's profile object. For `options-cc` the table fields are `arm9_base`, `main_end`, `row_count`, `msg_ptr`, `option_to_cc`, `cc_to_option`, `unlock_a`, `unlock_b`, `mirror_load`, `mirror_compare`, `stock_ids`, `engine_mode`, `engine_hook`, `engine_config`, `engine_resume`, `engine_word`; the engine values are `max_speed_50`…`max_speed_300`, `max_speed_*_q12`, `drift_50`…`drift_300`, `drift_50_mvn`, `drift_100_mvn` (see `mods/options-cc/engine.json`). Also: `new_ids`, `new_ids_json`, `new_id0`, `new_id1`, `new_id2`.

`{{new_ids}}` is this mod's comma-separated BMG label ids, assigned after all selected mods' labels are planned; `{{new_id0}}`… are the individual ids. `verify.py` gets a context with `profile`, `image`, `base`, `new_ids`, `tools` and `u16()`/`u32()` readers; use `tools.verify.check(condition, message)`.

A mod should only touch addresses and labels it owns. The runner rejects overlaps before building.

## Requirements

- Python 3.9+
- A GCC toolchain: `arm-none-eabi-gcc` on `PATH`, `DEVKITARM`/`DEVKITPRO`, `ARM_GCC`/`ARM_TOOLCHAIN`, or the auto-downloaded xPack release.
- First run only: `git`, CMake, a C++20 compiler (for NCPatcher) and internet access, unless NCPatcher and the toolchain are already installed.
- Override locations with `NCPATCHER`, `NCPATCHER_SDK`, `ARM_GCC`, `ARM_TOOLCHAIN`, `DEVKITARM`/`DEVKITPRO` or `PATH`.

### Toolchain and headers

These patch units are not homebrew programs: they are linked into the retail ARM9. Use NCPatcher's `ncp.h`, `<stdint.h>` and the mod's own headers. Do not include libnds/devkitARM headers (`<nds.h>`, `nds/arm9/...`) in patch units: they assume a homebrew runtime, IRQ setup and ABI that the retail game does not provide, and can conflict with the game's structs and symbols.

An existing devkitARM installation is used as the compiler if `DEVKITARM`/`DEVKITPRO` is set; its libnds headers are not used. libnds' `u8`/`u16`/`u32`/`f32` names are aliases for the same EABI types (`uint8_t`/`uint16_t`/`uint32_t`/`float`); the patch uses the standard names directly and does not include libnds.

## AI-assisted contributions

Contributions made with generative AI tools are welcome. Disclose the tools used in the pull request or commit message, keep the change reviewable, and make sure you have the right to contribute the code and any assets. Every contribution is reviewed for correctness, licensing and provenance. The project itself was developed with substantial AI involvement; see [AI disclosure](#ai-disclosure).

## Credits

- Maintainer: [GolyBidoof](https://github.com/GolyBidoof)
- AI disclosure: substantial AI involvement; see [AI disclosure](#ai-disclosure) and [CREDITS.md](CREDITS.md).
- Recompilation/debug origin: [DS-Kart-Recompiled](https://github.com/AlonsoTlol/DS-Kart-Recompiled)
- Format references, tool authors, licences and links: [CREDITS.md](CREDITS.md).

## Contributors and privacy

The project maintainer is [GolyBidoof](https://github.com/GolyBidoof).

Out of respect for community members and researchers who do not want to be associated with generative AI tooling, other individual contributors have asked to deliberately not be named. This project honors that request and does not list them.

## Tests

```sh
python3 -m unittest discover -s tests
```

The tests build a synthetic BMG in code; they never read a game file. CI runs them on Python 3.9 and 3.12.

## Licence

MIT. See `LICENSE`. Third-party notices and the DS-Kart-Recompiled MIT text are in `CREDITS.md` and `LICENSES/`.
