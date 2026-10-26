"""Global application configuration management using Pydantic Settings."""

from functools import lru_cache
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration for database, environment, and runtime flags."""

    # Database Configuration (PostgreSQL with asyncpg default)
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/ptg_db"
    DATABASE_ECHO: bool = False

    # Runtime Environment
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache()
def get_settings() -> Settings:
    """Return cached global settings instance."""
    return Settings()
