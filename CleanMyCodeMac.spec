# -*- mode: python ; coding: utf-8 -*-

import os
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules


project_root = Path(SPECPATH)
app_root = project_root / "cleanmycodemac"
icon_path = project_root / "resources" / "app.icns"
target_arch = os.environ.get("PYINSTALLER_TARGET_ARCH") or None

hiddenimports = collect_submodules("webview")
datas = collect_data_files("webview")

a = Analysis(
    ["cleanmycodemac/main.py"],
    pathex=[str(app_root)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="CleanMyCodeMac",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    target_arch=target_arch,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="CleanMyCodeMac",
)

app = BUNDLE(
    coll,
    name="CleanMyCodeMac.app",
    icon=str(icon_path) if icon_path.exists() else None,
    bundle_identifier="com.cleanmycodemac.app",
    info_plist={
        "CFBundleName": "CleanMyCodeMac",
        "CFBundleDisplayName": "CleanMyCodeMac",
        "CFBundleShortVersionString": "1.0.0",
        "CFBundleVersion": "1.0.0",
        "CFBundleIconFile": "app.icns",
        "NSHumanReadableCopyright": "Copyright © 2026 CleanMyCodeMac contributors.",
        "NSHighResolutionCapable": True,
        "LSMinimumSystemVersion": "12.0",
    },
)
