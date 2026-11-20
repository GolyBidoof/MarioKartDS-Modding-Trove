# Tooling API

> **Project:** Mario Kart DS Modding Trove · **Licence:** MIT

Reusable helpers for ROM readers and patch profiles. They are deliberately
small and dependency-free so they can be used by a mod profile, a verifier, or
a standalone script.

## NDS overlay reader

```python
from tools.nds import overlay_from_nds

ram, data = overlay_from_nds("game.nds", 1)
```

`overlay_from_nds(path, overlay_id)` returns:

- `ram` — the overlay's load address;
- `data` — the overlay bytes, already BLZ-decompressed when the overlay-table
  compressed flag is set.

The bytes are addressed as `runtime_address - ram`. A missing overlay raises
`ValueError`.

Why this exists: overlay tables are separate from the ARM9 image, and the load
address changes by region. Hard-coding a base works for one image and silently
corrupts another. The reader uses the ROM's own table every time.

Minimal example:

```python
from tools.nds import overlay_from_nds

ram, data = overlay_from_nds("game.nds", 1)
address = 0x021855CC
print(data[address - ram:address - ram + 8].hex())
```

## Thumb BL decoder

```python
from tools.arm import thumb_bl_target

target = thumb_bl_target(0x021855D0, bytes.fromhex("1bf0f8fd"))
# 0x021A11C4
```

`thumb_bl_target(address, data, offset=0)` decodes the 32-bit Thumb `BL` at
`data[offset:offset+4]`. `address` is the runtime address of the `BL` itself.
It returns the branch target.

This is for patch profiles that need to follow a call without a symbol file. It
decodes `BL` only, not `BLX` or literal-pool loads; check the instruction class
before using it.

## DWC utility archive reader

```python
from tools import dwc_utility

data = open("utility.bin", "rb").read()
files = dwc_utility.verify(data)
for entry in files:
    print(entry.file_id, entry.path, entry.size)
```

`tools/dwc_utility.py` parses the NARC-less DWC envelope (16-byte header,
Nitro FNT, Nitro FAT) and walks the directory tree. `verify()` also checks
that every FAT range is reachable and non-overlapping. The CLI has `list`,
`verify` and `extract`:

```sh
python3 tools/dwc_utility.py list utility.bin
python3 tools/dwc_utility.py verify utility.bin
python3 tools/dwc_utility.py extract utility.bin -o out/dwc
```

Extracted payloads are considered derived data and stay under `out/`.

## Writing an overlay mod profile

A profile receives the decompressed ARM9 bytes and the image base:

```python
def detect(arm9, base, rom_path=None):
    ...
```

`rom_path` is optional for profiles that only need ARM9. When present, use the
overlay reader:

```python
from tools.arm import thumb_bl_target
from tools.nds import overlay_from_nds

def detect(arm9, base, rom_path=None):
    ram, ov = overlay_from_nds(rom_path, 1)
    pos = ov.find(bytes.fromhex("01 28 02 d0 02 28 05 d0"))
    if pos < 0 or ov.find(bytes.fromhex("01 28 02 d0 02 28 05 d0"), pos + 1) >= 0:
        raise RuntimeError("signature not found or not unique")
    hook = ram + pos - 8
    update = thumb_bl_target(hook + 4, ov, pos - 4)
    return {"overlay_ram": ram, "hook": hook, "update": update}
```

Rules that keep profiles reliable:

1. Prefer a signature that includes surrounding instructions, not a single
   constant.
2. Reject a signature that occurs more than once.
3. Validate the original bytes at every patch site.
4. Return runtime addresses; let the template render them.
5. In `verify.py`, re-open the output ROM with the same overlay reader and check
   the written bytes again.

## Screenshot diff

```python
from tools import bmp

result = bmp.compare("mirror.bmp", "control.bmp", threshold=8)
print(result["changed_pixels"], result["changed_ratio"], result["bbox"])
bmp.save_diff("mirror.bmp", "control.bmp", "diff.bmp", threshold=8)
```

`compare()` returns `same_size`, `changed_pixels`, `changed_ratio`,
`max_delta`, `mean_delta`, a bounding box, and `equal`. `save_diff()` writes a
24-bit BMP with changed pixels in red and identical pixels grey.

Use a control run of the same scene when judging a change; a single frame in
isolation is not a regression test.

## Overlay sources in a mod

The NCPatcher project generator maps source paths to regions:

```text
mods/my-mod/source/main/foo.c.tmpl   -> dest: main
mods/my-mod/source/ov1/bar.c.tmpl    -> dest: ov1
mods/my-mod/source/my_header.h.tmpl  -> include-only
```

Only `.c` and `.s` files are listed as compiler inputs; rendered headers are
written beside the sources and are found through the normal include path. A
`mod.json` entry is just the source list:

```json
{
  "id": "my-mod",
  "profile": "profile.py",
  "sources": [
    {"file": "source/main/foo.c.tmpl"},
    {"file": "source/ov1/bar.c.tmpl"},
    {"file": "source/my_header.h.tmpl"}
  ]
}
```

Code in `source/ov1` is appended to overlay 1 by NCPatcher, and the overlay
table is updated automatically. Use `ncp_hook(address, 1)` /
`ncp_thook(address, 1)` from that file, or from a main source when only the
bridge needs to sit in the overlay.

## Related readers

- `tools.nds.arm9_from_nds(path)` — decompressed ARM9 bytes and base.
- `tools.nds.blz_decompress(data)` — BLZ decompression.
- `tools.nds.lz77_decompress(data)` — LZ77 decompression.
- `tools.nds.narc_members(data)` — NARC member map.

The mod framework itself lives in `tools/patch.py` (`ncp_jump`, `ncp_call`,
`ncp_hook`, overlay regions, conflict checks) and is documented in the
[NCPatcher patch reference](https://github.com/TheGameratorT/NCPatcher/blob/master/docs/patches.md).

## Region regression test

The real-ROM profile check is opt-in:

```sh
MKDS_TEST_ROMS=/path/to/roms python3 -m unittest tests.test_regions -v
```

It reads `Europe.nds`, `US.nds` and `Japan.nds` when present and asserts the
derived overlay base and menu sites.

