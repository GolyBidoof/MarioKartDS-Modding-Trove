# Credits

## AI disclosure

This repository was developed with substantial generative-AI involvement. Substantial portions of the code, tests, documentation and patch templates were drafted or rewritten by **DeepSeek v4.1 Flash** through the **Command Code** coding agent, under human direction and review.

AI systems are tools, not authors; the human contributors are named below. The patches have been built and structurally verified, but this is not a correctness or fitness guarantee.

- **DeepSeek v4.1 Flash** — [deepseek.com](https://www.deepseek.com/)

## Core tools

| Tool | Licence | Link |
|---|---|---|
| NCPatcher (`ncp_v2`) | GPL-3.0 | https://github.com/TheGameratorT/NCPatcher |
| xPack GNU Arm Embedded GCC | GPL-3.0 with GCC exception | https://github.com/xpack-dev-tools/arm-none-eabi-gcc-xpack |
| Arm GNU Toolchain | GPL-3.0 with GCC exception | https://developer.arm.com/downloads/-/arm-gnu-toolchain-downloads |
| Python | PSF-2.0 | https://www.python.org/ |
| Git | GPL-2.0 | https://git-scm.com/ |
| CMake | BSD-3-Clause | https://cmake.org/ |
| Ninja (optional) | Apache-2.0 | https://ninja-build.org/ |
| GNU Make (optional) | GPL-3.0 | https://www.gnu.org/software/make/ |
| C++20 compiler (Apple Clang, GCC or MSVC) | Apache-2.0 with LLVM exception / GPL-3.0 / proprietary | https://clang.llvm.org/ · https://gcc.gnu.org/ · https://visualstudio.microsoft.com/ |

## Optional tools

| Tool | Licence | Link |
|---|---|---|
| Mario Kart Toolbox | MIT | https://github.com/HaroohiePals/MarioKartToolbox |
| .NET (only if using the Toolbox CLI) | MIT | https://dotnet.microsoft.com/ |
| devkitPro devkitARM (optional toolchain) | component licences (GCC/binutils/newlib/libnds) | https://devkitpro.org/ |
| Ghidra (optional GUI debugger/GDB agent) | Apache-2.0 | https://ghidra-sre.org/ |

The default pipeline reads Nitro archives directly, so Mario Kart Toolbox and .NET are not needed. Mario Kart Toolbox remains useful for inspecting ROMs and its data model informed the archive and BMG tools.

The Python framework uses only the standard library; there are no third-party Python packages.

## Format references

The generic headers and format notes are independent declarations of publicly documented Nitro/NDS layouts. No code from these projects is included.

- **GBATEK** (Martin Korth) — NDS header, FNT/FAT, overlays and compression: https://problemkaputt.de/gbatek.htm
- **ndstool** (devkitPro) — NDS/NitroFS filesystem tooling: https://github.com/devkitPro/ndstool
- **Mario Kart Toolbox** (HaroohiePals) — archive and BMG data model: https://github.com/HaroohiePals/MarioKartToolbox
- **NCPatcher** (TheGameratorT) — Nitro archive patching: https://github.com/TheGameratorT/NCPatcher

The Options/engine addresses and byte patterns are this project's observations, documented in `docs/options-class-row.md`; they are not copied from a symbol file or another mod.

## Debug layer

The debug server/client in `debug/` was extracted from `DS-Kart-Recompiled` (MIT, Copyright (c) 2026 alontube) and generalized for reuse. The original license text is in [`LICENSES/DS-Kart-Recompiled-MIT.txt`](LICENSES/DS-Kart-Recompiled-MIT.txt). The GDB Remote Serial Protocol behavior is modeled on melonDS's GDB stub.

- **DS-Kart-Recompiled** — origin of the debug layer: https://github.com/AlonsoTlol/DS-Kart-Recompiled
- **melonDS GDB stub** (protocol reference) — https://github.com/melonDS-emu/melonDS

## Contributors

- **GolyBidoof** — project author and maintainer: https://github.com/GolyBidoof

Other contributors have asked to remain unnamed; see the "Contributors and privacy" note in [README.md](README.md).
