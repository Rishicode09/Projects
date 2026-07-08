"""Current date and time, optionally in a named timezone."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from ..base import Tool, ToolError


class ClockTool(Tool):
    name = "current_time"
    description = (
        "Get the current date and time. Use this whenever the answer depends on "
        "today's date or the current time — do not guess."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "timezone": {
                "type": "string",
                "description": "IANA timezone name such as 'Europe/London'. Defaults to UTC.",
            }
        },
        "required": [],
    }

    def run(self, tool_input: dict[str, Any]) -> str:
        tz_name = tool_input.get("timezone") or "UTC"
        if tz_name == "UTC":
            now = datetime.now(UTC)
        else:
            try:
                now = datetime.now(ZoneInfo(tz_name))
            except (ZoneInfoNotFoundError, ValueError) as exc:
                raise ToolError(f"Unknown timezone {tz_name!r}") from exc
        return f"{now.isoformat(timespec='seconds')} ({now.strftime('%A')}, {tz_name})"
