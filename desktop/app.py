"""Baccano AI Desktop — main entry point.

Starts the Streamlit UI and optionally a system-tray icon.
This is what PyInstaller packages into the .exe / .app.

Usage:
    python -m desktop.app          # or just double-click the packaged exe
    python -m desktop.app --no-tray  # skip system tray (debugging)
"""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import threading
import webbrowser
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_HOST = "127.0.0.1"
_PORT = 8501
_URL = f"http://{_HOST}:{_PORT}"

# Locate the streamlit_app relative to this file
_ROOT = Path(__file__).resolve().parent.parent
_STREAMLIT_APP = _ROOT / "streamlit_app" / "app.py"


def _find_streamlit() -> str:
    """Find the streamlit executable."""
    # When packaged, streamlit is on PATH inside the bundle
    import shutil
    s = shutil.which("streamlit")
    if s:
        return s
    # Fallback: run as module
    return f"{sys.executable} -m streamlit"


# ---------------------------------------------------------------------------
# System tray (optional — requires pystray + Pillow)
# ---------------------------------------------------------------------------

def _run_tray(stop_event: threading.Event) -> None:
    """Show a system-tray icon with Open / Quit options."""
    try:
        import pystray
        from PIL import Image, ImageDraw
    except ImportError:
        return  # pystray not installed — skip silently

    # Create a simple icon (blue circle with "B")
    img = Image.new("RGB", (64, 64), color=(30, 30, 30))
    draw = ImageDraw.Draw(img)
    draw.ellipse([4, 4, 60, 60], fill=(0, 120, 255))
    draw.text((22, 16), "B", fill="white")

    def on_open(icon, item):
        webbrowser.open(_URL)

    def on_quit(icon, item):
        stop_event.set()
        icon.stop()

    icon = pystray.Icon(
        "baccano-ai",
        img,
        "Baccano AI",
        menu=pystray.Menu(
            pystray.MenuItem("Open Baccano AI", on_open, default=True),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quit", on_quit),
        ),
    )
    icon.run()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    no_tray = "--no-tray" in sys.argv

    stop_event = threading.Event()

    # Start system tray in a background thread
    if not no_tray:
        tray_thread = threading.Thread(target=_run_tray, args=(stop_event,), daemon=True)
        tray_thread.start()

    # Build the streamlit command
    streamlit_bin = _find_streamlit()
    cmd = (
        f"{streamlit_bin} run {_STREAMLIT_APP} "
        f"--server.port {_PORT} "
        f"--server.address {_HOST} "
        f"--server.headless true "
        f"--browser.gatherUsageStats false"
    )

    # Start Streamlit as a subprocess
    proc = subprocess.Popen(
        cmd,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )

    # Open the browser after a short delay
    def _open_browser():
        import time
        time.sleep(3)
        webbrowser.open(_URL)

    threading.Thread(target=_open_browser, daemon=True).start()

    # Wait for either Streamlit to exit or tray quit signal
    try:
        while not stop_event.is_set():
            retcode = proc.poll()
            if retcode is not None:
                break
            stop_event.wait(timeout=1)
    except KeyboardInterrupt:
        pass
    finally:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()

    sys.exit(0)


if __name__ == "__main__":
    main()
