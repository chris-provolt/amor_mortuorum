# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for CLI (console) build of Amor Mortuorum MVP
# Run: pyinstaller -y pyinstaller/amor_mortuorum_cli.spec

import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

project_root = Path(__file__).resolve().parents[1]
src_dir = project_root / "src"

block_cipher = None

# Hidden imports are minimal for CLI, but keep arcade optionally available
hiddenimports = []
hiddenimports += collect_submodules("arcade")
hiddenimports += collect_submodules("pyglet")

arcade_datas = collect_data_files("arcade")

project_data_dir = project_root / "data"
proj_datas = []
if project_data_dir.exists():
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
    name="AmorMortuorum_CLI",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,  # console app
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
)
coll = COLLECT(exe, name="AmorMortuorum_CLI")
