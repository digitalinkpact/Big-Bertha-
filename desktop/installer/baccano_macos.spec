"""PyInstaller build spec for Baccano AI Desktop — macOS .app

Usage:
    pip install pyinstaller
    python -m PyInstaller desktop/installer/baccano_macos.spec
"""

# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

block_cipher = None

ROOT = Path(SPECPATH).parent.parent  # repo root

a = Analysis(
    [str(ROOT / "desktop" / "app.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[
        (str(ROOT / "streamlit_app"), "streamlit_app"),
        (str(ROOT / "nanobot"), "nanobot"),
        (str(ROOT / "desktop"), "desktop"),
        (str(ROOT / "nanobot" / "skills"), "nanobot/skills"),
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
    noarchive=False,
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="BaccanoAI",
    debug=False,
    strip=False,
    upx=True,
    console=False,
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

app = BUNDLE(
    coll,
    name="Baccano AI.app",
    icon=str(ROOT / "desktop" / "installer" / "baccano.icns")
    if (ROOT / "desktop" / "installer" / "baccano.icns").exists()
    else None,
    bundle_identifier="com.baccano.ai",
    info_plist={
        "CFBundleShortVersionString": "0.1.4",
        "CFBundleName": "Baccano AI",
        "NSHighResolutionCapable": True,
    },
)
