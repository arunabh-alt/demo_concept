from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "AppBank Voice Pipeline"
    app_env: str = "development"
    api_prefix: str = "/v1"
    aws_region: str = "us-east-1"
    aws_transcribe_language_code: str = "en-US"
    aws_transcribe_media_encoding: str = "pcm"
    aws_transcribe_sample_rate_hz: int = 16000
    aws_nova_model_id: str = "amazon.nova-lite-v1:0"
    pipeline_chunk_acknowledgements: bool = False


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
