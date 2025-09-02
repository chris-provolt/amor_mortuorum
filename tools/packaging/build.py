from __future__ import annotations

import argparse
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path


THIS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = THIS_DIR.parents[2]
PYINSTALLER_DIR = PROJECT_ROOT / "pyinstaller"
DIST_DIR = PROJECT_ROOT / "dist"
BUILD_DIR = PROJECT_ROOT / "build"


def run(cmd: list[str]) -> int:
    print("$", " ".join(cmd))
    return subprocess.call(cmd)


def build(mode: str, clean: bool, onefile: bool) -> int:
    spec_name = "amor_mortuorum_gui.spec" if mode == "gui" else "amor_mortuorum_cli.spec"
    spec_path = PYINSTALLER_DIR / spec_name

    if clean:
        shutil.rmtree(DIST_DIR, ignore_errors=True)
        shutil.rmtree(BUILD_DIR, ignore_errors=True)

    args = [sys.executable, "-m", "PyInstaller", "-y", str(spec_path)]

    # Switch to --onefile by collapsing COLLECT? We'll rely on PyInstaller default spec COLLECT
    # and use --onefile flag when desired, which overrides the spec's default.
    if onefile:
        args.append("--onefile")

    # Set name suffix by platform for convenience
    suffix = {
        "Windows": "win",
        "Darwin": "mac",
        "Linux": "linux",
    }.get(platform.system(), "")
    if suffix:
        args.extend(["--name", f"AmorMortuorum_{mode}_{suffix}"])

    return run(args)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build Amor Mortuorum executables via PyInstaller")
    parser.add_argument("--mode", choices=["gui", "cli"], default="gui", help="Build GUI or CLI executable")
    parser.add_argument("--clean", action="store_true", help="Clean build and dist directories before building")
    parser.add_argument("--onefile", action="store_true", help="Produce a single-file executable")

    args = parser.parse_args(argv)
    return build(args.mode, args.clean, args.onefile)


if __name__ == "__main__":
    raise SystemExit(main())
