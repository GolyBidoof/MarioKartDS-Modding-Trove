# C-table generators

> **Project:** Mario Kart DS Modding Trove · **Licence:** MIT

```text
tools/ctables/
  common/    C formatting, enum-name lookup, compile harness
  generic/   Nitro G2D, G3D and sound emitters
  mkds/      MKDS course, save, UI and small-table emitters
  edit.py    extract/build entry point
```

`edit.py` detects the format and dispatches to a module:

```sh
python3 tools/ctables/edit.py extract path/to/file -o file.c
python3 tools/ctables/edit.py build file.c -o rebuilt.bin
```

Generic emitters rebuild a Nitro resource byte-for-byte. MKDS emitters rebuild
a concrete stock file or save block. `mkds/save_image.py` is the full-image
save helper; the other modules are one file per format family.
