# PyInstaller spec for Amor Mortuorum
# This file aims to be resilient to repository layout differences.
# You can override the entry script by setting AMOR_ENTRY to a valid Python file path.

import os
import sys
from pathlib import Path

# Compute paths
ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
DEFAULT_ENTRY = SRC / "amor_mortuorum" / "__main__.py"
ENTRY = Path(os.getenv("AMOR_ENTRY", str(DEFAULT_ENTRY))).resolve()

if not ENTRY.exists():
    raise SystemExit(f"Entry script not found: {ENTRY}. Set AMOR_ENTRY to your game's entry point.")

# Optional icons
ico = ROOT / "tools" / "pyinstaller" / "AmorMortuorum.ico"
icns = ROOT / "tools" / "pyinstaller" / "AmorMortuorum.icns"

# Collect datas for package assets/configs if present
package_root = SRC / "amor_mortuorum"

def collect_datas():
    datas = []
    for name in ("assets", "configs", "data"):
        path = package_root / name
        if path.exists():
            for p in path.rglob("*"):
                if p.is_file():
                    # (source, dest)
                    rel = p.relative_to(package_root)
                    datas.append((str(p), str(Path("amor_mortuorum") / rel.parent)))
    return datas

block_cipher = None

a = Analysis(
    [str(ENTRY)],
    pathex=[str(SRC)],
    binaries=[],
    datas=collect_datas(),
    hiddenimports=[
        # Commonly required by arcade/pyglet, adjust as needed
        "pyglet",
        "arcade",
    ],
    hookspath=[str(ROOT / "tools" / "pyinstaller" / "hooks")],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

console = False  # windowed build by default (set to True to keep console window)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="AmorMortuorum",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=console,
    icon=str(ico) if ico.exists() else (str(icns) if icns.exists() else None),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="AmorMortuorum",
)
