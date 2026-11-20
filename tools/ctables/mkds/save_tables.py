# Mario Kart DS Modding Trove
# tools/ctables/mkds/save_tables.py — typed C emitters for save, ghost and kart tables
# SPDX-License-Identifier: MIT
"""Emit C programs that rebuild MKDS save blocks, ghost files and kart tables.

The emitters are deliberately data-driven: every fixed record is written as a
typed table using the declarations in ``include/nitro/mkds``.  Where a packed
word has a union overlay (for example ``SavGpInfo0`` or ``MkdsGhostIdentity``)
the generated initializer names the bitfields, so a round-trip also checks the
header's bitfield ABI.

Save blocks are round-tripped *after* decryption.  The flash encryption tables
are implementation data and are not part of the shared headers, so the module
does not pretend to rebuild an encrypted ``.sav`` image.  Callers pass the full
decrypted block (payload bytes plus the four-byte footer); the footer is emitted
as ``SavBlockFooter`` and the NKSY file tag remains in place as the eight-byte
plaintext prefix.  For standalone NKDG/NKPG files and every kart table the
input is the file itself.

All offsets in this module are hexadecimal; record sizes and counts are
decimal, matching the rest of the trove.  Generated C is written to a temporary
file by the caller and is never committed.
"""
from __future__ import annotations

from pathlib import Path
from typing import Callable, Iterable, Sequence

from tools.ctables.common.cformat import fx_decimal
from tools.ctables.common.cnames import enum_name

# ---------------------------------------------------------------------------
# Save container facts (offsets hex, sizes/counts decimal)
# ---------------------------------------------------------------------------

SAV_NKSY_SIZE = 256
SAV_NKEM_SIZE = 768
SAV_NKGP_SIZE = 1024
SAV_NKTA_SIZE = 5632
SAV_NKMR_SIZE = 256
SAV_NKFL_SIZE = 3072
SAV_NKFE_SIZE = 2816
SAV_NKPG_SIZE = 3584
SAV_NKDG_SIZE = 4096

SAV_BLOCK_SIZES = {
    "NKSY": SAV_NKSY_SIZE,
    "NKEM": SAV_NKEM_SIZE,
    "NKGP": SAV_NKGP_SIZE,
    "NKTA": SAV_NKTA_SIZE,
    "NKMR": SAV_NKMR_SIZE,
    "NKFL": SAV_NKFL_SIZE,
    "NKFE": SAV_NKFE_SIZE,
    "NKPG": SAV_NKPG_SIZE,
    "NKDG": SAV_NKDG_SIZE,
}

SAV_NICKNAME_UNITS = 10
SAV_GP_MODE_COUNT = 4
SAV_CUP_COUNT = 8
SAV_TIME_TRIALS_RANK_COUNT = 6
SAV_TIME_TRIALS_COURSE_COUNT = 32
SAV_MISSION_COUNT = 63
SAV_FRIEND_COUNT = 60
SAV_EMBLEM_SLOT_COUNT = 5
SAV_INPUT_ENTRY_COUNT = 1764
SAV_EMBLEM_SIZE = 512
SAV_GHOST_HEADER_SIZE = 48
SAV_INPUT_RECORDING_SIZE = 4 + 2 * SAV_INPUT_ENTRY_COUNT
SAV_GHOST_RUN_LENGTH_OFFSET = 0x30
SAV_GHOST_EMBLEM_OFFSET = 0x30
SAV_GHOST_RUN_DATA_OFFSET = 0x230
SAV_GHOST_FILE_RESERVED_OFFSET = 0xFFC
SAV_PERSONAL_GHOST_RESERVED_OFFSET = 0xDFC

# Block magic word values, little-endian ASCII.
SAV_MAGICS = {
    "NKSY": 0x59534B4E,
    "NKEM": 0x4D454B4E,
    "NKGP": 0x50474B4E,
    "NKTA": 0x41544B4E,
    "NKMR": 0x524D4B4E,
    "NKFL": 0x4C464B4E,
    "NKFE": 0x45464B4E,
    "NKPG": 0x47504B4E,
    "NKDG": 0x47444B4E,
}

# Standalone ghost files.
GHOST_SIZE_NKDG = 4096
GHOST_SIZE_NKPG = 3584

# Kart and character parameter tables (offsets hex, sizes/counts decimal).
KART_PHYS_ROW_152 = 152
KART_PHYS_ROW_148 = 148
KART_PHYS_ROW_144 = 144
KART_AI_ROW = 12
KART_COLOR_ROW = 8
KART_OFFSET_ROW = 224
KART_MENU_ROW = 12
CHAR_PHYS_ROW = 8
CHAR_U16_ROW = 2
CHAR_MENU_ROW = 2


class TableError(ValueError):
    """Raised when an input file does not match a declared table shape."""


# ---------------------------------------------------------------------------
# Save footer helpers
# ---------------------------------------------------------------------------

def sav_crc16(data: bytes) -> int:
    """CRC16-CCITT (poly 0x1021, initial 0) used by the save footer."""
    crc = 0
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ 0x1021) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
    return crc


def sav_make_footer(payload: bytes, timestamp: int = 0) -> bytes:
    """Build the 4-byte footer: timestamp high byte first, then CRC high first.

    ``payload`` is the block without its footer.  The timestamp bytes are
    zeroed while calculating the CRC, which is the same convention the game
    uses when it validates a block (zero the timestamp, require CRC == 0 over
    the complete block including the two CRC bytes).
    """
    if not 0 <= timestamp <= 0xFFFF:
        raise TableError("timestamp must fit in 16 bits")
    stamp = bytes((timestamp >> 8, timestamp & 0xFF))
    # The timestamp is excluded from the checksum: the verifier zeroes both
    # timestamp bytes and requires the CRC over the complete block to be zero.
    # As with XMODEM, the value to store is the CRC of the message without the
    # two CRC bytes; appending it high byte first then makes validation zero.
    crc = sav_crc16(payload + b"\x00\x00")
    return stamp + bytes((crc >> 8, crc & 0xFF))


def sav_footer_valid(block: bytes) -> bool:
    """True when a decrypted block satisfies the zero-CRC contract."""
    if len(block) < 4:
        return False
    body = block[:-4] + b"\x00\x00" + block[-2:]
    return sav_crc16(body) == 0


# ---------------------------------------------------------------------------
# Small C rendering helpers
# ---------------------------------------------------------------------------

def _u8(value: int) -> str:
    return f"0x{value:02X}u"


def _u16(value: int) -> str:
    return f"0x{value:04X}u"


def _u32(value: int) -> str:
    return f"0x{value:08X}u"


def _s16(value: int) -> str:
    return str(value) if value >= 0 else f"-{abs(value)}"


def _s32(value: int) -> str:
    return str(value) if value >= 0 else f"-{abs(value)}"


def _fx32(raw: int) -> str:
    return f"FX32({fx_decimal(raw, 12)})"


def _fx16(raw: int) -> str:
    return f"FX16({fx_decimal(raw, 12)})"


def _bit_fields(pairs: Iterable[tuple[str, int]]) -> str:
    body = ", ".join(f".{name} = {value}" for name, value in pairs)
    return "{ .bits = { " + body + " } }"


def _struct(pairs: Iterable[tuple[str, str]]) -> str:
    body = ", ".join(f".{name} = {value}" for name, value in pairs)
    return "{ " + body + " }"


def _array(items: Iterable[tuple]) -> str:
    parts = []
    for item in items:
        index, value = item[0], item[1]
        comment = item[2] if len(item) > 2 else None
        text = f"{index} = {value}"
        if comment:
            text = f"/* {comment} */\n{text}"
        parts.append(text)
    body = ", ".join(parts)
    return "{ " + body + " }" if body else "{ 0 }"


def _utf16_units(data: bytes) -> str:
    """Emit a UTF-16LE nickname as readable character constants when possible."""
    count = len(data) // 2
    units = [_read_u16(data, 2 * index) for index in range(count)]
    text = []
    for unit in units:
        if unit == 0:
            break
        if unit < 0x20 or unit > 0x7E:
            return _u16_array(data, 0, count)
        char = chr(unit)
        if char in ("'", "\\"):
            char = "\\" + char
        text.append(f"'{char}'")
    if not text:
        return _u16_array(data, 0, count)
    # Keep the explicit width: the field is a uint16 array, not a string.
    text.extend(["0"] * (count - len(text)))
    return "{ " + ", ".join(text) + " }"


def _byte_literal(data: bytes) -> str:
    """A character-string initializer for a uint8_t array (exact length)."""
    if not data:
        return '""'
    chunks = []
    for start in range(0, len(data), 32):
        chunk = data[start:start + 32]
        chunks.append('"' + "".join(f"\\x{byte:02X}" for byte in chunk) + '"')
    if len(chunks) == 1:
        return chunks[0]
    return "\n" + "\n".join("        " + chunk for chunk in chunks)


def _bytes_field(data: bytes) -> str:
    """Emit a byte field as inspectable numbers, never as a long string.

    All-zero regions collapse to ``{ 0 }`` because C zero-initialises the
    remainder.  Non-zero regions keep every byte so the round-trip is exact.
    """
    if not data or not any(data):
        return "{ 0 }"
    return "{ " + ", ".join(_u8(byte) for byte in data) + " }"


def _emblem_bitmap(data: bytes, offset: int) -> str:
    """Emit a 512-byte emblem as 32 rows of 16 bytes."""
    chunk = data[offset:offset + 512]
    if not any(chunk):
        return "{ 0 }"
    rows = []
    for row in range(32):
        chunk = data[offset + row * 16:offset + (row + 1) * 16]
        rows.append("{ " + ", ".join(_u8(byte) for byte in chunk) + " }")
    return "{ .rows = { " + ", ".join(rows) + " } }"


def _u16_array(data: bytes, offset: int, count: int) -> str:
    values = ", ".join(_u16(_read_u16(data, offset + 2 * index))
                       for index in range(count))
    return "{ " + values + " }"


def _byte_matrix(data: bytes, offset: int, rows: int, cols: int) -> str:
    return _array(
        (f"[{row}][{col}]",
         _u8(data[offset + row * cols + col]))
        for row in range(rows) for col in range(cols)
    )


def _tail(data: bytes, offset: int, length: int) -> bytes:
    """Bytes from ``offset`` padded with zeros to ``length`` (footer excluded)."""
    chunk = data[offset:offset + length]
    return chunk + bytes(length - len(chunk))


def _read_u16(data: bytes, offset: int) -> int:
    return int.from_bytes(data[offset:offset + 2], "little")


def _read_u32(data: bytes, offset: int) -> int:
    return int.from_bytes(data[offset:offset + 4], "little")


def _read_s16(data: bytes, offset: int) -> int:
    return int.from_bytes(data[offset:offset + 2], "little", signed=True)


def _read_s32(data: bytes, offset: int) -> int:
    return int.from_bytes(data[offset:offset + 4], "little", signed=True)


def _magic_expr(value: int, kind: str) -> str:
    expected = SAV_MAGICS.get(kind)
    if expected is not None and value == expected:
        return f"SAV_MAGIC_{kind}"
    return _u32(value)


def _c_program(decls: str, statements: str, headers: Sequence[str]) -> str:
    include_lines = "\n".join(f'#include "{header}"' for header in headers)
    return (
        "/* generated typed table; rebuild with tools/ctables/edit.py. */\n"
        "#include <stdint.h>\n"
        "#include <stdio.h>\n"
        "#include <string.h>\n"
        f"{include_lines}\n"
        "\n"
        f"{decls}\n"
        "\n"
        "int main(int argc, char **argv)\n"
        "{\n"
        "    if (argc != 2)\n"
        "        return 2;\n"
        '    FILE *f = fopen(argv[1], "wb");\n'
        "    if (!f)\n"
        "        return 1;\n"
        f"{statements}"
        "    return fclose(f) == 0 ? 0 : 1;\n"
        "}\n"
    )


def _block_program(struct_name: str, init: str, size: int,
                   footer: bytes, patches: Sequence[tuple[int, int]] = ()) -> str:
    patch_lines = "".join(
        f"    image[0x{offset:03X}] = {_u8(value)};\n"
        for offset, value in patches
    )
    decls = (
        f"static const {struct_name} block = {init};\n"
        f"static const uint8_t footer[4] = {_bytes_field(footer)};\n"
        f'_Static_assert(sizeof block == {size}u, "{struct_name} size");'
    )
    statements = (
        "    uint8_t image[sizeof block];\n"
        "    memcpy(image, &block, sizeof block);\n"
        "    memcpy(image + sizeof block - sizeof footer, footer, sizeof footer);\n"
        f"{patch_lines}"
        "    if (fwrite(image, 1, sizeof image, f) != sizeof image)\n"
        "        return 1;\n"
    )
    return _c_program(decls, statements, ("nitro/mkds/save/save.h",))


# ---------------------------------------------------------------------------
# Save block initializers
# ---------------------------------------------------------------------------

def _init_nksy(body: bytes) -> str:
    flags = body[0x31]
    return _struct([
        ("file_magic", _char_name(body[0x00:0x08], 0x08)),
        ("block_magic", _magic_expr(_read_u32(body, 0x08), "NKSY")),
        ("nickname", _utf16_units(body[0x0C:0x0C + 2 * SAV_NICKNAME_UNITS])),
        ("unlock_bits", _bytes_field(body[0x20:0x24])),
        ("elo", _u16(_read_u16(body, 0x24))),
        ("personal_ghost_bits", _bytes_field(body[0x26:0x2A])),
        ("download_ghost_bits", _bytes_field(body[0x2A:0x2E])),
        ("emblem_used_bits", _bytes_field(body[0x2E:0x30])),
        ("padding_30", _u8(body[0x30])),
        ("flags_31", _bit_fields([
            ("nickname_set", flags & 0x01),
            ("sound", (flags >> 1) & 0x03),
            ("emblem_deleted", (flags >> 3) & 0x01),
            ("reserved", (flags >> 4) & 0x0F),
        ])),
        ("padding_32", _u8(body[0x32])),
        ("any_unlock", "{ .raw = 0x%08Xu }" % _read_u32(body, 0x34)),
        ("max_kart_unlock_level", _u8(body[0x38])),
        ("min_kart_unlock_level", _u8(body[0x39])),
        ("padding_3A", _bytes_field(body[0x3A:0x3C])),
        ("reserved_3C", _u32(_read_u32(body, 0x3C))),
        ("reserved_40", _u32(_read_u32(body, 0x40))),
        ("net_wins", _u32(_read_u32(body, 0x44))),
        ("net_losses", _u32(_read_u32(body, 0x48))),
        ("dwc_user", _bytes_field(body[0x4C:0x8C])),
        ("reserved_8C", _bytes_field(_tail(body, 0x8C, 0x100 - 0x8C))),
    ])


def _init_nkem(body: bytes) -> str:
    flags = body[0x04]
    return _struct([
        ("magic", _magic_expr(_read_u32(body, 0x00), "NKEM")),
        ("valid_and_reserved", _bit_fields([
            ("valid", flags & 0x01),
            ("reserved", (flags >> 1) & 0x7F),
        ])),
        ("reserved_5", _bytes_field(body[0x05:0x08])),
        ("emblem", _emblem_bitmap(body, 0x08)),
        ("reserved_208", _bytes_field(_tail(body, 0x208, 0x300 - 0x208))),
    ])


def _gp_info0(value: int) -> str:
    valid = value & 0x01
    character = (value >> 1) & 0x7F
    kart = (value >> 8) & 0xFF
    character_text = enum_name("MkdsCharacter", character) if valid else None
    kart_text = enum_name("MkdsKart", kart) if valid else None
    return _bit_fields([
        ("valid", valid),
        ("character", character_text or character),
        ("kart", kart_text or kart),
        ("rank_points", (value >> 16) & 0xFF),
        ("rank", (value >> 24) & 0xFF),
    ])


def _gp_info1(value: int) -> str:
    return _bit_fields([
        ("trophy", value & 0xFF),
        ("minutes", (value >> 8) & 0x7F),
        ("seconds", (value >> 15) & 0x7F),
        ("milliseconds", (value >> 22) & 0x3FF),
    ])


def _gp_entry(data: bytes, offset: int) -> str:
    return _struct([
        ("info_0", _gp_info0(_read_u32(data, offset + 0x00))),
        ("info_1", _gp_info1(_read_u32(data, offset + 0x04))),
        ("nickname", _utf16_units(data[offset + 0x08:offset + 0x08 + 2 * SAV_NICKNAME_UNITS])),
    ])


def _init_nkgp(body: bytes) -> str:
    entries = []
    mode_names = ("MKDS_ENGINE_50CC", "MKDS_ENGINE_100CC",
                  "MKDS_ENGINE_150CC", "MKDS_ENGINE_MIRROR")
    cup_names = ("MKDS_CUP_MUSHROOM", "MKDS_CUP_FLOWER",
                 "MKDS_CUP_STAR", "MKDS_CUP_SPECIAL",
                 "MKDS_CUP_SHELL", "MKDS_CUP_BANANA",
                 "MKDS_CUP_LEAF", "MKDS_CUP_LIGHTNING")
    for mode in range(SAV_GP_MODE_COUNT):
        for cup in range(SAV_CUP_COUNT):
            offset = 0x04 + (mode * SAV_CUP_COUNT + cup) * 28
            entries.append((f"[{mode_names[mode]}][{cup_names[cup]}]",
                            _gp_entry(body, offset)))
    return _struct([
        ("magic", _magic_expr(_read_u32(body, 0x00), "NKGP")),
        ("entries", _array(entries)),
        ("reserved_384", _bytes_field(_tail(body, 0x384, 0x400 - 0x384))),
    ])


def _time_trials_info(value: int) -> str:
    valid = value & 0x01
    character = (value >> 1) & 0x7F
    character_text = enum_name("MkdsCharacter", character) if valid else None
    return _bit_fields([
        ("valid", valid),
        ("character", character_text or character),
        ("minutes", (value >> 8) & 0x7F),
        ("seconds", (value >> 15) & 0x7F),
        ("milliseconds", (value >> 22) & 0x3FF),
    ])


def _time_trials_entry(data: bytes, offset: int) -> str:
    return _struct([
        ("info_0", _time_trials_info(_read_u32(data, offset + 0x00))),
        ("kart", enum_name("MkdsKart", data[offset + 0x04])
         or _u8(data[offset + 0x04])),
        ("reserved_5", _bytes_field(data[offset + 0x05:offset + 0x08])),
        ("nickname", _utf16_units(data[offset + 0x08:offset + 0x08 + 2 * SAV_NICKNAME_UNITS])),
    ])


def _init_nkta(body: bytes) -> str:
    entries = []
    for place in range(SAV_TIME_TRIALS_RANK_COUNT):
        place_name = enum_name("MkdsTimeTrialsPlace", place) or str(place)
        for order in range(SAV_TIME_TRIALS_COURSE_COUNT):
            order_name = enum_name("MkdsCourseOrder", order) or str(order)
            offset = 0x04 + (place * SAV_TIME_TRIALS_COURSE_COUNT + order) * 28
            entries.append((f"[{place_name}][{order_name}]",
                            _time_trials_entry(body, offset)))
    return _struct([
        ("magic", _magic_expr(_read_u32(body, 0x00), "NKTA")),
        ("entries", _array(entries)),
        ("reserved_1504", _bytes_field(_tail(body, 0x1504, 0x1600 - 0x1504))),
    ])


def _init_nkmr(body: bytes) -> str:
    entries = []
    for index in range(SAV_MISSION_COUNT):
        value = body[0x04 + index]
        slot_name = enum_name("MkdsMissionMenuSlot", index) or str(index)
        entries.append((f"[{slot_name}]", _bit_fields([
            ("valid", value & 0x01),
            ("rank", (value >> 1) & 0x7F),
        ])))
    return _struct([
        ("magic", _magic_expr(_read_u32(body, 0x00), "NKMR")),
        ("entries", _array(entries)),
        ("reserved_43", _bytes_field(_tail(body, 0x43, 0x100 - 0x43))),
    ])


def _friend_date(value: int) -> str:
    return _bit_fields([
        ("year", value & 0x7F),
        ("month", (value >> 7) & 0x0F),
        ("day", (value >> 11) & 0x1F),
    ])


def _friend_flags(value: int) -> str:
    return _bit_fields([
        ("valid", value & 0x01),
        ("offline", (value >> 1) & 0x01),
        ("has_emblem", (value >> 2) & 0x01),
        ("locked", (value >> 3) & 0x01),
        ("flags", (value >> 4) & 0x0F),
    ])


def _friend_profile(data: bytes, offset: int) -> str:
    return _struct([
        ("vs_wins", _u16(_read_u16(data, offset + 0x00))),
        ("vs_losses", _u16(_read_u16(data, offset + 0x02))),
        ("battle_wins", _u16(_read_u16(data, offset + 0x04))),
        ("battle_losses", _u16(_read_u16(data, offset + 0x06))),
        ("net_wins", _u16(_read_u16(data, offset + 0x08))),
        ("net_losses", _u16(_read_u16(data, offset + 0x0A))),
        ("date", _friend_date(_read_u16(data, offset + 0x0C))),
        ("nickname", _utf16_units(data[offset + 0x0E:offset + 0x0E + 2 * SAV_NICKNAME_UNITS])),
        ("flags", _friend_flags(data[offset + 0x22])),
        ("reserved_23", _u8(data[offset + 0x23])),
    ])


def _init_nkfl(body: bytes) -> str:
    profiles = []
    for index in range(SAV_FRIEND_COUNT):
        name = enum_name("MkdsFriendSlot", index) or str(index)
        profiles.append((f"[{name}]", _friend_profile(body, 0x04 + index * 36)))
    return _struct([
        ("magic", _magic_expr(_read_u32(body, 0x00), "NKFL")),
        ("profiles", _array(profiles)),
        ("dwc_friends", _bytes_field(body[0x874:0xB44])),
        ("reserved_B44", _bytes_field(_tail(body, 0xB44, 0xC00 - 0xB44))),
    ])


def _emblem_slots(body: bytes) -> str:
    items = []
    for slot in range(5):
        name = enum_name("MkdsEmblemSlot", slot) or str(slot)
        items.append((f"[{name}]",
                      _emblem_bitmap(body, 0x08 + slot * 0x200)))
    return _array(items)


def _init_nkfe(body: bytes) -> str:
    emblems = []
    for slot in range(SAV_EMBLEM_SLOT_COUNT):
        name = enum_name("MkdsEmblemSlot", slot) or str(slot)
        emblems.append((f"[{name}]", _emblem_bitmap(body, 0x08 + slot * 0x200)))
    return _struct([
        ("magic", _magic_expr(_read_u32(body, 0x00), "NKFE")),
        ("emblem_slot_mask", _u8(body[0x04])),
        ("reserved_5", _bytes_field(body[0x05:0x08])),
        ("emblems", _array(emblems)),
        ("reserved_A08", _bytes_field(_tail(body, 0xA08, 0xB00 - 0xA08))),
    ])


SAV_BLOCK_INITIALIZERS: dict[str, tuple[str, Callable[[bytes], str]]] = {
    "NKSY": ("SavIdentityBlock", _init_nksy),
    "NKEM": ("SavEmblemBlock", _init_nkem),
    "NKGP": ("SavGpBlock", _init_nkgp),
    "NKTA": ("SavTimeTrialsBlock", _init_nkta),
    "NKMR": ("SavMissionRankBlock", _init_nkmr),
    "NKFL": ("SavFriendBlock", _init_nkfl),
    "NKFE": ("SavEmblemBank", _init_nkfe),
}

# NKSY has one unnamed padding byte at 0x33 between padding_32 and any_unlock.
SAV_BLOCK_GAPS = {"NKSY": (0x33,)}


def emit_sav_block(data: bytes, kind: str) -> str:
    """Emit a typed C program that writes one *decrypted* save block."""
    kind = kind.upper()
    if kind not in SAV_BLOCK_SIZES:
        raise TableError(f"unknown save block {kind!r}")
    size = SAV_BLOCK_SIZES[kind]
    if len(data) != size:
        raise TableError(f"{kind}: expected {size} bytes, got {len(data)}")

    body = data[:size - 4]
    footer = data[size - 4:]

    if kind in ("NKPG", "NKDG"):
        struct_name = "SavPersonalGhostBlock" if kind == "NKPG" else "SavDownloadGhostBlock"
        init = _init_sav_ghost_block(body, kind)
        patches: list[tuple[int, int]] = []
    else:
        struct_name, initializer = SAV_BLOCK_INITIALIZERS[kind]
        init = initializer(body)
        patches = [(offset, body[offset]) for offset in SAV_BLOCK_GAPS.get(kind, ())]

    return _block_program(struct_name, init, size, footer, patches)


# ---------------------------------------------------------------------------
# Ghost header, blocks and standalone files
# ---------------------------------------------------------------------------

def _ghost_identity(value: int) -> str:
    character = value & 0x0F
    kart = (value >> 4) & 0x3F
    course = (value >> 10) & 0x3F
    return _bit_fields([
        ("character", enum_name("MkdsCharacter", character) or character),
        ("kart", enum_name("MkdsKart", kart) or kart),
        ("course", enum_name("MkdsRaceCourse", course) or course),
        ("year", (value >> 16) & 0x7F),
        ("month", (value >> 23) & 0x0F),
        ("day", (value >> 27) & 0x1F),
    ])


def _ghost_result(value: int) -> str:
    return _bit_fields([
        ("valid", value & 0x01),
        ("flag_1", (value >> 1) & 0x01),
        ("region", (value >> 2) & 0x03),
        ("flags_4_7", (value >> 4) & 0x0F),
        ("minutes", (value >> 8) & 0x7F),
        ("seconds", (value >> 15) & 0x7F),
        ("milliseconds", (value >> 22) & 0x3FF),
    ])


def _input_keys(mask: int) -> str:
    names = (("button_a", 0x01), ("button_b", 0x02), ("button_r", 0x04),
             ("button_lx", 0x08),
             ("dpad_right", 0x10), ("dpad_left", 0x20),
             ("dpad_down", 0x40), ("dpad_up", 0x80))
    pairs = [(name, 1) for name, bit in names if mask & bit]
    if not pairs:
        return "{ .raw = 0x00u }"
    return _bit_fields(pairs)


_LAP_SLOTS = ("MKDS_GHOST_LAP_1", "MKDS_GHOST_LAP_2",
              "MKDS_GHOST_LAP_3", "MKDS_GHOST_LAP_4", "MKDS_GHOST_LAP_5")
_LAP_PARTS = ("MKDS_GHOST_LAP_MINUTES", "MKDS_GHOST_LAP_SECONDS",
              "MKDS_GHOST_LAP_MILLISECONDS")


def _ghost_lap_times(data: bytes, offset: int) -> str:
    """The save header stores the 15 lap bytes as one flat array."""
    return _array(
        (f"[MKDS_GHOST_LAP_BYTE({_LAP_SLOTS[lap]}, {_LAP_PARTS[part]})]",
         _u8(data[offset + lap * 3 + part]))
        for lap in range(5) for part in range(3)
    )


def _ghost_lap_time_grid(data: bytes, offset: int) -> str:
    """The standalone ghost header stores five 3-byte lap entries."""
    return _array(
        (f"[{_LAP_SLOTS[lap]}][{_LAP_PARTS[part]}]",
         _u8(data[offset + lap * 3 + part]))
        for lap in range(5) for part in range(3)
    )


def _init_sav_ghost_header(data: bytes, offset: int) -> str:
    return _struct([
        ("magic", _magic_expr(_read_u32(data, offset + 0x00),
                               "NKDG" if _read_u32(data, offset) == SAV_MAGICS["NKDG"]
                               else "NKPG")),
        ("info_0", _ghost_identity(_read_u32(data, offset + 0x04))),
        ("info_1", _ghost_result(_read_u32(data, offset + 0x08))),
        ("nickname", _utf16_units(data[offset + 0x0C:offset + 0x0C + 2 * SAV_NICKNAME_UNITS])),
        ("lap_times", _ghost_lap_times(data, offset + 0x20)),
        ("rank_tier_2F",
         enum_name("MkdsGhostCupTier", data[offset + 0x2F])
         if data[offset + 0x2F] & ~0x03 == 0
         else _u8(data[offset + 0x2F])),
    ])


def _init_input_recording(data: bytes, offset: int) -> str:
    length = _read_u32(data, offset + 0x00)
    entries = []
    for index in range(SAV_INPUT_ENTRY_COUNT):
        entry = offset + 0x04 + index * 2
        mask = data[entry]
        duration = data[entry + 1]
        if mask or duration:
            entries.append((f"[{index}]", _struct([
                ("keys", _input_keys(mask)),
                ("duration", _u8(duration)),
            ])))
    fields: list[tuple[str, str]] = [("data_length", _u32(length))]
    if entries:
        fields.append(("entries", _array(entries)))
    return _struct(fields)


def _init_sav_ghost_block(body: bytes, kind: str) -> str:
    if kind == "NKPG":
        input_offset = SAV_GHOST_RUN_LENGTH_OFFSET
        reserved_offset = SAV_PERSONAL_GHOST_RESERVED_OFFSET
        fields = [
            ("header", _init_sav_ghost_header(body, 0x00)),
            ("input", _init_input_recording(body, input_offset)),
            ("reserved_FCC", _bytes_field(b"\x00" * 4)),
        ]
    else:
        input_offset = SAV_GHOST_RUN_DATA_OFFSET
        reserved_offset = SAV_GHOST_FILE_RESERVED_OFFSET
        fields = [
            ("header", _init_sav_ghost_header(body, 0x00)),
            ("emblem", _bytes_field(body[SAV_GHOST_EMBLEM_OFFSET:input_offset])),
            ("input", _init_input_recording(body, input_offset)),
            ("reserved_FFC", _bytes_field(b"\x00" * 4)),
        ]
    if reserved_offset != len(body):
        raise TableError(f"{kind}: unexpected reserved offset")
    return _struct(fields)


def _init_standalone_ghost_header(data: bytes) -> str:
    magic = data[0x00:0x04]
    return _struct([
        ("magic", _char_name(magic, 4)),
        ("identity", _ghost_identity(_read_u32(data, 0x04))),
        ("result", _ghost_result(_read_u32(data, 0x08))),
        ("nickname", _utf16_units(data[0x0C:0x0C + 2 * SAV_NICKNAME_UNITS])),
        ("lap_time", _ghost_lap_time_grid(data, 0x20)),
        ("rank_tier_2f",
         enum_name("MkdsGhostCupTier", data[0x2F])
         if data[0x2F] & ~0x03 == 0 else _u8(data[0x2F])),
    ])


def emit_ghost_file(data: bytes, magic: str) -> str:
    """Emit a standalone NKDG (4096-byte) or NKPG (3584-byte) ghost file."""
    magic = magic.upper()
    expected = {"NKDG": GHOST_SIZE_NKDG, "NKPG": GHOST_SIZE_NKPG}
    if magic not in expected:
        raise TableError(f"unknown ghost file magic {magic!r}")
    size = expected[magic]
    if len(data) != size:
        raise TableError(f"{magic}: expected {size} bytes, got {len(data)}")

    if magic == "NKDG":
        emblem = data[SAV_GHOST_EMBLEM_OFFSET:SAV_GHOST_RUN_DATA_OFFSET]
        input_offset = SAV_GHOST_RUN_DATA_OFFSET
        reserved_offset = SAV_GHOST_FILE_RESERVED_OFFSET
    else:
        emblem = b""
        input_offset = SAV_GHOST_RUN_LENGTH_OFFSET
        reserved_offset = SAV_PERSONAL_GHOST_RESERVED_OFFSET

    decls = (
        f"static const MkdsGhostHeader header = "
        f"{_init_standalone_ghost_header(data)};\n"
        f"static const SavInputRecording input = "
        f"{_init_input_recording(data, input_offset)};\n"
        f'static const uint8_t reserved[4] = '
        f"{_bytes_field(data[reserved_offset:reserved_offset + 4])};\n"
        f'_Static_assert(sizeof header == {SAV_GHOST_HEADER_SIZE}u, "ghost header");\n'
        f'_Static_assert(sizeof input == {SAV_INPUT_RECORDING_SIZE}u, "input recording");'
    )
    if magic == "NKDG":
        decls = (
            f"static const uint8_t emblem[{SAV_EMBLEM_SIZE}] = "
            f"{_bytes_field(emblem)};\n" + decls
        )

    writes = [
        "    if (fwrite(&header, 1, sizeof header, f) != sizeof header)\n        return 1;\n"
    ]
    if magic == "NKDG":
        writes.append(
            "    if (fwrite(emblem, 1, sizeof emblem, f) != sizeof emblem)\n        return 1;\n"
        )
    writes.append(
        "    if (fwrite(&input, 1, sizeof input, f) != sizeof input)\n        return 1;\n"
    )
    writes.append(
        "    if (fwrite(reserved, 1, sizeof reserved, f) != sizeof reserved)\n        return 1;\n"
    )
    return _c_program(decls, "".join(writes),
                      ("nitro/mkds/common/ids.h", "nitro/mkds/save/ghost.h"))


def emit_input_recording(data: bytes) -> str:
    """Emit the 0xDCC-byte ghost input recording as SavInputRecording."""
    if len(data) != SAV_INPUT_RECORDING_SIZE:
        raise TableError(
            f"input recording: expected {SAV_INPUT_RECORDING_SIZE} bytes, got {len(data)}")
    decls = (
        f"static const SavInputRecording input = {_init_input_recording(data, 0)};\n"
        f'_Static_assert(sizeof input == {SAV_INPUT_RECORDING_SIZE}u, "input recording");'
    )
    statements = (
        "    if (fwrite(&input, 1, sizeof input, f) != sizeof input)\n"
        "        return 1;\n"
    )
    return _c_program(decls, statements,
                      ("nitro/mkds/common/ids.h", "nitro/mkds/save/ghost.h"))


# ---------------------------------------------------------------------------
# Kart and character parameter tables
# ---------------------------------------------------------------------------

def _require_divisible(name: str, data: bytes, width: int) -> int:
    if len(data) % width:
        raise TableError(f"{name}: {len(data)} bytes is not a multiple of {width}")
    return len(data) // width


def _phys_row(data: bytes, offset: int, width: int) -> str:
    if width == 152:
        schema = [
            ("collision_sphere_size", 0x00, "fx32"),
            ("collision_sphere_z_offset", 0x04, "fx32"),
            ("extent_08", 0x08, "fx32"),
            ("weight", 0x0C, "fx16"),
            ("drift_boost_frames", 0x0E, "i16"),
            ("max_speed", 0x10, "fx32"),
            ("base_acceleration", 0x14, "fx32"),
            ("acceleration_at_curve_end", 0x18, "fx32"),
            ("acceleration_curve_fraction", 0x1C, "fx32"),
            ("drift_base_acceleration", 0x20, "fx32"),
            ("drift_acceleration_at_curve_end", 0x24, "fx32"),
            ("drift_curve_fraction", 0x28, "fx32"),
            ("deceleration", 0x2C, "fx32"),
            ("handling", 0x30, "fx16"),
            ("drift", 0x32, "fx16"),
            ("drift_turn_compensation", 0x34, "fx32"),
            ("collision_velocity_multiplier", 0x38, "surface_fx32"),
            ("collision_speed_multiplier", 0x68, "surface_fx32"),
        ]
    elif width == 148:
        schema = [
            ("collision_sphere_size", 0x00, "fx32"),
            ("collision_sphere_z_offset", 0x04, "fx32"),
            ("extent_08", 0x08, "fx32"),
            ("weight", 0x0C, "fx16"),
            ("drift_boost_frames", 0x0E, "i16"),
            ("max_speed", 0x10, "fx32"),
            ("base_acceleration", 0x14, "fx32"),
            ("acceleration_at_curve_end", 0x18, "fx32"),
            ("acceleration_curve_fraction", 0x1C, "fx32"),
            ("drift_base_acceleration", 0x20, "fx32"),
            ("drift_acceleration_at_curve_end", 0x24, "fx32"),
            ("drift_curve_fraction", 0x28, "fx32"),
            ("deceleration", 0x2C, "fx32"),
            ("handling", 0x30, "fx16"),
            ("drift", 0x32, "fx16"),
            ("collision_velocity_multiplier", 0x34, "surface_fx32"),
            ("collision_speed_multiplier", 0x64, "surface_fx32"),
        ]
    elif width == 144:
        schema = [
            ("collision_sphere_size", 0x00, "fx32"),
            ("collision_sphere_z_offset", 0x04, "fx32"),
            ("weight", 0x08, "fx16"),
            ("drift_boost_frames", 0x0A, "i16"),
            ("max_speed", 0x0C, "fx32"),
            ("base_acceleration", 0x10, "fx32"),
            ("acceleration_at_curve_end", 0x14, "fx32"),
            ("acceleration_curve_fraction", 0x18, "fx32"),
            ("drift_base_acceleration", 0x1C, "fx32"),
            ("drift_acceleration_at_curve_end", 0x20, "fx32"),
            ("drift_curve_fraction", 0x24, "fx32"),
            ("deceleration", 0x28, "fx32"),
            ("handling", 0x2C, "fx16"),
            ("drift", 0x2E, "fx16"),
            ("collision_velocity_multiplier", 0x30, "surface_fx32"),
            ("collision_speed_multiplier", 0x60, "surface_fx32"),
        ]
    else:
        raise TableError(f"unknown kart physical row width {width}")

    fields = []
    for name, field_offset, kind in schema:
        position = offset + field_offset
        if kind == "fx32":
            fields.append((name, _fx32(_read_s32(data, position))))
        elif kind == "fx16":
            fields.append((name, _fx16(_read_s16(data, position))))
        elif kind == "i16":
            fields.append((name, _s16(_read_s16(data, position))))
        elif kind == "bytes4":
            fields.append((name, _bytes_field(data[position:position + 4])))
        elif kind == "surface_fx32":
            fields.append((name, _array(
                (f"[{enum_name('MkdsCollisionSurface', index) or index}]",
                 _fx32(_read_s32(data, position + 4 * index)))
                for index in range(12)
            )))
        else:  # pragma: no cover - schema is fixed above
            raise AssertionError(kind)
    return _struct(fields)


def emit_kart_physical(data: bytes, width: int) -> str:
    """Emit a 152/148/144-byte kartphysicalparam.bin table."""
    if width not in (KART_PHYS_ROW_152, KART_PHYS_ROW_148, KART_PHYS_ROW_144):
        raise TableError(f"unsupported kart physical row width {width}")
    rows = _require_divisible("kartphysicalparam.bin", data, width)
    struct_name = {
        KART_PHYS_ROW_152: "MkdsKartPhysRow152",
        KART_PHYS_ROW_148: "MkdsKartPhysRow148",
        KART_PHYS_ROW_144: "MkdsKartPhysRow144",
    }[width]
    items = [
        (f"[{enum_name('MkdsKart', index) or index}]",
         _phys_row(data, index * width, width))
        for index in range(rows)
    ]
    decls = (
        f"static const {struct_name} table[{rows}] = {_array(items)};\n"
        f'_Static_assert(sizeof table == {len(data)}u, "kart physical table");'
    )
    statements = (
        "    if (fwrite(table, 1, sizeof table, f) != sizeof table)\n"
        "        return 1;\n"
    )
    return _c_program(decls, statements, ("nitro/mkds/race/kartparams.h",))


def emit_kart_ai(data: bytes) -> str:
    """Emit kartAIparam.bin as 480 MkdsKartAiRow records."""
    rows = _require_divisible("kartAIparam.bin", data, KART_AI_ROW)
    courses = rows // 12
    if rows % 12:
        raise TableError("kartAIparam.bin: record count is not 12 per course")
    engine_names = ("MKDS_ENGINE_50CC", "MKDS_ENGINE_100CC",
                    "MKDS_ENGINE_150CC")
    cpu_names = ("MKDS_CPU_EASY", "MKDS_CPU_NORMAL", "MKDS_CPU_HARD")
    rows_out = []
    for course in range(courses):
        race_name = enum_name("MkdsRaceCourse", course + 1)
        course_key = f"{race_name} - 1" if race_name else str(course)
        slots = []
        for slot in range(12):
            offset = (course * 12 + slot) * KART_AI_ROW
            if slot < 3:
                designator = (f"MKDS_KART_AI_GP_SLOT("
                              f"{engine_names[slot]})")
            else:
                engine = engine_names[(slot - 3) // 3]
                cpu = cpu_names[(slot - 3) % 3]
                designator = (f"MKDS_KART_AI_OTHER_SLOT("
                              f"{engine}, {cpu})")
            slots.append((f"[{designator}]", _struct([
                ("rival_target_speed_bonus", _fx32(_read_s32(data, offset + 0x00))),
                ("pack_closing_response_scale", _fx32(_read_s32(data, offset + 0x04))),
                ("leading_cpu_slowdown_threshold", _fx32(_read_s32(data, offset + 0x08))),
            ])))
        rows_out.append((f"[{course_key}]", _array(slots)))
    decls = (
        f"static const MkdsKartAiRow table[{courses}][12] = "
        f"{_array(rows_out)};\n"
        f'_Static_assert(sizeof table == {len(data)}u, "kart AI table");'
    )
    statements = (
        "    if (fwrite(table, 1, sizeof table, f) != sizeof table)\n"
        "        return 1;\n"
    )
    return _c_program(decls, statements, ("nitro/mkds/race/kartparams.h",))


def emit_kart_colors(data: bytes) -> str:
    """Emit kartcrsmat.bin as MkdsKartColorRow records."""
    rows = _require_divisible("kartcrsmat.bin", data, KART_COLOR_ROW)
    items = []
    for index in range(rows):
        offset = index * KART_COLOR_ROW
        race_name = enum_name("MkdsRaceCourse", index + 1)
        designator = f"[{race_name} - 1]" if race_name else f"[{index}]"
        items.append((designator, _struct([
            ("diffuse", _rgb555(_read_u16(data, offset + 0x00))),
            ("ambient", _rgb555(_read_u16(data, offset + 0x02))),
            ("specular", _rgb555(_read_u16(data, offset + 0x04))),
            ("emission", _rgb555(_read_u16(data, offset + 0x06))),
        ])))
    decls = (
        f"static const MkdsKartColorRow table[{rows}] = {_array(items)};\n"
        f'_Static_assert(sizeof table == {len(data)}u, "kart colour table");'
    )
    statements = (
        "    if (fwrite(table, 1, sizeof table, f) != sizeof table)\n"
        "        return 1;\n"
    )
    headers = ["nitro/mkds/race/kartparams.h"]
    if _RGB555_HEADER.exists():
        headers.insert(0, "nitro/rgb555.h")
    return _c_program(decls, statements, headers)


_AXIS_NAMES = ("MKDS_AXIS_X", "MKDS_AXIS_Y", "MKDS_AXIS_Z")

_TIRE_SLOT_NAMES = (
    "MKDS_TIRE_FRONT_POS_X",
    "MKDS_TIRE_FRONT_NEG_X",
    "MKDS_TIRE_REAR_POS_X",
    "MKDS_TIRE_REAR_NEG_X",
)

_CHARACTER_SLOT_NAMES = (
    "MKDS_CHARACTER_MARIO",
    "MKDS_CHARACTER_LUIGI",
    "MKDS_CHARACTER_PEACH",
    "MKDS_CHARACTER_YOSHI",
    "MKDS_CHARACTER_TOAD",
    "MKDS_CHARACTER_DONKEY_KONG",
    "MKDS_CHARACTER_WARIO",
    "MKDS_CHARACTER_DAISY",
    "MKDS_CHARACTER_WALUIGI",
    "MKDS_CHARACTER_DRY_BONES",
    "MKDS_CHARACTER_BOWSER",
    "MKDS_CHARACTER_ROB",
    "MKDS_CHARACTER_SHY_GUY",
)

_RGB555_HEADER = (Path(__file__).resolve().parents[3]
                  / "include/nitro/rgb555.h")


def _rgb555(value: int) -> str:
    if _RGB555_HEADER.exists() and not (value & 0x8000):
        red = value & 0x1F
        green = (value >> 5) & 0x1F
        blue = (value >> 10) & 0x1F
        return f"NITRO_RGB555({red}, {green}, {blue})"
    return f"0x{value:04X}u"


def _fx32_triples(data: bytes, offset: int, slot_names: Sequence[str | None]) -> str:
    """Emit [slot][axis] = FX32(value), naming both dimensions where known."""
    rows = []
    for index, slot in enumerate(slot_names):
        values = []
        for axis in range(3):
            raw = _read_s32(data, offset + (index * 3 + axis) * 4)
            values.append(f"[{_AXIS_NAMES[axis]}] = {_fx32(raw)}")
        if slot is None:
            rows.append((f"[{index}]", "{ " + ", ".join(values) + " }"))
        else:
            rows.append((f"[{slot}]", "{ " + ", ".join(values) + " }"))
    return _array(rows)


def _char_name(data: bytes, size: int) -> str:
    """Emit a NUL-padded ASCII name as a string literal when exact."""
    trim = data.rstrip(b"\0")
    if b"\0" not in trim and all(32 <= byte < 127 for byte in trim):
        text = trim.decode("ascii").replace("\\", "\\\\").replace('"', '\\"')
        return f'"{text}"'
    return "{ " + ", ".join(_u8(byte) for byte in data) + " }"


def emit_kart_offsets(data: bytes) -> str:
    """Emit kartoffsetdata.bin as MkdsKartOffsetRow records."""
    rows = _require_divisible("kartoffsetdata.bin", data, KART_OFFSET_ROW)
    items = []
    for index in range(rows):
        offset = index * KART_OFFSET_ROW
        items.append((f"[{enum_name('MkdsKart', index) or index}]", _struct([
            ("tire_name", _char_name(data[offset:offset + 0x10], 0x10)),
            ("front_tire_scale", _fx32(_read_s32(data, offset + 0x10))),
            ("tire_positions", _fx32_triples(data, offset + 0x14,
                                            _TIRE_SLOT_NAMES)),
            ("character_positions", _fx32_triples(
                data, offset + 0x44, _CHARACTER_SLOT_NAMES)),
        ])))
    decls = (
        f"static const MkdsKartOffsetRow table[{rows}] = {_array(items)};\n"
        f'_Static_assert(sizeof table == {len(data)}u, "kart offset table");'
    )
    statements = (
        "    if (fwrite(table, 1, sizeof table, f) != sizeof table)\n"
        "        return 1;\n"
    )
    return _c_program(decls, statements, ("nitro/mkds/race/kartparams.h",))


def emit_kart_menu(data: bytes) -> str:
    """Emit kartmenuparam.bin as 50 MkdsKartMenuRow records."""
    rows = _require_divisible("kartmenuparam.bin", data, KART_MENU_ROW)
    items = []
    for index in range(rows):
        offset = index * KART_MENU_ROW
        items.append((f"[{enum_name('MkdsKart', index) or index}]", _struct([
            ("speed", _s16(_read_s16(data, offset + 0x00))),
            ("acceleration", _s16(_read_s16(data, offset + 0x02))),
            ("weight", _s16(_read_s16(data, offset + 0x04))),
            ("handling", _s16(_read_s16(data, offset + 0x06))),
            ("drift", _s16(_read_s16(data, offset + 0x08))),
            ("items", _s16(_read_s16(data, offset + 0x0A))),
        ])))
    decls = (
        f"static const MkdsKartMenuRow table[{rows}] = {_array(items)};\n"
        f'_Static_assert(sizeof table == {len(data)}u, "kart menu table");'
    )
    statements = (
        "    if (fwrite(table, 1, sizeof table, f) != sizeof table)\n"
        "        return 1;\n"
    )
    return _c_program(decls, statements, ("nitro/mkds/race/kartparams.h",))


def emit_char_physical(data: bytes) -> str:
    """Emit the 104-byte charphysicalparam.bin table (13 x MkdsCharPhysRow)."""
    rows = _require_divisible("charphysicalparam.bin", data, CHAR_PHYS_ROW)
    items = []
    for index in range(rows):
        offset = index * CHAR_PHYS_ROW
        items.append((f"[{enum_name('MkdsCharacter', index) or index}]",
                      _struct([
            ("collision_speed_scale", _fx32(_read_s32(data, offset + 0x00))),
            ("weight", _fx32(_read_s32(data, offset + 0x04))),
        ])))
    decls = (
        f"static const MkdsCharPhysRow table[{rows}] = {_array(items)};\n"
        f'_Static_assert(sizeof table == {len(data)}u, "character physical table");'
    )
    statements = (
        "    if (fwrite(table, 1, sizeof table, f) != sizeof table)\n"
        "        return 1;\n"
    )
    return _c_program(decls, statements, ("nitro/mkds/race/kartparams.h",))


def emit_char_menu(data: bytes) -> str:
    """Emit charmenuparam.bin as 13 MkdsCharacterMenuRow records."""
    rows = _require_divisible("charmenuparam.bin", data, CHAR_MENU_ROW)
    items = []
    for index in range(rows):
        name = enum_name("MkdsCharacter", index) or str(index)
        items.append((f"[{name}]", _struct([
            ("weight_offset", _s16(_read_s16(data, index * CHAR_MENU_ROW))),
        ])))
    decls = (
        f"static const MkdsCharacterMenuRow table[{rows}] = {_array(items)};\n"
        f'_Static_assert(sizeof table == {len(data)}u, "character menu table");'
    )
    statements = (
        "    if (fwrite(table, 1, sizeof table, f) != sizeof table)\n"
        "        return 1;\n"
    )
    return _c_program(decls, statements, ("nitro/mkds/race/kartparams.h",))


def emit_char_u16(data: bytes) -> str:
    """Emit a 13-entry uint16 table (charmenuparam.bin, 26-byte physical)."""
    rows = _require_divisible("character u16 table", data, CHAR_U16_ROW)
    decls = (
        f"static const uint16_t table[{rows}] = {_u16_array(data, 0, rows)};\n"
        f'_Static_assert(sizeof table == {len(data)}u, "character u16 table");'
    )
    statements = (
        "    if (fwrite(table, 1, sizeof table, f) != sizeof table)\n"
        "        return 1;\n"
    )
    return _c_program(decls, statements, ("nitro/mkds/race/kartparams.h",))
