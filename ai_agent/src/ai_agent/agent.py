"""The agent loop: reason, call tools, feed results back, repeat until done."""

from __future__ import annotations

import logging
from typing import Any

from .config import Config
from .llm import LLMClient
from .memory import ConversationMemory
from .tools import ToolRegistry


class Agent:
    """Drives a conversation with the model until the task is complete.

    Each ``run`` call is one user turn. The model may take multiple reasoning
    and tool-use steps within that turn, bounded by ``config.max_iterations``.
    Conversation memory persists across ``run`` calls, so follow-up questions
    keep their context.
    """

    def __init__(
        self,
        config: Config,
        llm: LLMClient,
        tools: ToolRegistry,
        memory: ConversationMemory | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        self._config = config
        self._llm = llm
        self._tools = tools
        self._memory = memory or ConversationMemory(config.memory_max_turns)
        self._logger = logger or logging.getLogger("ai_agent.agent")

    @property
    def memory(self) -> ConversationMemory:
        return self._memory

    def run(self, user_input: str) -> str:
        """Handle one user request and return the model's final answer."""
        self._memory.add_user_message(user_input)
        self._logger.info("Turn started", extra={"input_chars": len(user_input)})

        response: Any = None
        for step in range(1, self._config.max_iterations + 1):
            response = self._llm.complete(
                messages=self._memory.messages(),
                tools=self._tools.schemas(),
                system=self._config.system_prompt,
            )
            self._memory.add_assistant_content(response.content)

            match response.stop_reason:
                case "tool_use":
                    self._memory.add_tool_results(self._execute_tool_calls(response))
                case "pause_turn":
                    # Server paused mid-turn; re-sending the history resumes it.
                    self._logger.info("Turn paused by server; resuming", extra={"step": step})
                case "refusal":
                    self._logger.warning("Model refused the request")
                    return "The model declined this request for safety reasons."
                case "max_tokens":
                    self._logger.warning("Response truncated at max_tokens")
                    return (
                        _final_text(response)
                        + "\n\n[Response was truncated: the token limit was reached.]"
                    )
                case _:  # end_turn, stop_sequence
                    self._logger.info("Turn finished", extra={"steps": step})
                    return _final_text(response)

        self._logger.warning(
            "Stopped at iteration limit", extra={"max_iterations": self._config.max_iterations}
        )
        return (
            _final_text(response)
            + f"\n\n[Stopped after {self._config.max_iterations} steps without finishing;"
            " ask me to continue if needed.]"
        )

    def _execute_tool_calls(self, response: Any) -> list[dict[str, Any]]:
        """Run every tool_use block and return the tool_result blocks."""
        results: list[dict[str, Any]] = []
        for block in response.content:
            if getattr(block, "type", None) != "tool_use":
                continue
            outcome = self._tools.execute(block.name, block.input)
            result: dict[str, Any] = {
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": outcome.content,
            }
            if outcome.is_error:
                result["is_error"] = True
            results.append(result)
        return results


def _final_text(response: Any) -> str:
    """Join the text blocks of the last response into the user-facing answer."""
    if response is None:
        return ""
    parts = [
        block.text for block in response.content if getattr(block, "type", None) == "text"
    ]
    return "\n".join(parts).strip()
