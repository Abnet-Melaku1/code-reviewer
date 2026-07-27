from pydantic_settings import BaseSettings, SettingsConfigDict


class ApiConfig(BaseSettings):
    """Configuration loader for the FastAPI service."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/codereviewer"
    redis_url: str = "redis://localhost:6379"
    github_webhook_secret: str = "super_secret_webhook_key"
