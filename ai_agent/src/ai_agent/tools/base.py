"""Tool interface: subclass Tool, register it, and the agent can call it."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class ToolError(Exception):
    """Raise from Tool.run for expected failures (bad input, missing file, ...).

    The message is returned to the model as an error tool_result so it can
    adjust its approach. Unexpected exceptions are also caught by the registry,
    but ToolError lets a tool control the exact message the model sees.
    """


class Tool(ABC):
    """A capability the agent can invoke.

    Subclasses define ``name``, ``description``, and ``input_schema`` (a JSON
    Schema for the inputs), and implement ``run``.
    """

    name: str
    description: str
    input_schema: dict[str, Any]

    @abstractmethod
    def run(self, tool_input: dict[str, Any]) -> str:
        """Execute the tool and return its result as text."""

    def to_schema(self) -> dict[str, Any]:
        """The tool definition in Messages API format."""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
        }
