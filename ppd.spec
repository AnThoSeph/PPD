# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec — builds dist/PPD-Resume/PPD-Resume.exe"""

import sys
from pathlib import Path

ROOT = Path(SPECPATH)

a = Analysis(
    [str(ROOT / "ppd" / "gui_web.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[
        (str(ROOT / "templates"), "templates"),
        (str(ROOT / "templates" / "reference"), "templates/reference"),
        (str(ROOT / "ppd" / "web"), "ppd/web"),
        (str(ROOT / "data" / "config.yaml"), "data"),
        (str(ROOT / "data" / "resume.yaml"), "data"),
    ],
    hiddenimports=[
        "pymupdf",
        "fitz",
        "PIL",
        "PIL.Image",
        "pytesseract",
        "pydantic",
        "yaml",
        "click",
        "webview",
        "ppd.api",
        "ppd.ats",
        "ppd.assistant",
        "ppd.gui_web",
        "ppd.design",
        "ppd.preview_render",
        "ppd.cli",
        "ppd.forensics",
        "ppd.import_file",
        "ppd.import_image",
        "ppd.import_pdf",
        "ppd.import_semantic",
        "ppd.resume_v2",
        "ppd.template_catalog",
        "ppd.paths",
        "ppd.schema",
        "ppd.build",
    ],
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
    name="PPD-Resume",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="PPD-Resume",
)
