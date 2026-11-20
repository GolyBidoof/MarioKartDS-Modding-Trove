# Mario Kart DS Modding Trove
# tools/ctables/common/cformat.py — small C initializer formatter
# SPDX-License-Identifier: MIT
import re

_SIMPLE_BRACE = re.compile(r"\{([^{}]*)\}")


def fx_decimal(raw: int, bits: int = 12) -> str:
    """Shortest decimal that rebuilds ``raw`` through the FX32/FX16 macro.

    The macro truncates toward zero, so a decimal is accepted only when
    ``int(value * 2**bits) == raw``.  Prefer the fewest decimal places, then
    the representation with the fewest significant digits.  Fall back to the
    exact 1/2**bits expansion when no short form works.
    """
    scale = 1 << bits
    if raw == 0:
        return "0.0"
    sign = "-" if raw < 0 else ""
    magnitude = abs(raw)

    def render(numerator: int, decimals: int) -> str:
        if decimals == 0:
            return f"{numerator}.0"
        factor = 10 ** decimals
        whole, frac = divmod(numerator, factor)
        text = f"{whole}.{frac:0{decimals}d}".rstrip("0").rstrip(".")
        return text if "." in text else text + ".0"

    for decimals in range(0, 10):
        factor = 10 ** decimals
        numerator = (magnitude * factor + scale // 2) // scale
        if numerator == 0:
            continue
        value = numerator / factor
        if int(value * scale) == magnitude:
            return sign + render(numerator, decimals)

    digits = 10 ** bits
    whole, frac = divmod(magnitude * (digits // scale), digits)
    if frac:
        return f"{sign}{whole}.{frac:0{bits}d}".rstrip("0")
    return f"{sign}{whole}.0"


def fx_literal(raw: int, bits: int = 12) -> str:
    return f"FX{'32' if bits == 12 else '16'}({fx_decimal(raw, bits)})"


def _collapse_simple(source: str) -> str:
    """Keep short scalar initializers on one line, e.g. { 0, 1, 2 }."""
    def replace(match: re.Match[str]) -> str:
        body = match.group(1)
        if ('"' in body or "'" in body or "/*" in body
                or ";" in body or "#" in body):
            return match.group(0)
        parts = [part.strip() for part in body.split(",") if part.strip()]
        if not parts:
            return match.group(0)
        text = "{ " + ", ".join(parts) + " }"
        return text if len(text) <= 180 else match.group(0)

    previous = None
    while previous != source:
        previous = source
        source = _SIMPLE_BRACE.sub(replace, source)
    return source


def pretty_c(source: str) -> str:
    """Expand brace/comma-separated initializers into one field per line."""
    out: list[str] = []
    depth = 0
    paren = 0
    i = 0
    n = len(source)
    while i < n:
        c = source[i]
        if c == "#" and (i == 0 or source[i - 1] == "\n"):
            j = source.find("\n", i)
            j = n if j < 0 else j
            out.append(source[i:j])
            i = j
            continue
        if c == "/" and i + 1 < n and source[i + 1] == "*":
            j = source.find("*/", i + 2)
            j = n if j < 0 else j + 2
            if out and out[-1] and not out[-1][-1].isspace():
                out.append(" ")
            out.append(source[i:j])
            i = j
            # A comment that ends its own line starts the next line at the
            # current brace depth, so leading comments stay aligned.
            k = i
            newline = False
            while k < n and source[k] in " \t\r\n":
                if source[k] == "\n":
                    newline = True
                k += 1
            if newline:
                out.append("\n" + "    " * depth)
                i = k
            continue
        if c == "/" and i + 1 < n and source[i + 1] == "/":
            j = source.find("\n", i)
            j = n if j < 0 else j
            out.append(source[i:j])
            i = j
            continue
        if c in ('"', "'"):
            quote = c
            j = i + 1
            while j < n:
                if source[j] == "\\":
                    j += 2
                    continue
                if source[j] == quote:
                    j += 1
                    break
                j += 1
            out.append(source[i:j])
            i = j
            continue
        if c == "{":
            out.append("{\n" + "    " * (depth + 1))
            depth += 1
            i += 1
            while i < n and source[i] in " \t\r\n":
                i += 1
            continue
        if c == "}":
            depth = max(0, depth - 1)
            while out and out[-1] in (" ", "\t", "\n"):
                out.pop()
            if out and out[-1].endswith("    " * (depth + 1)):
                out[-1] = out[-1].rstrip(" ")
            out.append("\n" + "    " * depth + "}")
            i += 1
            continue
        if c == "(":
            paren += 1
            out.append(c)
            i += 1
            continue
        if c == ")":
            paren = max(0, paren - 1)
            out.append(c)
            i += 1
            continue
        if c == "," and depth > 0 and paren == 0:
            out.append(",\n" + "    " * depth)
            i += 1
            while i < n and source[i] in " \t\r\n":
                i += 1
            continue
        out.append(c)
        i += 1
    text = _collapse_simple("".join(out))
    # collapse excessive blank lines and trailing spaces
    lines = [line.rstrip() for line in text.splitlines()]
    result = []
    for line in lines:
        if not line and result and not result[-1]:
            continue
        result.append(line)
    return "\n".join(result).strip() + "\n"
