from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables / .env file."""

    # Supabase project config
    SUPABASE_URL: str          # e.g., "https://xxxx.supabase.co"
    SUPABASE_SERVICE_KEY: str  # service_role secret key
    SUPABASE_DB_URL: str       # e.g., "postgresql+asyncpg://postgres.[ref]:[password]@...pooler.supabase.com:6543/postgres"

    # Application config
    APP_NAME: str = "Plant Monitor Dashboard"
    DEBUG: bool = False
    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "https://industrial-plant-monitor.vercel.app",
        "https://industrial-plant-monitor-git-master-fifth-islands-projects.vercel.app",
    ]

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton."""
    return Settings()
