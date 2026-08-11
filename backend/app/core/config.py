from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

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

    # --- RAG / documentation normative (V2) ---
    rag_enabled: bool = True
    embedding_provider: str = "mock"  # "mock" ou "sentence_transformer"
    embedding_model: str = "paraphrase-multilingual-MiniLM-L12-v2"
    embedding_dimension: int = 384
    rag_top_k: int = 5
    rag_min_score: float = 0.65
    rag_chunk_size: int = 800
    rag_chunk_overlap: int = 120
    max_upload_size_mb: int = 25
    allowed_document_types: str = "pdf,docx,txt,md,csv,xlsx"

    @property
    def allowed_document_types_list(self) -> list[str]:
        return [t.strip() for t in self.allowed_document_types.split(",") if t.strip()]

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
