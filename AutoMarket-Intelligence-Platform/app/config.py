"""Application settings.

All configuration comes from environment variables (or a local .env file),
loaded and type-checked by pydantic-settings. Keeping settings in one typed
object means no other file needs to touch os.environ.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "AutoMarket Intelligence Platform"
    app_version: str = "0.1.0"
    # SQLite keeps local setup to zero steps; swap for a PostgreSQL URL in production.
    database_url: str = "sqlite:///./automarket.db"


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance so the .env file is only read once."""
    return Settings()
