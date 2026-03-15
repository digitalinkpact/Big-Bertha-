"""PyInstaller build spec for Baccano AI Desktop — Windows .exe

Usage:
    pip install pyinstaller
    python -m PyInstaller desktop/installer/baccano_windows.spec
"""

# -*- mode: python ; coding: utf-8 -*-
import sys
from pathlib import Path

block_cipher = None

ROOT = Path(SPECPATH).parent.parent  # repo root

a = Analysis(
    [str(ROOT / "desktop" / "app.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[
        # Include streamlit app
        (str(ROOT / "streamlit_app"), "streamlit_app"),
        # Include nanobot package
        (str(ROOT / "nanobot"), "nanobot"),
        # Include desktop tools
        (str(ROOT / "desktop"), "desktop"),
        # Include skills
        (str(ROOT / "nanobot" / "skills"), "nanobot/skills"),
        # Include templates
        (str(ROOT / "nanobot" / "templates"), "nanobot/templates"),
    ],
    hiddenimports=[
        "streamlit",
        "nanobot",
        "nanobot.cli.commands",
        "nanobot.config.loader",
        "nanobot.config.schema",
        "nanobot.providers.litellm_provider",
        "nanobot.agent.loop",
        "nanobot.bus.queue",
        "desktop.tools",
        "desktop.tools.illustrator",
        "desktop.tools.autocad",
        "desktop.tools.solidworks",
        "desktop.tools.blender",
        "desktop.tools.approval",
        "pystray",
        "PIL",
        "litellm",
        "pydantic",
        "typer",
        "httpx",
        "tiktoken",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="BaccanoAI",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # No console window — runs as GUI app
    icon=str(ROOT / "desktop" / "installer" / "baccano.ico")
    if (ROOT / "desktop" / "installer" / "baccano.ico").exists()
    else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="BaccanoAI",
)
