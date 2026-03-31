from functools import lru_cache

from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Full Stack Auth API"
    app_env: str = "development"
    api_prefix: str = "/api"
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/fullstack_auth"
    jwt_secret_key: str = "change-me-in-local-env"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60
    backend_cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    aws_region: str = "us-east-1"
    aws_transcribe_language_code: str = "en-US"
    aws_transcribe_media_encoding: str = "pcm"
    aws_transcribe_sample_rate_hz: int = 16000

    @computed_field
    @property
    def backend_cors_origins_list(self) -> list[str]:
        return [item.strip() for item in self.backend_cors_origins.split(",") if item.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
