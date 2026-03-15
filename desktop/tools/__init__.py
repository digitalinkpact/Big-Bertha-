"""Baccano AI desktop tool plugins for local application control."""

from desktop.tools.illustrator import IllustratorTool
from desktop.tools.autocad import AutoCADTool
from desktop.tools.solidworks import SolidWorksTool
from desktop.tools.blender import BlenderTool

ALL_DESKTOP_TOOLS = [
    IllustratorTool,
    AutoCADTool,
    SolidWorksTool,
    BlenderTool,
]

__all__ = [
    "IllustratorTool",
    "AutoCADTool",
    "SolidWorksTool",
    "BlenderTool",
    "ALL_DESKTOP_TOOLS",
]
