"""Registry that holds tools and executes them safely."""

from __future__ import annotations

import logging
from typing import Any

from .base import Tool, ToolError


class ToolResult:
    """Outcome of a tool execution, ready to send back to the model."""

    __slots__ = ("content", "is_error")

    def __init__(self, content: str, is_error: bool = False) -> None:
        self.content = content
        self.is_error = is_error


class ToolRegistry:
    def __init__(self, logger: logging.Logger | None = None) -> None:
        self._tools: dict[str, Tool] = {}
        self._logger = logger or logging.getLogger("ai_agent.tools")

    def register(self, tool: Tool) -> None:
        if tool.name in self._tools:
            raise ValueError(f"Tool {tool.name!r} is already registered")
        self._tools[tool.name] = tool

    def names(self) -> list[str]:
        return sorted(self._tools)

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def schemas(self) -> list[dict[str, Any]]:
        """Tool definitions for the Messages API, in stable (sorted) order."""
        return [self._tools[name].to_schema() for name in self.names()]

    def execute(self, name: str, tool_input: dict[str, Any]) -> ToolResult:
        """Run a tool, converting any failure into an error result for the model."""
        tool = self._tools.get(name)
        if tool is None:
            return ToolResult(f"Unknown tool: {name!r}", is_error=True)

        self._logger.info("Executing tool", extra={"tool": name, "input": tool_input})
        try:
            result = ToolResult(tool.run(tool_input))
        except ToolError as exc:
            result = ToolResult(f"Tool error: {exc}", is_error=True)
        except Exception:
            self._logger.exception("Tool crashed", extra={"tool": name})
            result = ToolResult(
                f"Tool {name!r} failed unexpectedly; try different input or another approach.",
                is_error=True,
            )
        self._logger.info(
            "Tool finished",
            extra={"tool": name, "is_error": result.is_error, "output_chars": len(result.content)},
        )
        return result
