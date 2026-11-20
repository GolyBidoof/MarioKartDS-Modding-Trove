# Mario Kart DS Modding Trove
# tools/ctables/mkds/ui_c.py — shared C source construction for MKDS UI tables
# SPDX-License-Identifier: MIT
"""Small helpers that turn parsed UI records into a standalone C program.

Every generated program is deliberately self-contained: it includes the real
format header, keeps the on-disk records in static tables with designated
initializers, and writes those tables to ``argv[1]`` in file order.
"""
from __future__ import annotations

from typing import List, Sequence, Tuple

MAGIC_HEADER = """\
struct ImagePart {
    const void *data;
    size_t size;
};

static int write_image(const char *path, const struct ImagePart *parts,
                       size_t part_count)
{
    FILE *file = fopen(path, "wb");
    if (file == NULL)
        return 1;
    int ok = 1;
    for (size_t i = 0; i < part_count; ++i) {
        if (fwrite(parts[i].data, 1, parts[i].size, file) != parts[i].size) {
            ok = 0;
            break;
        }
    }
    if (fclose(file) != 0)
        ok = 0;
    return ok ? 0 : 1;
}
"""

_ORIGIN_NAMES = {
    0: "MKDS_UI_ORIGIN_START",
    1: "MKDS_UI_ORIGIN_CENTER",
    2: "MKDS_UI_ORIGIN_END",
}
_LINE_ALIGN_NAMES = {
    0: "MKDS_UI_LINE_ALIGN_START",
    1: "MKDS_UI_LINE_ALIGN_CENTER",
    2: "MKDS_UI_LINE_ALIGN_END",
}


def hex8(value: int) -> str:
    return f"0x{value:02X}"


def hex16(value: int) -> str:
    return f"0x{value:04X}"


def hex32(value: int) -> str:
    return f"0x{value:08X}"


def signed(value: int) -> str:
    """A signed C literal that is unambiguous inside a bitfield initializer."""
    return str(value)


def origin_name(value: int) -> str:
    """Use the header constant where one exists, otherwise the raw value."""
    return _ORIGIN_NAMES.get(value, str(value))


def line_align_name(value: int) -> str:
    return _LINE_ALIGN_NAMES.get(value, str(value))


def coord_initializer(raw: int) -> str:
    """Expand a MkdsUiCoord halfword into its union bitfield form."""
    value = raw & 0x0FFF
    if value & 0x0800:
        value -= 0x1000
    origin = (raw >> 12) & 0x3
    param = (raw >> 14) & 0x3
    return (
        "{ .bits = { .value = %s, .origin = %s, .param = %s } }"
        % (signed(value), origin_name(origin), line_align_name(param))
    )


def style_initializer(raw: int) -> str:
    """Expand a MkdsUiLabelStyle halfword into colour/palette/font fields."""
    return (
        "{ .bits = { .color = %d, .palette = %d, .font = %d } }"
        % (raw & 0xFF, (raw >> 8) & 0xF, (raw >> 12) & 0xF)
    )


def byte_array(values: Sequence[int], indent: str = "    ",
               per_line: int = 12) -> List[str]:
    """Format uint8_t values as C initializer lines."""
    lines = []
    for start in range(0, len(values), per_line):
        chunk = values[start:start + per_line]
        lines.append(indent + ", ".join(hex8(value) for value in chunk) + ",")
    return lines


def word_array(values: Sequence[int], indent: str = "    ",
               per_line: int = 8) -> List[str]:
    """Format uint16_t values as C initializer lines."""
    lines = []
    for start in range(0, len(values), per_line):
        chunk = values[start:start + per_line]
        lines.append(indent + ", ".join(hex16(value) for value in chunk) + ",")
    return lines


def sanitize_comment(text: str) -> str:
    """Make text safe to place inside a C block comment on one line."""
    text = text.replace("*/", "* /")
    text = text.replace("\r", " ").replace("\n", " ")
    return "".join(ch if ch.isprintable() else "?" for ch in text)


def printable_ascii(units: Sequence[int]) -> str:
    """Return a comment-friendly ASCII rendering, or an empty string."""
    chars = []
    for unit in units:
        if unit == 0:
            continue
        if 0x20 <= unit <= 0x7E:
            chars.append(chr(unit))
        else:
            return ""
    return "".join(chars)


class CProgram:
    """Collect declarations and output parts for one generated C program."""

    def __init__(self, emitter: str, format_name: str, header: str) -> None:
        self.emitter = emitter
        self.format_name = format_name
        self.header = header
        self.asserts: List[str] = []
        self.declarations: List[str] = []
        self.parts: List[Tuple[str, str]] = []

    def add_assert(self, text: str) -> None:
        self.asserts.append(text)

    def add_decl(self, text: str) -> None:
        self.declarations.append(text.rstrip())

    def add_comment(self, text: str) -> None:
        pass

    def add_part(self, expression: str, size: str) -> None:
        self.parts.append((expression, size))

    def add_array_part(self, name: str) -> None:
        self.add_part(name, "sizeof " + name)

    def render(self) -> str:
        lines = [
            "/* %s. */"
            % self.format_name,
            "",
            "#include <stddef.h>",
            "#include <stdint.h>",
            "#include <stdio.h>",
            "",
            '#include "%s"' % self.header,
            "",
        ]
        for declaration in self.declarations:
            lines.append(declaration)
            lines.append("")
        if self.asserts:
            lines.extend(self.asserts)
            lines.append("")
        lines.append(MAGIC_HEADER.rstrip())
        lines.append("")
        lines.append("int main(int argc, char **argv)")
        lines.append("{")
        lines.append("    if (argc != 2)")
        lines.append("        return 2;")
        lines.append("")
        if self.parts:
            lines.append("    const struct ImagePart parts[] = {")
            for expression, size in self.parts:
                lines.append("        { %s, %s }," % (expression, size))
            lines.append("    };")
            lines.append("    return write_image(argv[1], parts, "
                         "sizeof parts / sizeof parts[0]);")
        else:
            lines.append("    return write_image(argv[1], NULL, 0);")
        lines.append("}")
        lines.append("")
        return "\n".join(lines)
