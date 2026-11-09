"""Application settings, loaded from environment variables or a .env file."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Values read from .env (see .env.example).

    Each field name matches an upper-case key in .env, e.g. `tenant_id` <- TENANT_ID.
    """

    workiq_mcp_url: str = "https://workiq.svc.cloud.microsoft/mcp"

    # Option 1: a fixed Work IQ token (handy for testing).
    # If this is set, it is always used and the On-Behalf-Of settings below are ignored.
    workiq_access_token: str | None = None

    # Option 2: On-Behalf-Of (OBO). Used when WORKIQ_ACCESS_TOKEN is empty.
    # These values come from your Entra ID app registration.
    tenant_id: str | None = None
    client_id: str | None = None
    client_secret: str | None = None
    scope: str = "api://workiq.svc.cloud.microsoft/WorkIQAgent.Ask"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    """Create the settings once and reuse them."""
    return Settings()
