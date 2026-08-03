from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str
    cors_origins: str = "http://localhost:5173"

    safety_factor: float = 1.10
    flux_tolerance_min: float = 0.95
    flux_tolerance_max: float = 1.15
    current_fixed_tolerance_ma: float = 0.0
    module_voltage_tolerance_percent: float = 10.0
    module_current_tolerance_percent: float = 10.0
    lens_pitch_tolerance_mm: float = 0.2
    max_results: int = 3

    max_import_file_size_mb: int = 20

    log_level: str = "INFO"
    environment: str = "development"

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
