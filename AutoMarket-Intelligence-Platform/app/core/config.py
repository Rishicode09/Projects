"""Application configuration.

All runtime configuration is loaded from environment variables (optionally via a
local ``.env`` file) and validated by Pydantic at startup. Nothing else in the
codebase reads ``os.environ`` directly -- every module depends on the typed
``Settings`` object instead, which makes configuration testable and misconfiguration
fail fast at boot rather than deep inside a request.

Nested settings use ``__`` as a delimiter, e.g. ``DATABASE__PORT=5433``.
"""

from functools import lru_cache
from typing import Literal

from pydantic import BaseModel, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

Environment = Literal["development", "testing", "production"]


class DatabaseSettings(BaseModel):
    """PostgreSQL connection settings."""

    host: str = "localhost"
    port: int = 5432
    user: str = "automarket"
    password: str = "automarket"
    name: str = "automarket"
    pool_size: int = 10
    max_overflow: int = 20
    echo: bool = False

    @property
    def url(self) -> str:
        """Async SQLAlchemy connection URL (asyncpg driver)."""
        return (
            f"postgresql+asyncpg://{self.user}:{self.password}"
            f"@{self.host}:{self.port}/{self.name}"
        )

    @property
    def sync_url(self) -> str:
        """Sync connection URL, used by Alembic migrations and Celery tasks."""
        return (
            f"postgresql+psycopg2://{self.user}:{self.password}"
            f"@{self.host}:{self.port}/{self.name}"
        )


class RedisSettings(BaseModel):
    """Redis settings, shared by the cache, rate limiter and Celery broker."""

    host: str = "localhost"
    port: int = 6379
    db: int = 0

    @property
    def url(self) -> str:
        return f"redis://{self.host}:{self.port}/{self.db}"


class SecuritySettings(BaseModel):
    """JWT and password-hashing settings."""

    secret_key: str = "dev-only-secret-change-me"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7


class Settings(BaseSettings):
    """Top-level application settings, composed from nested sections."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_nested_delimiter="__",
        extra="ignore",
    )

    app_name: str = "AutoMarket Intelligence Platform"
    app_version: str = "0.1.0"
    environment: Environment = "development"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"
    log_level: str = "INFO"
    log_json: bool = Field(
        default=False,
        description="Emit structured JSON logs (enable in production for log aggregators).",
    )

    database: DatabaseSettings = DatabaseSettings()
    redis: RedisSettings = RedisSettings()
    security: SecuritySettings = SecuritySettings()

    @model_validator(mode="after")
    def _forbid_default_secret_in_production(self) -> "Settings":
        """Refuse to boot in production with the default (public) signing key."""
        if (
            self.environment == "production"
            and self.security.secret_key == SecuritySettings().secret_key
        ):
            raise ValueError(
                "SECURITY__SECRET_KEY must be set to a strong random value in production."
            )
        return self

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide settings singleton.

    Cached so every caller shares one validated instance; tests can bypass the
    cache by constructing ``Settings`` directly or calling ``get_settings.cache_clear()``.
    """
    return Settings()
