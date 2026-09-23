"""Central configuration.

Every tunable -- especially Gemini model strings -- lives here and is read from
the environment. Addendum section 3: model names are never hardcoded in
LangGraph node code, because Google has been shipping Flash-tier releases every
few weeks and the 2.5 series is already shut down. Changing a model is an .env
edit, not a code change.
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Supabase -----------------------------------------------------------
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""
    database_url: str = ""

    # --- Gemini -------------------------------------------------------------
    google_api_key: str = ""
    # Gemini free tier configuration:
    # Both tiers default to gemini-3.6-flash so free tier API keys are used throughout
    # without hitting Pro tier 2 RPM limits or paid billing.
    gemini_pro_model: str = "gemini-3.1-pro"
    gemini_flash_model: str = "gemini-3.5-flash-lite"

    # --- Embeddings ---------------------------------------------------------
    embedding_model: str = "BAAI/bge-m3"
    embedding_dim: int = 1024
    embedding_device: Literal["auto", "cpu", "cuda"] = "auto"

    # --- Retrieval ----------------------------------------------------------
    retrieval_candidate_k: int = 30  # per-retriever pool before fusion
    retrieval_final_k: int = 5  # after rerank
    rrf_k: int = 60  # Reciprocal Rank Fusion smoothing constant
    chunk_tokens: int = 350
    chunk_overlap: int = 60

    # --- Scrapers -----------------------------------------------------------
    data_gov_in_api_key: str = ""

    # --- Verification / revision loop --------------------------------------
    fabrication_threshold: float = 0.10
    max_revision_cycles: int = 2

    # --- App ----------------------------------------------------------------
    api_host: str = "0.0.0.0"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000,http://127.0.0.1:3000"
    log_level: str = "INFO"
    environment: str = Field(default="development")

    @property
    def cors_origin_list(self) -> list[str]:
        defaults = [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ]
        user_origins = [o.strip() for o in self.cors_origins.split(",") if o.strip()]
        return list(set(defaults + user_origins))

    def missing_required(self) -> list[str]:
        """Names of settings the app needs before it can do real work.

        The API still boots without them so `/health` and the graph skeleton
        stay inspectable during Phase 0 -- but /health reports what is missing.
        """
        required = {
            "SUPABASE_URL": self.supabase_url,
            "SUPABASE_SERVICE_ROLE_KEY": self.supabase_service_role_key,
            "GOOGLE_API_KEY": self.google_api_key,
        }
        return [name for name, value in required.items() if not value]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
