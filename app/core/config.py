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
    openai_api_key: str | None = None
    hazard_ai_model: str = "gpt-4o-mini"
    mailtrap_api_token: str | None = None
    mailtrap_sender_email: str | None = None
    mailtrap_sender_name: str = "Danfoss Safety Intelligence"
    mailtrap_default_recipient_email: str = "ilavskymatus@gmail.com"
    mailtrap_api_url: str = "https://send.api.mailtrap.io/api/send"

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
