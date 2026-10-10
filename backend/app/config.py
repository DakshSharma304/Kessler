from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="KESSLER_", env_file=".env", extra="ignore")

    data_dir: Path = Path("data")
    cache_ttl_gp_seconds: int = 7_200
    cache_ttl_socrates_seconds: int = 39_600
    cors_origins: str = "http://localhost:5173"
    max_trajectory_samples: int = Field(1_000, ge=10, le=10_000)
    max_propagated_objects: int = Field(20_000, ge=1, le=100_000)
    max_concurrent_jobs: int = Field(2, ge=1, le=8)
    auto_refresh_catalog: bool = True
    source_timeout_seconds: float = Field(30, gt=0, le=120)

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
