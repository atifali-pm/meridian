"""Runtime configuration. Reads from process env, falls back to .env via pydantic-settings."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    anthropic_api_key: str = ""
    tavily_api_key: str = ""

    database_url: str = "postgresql://meridian:meridian@localhost:5455/meridian"
    redis_url: str = "redis://localhost:6381/0"

    anthropic_planner_model: str = "claude-sonnet-4-6"
    anthropic_agent_model: str = "claude-sonnet-4-6"
    anthropic_judge_model: str = "claude-opus-4-7"
    anthropic_cheap_model: str = "claude-haiku-4-5-20251001"

    embedding_dim: int = 1024


settings = Settings()
