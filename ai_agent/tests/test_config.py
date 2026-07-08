import json
import logging

import pytest

from ai_agent.config import Config, load_env_file
from ai_agent.logging_setup import JsonFormatter


def test_load_env_file_parses_and_skips_junk(tmp_path, monkeypatch):
    monkeypatch.delenv("FOO", raising=False)
    monkeypatch.delenv("QUOTED", raising=False)
    env = tmp_path / ".env"
    env.write_text("# comment\n\nFOO=bar\nQUOTED='hello world'\nnot a pair\n")

    applied = load_env_file(env)

    assert applied == {"FOO": "bar", "QUOTED": "hello world"}


def test_load_env_file_does_not_override_existing(tmp_path, monkeypatch):
    monkeypatch.setenv("FOO", "existing")
    env = tmp_path / ".env"
    env.write_text("FOO=from_file\n")

    applied = load_env_file(env)

    assert applied == {}
    assert Config.from_env(env)  # no error
    import os

    assert os.environ["FOO"] == "existing"


def test_load_env_file_missing_is_noop(tmp_path):
    assert load_env_file(tmp_path / "nope.env") == {}


def test_config_from_env_reads_values(tmp_path, monkeypatch):
    for var in ("AGENT_MODEL", "AGENT_MAX_TOKENS", "RETRY_BASE_DELAY"):
        monkeypatch.delenv(var, raising=False)
    env = tmp_path / ".env"
    env.write_text("AGENT_MODEL=claude-test\nAGENT_MAX_TOKENS=512\nRETRY_BASE_DELAY=0.5\n")

    config = Config.from_env(env)

    assert config.model == "claude-test"
    assert config.max_tokens == 512
    assert config.retry_base_delay == 0.5
    assert config.max_iterations == 10  # default preserved


def test_config_rejects_bad_integer(monkeypatch, tmp_path):
    monkeypatch.setenv("AGENT_MAX_TOKENS", "lots")
    with pytest.raises(ValueError, match="AGENT_MAX_TOKENS"):
        Config.from_env(tmp_path / "absent.env")


def test_json_formatter_emits_valid_json_with_extras():
    record = logging.LogRecord(
        "ai_agent", logging.INFO, __file__, 1, "tool executed", (), None
    )
    record.tool_name = "calculator"

    payload = json.loads(JsonFormatter().format(record))

    assert payload["message"] == "tool executed"
    assert payload["level"] == "INFO"
    assert payload["tool_name"] == "calculator"
    assert "timestamp" in payload
