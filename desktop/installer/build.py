"""Build helper — packages Baccano AI for the current platform.

Usage:
    python desktop/installer/build.py          # auto-detect OS
    python desktop/installer/build.py windows  # force Windows build
    python desktop/installer/build.py macos    # force macOS build
"""

from __future__ import annotations

import platform
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
INSTALLER_DIR = ROOT / "desktop" / "installer"


def build(target: str | None = None) -> None:
    if target is None:
        system = platform.system()
        target = "windows" if system == "Windows" else "macos" if system == "Darwin" else "linux"

    spec_map = {
        "windows": INSTALLER_DIR / "baccano_windows.spec",
        "macos": INSTALLER_DIR / "baccano_macos.spec",
    }

    spec = spec_map.get(target)
    if spec is None or not spec.exists():
        print(f"No build spec for target '{target}'. Supported: {list(spec_map.keys())}")
        sys.exit(1)

    print(f"Building Baccano AI for {target}...")
    print(f"Spec file: {spec}")

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--distpath", str(ROOT / "dist"),
        "--workpath", str(ROOT / "build"),
        str(spec),
    ]

    result = subprocess.run(cmd, cwd=str(ROOT))
    if result.returncode != 0:
        print("Build failed!")
        sys.exit(1)

    print(f"\nBuild complete! Output in: {ROOT / 'dist' / 'BaccanoAI'}")
    if target == "windows":
        print("Run: dist/BaccanoAI/BaccanoAI.exe")
    elif target == "macos":
        print("Run: open dist/BaccanoAI/Baccano\\ AI.app")


if __name__ == "__main__":
    t = sys.argv[1] if len(sys.argv) > 1 else None
    build(t)
