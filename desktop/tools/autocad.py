"""AutoCAD tool — runs AutoLISP / command-line operations.

Windows:  Uses COM automation (``AutoCAD.Application``).
macOS:    Uses AutoCAD command-line interface if available.
"""

from __future__ import annotations

import asyncio
import platform
import tempfile
from pathlib import Path
from typing import Any

from nanobot.agent.tools.base import Tool


class AutoCADTool(Tool):
    """Execute AutoLISP or send commands to AutoCAD."""

    @property
    def name(self) -> str:
        return "autocad"

    @property
    def description(self) -> str:
        return (
            "Run an AutoLISP expression or send a command string to AutoCAD. "
            "Use this to open drawings, create geometry, set layers, export DWG/PDF, etc."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": (
                        "AutoLISP expression (e.g. '(command \"LINE\" ...)') "
                        "or a .scr script body to execute"
                    ),
                },
                "mode": {
                    "type": "string",
                    "enum": ["lisp", "script"],
                    "description": "Whether 'command' is a LISP expression or a .scr script body",
                },
                "description": {
                    "type": "string",
                    "description": "Human-readable summary of what this does",
                },
            },
            "required": ["command", "description"],
        }

    async def execute(
        self,
        command: str,
        description: str,
        mode: str = "lisp",
        **kwargs: Any,
    ) -> str:
        from desktop.tools.approval import require_approval

        approved = await require_approval(
            tool="AutoCAD",
            action=description,
            details=command[:500],
            risk_level="medium",
        )
        if not approved:
            return "Action denied by user."

        system = platform.system()
        if system == "Windows":
            return await self._run_windows(command, mode)
        elif system == "Darwin":
            return await self._run_macos(command, mode)
        else:
            return "Error: AutoCAD control is only supported on Windows and macOS."

    # ------------------------------------------------------------------
    # Windows — COM automation
    # ------------------------------------------------------------------

    async def _run_windows(self, command: str, mode: str) -> str:
        if mode == "script":
            return await self._run_script_windows(command)

        # LISP via COM SendCommand
        ps_cmd = (
            '$acad = [System.Runtime.InteropServices.Marshal]::'
            'GetActiveObject("AutoCAD.Application"); '
            '$doc = $acad.ActiveDocument; '
            f'$doc.SendCommand("{command}\\n")'
        )
        proc = await asyncio.create_subprocess_exec(
            "powershell", "-NoProfile", "-Command", ps_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)

        if proc.returncode != 0:
            return f"Error (exit {proc.returncode}): {stderr.decode(errors='replace')}"
        return stdout.decode(errors="replace").strip() or "(command sent to AutoCAD)"

    async def _run_script_windows(self, script_body: str) -> str:
        """Write a .scr temp file and execute it via COM."""
        with tempfile.NamedTemporaryFile(
            suffix=".scr", mode="w", delete=False, encoding="utf-8",
        ) as f:
            f.write(script_body)
            scr_path = f.name

        ps_cmd = (
            '$acad = [System.Runtime.InteropServices.Marshal]::'
            'GetActiveObject("AutoCAD.Application"); '
            '$doc = $acad.ActiveDocument; '
            f'$doc.SendCommand("(command \\"SCRIPT\\" \\"{scr_path}\\")\\n")'
        )
        try:
            proc = await asyncio.create_subprocess_exec(
                "powershell", "-NoProfile", "-Command", ps_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)
        finally:
            Path(scr_path).unlink(missing_ok=True)

        if proc.returncode != 0:
            return f"Error (exit {proc.returncode}): {stderr.decode(errors='replace')}"
        return stdout.decode(errors="replace").strip() or "(script executed in AutoCAD)"

    # ------------------------------------------------------------------
    # macOS — accoreconsole CLI (headless) or AppleScript
    # ------------------------------------------------------------------

    async def _run_macos(self, command: str, mode: str) -> str:
        # Try accoreconsole (AutoCAD command-line on Mac)
        if mode == "script":
            with tempfile.NamedTemporaryFile(
                suffix=".scr", mode="w", delete=False, encoding="utf-8",
            ) as f:
                f.write(command)
                scr_path = f.name

            try:
                proc = await asyncio.create_subprocess_exec(
                    "/usr/local/bin/accoreconsole",
                    "-s", scr_path,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)
            finally:
                Path(scr_path).unlink(missing_ok=True)

            if proc.returncode != 0:
                return f"Error (exit {proc.returncode}): {stderr.decode(errors='replace')}"
            return stdout.decode(errors="replace").strip() or "(script executed)"

        # LISP via AppleScript
        escaped = command.replace("\\", "\\\\").replace('"', '\\"')
        apple = (
            'tell application "AutoCAD"\n'
            f'  do script "{escaped}"\n'
            "end tell"
        )
        proc = await asyncio.create_subprocess_exec(
            "osascript", "-e", apple,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)
        if proc.returncode != 0:
            return f"Error (exit {proc.returncode}): {stderr.decode(errors='replace')}"
        return stdout.decode(errors="replace").strip() or "(LISP sent to AutoCAD)"
