"""Blender tool — runs Python (bpy) scripts inside Blender.

Works on Windows, macOS, and Linux.
Blender is launched in background mode (``--background``) to execute
scripts, or can target an already-running instance via the command port.
"""

from __future__ import annotations

import asyncio
import platform
import shutil
import tempfile
from pathlib import Path
from typing import Any

from nanobot.agent.tools.base import Tool

# Common Blender install locations
_BLENDER_PATHS = {
    "Windows": [
        r"C:\Program Files\Blender Foundation\Blender 4.2\blender.exe",
        r"C:\Program Files\Blender Foundation\Blender 4.1\blender.exe",
        r"C:\Program Files\Blender Foundation\Blender 4.0\blender.exe",
        r"C:\Program Files\Blender Foundation\Blender 3.6\blender.exe",
    ],
    "Darwin": [
        "/Applications/Blender.app/Contents/MacOS/Blender",
    ],
    "Linux": [
        "/usr/bin/blender",
        "/snap/bin/blender",
    ],
}


def _find_blender() -> str | None:
    """Locate the Blender executable on the current system."""
    # Check PATH first
    found = shutil.which("blender")
    if found:
        return found
    # Check known locations
    for path in _BLENDER_PATHS.get(platform.system(), []):
        if Path(path).exists():
            return path
    return None


class BlenderTool(Tool):
    """Execute Python scripts in Blender (background or interactive)."""

    @property
    def name(self) -> str:
        return "blender"

    @property
    def description(self) -> str:
        return (
            "Run a Python (bpy) script in Blender. Use this for 3D modelling, "
            "rendering, animation, and file conversions. Blender runs in "
            "background mode by default, or opens the GUI if 'headless' is false."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "script": {
                    "type": "string",
                    "description": "Python script using Blender's bpy API",
                },
                "blend_file": {
                    "type": "string",
                    "description": "Optional .blend file to open before running the script",
                },
                "headless": {
                    "type": "boolean",
                    "description": "Run in background mode (no GUI). Default true.",
                },
                "description": {
                    "type": "string",
                    "description": "Human-readable summary of what this script does",
                },
            },
            "required": ["script", "description"],
        }

    async def execute(
        self,
        script: str,
        description: str,
        blend_file: str | None = None,
        headless: bool = True,
        **kwargs: Any,
    ) -> str:
        from desktop.tools.approval import require_approval

        approved = await require_approval(
            tool="Blender",
            action=description,
            details=script[:500],
            risk_level="medium",
        )
        if not approved:
            return "Action denied by user."

        blender = _find_blender()
        if not blender:
            return (
                "Error: Blender not found. Install Blender and ensure it's on "
                "your PATH, or install to a standard location."
            )

        # Write the script to a temp .py file
        with tempfile.NamedTemporaryFile(
            suffix=".py", mode="w", delete=False, encoding="utf-8",
        ) as f:
            f.write(script)
            script_path = f.name

        cmd = [blender]
        if headless:
            cmd.append("--background")
        if blend_file:
            cmd.append(blend_file)
        cmd.extend(["--python", script_path])

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=300)
        finally:
            Path(script_path).unlink(missing_ok=True)

        output = stdout.decode(errors="replace").strip()
        errors = stderr.decode(errors="replace").strip()

        # Blender prints a lot of info to stdout — trim to last 2000 chars
        if len(output) > 2000:
            output = "...(truncated)...\n" + output[-2000:]

        if proc.returncode != 0:
            return f"Error (exit {proc.returncode}):\n{errors}\n\nOutput:\n{output}"
        return output or "(script completed in Blender)"
