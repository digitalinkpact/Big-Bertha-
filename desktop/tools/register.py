"""Register desktop tools with the Baccano AI agent.

Call ``register_desktop_tools(registry)`` after the agent loop is created
to add Illustrator, AutoCAD, SolidWorks, and Blender tools.

These tools are only useful when running locally on a PC/Mac — they are
no-ops in a cloud/Codespace environment.
"""

from __future__ import annotations

import platform
from typing import TYPE_CHECKING

from loguru import logger

if TYPE_CHECKING:
    from nanobot.agent.tools.registry import ToolRegistry


def is_desktop_environment() -> bool:
    """Return True if we appear to be running on a local workstation."""
    system = platform.system()
    # In a Codespace / Docker container, there's usually no display
    # On Windows or macOS with a display, we're likely on a desktop
    if system in ("Windows", "Darwin"):
        return True
    # On Linux, check for DISPLAY or WAYLAND
    import os
    return bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))


def register_desktop_tools(registry: ToolRegistry) -> list[str]:
    """Register all desktop tools and return a list of registered tool names.

    Only registers on desktop environments (Windows/macOS).  On cloud/server
    environments this is a no-op.
    """
    if not is_desktop_environment():
        logger.info("Not a desktop environment — skipping desktop tool registration")
        return []

    from desktop.tools.illustrator import IllustratorTool
    from desktop.tools.autocad import AutoCADTool
    from desktop.tools.solidworks import SolidWorksTool
    from desktop.tools.blender import BlenderTool

    tools = [
        IllustratorTool(),
        AutoCADTool(),
        SolidWorksTool(),
        BlenderTool(),
    ]

    registered = []
    for tool in tools:
        registry.register(tool)
        registered.append(tool.name)
        logger.info("Registered desktop tool: {}", tool.name)

    return registered
