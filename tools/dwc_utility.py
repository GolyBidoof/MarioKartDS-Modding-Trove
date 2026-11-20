# Mario Kart DS Modding Trove
# tools/dwc_utility.py — list and extract the NARC-less DWC utility archive
# SPDX-License-Identifier: MIT
"""Read data/dwc/utility.bin without guessing at its contents.

The archive is the DWC variant of NitroFS: a 16-byte header with FNT/FAT
offsets and sizes, then a normal Nitro FNT and FAT with no ``NARC`` chunk
wrapper. FAT offsets are relative to the start of ``utility.bin``.

    python3 tools/dwc_utility.py list utility.bin
    python3 tools/dwc_utility.py extract utility.bin -o out/dwc
    python3 tools/dwc_utility.py verify utility.bin

Nothing is written unless ``extract`` or ``-o`` is used. The output tree is
meant for ``out/``; the stock archive is never modified.
"""
from __future__ import annotations

import argparse
import struct
import sys
from dataclasses import dataclass
from pathlib import Path

HEADER = struct.Struct("<4I")
FAT_ENTRY = struct.Struct("<2I")
FNT_ENTRY = struct.Struct("<IHH")

HEADER_SIZE = 16
FNT_ROOT_ID = 0xF000
DIRECTORY_FLAG = 0x80
SUBTABLE_END = 0x00


class ArchiveError(ValueError):
    """The file is not a structurally valid NARC-less DWC archive."""


@dataclass(frozen=True)
class DwcFatEntry:
    file_id: int
    start: int
    end: int

    @property
    def size(self) -> int:
        return self.end - self.start


@dataclass(frozen=True)
class DwcFile:
    file_id: int
    path: str
    start: int
    size: int


def parse_header(data: bytes) -> tuple[int, int, int, int]:
    if len(data) < HEADER_SIZE:
        raise ArchiveError("utility.bin: shorter than the 16-byte header")
    fnt_offset, fnt_size, fat_offset, fat_size = HEADER.unpack_from(data, 0)
    if fnt_offset < HEADER_SIZE or fnt_offset + fnt_size > len(data):
        raise ArchiveError("utility.bin: FNT is outside the file")
    if fat_offset < HEADER_SIZE or fat_offset + fat_size > len(data):
        raise ArchiveError("utility.bin: FAT is outside the file")
    if fat_size % FAT_ENTRY.size:
        raise ArchiveError("utility.bin: FAT size is not a whole entry count")
    return fnt_offset, fnt_size, fat_offset, fat_size


def parse_fat(data: bytes, fat_offset: int, fat_size: int) -> list[DwcFatEntry]:
    entries: list[DwcFatEntry] = []
    for index in range(fat_size // FAT_ENTRY.size):
        start, end = FAT_ENTRY.unpack_from(data, fat_offset + index * FAT_ENTRY.size)
        if start == 0 and end == 0:
            continue
        if start > end or end > len(data):
            raise ArchiveError(
                f"utility.bin: FAT entry {index} has invalid range "
                f"0x{start:X}..0x{end:X}")
        entries.append(DwcFatEntry(index, start, end))
    return entries


def _read_subtable(fnt: bytes, offset: int,
                   first_file_id: int) -> list[tuple[str, int, bool]]:
    entries: list[tuple[str, int, bool]] = []
    position = offset
    file_id = first_file_id
    while position < len(fnt):
        type_length = fnt[position]
        position += 1
        if type_length == SUBTABLE_END:
            break
        is_directory = bool(type_length & DIRECTORY_FLAG)
        length = type_length & 0x7F
        if length == 0 or position + length > len(fnt):
            raise ArchiveError(
                f"utility.bin: malformed FNT entry at 0x{position - 1:X}")
        name = fnt[position:position + length].decode("ascii", "replace")
        position += length
        if is_directory:
            if position + 2 > len(fnt):
                raise ArchiveError("utility.bin: truncated FNT directory id")
            directory_id = struct.unpack_from("<H", fnt, position)[0]
            position += 2
            entries.append((name, directory_id, True))
        else:
            entries.append((name, file_id, False))
            file_id += 1
    return entries


def parse_tree(data: bytes) -> list[DwcFile]:
    fnt_offset, fnt_size, fat_offset, fat_size = parse_header(data)
    fnt = data[fnt_offset:fnt_offset + fnt_size]
    if len(fnt) < FNT_ENTRY.size:
        raise ArchiveError("utility.bin: FNT has no root entry")
    subtable_offset, first_file_id, directory_count = FNT_ENTRY.unpack_from(fnt, 0)
    if directory_count == 0 or directory_count > 4096:
        raise ArchiveError("utility.bin: implausible directory count")
    if FNT_ENTRY.size * directory_count > fnt_size:
        raise ArchiveError("utility.bin: FNT main table is larger than the FNT")

    directories: dict[int, tuple[int, int]] = {FNT_ROOT_ID: (subtable_offset, first_file_id)}
    for index in range(1, directory_count):
        offset, first, parent = FNT_ENTRY.unpack_from(fnt, index * FNT_ENTRY.size)
        directories[FNT_ROOT_ID + index] = (offset, first)

    fat = {entry.file_id: entry for entry in parse_fat(data, fat_offset, fat_size)}
    files: list[DwcFile] = []
    seen: set[int] = set()

    def walk(directory_id: int, prefix: str) -> None:
        if directory_id in seen:
            raise ArchiveError("utility.bin: FNT directory cycle")
        seen.add(directory_id)
        offset, first = directories[directory_id]
        for name, child_id, is_directory in _read_subtable(fnt, offset, first):
            path = f"{prefix}/{name}" if prefix else name
            if is_directory:
                if child_id not in directories:
                    raise ArchiveError(
                        f"utility.bin: directory id 0x{child_id:04X} is missing")
                walk(child_id, path)
            else:
                entry = fat.get(child_id)
                if entry is None:
                    raise ArchiveError(
                        f"utility.bin: file id {child_id} has no FAT entry")
                files.append(DwcFile(child_id, path, entry.start, entry.size))

    walk(FNT_ROOT_ID, "")
    return files


def verify(data: bytes) -> list[DwcFile]:
    """Parse the archive and prove every FAT range is reachable exactly once."""
    files = parse_tree(data)
    ranges = sorted((file.start, file.start + file.size, file.path)
                    for file in files)
    for (start_a, end_a, path_a), (start_b, end_b, path_b) in zip(ranges, ranges[1:]):
        if start_b < end_a:
            raise ArchiveError(
                f"utility.bin: {path_a} and {path_b} overlap")
    return files


def extract(data: bytes, destination: Path) -> list[Path]:
    written: list[Path] = []
    for file in parse_tree(data):
        target = destination / file.path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data[file.start:file.start + file.size])
        written.append(target)
    return written


def cmd_list(args) -> int:
    data = Path(args.input).read_bytes()
    fnt_offset, fnt_size, fat_offset, fat_size = parse_header(data)
    print(f"FNT 0x{fnt_offset:X} ({fnt_size} bytes)")
    print(f"FAT 0x{fat_offset:X} ({fat_size} bytes, "
          f"{fat_size // FAT_ENTRY.size} entries)")
    for file in parse_tree(data):
        print(f"{file.file_id:4d} 0x{file.start:06X} {file.size:7d}  {file.path}")
    return 0


def cmd_verify(args) -> int:
    data = Path(args.input).read_bytes()
    files = verify(data)
    print(f"ok: {len(files)} files")
    return 0


def cmd_extract(args) -> int:
    data = Path(args.input).read_bytes()
    written = extract(data, Path(args.output))
    print(f"wrote {len(written)} files to {args.output}")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    for name, function in (("list", cmd_list), ("verify", cmd_verify),
                           ("extract", cmd_extract)):
        command = sub.add_parser(name)
        command.add_argument("input")
        if name == "extract":
            command.add_argument("-o", "--output", required=True)
        command.set_defaults(func=function)

    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except ArchiveError as error:
        sys.stderr.write(f"{error}\n")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
