"""Tests for app.core.config."""

import pytest

from app.core.config import DatabaseSettings, Settings, get_settings

pytestmark = pytest.mark.unit


class TestDatabaseSettings:
    def test_async_url_uses_asyncpg_driver(self) -> None:
        db = DatabaseSettings(host="db", port=5433, user="u", password="p", name="cars")
        assert db.url == "postgresql+asyncpg://u:p@db:5433/cars"

    def test_sync_url_uses_psycopg2_driver(self) -> None:
        db = DatabaseSettings()
        assert db.sync_url.startswith("postgresql+psycopg2://")


class TestSettings:
    def test_defaults_are_development(self) -> None:
        settings = Settings(_env_file=None)
        assert settings.environment == "development"
        assert settings.is_production is False

    def test_nested_env_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("DATABASE__PORT", "6543")
        monkeypatch.setenv("ENVIRONMENT", "testing")
        settings = Settings(_env_file=None)
        assert settings.database.port == 6543
        assert settings.environment == "testing"

    def test_production_rejects_default_secret_key(self) -> None:
        with pytest.raises(ValueError, match="SECURITY__SECRET_KEY"):
            Settings(_env_file=None, environment="production")

    def test_production_boots_with_real_secret_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SECURITY__SECRET_KEY", "a-strong-random-key")
        settings = Settings(_env_file=None, environment="production")
        assert settings.is_production is True


class TestGetSettings:
    def test_returns_cached_singleton(self) -> None:
        get_settings.cache_clear()
        try:
            assert get_settings() is get_settings()
        finally:
            get_settings.cache_clear()
