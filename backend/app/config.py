from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables / .env file."""

    # Database connection (local PostgreSQL by default)
    DATABASE_URL: str = "postgresql://plant_user:plant_pass@localhost:5433/plant_monitor"

    # Application config
    APP_NAME: str = "Plant Monitor Dashboard"
    DEBUG: bool = False
    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
    ]

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton."""
    return Settings()
