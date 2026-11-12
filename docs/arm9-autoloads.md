# ARM9 autoloads

> **Project:** Mario Kart DS Modding Trove · **Licence:** MIT · **Code:** `tools/nds.py`

NDS ARM9 images can carry a module-params block and an autoload list. NCPatcher uses them to place a patch in free RAM; the verifier uses them to read the result.

## Module params

Find the magic `0xDEC00621 0x2106C0DE` near the end of the decompressed image. The module-params block starts at `magic_position - 0x1C`. Fields used here:

| Offset | Field |
|---|---|
| +0x00 | autoload list start (RAM) |
| +0x04 | autoload list end (RAM) |
| +0x08 | autoload payload start (RAM) |
| +0x0C | static BSS start |
| +0x10 | static BSS end |
| +0x14 | compressed static end |

`compressed_static_end` is a RAM address. If it is non-zero, the image is BLZ-compressed up to `compressed_static_end - arm9_base`; everything after that is stored plain. After decompressing, the field is zeroed so the runtime does not decompress it again.

## Autoload list

Entries are 12 bytes: `address`, `size`, `bss_size`. The payloads are stored one after another starting at `autoload_start - arm9_base`; an entry's data offset is implicit (the sum of the sizes before it). `bss_size` bytes of zero-initialised RAM follow the entry.

## Runtime address mapping

A patch pointer is a runtime address, and its bytes may not be at `address - base`:

- Main image (`base <= address < autoload_start`): file offset `address - base`.
- Autoload: find the entry whose `[address, address + size)` contains the address; file offset `payload + (address - entry.address)`.
- BSS is not stored; `Arm9Image` does not map BSS addresses.

`tools/nds.py` exposes this as `Arm9Image.offset()`, `u16()` and `u32()`. The verifier needs it because a patched literal pool word points at a table that NCPatcher placed in an autoload.

## Reuse

`Arm9Image` is independent of the mods. It can read any module-params ARM9 with autoloads, including a plain or BLZ image, and is useful for inspecting patched ROMs or writing another tool that follows runtime pointers.
