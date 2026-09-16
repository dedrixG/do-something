# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

repo = Path(SPECPATH).resolve().parents[1]

a = Analysis(
    [str(repo / "do_something.py")],
    pathex=[str(repo)],
    binaries=[],
    datas=[
        (str(repo / "share" / "icon.svg"), "share"),
        (str(repo / "share" / "icon-256.png"), "share"),
    ],
    hiddenimports=["PySide6.QtSvg", "shiboken6"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter",
        "matplotlib",
        "numpy",
        "PySide6.QtWebEngineCore",
        "PySide6.QtWebEngineWidgets",
        "PySide6.QtWebEngineQuick",
        "PySide6.Qt3DCore",
        "PySide6.QtBluetooth",
        "PySide6.QtNfc",
        "PySide6.QtPdf",
        "PySide6.QtDesigner",
        "PySide6.QtTest",
        "PySide6.QtQuick",
        "PySide6.QtQml",
        "PySide6.QtMultimedia",
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="do-something",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="do-something",
)
