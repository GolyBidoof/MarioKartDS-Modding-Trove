#!/usr/bin/env python3
# Mario Kart DS Modding Trove
# bootstrap.py — first-run tool bootstrap
# SPDX-License-Identifier: MIT
"""Fetch or build the public tools used by apply.py.

Existing tools are reused.  Missing ones are handled automatically:
  - NCPatcher 2.x: cloned from the upstream ncp_v2 branch and built with CMake.
  - Arm GNU Toolchain: the latest xPack release for this OS/architecture,
    downloaded into .tools/ (no version pinned here).

Run ``python3 bootstrap.py --check`` to only report what is found.
"""
from __future__ import annotations

import hashlib
import json
import platform
import shutil
import subprocess
import sys
import tarfile
import urllib.request
import zipfile
from pathlib import Path

from tools import patch

REPO = Path(__file__).resolve().parent
TOOLS = REPO / ".tools"

NCPATCHER_REPO = "https://github.com/TheGameratorT/NCPatcher.git"
NCPATCHER_BRANCH = "ncp_v2"
XPACK_API = ("https://api.github.com/repos/xpack-dev-tools/"
             "arm-none-eabi-gcc-xpack/releases/latest")
ARM_PAGE = "https://developer.arm.com/downloads/-/arm-gnu-toolchain-downloads"


class SetupError(RuntimeError):
    pass


def _run(cmd: list[str], cwd: Path | None = None) -> None:
    result = subprocess.run(cmd, cwd=cwd)
    if result.returncode != 0:
        raise SetupError(f"command failed: {' '.join(cmd)}")


def _require(cmd: str, hint: str) -> None:
    if not shutil.which(cmd):
        raise SetupError(f"{cmd} not found. {hint}")


def _github_json(url: str) -> dict:
    request = urllib.request.Request(
        url, headers={"User-Agent": "mkds-modding-trove"})
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.load(response)


def _platform_tag() -> str:
    system = platform.system()
    machine = platform.machine().lower()
    if system == "Darwin":
        return "darwin-arm64" if machine in ("arm64", "aarch64") else "darwin-x64"
    if system == "Linux":
        return "linux-arm64" if machine in ("arm64", "aarch64") else "linux-x64"
    if system == "Windows":
        return "win32-x64"
    raise SetupError(
        f"no automatic toolchain for {system}/{platform.machine()}; "
        f"install arm-none-eabi-gcc from {ARM_PAGE}")


def _latest_toolchain_asset() -> dict:
    release = _github_json(XPACK_API)
    tag = _platform_tag()
    for asset in release.get("assets", []):
        name = asset["name"]
        if f"-{tag}." in name and name.endswith((".tar.gz", ".zip")):
            return asset
    raise SetupError(
        f"the latest xPack release has no {tag} archive; see {ARM_PAGE}")


def _download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f"   downloading {url}")
    urllib.request.urlretrieve(url, dest)


def _verify_sha(archive: Path, sha_asset: dict) -> None:
    request = urllib.request.Request(
        sha_asset["browser_download_url"],
        headers={"User-Agent": "mkds-modding-trove"})
    with urllib.request.urlopen(request, timeout=60) as response:
        expected = response.read().decode("ascii", "replace").split()[0].lower()
    actual = hashlib.sha256(archive.read_bytes()).hexdigest()
    if actual != expected:
        raise SetupError(f"SHA-256 mismatch for {archive.name}")


def _extract(archive: Path, dest: Path) -> Path:
    dest.mkdir(parents=True, exist_ok=True)
    if archive.suffix == ".zip":
        with zipfile.ZipFile(archive) as zf:
            zf.extractall(dest)
    else:
        with tarfile.open(archive, "r:gz") as tf:
            if sys.version_info >= (3, 12):
                tf.extractall(dest, filter="data")
            else:
                tf.extractall(dest)
    gcc = next(dest.rglob("bin/arm-none-eabi-gcc*"), None)
    if gcc is None:
        raise SetupError(f"{archive.name} has no bin/arm-none-eabi-gcc")
    for binary in gcc.parent.iterdir():
        if binary.is_file():
            binary.chmod(binary.stat().st_mode | 0o111)
    return gcc


def _install_toolchain() -> Path:
    asset = _latest_toolchain_asset()
    archive = TOOLS / asset["name"]
    _download(asset["browser_download_url"], archive)
    sha_name = asset["name"] + ".sha"
    sha_asset = next((a for a in
                      _github_json(XPACK_API).get("assets", [])
                      if a["name"] == sha_name), None)
    if sha_asset:
        _verify_sha(archive, sha_asset)
    print("   extracting ...")
    gcc = _extract(archive, TOOLS / "arm-gnu-toolchain")
    archive.unlink()
    print(f"   arm-none-eabi-gcc: {gcc}")
    return gcc


def _build_ncpatcher() -> Path:
    _require("git", "Install Git: https://git-scm.com/downloads")
    _require("cmake", "Install CMake: https://cmake.org/download/")
    if not any(shutil.which(cxx) for cxx in ("c++", "clang++", "g++")):
        raise SetupError(
            "no C++ compiler found (install Xcode command line tools, "
            "build-essential, or MSVC)")

    dest = TOOLS / "NCPatcher"
    if (dest / ".git").is_dir():
        _run(["git", "fetch", "--depth", "1", "origin", NCPATCHER_BRANCH], dest)
        _run(["git", "reset", "--hard", "FETCH_HEAD"], dest)
    else:
        dest.parent.mkdir(parents=True, exist_ok=True)
        _run(["git", "clone", "--branch", NCPATCHER_BRANCH, "--depth", "1",
              NCPATCHER_REPO, str(dest)])

    print("   building NCPatcher ...")
    _run(["cmake", "-B", "build", "-DCMAKE_BUILD_TYPE=Release"], dest)
    _run(["cmake", "--build", "build", "--parallel"], dest)
    candidates = [
        dest / "build" / "ncpatcher",
        dest / "build" / "ncpatcher.exe",
        *dest.glob("build/*/ncpatcher.exe"),
    ]
    binary = next((path for path in candidates if path.exists()), None)
    if binary is None:
        raise SetupError("NCPatcher build produced no ncpatcher binary")
    print(f"   NCPatcher: {binary}")
    return binary


def ensure_tools() -> patch.Tools:
    try:
        tools = patch.locate()
        print("Tools ready:")
        print(f"   NCPatcher: {tools.ncpatcher}")
        print(f"   arm-none-eabi-gcc: {tools.toolchain_bin / 'arm-none-eabi-gcc'}")
        return tools
    except patch.ToolError as exc:
        print(f"   {exc}")

    try:
        patch.find_ncpatcher()
    except patch.ToolError:
        _build_ncpatcher()
    try:
        patch.find_gcc()
    except patch.ToolError:
        _install_toolchain()

    tools = patch.locate()
    print("Tools ready:")
    print(f"   NCPatcher: {tools.ncpatcher}")
    print(f"   arm-none-eabi-gcc: {tools.toolchain_bin}")
    return tools


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if any(arg in ("-h", "--help") for arg in argv):
        print(__doc__)
        return 0
    if "--check" in argv:
        try:
            tools = patch.locate()
        except patch.ToolError as exc:
            print(exc, file=sys.stderr)
            return 1
        print(f"NCPatcher: {tools.ncpatcher}")
        print(f"SDK: {tools.sdk}")
        print(f"arm-none-eabi-gcc: {tools.toolchain_bin / 'arm-none-eabi-gcc'}")
        return 0

    try:
        ensure_tools()
    except (SetupError, patch.ToolError, OSError) as exc:
        print(f"setup failed: {exc}", file=sys.stderr)
        return 1
    print("\nReady. Run: python3 apply.py /path/to/game.nds")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
