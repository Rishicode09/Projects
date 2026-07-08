"""Retry transient failures with exponential backoff and jitter.

The Anthropic SDK already retries a couple of times internally; this layer adds
a configurable outer loop so the agent survives longer outages, and it is
reused for anything else that can fail transiently.
"""

from __future__ import annotations

import logging
import random
import time
from collections.abc import Callable
from typing import TypeVar

T = TypeVar("T")

logger = logging.getLogger("ai_agent.retry")


def retry_call(
    func: Callable[[], T],
    *,
    is_retryable: Callable[[Exception], bool],
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    sleep: Callable[[float], None] = time.sleep,
) -> T:
    """Call ``func``, retrying retryable exceptions with exponential backoff.

    Delay for attempt N is ``min(base_delay * 2**N, max_delay)`` plus up to one
    second of jitter. Non-retryable exceptions and the final failure propagate.
    """
    if max_attempts < 1:
        raise ValueError("max_attempts must be at least 1")

    for attempt in range(max_attempts):
        try:
            return func()
        except Exception as exc:
            last_attempt = attempt == max_attempts - 1
            if last_attempt or not is_retryable(exc):
                raise
            delay = min(base_delay * (2**attempt), max_delay) + random.uniform(0, 1)
            logger.warning(
                "Retrying after transient error",
                extra={
                    "attempt": attempt + 1,
                    "max_attempts": max_attempts,
                    "delay_seconds": round(delay, 2),
                    "error": repr(exc),
                },
            )
            sleep(delay)

    raise AssertionError("unreachable")  # pragma: no cover
