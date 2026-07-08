"""Thin wrapper around the Anthropic Messages API with retry on transient errors."""

from __future__ import annotations

import logging
from typing import Any

import anthropic

from .config import Config
from .retry import retry_call


def is_retryable_api_error(exc: Exception) -> bool:
    """Retry network failures, rate limits, and server-side errors only."""
    if isinstance(exc, anthropic.APIConnectionError | anthropic.RateLimitError):
        return True
    if isinstance(exc, anthropic.APIStatusError):
        return exc.status_code >= 500
    return False


class LLMClient:
    """Calls Claude with the agent's settings and returns the raw Message.

    A pre-built client can be injected for testing.
    """

    def __init__(
        self,
        config: Config,
        client: anthropic.Anthropic | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        self._config = config
        self._client = client or anthropic.Anthropic()
        self._logger = logger or logging.getLogger("ai_agent.llm")

    def complete(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        system: str,
    ) -> Any:
        def call() -> Any:
            return self._client.messages.create(
                model=self._config.model,
                max_tokens=self._config.max_tokens,
                system=system,
                messages=messages,
                tools=tools,
                thinking={"type": "adaptive"},
            )

        response = retry_call(
            call,
            is_retryable=is_retryable_api_error,
            max_attempts=self._config.retry_max_attempts,
            base_delay=self._config.retry_base_delay,
            max_delay=self._config.retry_max_delay,
        )
        usage = getattr(response, "usage", None)
        self._logger.info(
            "Model responded",
            extra={
                "model": self._config.model,
                "stop_reason": response.stop_reason,
                "input_tokens": getattr(usage, "input_tokens", None),
                "output_tokens": getattr(usage, "output_tokens", None),
            },
        )
        return response
