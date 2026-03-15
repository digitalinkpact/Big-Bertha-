"""SolidWorks tool — controls SolidWorks via COM (Windows only).

SolidWorks exposes ``SldWorks.Application`` through COM automation.
This tool sends VBA-style macro commands or runs saved macros.
"""

from __future__ import annotations

import asyncio
import platform
import tempfile
from pathlib import Path
from typing import Any

from nanobot.agent.tools.base import Tool


class SolidWorksTool(Tool):
    """Execute SolidWorks macro commands via COM automation."""

    @property
    def name(self) -> str:
        return "solidworks"

    @property
    def description(self) -> str:
        return (
            "Run a SolidWorks VBA macro snippet or open/export files. "
            "Use this for part modelling, assembly operations, drawing generation, "
            "and file conversions.  Windows only (SolidWorks is Windows-exclusive)."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "macro": {
                    "type": "string",
                    "description": (
                        "VBA macro code to execute in SolidWorks, OR a command "
                        "like 'open:<filepath>' or 'export_pdf:<filepath>'"
                    ),
                },
                "description": {
                    "type": "string",
                    "description": "Human-readable summary of what this does",
                },
            },
            "required": ["macro", "description"],
        }

    async def execute(self, macro: str, description: str, **kwargs: Any) -> str:
        from desktop.tools.approval import require_approval

        approved = await require_approval(
            tool="SolidWorks",
            action=description,
            details=macro[:500],
            risk_level="medium",
        )
        if not approved:
            return "Action denied by user."

        if platform.system() != "Windows":
            return "Error: SolidWorks is only available on Windows."

        # Handle shortcut commands
        if macro.startswith("open:"):
            return await self._open_file(macro[5:].strip())
        if macro.startswith("export_pdf:"):
            return await self._export_pdf(macro[11:].strip())

        return await self._run_macro(macro)

    async def _run_macro(self, vba_code: str) -> str:
        """Write VBA to a temp .swp macro and run it."""
        with tempfile.NamedTemporaryFile(
            suffix=".swp", mode="w", delete=False, encoding="utf-8",
        ) as f:
            f.write(vba_code)
            macro_path = f.name

        ps_cmd = (
            '$sw = [System.Runtime.InteropServices.Marshal]::'
            'GetActiveObject("SldWorks.Application"); '
            f'$sw.RunMacro2("{macro_path}", "", "main", 0, [ref]$null)'
        )
        try:
            proc = await asyncio.create_subprocess_exec(
                "powershell", "-NoProfile", "-Command", ps_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=180)
        finally:
            Path(macro_path).unlink(missing_ok=True)

        if proc.returncode != 0:
            return f"Error (exit {proc.returncode}): {stderr.decode(errors='replace')}"
        return stdout.decode(errors="replace").strip() or "(macro executed in SolidWorks)"

    async def _open_file(self, filepath: str) -> str:
        """Open a SolidWorks file via COM."""
        ps_cmd = (
            '$sw = [System.Runtime.InteropServices.Marshal]::'
            'GetActiveObject("SldWorks.Application"); '
            f'$sw.OpenDoc("{filepath}", 1)'  # 1 = swDocPART
        )
        proc = await asyncio.create_subprocess_exec(
            "powershell", "-NoProfile", "-Command", ps_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=60)
        if proc.returncode != 0:
            return f"Error: {stderr.decode(errors='replace')}"
        return f"Opened {filepath} in SolidWorks."

    async def _export_pdf(self, filepath: str) -> str:
        """Export the active SolidWorks drawing to PDF."""
        pdf_path = str(Path(filepath).with_suffix(".pdf"))
        ps_cmd = (
            '$sw = [System.Runtime.InteropServices.Marshal]::'
            'GetActiveObject("SldWorks.Application"); '
            '$doc = $sw.ActiveDoc; '
            '$doc.Extension.SaveAs('
            f'"{pdf_path}", 0, 0, $null, [ref]$null, [ref]$null)'
        )
        proc = await asyncio.create_subprocess_exec(
            "powershell", "-NoProfile", "-Command", ps_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=60)
        if proc.returncode != 0:
            return f"Error: {stderr.decode(errors='replace')}"
        return f"Exported PDF to {pdf_path}."
