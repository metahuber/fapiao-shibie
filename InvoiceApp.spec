# -*- mode: python ; coding: utf-8 -*-

"""PyInstaller 打包配置 — 数电发票识别工具"""

from pathlib import Path

SRC_DIR = Path('.')
RESOURCES = [
    (str(SRC_DIR / 'InvoiceApp' / 'resources'), 'InvoiceApp/resources'),
]

a = Analysis(
    ['InvoiceApp/__main__.py'],
    pathex=[str(SRC_DIR)],
    binaries=[],
    datas=RESOURCES,
    hiddenimports=[
        'PySide6.QtCore',
        'PySide6.QtGui',
        'PySide6.QtWidgets',
        'PySide6.QtSvg',
        'pdfplumber',
        'openpyxl',
        'fitz',
        'PIL',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'test', 'unittest', 'distutils'],
    win_no_prefer_redirects=False,
    win_prefer_optional_redirects=True,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='数电发票识别工具',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='数电发票识别工具',
)
