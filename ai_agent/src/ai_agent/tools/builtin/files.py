"""Read-only file access confined to a workspace root.

Paths supplied by the model are untrusted: every path is resolved and must
stay inside the root or the call is rejected.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..base import Tool, ToolError

_MAX_FILE_BYTES = 256 * 1024
_MAX_LIST_ENTRIES = 200


class _WorkspaceTool(Tool):
    def __init__(self, root: str | Path | None = None) -> None:
        self._root = Path(root or Path.cwd()).resolve()

    def _resolve(self, raw_path: str) -> Path:
        if not raw_path or not isinstance(raw_path, str):
            raise ToolError("Provide a 'path' string")
        candidate = (self._root / raw_path).resolve()
        if candidate != self._root and self._root not in candidate.parents:
            raise ToolError(f"Path {raw_path!r} is outside the workspace")
        return candidate


class ReadFileTool(_WorkspaceTool):
    name = "read_file"
    description = (
        "Read a text file inside the workspace. Use list_files first if you are "
        "unsure of the exact path. Paths are relative to the workspace root."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Relative path of the file to read"}
        },
        "required": ["path"],
    }

    def run(self, tool_input: dict[str, Any]) -> str:
        path = self._resolve(tool_input.get("path", ""))
        if not path.is_file():
            raise ToolError(f"No such file: {tool_input.get('path')!r}")
        if path.stat().st_size > _MAX_FILE_BYTES:
            raise ToolError(f"File larger than {_MAX_FILE_BYTES // 1024} KiB; refusing to read")
        try:
            return path.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            raise ToolError("File is not valid UTF-8 text") from exc


class ListFilesTool(_WorkspaceTool):
    name = "list_files"
    description = (
        "List files and directories inside the workspace. "
        "Paths are relative to the workspace root; use '.' for the root itself."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Relative directory path to list. Defaults to the root.",
            }
        },
        "required": [],
    }

    def run(self, tool_input: dict[str, Any]) -> str:
        path = self._resolve(tool_input.get("path") or ".")
        if not path.is_dir():
            raise ToolError(f"No such directory: {tool_input.get('path')!r}")
        entries = sorted(path.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))
        lines = [f"{entry.name}/" if entry.is_dir() else entry.name for entry in entries]
        if len(lines) > _MAX_LIST_ENTRIES:
            lines = lines[:_MAX_LIST_ENTRIES] + [f"... and {len(lines) - _MAX_LIST_ENTRIES} more"]
        return "\n".join(lines) if lines else "(empty directory)"
