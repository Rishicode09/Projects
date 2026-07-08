"""Configuration loaded from the environment, optionally seeded from a .env file."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

DEFAULT_SYSTEM_PROMPT = (
    "You are a capable assistant that solves tasks for the user. "
    "Think through each task, make a short plan, and use the available tools "
    "when they would give a more reliable answer than recall. "
    "When a tool fails, adjust your approach instead of repeating the same call. "
    "Answer concisely and state clearly when something could not be completed."
)


def load_env_file(path: str | Path = ".env", *, override: bool = False) -> dict[str, str]:
    """Load KEY=VALUE pairs from a .env file into os.environ.

    Existing environment variables win unless ``override`` is set. Lines that
    are blank, comments, or not in KEY=VALUE form are ignored. Returns the
    values that were applied.
    """
    path = Path(path)
    applied: dict[str, str] = {}
    if not path.is_file():
        return applied
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip("'\"")
        if not key:
            continue
        if override or key not in os.environ:
            os.environ[key] = value
            applied[key] = value
    return applied


@dataclass(frozen=True)
class Config:
    """Runtime settings for the agent."""

    model: str = "claude-opus-4-8"
    max_tokens: int = 16000
    max_iterations: int = 10
    system_prompt: str = DEFAULT_SYSTEM_PROMPT
    memory_max_turns: int = 20
    retry_max_attempts: int = 3
    retry_base_delay: float = 1.0
    retry_max_delay: float = 30.0
    log_level: str = "INFO"
    log_format: str = "json"

    @classmethod
    def from_env(cls, env_file: str | Path = ".env") -> Config:
        """Build a Config from the environment, reading ``env_file`` first."""
        load_env_file(env_file)
        defaults = cls()
        return cls(
            model=os.environ.get("AGENT_MODEL", defaults.model),
            max_tokens=_env_int("AGENT_MAX_TOKENS", defaults.max_tokens),
            max_iterations=_env_int("AGENT_MAX_ITERATIONS", defaults.max_iterations),
            system_prompt=os.environ.get("AGENT_SYSTEM_PROMPT", defaults.system_prompt),
            memory_max_turns=_env_int("MEMORY_MAX_TURNS", defaults.memory_max_turns),
            retry_max_attempts=_env_int("RETRY_MAX_ATTEMPTS", defaults.retry_max_attempts),
            retry_base_delay=_env_float("RETRY_BASE_DELAY", defaults.retry_base_delay),
            retry_max_delay=_env_float("RETRY_MAX_DELAY", defaults.retry_max_delay),
            log_level=os.environ.get("LOG_LEVEL", defaults.log_level).upper(),
            log_format=os.environ.get("LOG_FORMAT", defaults.log_format).lower(),
        )


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ValueError(f"Environment variable {name} must be an integer, got {raw!r}") from exc


def _env_float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return default
    try:
        return float(raw)
    except ValueError as exc:
        raise ValueError(f"Environment variable {name} must be a number, got {raw!r}") from exc
