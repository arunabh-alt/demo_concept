from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "AppBank Proxy 2026"
    app_env: str = "development"
    api_prefix: str = "/v1"
    anti_spoof_primary_model_id: str = "Speech-Arena-2025/DF_Arena_1B_V_1"
    anti_spoof_primary_reject_threshold: float = 0.6
    anti_spoof_primary_challenge_threshold: float = 0.4
    anti_spoof_secondary_reject_threshold: float = 0.5
    streaming_max_audio_bytes: int = 2_000_000


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
