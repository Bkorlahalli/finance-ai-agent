"""
Application configuration module.

Loads settings from environment variables with sensible defaults.
Uses pydantic-settings for type-safe configuration management.
"""

from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # OpenAI
    openai_api_key: str = ""
    openai_model: str = "gpt-3.5-turbo"

    # Database
    database_url: str = "sqlite:///./data/finance.db"

    # Application
    app_name: str = "Finance AI Agent"
    app_version: str = "1.0.0"
    debug: bool = False
    log_level: str = "INFO"

    # Alert Thresholds
    daily_spending_threshold: float = 5000.0

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    @property
    def is_openai_configured(self) -> bool:
        """Check if OpenAI API key is properly configured."""
        return bool(self.openai_api_key and self.openai_api_key != "sk-your-openai-api-key-here")


@lru_cache()
def get_settings() -> Settings:
    """Get cached application settings (singleton pattern)."""
    return Settings()
