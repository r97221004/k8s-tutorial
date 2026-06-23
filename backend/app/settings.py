from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Todo Board API"
    app_version: str = "0.1.0"
    database_path: str = "/data/todo.db"
    cors_origins: list[str] = Field(default_factory=list)

    model_config = SettingsConfigDict(env_prefix="", env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
