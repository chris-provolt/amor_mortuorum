# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for GUI build (windowed) of Amor Mortuorum MVP
# Works on Windows/macOS/Linux. Run: pyinstaller -y pyinstaller/amor_mortuorum_gui.spec

import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# Ensure project src is on analysis path
project_root = Path(__file__).resolve().parents[1]
src_dir = project_root / "src"

block_cipher = None

hiddenimports = []
hiddenimports += collect_submodules("arcade")
hiddenimports += collect_submodules("pyglet")

# Collect resource files for arcade if present
# This can be heavy, but ensures required resources are present for simple MVP
arcade_datas = collect_data_files("arcade")

# Optionally include your own data folder if it exists
project_data_dir = project_root / "data"
proj_datas = []
if project_data_dir.exists():
    # Include entire data tree at runtime folder 'data'
    for p in project_data_dir.rglob('*'):
        if p.is_file():
            rel = p.relative_to(project_root)
            proj_datas.append((str(p), str(rel.parent)))


a = Analysis(
    [str(src_dir / "amor_mortuorum" / "__main__.py")],
    pathex=[str(project_root), str(src_dir)],
    binaries=[],
    datas=arcade_datas + proj_datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    name="AmorMortuorum",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # windowed app
    disable_windowed_traceback=False,
    argv_emulation=sys.platform == "darwin",  # better app bundle arg handling on macOS
    target_arch=None,
)

# For a single-file executable
coll = COLLECT(exe, name="AmorMortuorum")
