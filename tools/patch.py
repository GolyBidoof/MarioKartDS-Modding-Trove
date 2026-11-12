# Mario Kart DS Modding Trove
# tools/patch.py — NCPatcher project, conflicts and verification
# SPDX-License-Identifier: MIT
# Notes: docs/nitro.md, docs/bmg.md
"""Locate the public toolchain and drive NCPatcher.

Background: docs/nitro.md (ROM/archive formats), docs/bmg.md (BMG repair).
Mod-specific detection lives with the mod (see mods/options-cc/profile.py).
"""
from __future__ import annotations

import dataclasses
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from . import nds
from .bmg import Bmg
from .mods import Mod
from .verify import VerifyError

REPO = Path(__file__).resolve().parent.parent
WORKSPACE = REPO.parent

DEFAULT_NCPATCHER = [
    WORKSPACE / "NCPatcher" / "build-v2" / "ncpatcher",
    WORKSPACE / "NCPatcher" / "build-v2" / "ncpatcher.exe",
    WORKSPACE / "NCPatcher" / "build" / "ncpatcher",
    WORKSPACE / "NCPatcher" / "build" / "ncpatcher.exe",
    REPO / ".tools" / "NCPatcher" / "build" / "ncpatcher",
    REPO / ".tools" / "NCPatcher" / "build" / "ncpatcher.exe",
    REPO / ".tools" / "ncpatcher" / "ncpatcher",
    REPO / ".tools" / "ncpatcher" / "ncpatcher.exe",
]


class ToolError(RuntimeError):
    pass


@dataclass(frozen=True)
class Tools:
    ncpatcher: Path
    sdk: Path
    toolchain_bin: Path | None


def _first(env: str, candidates: list[Path], what: str) -> Path:
    value = os.environ.get(env)
    if value:
        path = Path(value).expanduser()
        if path.exists():
            return path
        raise ToolError(f"{env} points at {path}, which does not exist")
    for path in candidates:
        if path.exists():
            return path
    raise ToolError(
        f"cannot find {what}; run python3 bootstrap.py or set {env} to one of:\n  "
        + "\n  ".join(str(p) for p in candidates))


def find_ncpatcher() -> Path:
    path = _first("NCPATCHER", DEFAULT_NCPATCHER, "NCPatcher")
    if not os.access(path, os.X_OK):
        raise ToolError(f"{path} is not executable")
    return path


def _find_sdk(ncpatcher: Path) -> Path:
    value = os.environ.get("NCPATCHER_SDK")
    sdk = Path(value).expanduser() if value else ncpatcher.parent
    if (sdk / "ncp.h").exists():
        return sdk
    for candidate in (ncpatcher.parent / "include",
                      ncpatcher.parent.parent / "share" / "ncpatcher"):
        if (candidate / "ncp.h").exists():
            return candidate
    raise ToolError(f"cannot find ncp.h next to {ncpatcher}; set NCPATCHER_SDK")


def find_gcc() -> Path:
    for env in ("ARM_GCC", "ARM_NONE_EABI_GCC"):
        value = os.environ.get(env)
        if value:
            path = Path(value).expanduser()
            if path.is_file():
                return path
            raise ToolError(f"{env} points at {path}, which does not exist")
    root = os.environ.get("ARM_TOOLCHAIN")
    if root:
        path = Path(root).expanduser() / "bin" / "arm-none-eabi-gcc"
        if path.is_file():
            return path
        raise ToolError(f"ARM_TOOLCHAIN has no bin/arm-none-eabi-gcc: {root}")
    for env, subdir in (("DEVKITARM", ""), ("DEVKITPRO", "devkitARM")):
        value = os.environ.get(env)
        if not value:
            continue
        path = (Path(value).expanduser() / subdir / "bin"
                / "arm-none-eabi-gcc")
        if path.is_file():
            return path
    which = shutil.which("arm-none-eabi-gcc")
    if which:
        return Path(which)
    for pattern in ("arm-gnu-toolchain*/**/bin/arm-none-eabi-gcc",
                    "arm-gnu-toolchain*/**/bin/arm-none-eabi-gcc.exe"):
        matches = sorted((REPO / ".tools").glob(pattern))
        if matches:
            return matches[0]
    raise ToolError("cannot find arm-none-eabi-gcc; run python3 bootstrap.py")


def locate() -> Tools:
    ncpatcher = find_ncpatcher()
    gcc = find_gcc()
    return Tools(ncpatcher=ncpatcher, sdk=_find_sdk(ncpatcher),
                 toolchain_bin=gcc.parent)


def _profile_fields(profile: object) -> dict[str, object]:
    if dataclasses.is_dataclass(profile):
        return dataclasses.asdict(profile)
    if isinstance(profile, Mapping):
        return dict(profile)
    return vars(profile)


def _format_value(value: object) -> str:
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, (list, tuple)):
        return ", ".join(_format_value(item) for item in value)
    if isinstance(value, int):
        # Addresses are large; engine values and ids are small and read
        # better in decimal in the generated assembly.
        if -0x10000 < value < 0x10000:
            return str(value)
        return f"0x{value:08X}"
    return str(value)


def render_context(profile: object, new_ids: list[int]) -> dict[str, str]:
    context: dict[str, str] = {}
    for key, value in _profile_fields(profile).items():
        text = _format_value(value)
        context[f"profile.{key}"] = text
        context[key] = text
    context.update({
        "new_ids": ", ".join(str(i) for i in new_ids),
        "new_ids_json": json.dumps(new_ids),
        "new_id0": str(new_ids[0]) if len(new_ids) > 0 else "0",
        "new_id1": str(new_ids[1]) if len(new_ids) > 1 else "0",
        "new_id2": str(new_ids[2]) if len(new_ids) > 2 else "0",
    })
    return context


def render(text: str, context: dict[str, str]) -> str:
    for key, value in context.items():
        text = text.replace("{{" + key + "}}", str(value))
    missing = sorted(set(re.findall(r"\{\{[^}]+\}\}", text)))
    if missing:
        raise ToolError(f"unresolved placeholders: {', '.join(missing)}")
    return text


def render_mod_sources(mod: Mod, profile: object,
                       new_ids: list[int]) -> list[tuple[str, str]]:
    context = render_context(profile, new_ids)
    rendered: list[tuple[str, str]] = []
    for source in mod.sources:
        if source.when and not all(context.get(k) == v
                                   for k, v in source.when.items()):
            continue
        text = render(mod.source_text(source), context)
        rendered.append((f"{mod.id}/{Path(source.file).stem}", text))
    return rendered


_DEFINE = re.compile(
    r"^\s*#define\s+([A-Za-z_]\w*)\s+(0x[0-9A-Fa-f]+)\s*$", re.MULTILINE)
_OVER = re.compile(
    r"\b(?:ncp_over|NCP_OVER)\s*\(\s*([A-Za-z_]\w*|0x[0-9A-Fa-f]+)\s*\)")
_ADDRESS_FIRST_ARG = re.compile(
    r"\bncp_(?:t?jump|t?call|t?hook|repl)\s*\(\s*(0x[0-9A-Fa-f]+)")
_SET_ADDRESS = re.compile(
    r"\bncp_set_(?:t?jump|t?call|t?hook)\s*\(\s*(0x[0-9A-Fa-f]+)")


def patch_addresses(text: str) -> set[int]:
    defines = {name: int(value, 16)
               for name, value in _DEFINE.findall(text)}
    found: set[int] = set()
    for match in _OVER.finditer(text):
        arg = match.group(1)
        if arg in defines:
            found.add(defines[arg])
        elif arg.startswith("0x"):
            found.add(int(arg, 16))
    for regex in (_ADDRESS_FIRST_ARG, _SET_ADDRESS):
        for match in regex.finditer(text):
            found.add(int(match.group(1), 16))
    return found


def check_conflicts(rendered_by_mod: dict[str, list[str]]) -> None:
    seen: dict[int, str] = {}
    for mod_id, texts in rendered_by_mod.items():
        own = patch_addresses("\n".join(texts))
        for address in sorted(own):
            if address in seen and seen[address] != mod_id:
                raise ToolError(
                    f"mods {seen[address]!r} and {mod_id!r} both patch "
                    f"{address:#010x}; keep them independent")
            seen[address] = mod_id


def _q(value: object) -> str:
    return json.dumps(str(value), ensure_ascii=False)


def write_ncp_project(tools: Tools, work: Path, rom: Path, output: Path,
                      sources: list[tuple[str, str]],
                      bmg_files: list[tuple[str, Path]]) -> Path:
    ncp = work / "ncp"
    source = ncp / "source"
    include = ncp / "include"
    (ncp / "build").mkdir(parents=True, exist_ok=True)
    source.mkdir(parents=True, exist_ok=True)
    include.mkdir(parents=True, exist_ok=True)
    for name, text in sources:
        target = source / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text)

    lines = [
        "version: 2",
        "",
        "rom:",
        f"  file: {_q(rom.resolve())}",
        f"  output: {_q(output.resolve())}",
        f"  backup: {_q((work / 'backup').resolve())}",
        "",
        "toolchain: arm-none-eabi-",
        "",
        "build:",
        "  threads: 0",
        "",
        "flags:",
        "  common: [\"-masm-syntax-unified\", \"-mno-unaligned-access\","
        " \"-mfloat-abi=soft\", \"-mabi=aapcs\"]",
        "  c: [\"-Os\", \"-fomit-frame-pointer\", \"-fno-builtin\","
        " \"-nostdlib\", \"-nodefaultlibs\", \"-nostartfiles\"]",
        "  asm: [\"-Os\", \"-x assembler-with-cpp\", \"-fomit-frame-pointer\","
        " \"-D__ncp_lang_asm\"]",
        "  ld: [\"-lgcc\", \"-lc\"]",
        "",
    ]
    if bmg_files:
        lines.append("files:")
        for dest, path in bmg_files:
            lines.append(f"  {_q(dest)}: {_q(path.resolve())}")
        lines.append("")
    lines += [
        "targets:",
        "  arm9:",
        "    build: build/arm9",
        "    includes:",
        f"      - {_q(source)}",
        f"      - {_q(include)}",
        f"      - {_q(REPO / 'include')}",
        f"      - {_q(tools.sdk)}",
        "    defines: [SDK_ARM9]",
        "    flags:",
        "      common: [\"-march=armv5te\", \"-mtune=arm946e-s\", \"-marm\"]",
        "    regions:",
        "      - dest: main",
        "        sources:",
        f"          - {_q(str(source) + '/**')}",
        "",
    ]
    (ncp / "ncpatcher.yaml").write_text("\n".join(lines))
    return ncp


def run_ncp(tools: Tools, ncp: Path, output: Path) -> None:
    if output.exists():
        output.unlink()
    env = os.environ.copy()
    if tools.toolchain_bin:
        env["PATH"] = str(tools.toolchain_bin) + os.pathsep + env.get("PATH", "")
    result = subprocess.run([str(tools.ncpatcher), "build"], cwd=ncp,
                            env=env, capture_output=True, text=True)
    if result.returncode != 0:
        raise ToolError(
            "NCPatcher failed:\n" + result.stdout + "\n" + result.stderr)
    if not output.exists():
        raise ToolError("NCPatcher reported success but wrote no ROM")


@dataclass
class ModContext:
    profile: object
    image: nds.Arm9Image
    base: int
    new_ids: list[int]
    tools: Tools

    def u16(self, address: int) -> int:
        try:
            return self.image.u16(address)
        except KeyError as exc:
            raise VerifyError(str(exc)) from None

    def u32(self, address: int) -> int:
        try:
            return self.image.u32(address)
        except KeyError as exc:
            raise VerifyError(str(exc)) from None


def verify_global(output: Path, base: int,
                  bmg_files: list[tuple[str, Path]]) -> nds.Arm9Image:
    arm9, out_base = nds.arm9_from_nds(str(output))
    if out_base != base:
        raise VerifyError(
            f"ARM9 base changed: {out_base:#x} != {base:#x}")
    image = nds.Arm9Image(arm9, out_base)
    data = output.read_bytes()
    for dest, generated in bmg_files:
        archive, member = dest.split("!", 1)
        members = nds.unpack_narc(nds.nds_member(data, archive))
        if member not in members:
            raise VerifyError(f"{archive} lost its {member}")
        if members[member] != generated.read_bytes():
            raise VerifyError(f"{archive}!{member} does not match the generated BMG")
        Bmg(members[member])
    return image


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ToolError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(name, None)
        raise
    return module


def load_profile(mod: Mod, arm9: bytes, base: int):
    if not mod.profile:
        raise ToolError(f"mod {mod.id!r} has no profile detector")
    path = mod.path / mod.profile
    module = _load_module(path, f"mkds_profile_{mod.id.replace('-', '_')}")
    detect = getattr(module, "detect", None)
    if detect is None:
        raise ToolError(f"{path} has no detect(arm9, base) function")
    return detect(arm9, base)


def verify_mod(mod: Mod, context: ModContext) -> None:
    path = mod.verify_path()
    if path is None:
        return
    module = _load_module(path, f"mkds_mod_{mod.id.replace('-', '_')}")
    verify = getattr(module, "verify", None)
    if verify is None:
        raise ToolError(f"{path} has no verify(context) function")
    verify(context)
