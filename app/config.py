"""Application settings, loaded from environment variables or a .env file."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Values read from .env (see .env.example)."""

    workiq_mcp_url: str = "https://workiq.svc.cloud.microsoft/mcp"
    workiq_access_token: str

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    """Create the settings once and reuse them."""
    return Settings()
