# Format headers and Mario Kart Toolbox

> **Project:** Mario Kart DS Modding Trove · **Scope:** C header ↔ C# model map · **Licence:** MIT

The headers in `include/nitro/` are host-compilable C11. They are intended for recompilation code, NCPatcher patch units and small native readers. Mario Kart Toolbox is C#/.NET and cannot include C headers directly, so the shared contract is the field/offset table in the matching `docs/formats-*.md` note.

Where a Toolbox model already exists, the C header deliberately uses the same on-disk offsets and neutral field names, not Toolbox's class names or C# property names. Where a format is not implemented in Toolbox yet, the header is the first reusable definition.

| Format family | C header | Existing Toolbox model | Toolbox status |
|---|---|---|---|
| NDS header/FNT/FAT/overlays | `nitro/nds.h` | `HaroohiePals.Nitro.Card.*` | read/write |
| NARC/CARC and LZ77 | `nitro/narc.h` | `HaroohiePals.Nitro.NitroSystem.Fnd.Narc` | read/write |
| BMG | `nitro/bmg.h` | none in this repository | no model |
| Shared MKDS ids | `nitro/mkds_ids.h` | partial enums in `HaroohiePals.NitroKart` | constants only |
| Save image and blocks | `nitro/save.h` | none | no model |
| G2D resources | `nitro/g2d.h` | `HaroohiePals.Nitro.NitroSystem.G2d.*` | mixed, see note |
| G3D resources | `nitro/g3d.h` | `HaroohiePals.Nitro.NitroSystem.G3d.*` | mixed, see note |
| Audio containers | `nitro/sdat.h` | `HaroohiePals.Nitro.NitroSystem.Snd.*` | read/write library, not wired |
| Course map/collision/particles | `nitro/mkds_course.h` | `HaroohiePals.NitroKart.MapData.Binary.*`, `HaroohiePals.KCollision.*`, `HaroohiePals.Nitro.JNLib.Spl.*` | NKM/KCL wired, SPA library only |
| JNLib UI resources | `nitro/mkds_ui.h` | none | no model |
| Race/ghost/mission data | `nitro/mkds_race.h` | partial map-data enums only | mostly no model |

For a new Toolbox reader, the natural order is: define the C structs and `_Static_assert` offsets from the field table, add the C# reader/writer in the existing namespace, then add a round-trip test over the stock corpus. For a new recomp or mod reader, include the C header directly; no generated bindings are required.

The C headers do not include Toolbox data, game addresses or region-specific values. A C# model can mirror the offsets without copying the header text, and a C reader can mirror a C# model the same way.
