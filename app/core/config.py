from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    """

    app_name: str = "Danfoss AI Safety Intelligence API"
    environment: str = "development"
    database_url: str = "sqlite:///./safety_intelligence.db"
    ai_provider: str = "mock"
    translator_provider: str = "mock"
    deepl_api_key: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """
    Load and cache application settings.

    Returns:
        Settings object.
    """
    return Settings()


settings = get_settings()
