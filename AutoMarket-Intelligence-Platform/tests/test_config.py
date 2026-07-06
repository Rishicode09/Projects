"""Tests for app.config."""

import pytest

from app.config import Settings, get_settings


def test_defaults() -> None:
    settings = Settings(_env_file=None)
    assert settings.app_name == "AutoMarket Intelligence Platform"
    assert settings.database_url.startswith("sqlite:///")


def test_env_variable_overrides_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "sqlite:///./test.db")
    settings = Settings(_env_file=None)
    assert settings.database_url == "sqlite:///./test.db"


def test_get_settings_is_cached() -> None:
    get_settings.cache_clear()
    try:
        assert get_settings() is get_settings()
    finally:
        get_settings.cache_clear()
