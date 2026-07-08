"""Modular tool system: Tool base class, registry, and built-in tools."""

from __future__ import annotations

import logging
from pathlib import Path

from .base import Tool, ToolError
from .builtin.calculator import CalculatorTool
from .builtin.clock import ClockTool
from .builtin.files import ListFilesTool, ReadFileTool
from .registry import ToolRegistry, ToolResult

__all__ = [
    "CalculatorTool",
    "ClockTool",
    "ListFilesTool",
    "ReadFileTool",
    "Tool",
    "ToolError",
    "ToolRegistry",
    "ToolResult",
    "default_registry",
]


def default_registry(
    workspace_root: str | Path | None = None,
    logger: logging.Logger | None = None,
) -> ToolRegistry:
    """A registry preloaded with the built-in tools."""
    registry = ToolRegistry(logger=logger)
    registry.register(CalculatorTool())
    registry.register(ClockTool())
    registry.register(ReadFileTool(workspace_root))
    registry.register(ListFilesTool(workspace_root))
    return registry
