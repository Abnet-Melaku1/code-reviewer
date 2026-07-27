from pydantic_settings import BaseSettings, SettingsConfigDict


class WorkerConfig(BaseSettings):
    """Configuration loader for the background worker."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/codereviewer"
    redis_url: str = "redis://localhost:6379"
    embeddings_provider: str = "fake"
    voyage_api_key: str = ""
    openai_api_key: str = ""
    embeddings_model: str = "voyage-code-3"
    llm_provider: str = "fake"
    llm_model: str = "gpt-4o"
