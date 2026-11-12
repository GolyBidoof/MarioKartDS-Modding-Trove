# Contributing and development patterns

This file is the durable guide for humans and AI agents working in this repository. The goal is to keep the framework generic, the mods independent, and every finding reusable.

## Repository layers

- `tools/` contains generic Nitro/BMG/NCPatcher/mods code. It must not contain MKDS-specific addresses or labels.
- `mods/<id>/` contains everything specific to one mod: `mod.json`, `profile.py`, templates, BMG catalogs, verifier, and README.
- `include/nitro/` contains host-compilable C declarations of generic data structures. It must not contain game data or mod-specific tables.
- `docs/` contains reverse-engineered formats, observations, provenance, and reuse notes.
- `debug/generic/` applies to recomp and melonDS: transport, proxy, MKDS custom layer, Ghidra notes.
- `debug/recomp/` is recomp-only: server, text client, screenshots, native C debugging.
- `debug/melonDS/` is melonDS-only: ports, configuration, single-attachment behavior.
- `tests/` contains synthetic/unit tests and format/compile guards.

## Where a change belongs

- A new format or layout observation goes in `docs/` with a metadata header, offsets, observed values, how it was found, and a reuse note.
- A new generic structure or constant goes in `include/nitro/` with a `_Static_assert` for size/offset and coverage in `tests/test_headers.py`.
- A reusable operation goes in `tools/` with a generic API, no MKDS addresses, and a synthetic test in `tests/`.
- A game-specific address, pattern, unlock rule, menu name, or engine value goes in the owning mod's `profile.py`, `engine.json`, or templates, not in `tools/`.
- A new mod gets a complete `mods/<id>/` directory: `mod.json`, profile, source templates, BMG messages, verifier, README, and a root README table row.
- Menu input sequences, animation waits, retries, and navigation findings go in `debug/generic/mkds/NAVIGATION.md` and `routes.json`. Keep both in sync.
- A debug behavior that works for both targets goes in `debug/generic/`; a recomp-only behavior goes in `debug/recomp/`; a melonDS-only detail goes in `debug/melonDS/`.
- A screenshot belongs with the feature it documents, at native resolution where possible. Note any Nintendo game content explicitly.

## Constraints

- Use public tools only: NCPatcher, `arm-none-eabi-gcc`, Python standard library, and optional Mario Kart Toolbox for inspection.
- Do not add ROM files, internal game files, archives, extracted game assets, or project-specific headers.
- Do not move build-specific patchers, address tables, or toolchain files into the generic framework.
- Do not move MKDS-specific knowledge into `tools/` merely for convenience. If two mods need it, give each mod its own profile/data or add a documented generic format layer.
- Use EABI fixed-width types from `<stdint.h>` in C. Do not include libnds headers in patch units.
- Name C concepts, not registers. Put raw instruction encodings in assembly or research docs and explain them there.
- Keep emitted patch constants derived from the mod's data (for example `engine.json` floats converted to Q12 at build time).
- Comments only where the behavior is non-obvious: ABI repair, address fixups, formula scale, or an instruction-site quirk.
- Never commit generated output, caches, screenshots without a documentation purpose, or local absolute paths.

## Mod independence

A mod owns its addresses, BMG labels, verifier, and documentation. The runner rejects two selected mods that patch the same address or append the same BMG label. When adding a mod, prove it works alone and with `--all-mods`; do not rely on another mod's tables being present.

## Debug and automation patterns

- Keep one long-lived session per target. For melonDS, use `debug/generic/transport/rsp_proxy.py` because its GDB stub accepts one upstream attachment.
- Record input order as data in `routes.json`, not only in prose. Include frame counts, retries, and observed menu states.
- Test animation waits. Re-read `menu` after a transition; a press can be consumed while an animation is running.
- Do not force a menu state directly when the game requires scene setup; navigate through the natural path.
- Screenshots are native/full per screen where the backend supports it. RSP targets expose CPU memory, not the composited framebuffer.

## Validation and definition of done

Run before committing:

```sh
python3 -m unittest discover -s tests
make -C debug/recomp check
python3 -m py_compile debug/recomp/client/*.py debug/generic/transport/*.py debug/generic/mkds/*.py debug/recomp/mkds/*.py
```

A change is ready when:

- Tests pass and new behavior has a test or an explicit manual verification note.
- Relevant docs, READMEs, tables, and route JSON are updated.
- Markdown/image links resolve.
- No ROMs, BMGs, archives, caches, build outputs, `.DS_Store`, or absolute paths are staged.
- Third-party code has its notice in `LICENSES/` and `CREDITS.md`.
- AI-assisted work follows the disclosure in the README.
- The root README or the owning mod README states where the behavior is visible, with a screenshot when it is a UI change.

## Documentation style

Keep paragraphs and list continuations on one line; use blank lines only to separate blocks. Preserve fenced code, tables, and list structure. Update `docs/README.md` when adding a new research document.
