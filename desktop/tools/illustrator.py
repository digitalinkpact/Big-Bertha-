"""Adobe Illustrator tool — runs ExtendScript via COM (Windows) or osascript (macOS).

This tool lets the Baccano AI agent control Illustrator by executing
ExtendScript (JSX) snippets.  Every action requires user approval.
"""

from __future__ import annotations

import asyncio
import platform
import shutil
import tempfile
from pathlib import Path
from typing import Any

from nanobot.agent.tools.base import Tool


class IllustratorTool(Tool):
    """Execute ExtendScript in Adobe Illustrator."""

    @property
    def name(self) -> str:
        return "illustrator"

    @property
    def description(self) -> str:
        return (
            "Run an ExtendScript (JSX) snippet inside Adobe Illustrator. "
            "Use this to open files, create artwork, export, manipulate "
            "layers, etc.  Requires Illustrator to be installed."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "script": {
                    "type": "string",
                    "description": "ExtendScript (JSX) code to execute in Illustrator",
                },
                "description": {
                    "type": "string",
                    "description": "Human-readable summary of what this script does",
                },
            },
            "required": ["script", "description"],
        }

    async def execute(self, script: str, description: str, **kwargs: Any) -> str:
        from desktop.tools.approval import require_approval

        approved = await require_approval(
            tool="Adobe Illustrator",
            action=description,
            details=script[:500],
            risk_level="medium",
        )
        if not approved:
            return "Action denied by user."

        system = platform.system()
        if system == "Windows":
            return await self._run_windows(script)
        elif system == "Darwin":
            return await self._run_macos(script)
        else:
            return "Error: Illustrator control is only supported on Windows and macOS."

    # ------------------------------------------------------------------
    # Windows — COM via PowerShell
    # ------------------------------------------------------------------

    async def _run_windows(self, script: str) -> str:
        # Write script to a temp .jsx file to avoid shell-escaping issues
        with tempfile.NamedTemporaryFile(
            suffix=".jsx", mode="w", delete=False, encoding="utf-8",
        ) as f:
            f.write(script)
            jsx_path = f.name

        ps_cmd = (
            '$ai = New-Object -ComObject Illustrator.Application; '
            f'$ai.DoJavaScriptFile("{jsx_path}")'
        )
        try:
            proc = await asyncio.create_subprocess_exec(
                "powershell", "-NoProfile", "-Command", ps_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)
        finally:
            Path(jsx_path).unlink(missing_ok=True)

        if proc.returncode != 0:
            return f"Error (exit {proc.returncode}): {stderr.decode(errors='replace')}"
        return stdout.decode(errors="replace").strip() or "(script completed)"

    # ------------------------------------------------------------------
    # macOS — osascript → AppleScript → do javascript
    # ------------------------------------------------------------------

    async def _run_macos(self, script: str) -> str:
        escaped = script.replace("\\", "\\\\").replace('"', '\\"')
        apple_script = (
            'tell application "Adobe Illustrator"\n'
            f'  do javascript "{escaped}"\n'
            "end tell"
        )
        proc = await asyncio.create_subprocess_exec(
            "osascript", "-e", apple_script,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)

        if proc.returncode != 0:
            return f"Error (exit {proc.returncode}): {stderr.decode(errors='replace')}"
        return stdout.decode(errors="replace").strip() or "(script completed)"
