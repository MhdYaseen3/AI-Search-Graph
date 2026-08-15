from functools import lru_cache
import os
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ------------------------------------------------------------------
    # Application
    # ------------------------------------------------------------------
    app_name: str = "Knowledge Graph Resume Search"
    app_version: str = "0.1.0"
    app_env: str = "development"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"
    session_secret_key: str = "local-development-secret-change-later"

    # ------------------------------------------------------------------
    # Server
    # ------------------------------------------------------------------
    host: str = "0.0.0.0"
    port: int = 8000

    # ------------------------------------------------------------------
    # Neo4j
    # ------------------------------------------------------------------
    neo4j_uri: str = "neo4j://127.0.0.1:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "yaseenaachu@123"
    neo4j_database: str = "neo4j"
    neo4j_max_connection_pool_size: int = 50
    neo4j_connection_timeout: int = 30
    neo4j_schema_init: bool = True

    # ------------------------------------------------------------------
    # Ollama
    # ------------------------------------------------------------------
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "gemma:2b"
    ollama_timeout: int = 120

    # ------------------------------------------------------------------
    # Gmail OAuth
    # ------------------------------------------------------------------
    google_client_id: str = os.getenv("GOOGLE_CLIENT_ID")
    google_client_secret: str =os.getenv("GOOGLE_CLIENT_SECRET")
    google_redirect_uri: str = "http://localhost:8000/api/v1/gmail/callback"
    gmail_scopes: str = "https://www.googleapis.com/auth/gmail.readonly"

    # ------------------------------------------------------------------
    # File Upload
    # ------------------------------------------------------------------
    upload_dir: Path = Path("./uploads/resumes")
    max_upload_size_mb: int = 10
    allowed_extensions: str = ".pdf"

    # ------------------------------------------------------------------
    # Search & Ranking
    # ------------------------------------------------------------------
    default_search_limit: int = 20
    max_search_limit: int = 100
    min_rank_score: float = 0.0

    @field_validator("upload_dir", mode="before")
    @classmethod
    def ensure_upload_path(cls, value: str | Path) -> Path:
        return Path(value)

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024

    @property
    def allowed_extension_set(self) -> set[str]:
        return {
            ext.strip().lower()
            for ext in self.allowed_extensions.split(",")
        }

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()