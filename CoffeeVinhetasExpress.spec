# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
from PyInstaller.utils.hooks import collect_submodules

project_root = Path(SPECPATH)
binaries = []
for exe_name in ("ffmpeg.exe", "ffprobe.exe"):
    exe_path = project_root / exe_name
    if exe_path.is_file():
        binaries.append((str(exe_path), "."))

hiddenimports = collect_submodules("coffee_vinhetas")

assets_dir = project_root / "src" / "coffee_vinhetas" / "assets"
datas = [(str(assets_dir), "coffee_vinhetas/assets")] if assets_dir.is_dir() else []

a = Analysis(
    ["main.py"],
    pathex=[str(project_root / "src")],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="CoffeeVinhetasExpress",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
)
