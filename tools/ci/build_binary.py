#!/usr/bin/env python3
"""
Build a standalone binary using PyInstaller with sensible auto-detection.

- Prefer a PyInstaller .spec file in ./pyinstaller/*.spec
- Otherwise, try to detect an entry point via pyproject [project.scripts]
- Otherwise, fall back to searching for src/**/__main__.py

Outputs a zipped artifact named:
  {name}-{version}-{platform}.zip
under the provided --out directory (default: dist/release).

This script is safe to import: its main logic runs only under __main__.
"""
from __future__ import annotations

import argparse
import importlib
import importlib.metadata as metadata
import os
import platform
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

try:
    import tomllib  # Python 3.11+
except Exception:  # pragma: no cover - backport only if needed
    tomllib = None  # type: ignore


@dataclass
class BuildPlan:
    spec_file: Optional[Path]
    entry_file: Optional[Path]
    app_name: str


def debug(msg: str) -> None:
    print(f"[build_binary] {msg}")


def get_version(default: str = "0.0.0") -> str:
    """Extract version from GITHUB_REF tag, or installed package, or fallback.
    """
    # 1) From tag (e.g., refs/tags/v1.2.3)
    ref = os.environ.get("GITHUB_REF", "")
    m = re.match(r"refs/tags/v(?P<v>[0-9]+\.[0-9]+\.[0-9]+.*)", ref)
    if m:
        return m.group("v")

    # 2) From installed package (best-effort)
    for candidate in ("amor-mortuorum", "amor_mortuorum", "amormortuorum"):
        try:
            return metadata.version(candidate)
        except metadata.PackageNotFoundError:
            continue
        except Exception:
            break
    return default


def platform_tag() -> str:
    sysname = platform.system().lower()
    machine = platform.machine().lower()

    # Normalize architecture
    arch = "x86_64"
    if machine in ("x86_64", "amd64"):  # Windows reports AMD64
        arch = "x86_64"
    elif machine in ("arm64", "aarch64"):
        arch = "arm64"

    if sysname.startswith("darwin") or sysname == "mac" or sysname == "macos":
        return f"macos-{arch}"
    if sysname.startswith("win"):
        return f"windows-{arch}"
    return f"linux-{arch}"


def find_spec_file(root: Path) -> Optional[Path]:
    # Prefer ./pyinstaller/*.spec
    pi = root / "pyinstaller"
    if pi.exists():
        specs = sorted(pi.glob("*.spec"))
        if specs:
            return specs[0]
    # Fallback: any .spec
    any_specs = sorted(root.glob("*.spec"))
    if any_specs:
        return any_specs[0]
    # Deep search as last resort
    for p in root.rglob("*.spec"):
        return p
    return None


def parse_pyproject_entrypoint(pyproject: Path) -> Optional[str]:
    if not pyproject.exists() or tomllib is None:
        return None
    try:
        data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    except Exception:
        return None
    proj = data.get("project", {})
    scripts = proj.get("scripts") or {}
    if not isinstance(scripts, dict) or not scripts:
        return None
    # take first script command 'module:func'
    first = next(iter(scripts.values()))
    if isinstance(first, str) and ":" in first:
        return first
    return None


def resolve_module_file(module_path: str) -> Optional[Path]:
    """Resolve a "module.sub:func" to the module file path via importlib."""
    mod_name = module_path.split(":", 1)[0]
    try:
        mod = importlib.import_module(mod_name)
    except Exception:
        return None
    file = getattr(mod, "__file__", None)
    if not file:
        return None
    return Path(file)


def find_src_main(root: Path) -> Optional[Path]:
    src = root / "src"
    if not src.exists():
        return None
    candidates = list(src.rglob("__main__.py"))
    if not candidates:
        return None
    # If multiple, prefer package names that look like the project
    preferred = [
        p for p in candidates if p.parent.name in ("amor_mortuorum", "amormortuorum", "game", "app")
    ]
    return preferred[0] if preferred else candidates[0]


def detect_entrypoint(root: Path) -> Optional[Path]:
    # Try pyproject scripts first
    pp = root / "pyproject.toml"
    ep = parse_pyproject_entrypoint(pp)
    if ep:
        mod_file = resolve_module_file(ep)
        if mod_file and mod_file.exists():
            return mod_file
    # Fallback to src/**/__main__.py
    return find_src_main(root)


def run_pyinstaller_with_spec(spec_file: Path) -> None:
    cmd = [sys.executable, "-m", "PyInstaller", str(spec_file)]
    debug(f"Running PyInstaller with spec: {' '.join(cmd)}")
    subprocess.run(cmd, check=True)


def run_pyinstaller_on_entry(entry_file: Path, name: str) -> None:
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--clean",
        "--onefile",
        "--name",
        name,
        str(entry_file),
    ]
    debug(f"Running PyInstaller on entry: {' '.join(cmd)}")
    subprocess.run(cmd, check=True)


def guess_built_binary(dist_dir: Path, preferred_name: Optional[str] = None) -> Optional[Path]:
    if not dist_dir.exists():
        return None

    # If we know the name, check obvious candidates first
    if preferred_name:
        base = dist_dir / preferred_name
        win = dist_dir / f"{preferred_name}.exe"
        if base.exists() and base.is_file():
            return base
        if win.exists() and win.is_file():
            return win
        # One-folder
        folder = dist_dir / preferred_name
        if folder.exists() and folder.is_dir():
            # executable inside folder
            inner_win = folder / f"{preferred_name}.exe"
            inner_unix = folder / preferred_name
            if inner_win.exists():
                return inner_win
            if inner_unix.exists():
                return inner_unix

    # Otherwise: pick the most recently modified file in dist or one level deep
    candidates: List[Path] = []
    for p in dist_dir.glob("*"):
        if p.is_file():
            candidates.append(p)
        elif p.is_dir():
            for q in p.glob("*"):
                if q.is_file():
                    candidates.append(q)
    if not candidates:
        return None
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0]


def zip_artifact(binary: Path, out_dir: Path, name: str, version: str, plat: str) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    archive = out_dir / f"{name}-{version}-{plat}.zip"
    import zipfile

    root = Path.cwd()
    readme = next((p for p in (root / "README.md", root / "readme.md") if p.exists()), None)
    license_file = None
    for candidate in ("LICENSE", "LICENSE.txt", "LICENSE.md", "COPYING", "COPYING.txt"):
        p = root / candidate
        if p.exists():
            license_file = p
            break

    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.write(binary, arcname=binary.name)
        if readme:
            zf.write(readme, arcname=readme.name)
        if license_file:
            zf.write(license_file, arcname=license_file.name)
    debug(f"Created artifact: {archive}")
    return archive


def prepare_environment() -> None:
    # Ensure PyInstaller is available
    if shutil.which("pyinstaller") is None:
        debug("PyInstaller not found on PATH; attempting to install...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=True)


def make_build_plan(root: Path, name: str) -> BuildPlan:
    spec = find_spec_file(root)
    if spec is not None:
        return BuildPlan(spec_file=spec, entry_file=None, app_name=name)
    entry = detect_entrypoint(root)
    return BuildPlan(spec_file=None, entry_file=entry, app_name=name)


def build(plan: BuildPlan) -> Path:
    prepare_environment()
    dist_dir = Path.cwd() / "dist"
    dist_dir.mkdir(exist_ok=True)

    if plan.spec_file is not None:
        debug(f"Using spec file: {plan.spec_file}")
        run_pyinstaller_with_spec(plan.spec_file)
        built = guess_built_binary(dist_dir, None)
    else:
        if plan.entry_file is None:
            raise SystemExit(
                "Could not detect an application entry point. Provide a .spec file or "
                "define [project.scripts] in pyproject.toml or add src/**/__main__.py"
            )
        debug(f"Using entry file: {plan.entry_file}")
        run_pyinstaller_on_entry(plan.entry_file, plan.app_name)
        built = guess_built_binary(dist_dir, plan.app_name)

    if not built or not built.exists():
        raise SystemExit("Build completed but no binary was found in dist/")
    return built


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build standalone binary and zip it for release"
    )
    parser.add_argument(
        "--name",
        default="AmorMortuorum",
        help="Base application/binary name",
    )
    parser.add_argument(
        "--out",
        default="dist/release",
        help="Output directory for zipped artifact",
    )
    args = parser.parse_args(argv)

    root = Path.cwd()
    plan = make_build_plan(root, args.name)

    debug(
        "Build plan: spec_file=%s, entry_file=%s, app_name=%s"
        % (plan.spec_file, plan.entry_file, plan.app_name)
    )
    binary = build(plan)

    version = get_version()
    plat = platform_tag()
    out_dir = Path(args.out)
    artifact = zip_artifact(binary, out_dir, args.name, version, plat)

    # Write a pointer file for CI steps if needed
    (out_dir / "artifacts.txt").write_text(str(artifact) + "\n", encoding="utf-8")
    print(str(artifact))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
