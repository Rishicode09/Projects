"""Conversation memory for the Messages API.

Stores the full message history (including assistant tool_use blocks and user
tool_result blocks) and trims the oldest turns when the conversation grows past
a limit. A "turn" starts at a plain-text user message; trimming only removes
whole turns so tool_use/tool_result pairs are never split.
"""

from __future__ import annotations

from typing import Any


class ConversationMemory:
    def __init__(self, max_turns: int = 20) -> None:
        if max_turns < 1:
            raise ValueError("max_turns must be at least 1")
        self._max_turns = max_turns
        self._messages: list[dict[str, Any]] = []

    def add_user_message(self, text: str) -> None:
        self._messages.append({"role": "user", "content": text})
        self._trim()

    def add_assistant_content(self, content: Any) -> None:
        """Store the full assistant response content (text, thinking, tool_use blocks)."""
        self._messages.append({"role": "assistant", "content": content})

    def add_tool_results(self, results: list[dict[str, Any]]) -> None:
        """Store tool_result blocks; the API expects them in a single user message."""
        self._messages.append({"role": "user", "content": results})

    def messages(self) -> list[dict[str, Any]]:
        """Return the history to send to the API. Do not mutate the result."""
        return list(self._messages)

    def clear(self) -> None:
        self._messages.clear()

    def __len__(self) -> int:
        return len(self._messages)

    def _turn_starts(self) -> list[int]:
        return [
            i
            for i, message in enumerate(self._messages)
            if message["role"] == "user" and isinstance(message["content"], str)
        ]

    def _trim(self) -> None:
        starts = self._turn_starts()
        if len(starts) > self._max_turns:
            # Keep the newest max_turns turns; drop everything before them.
            del self._messages[: starts[len(starts) - self._max_turns]]
