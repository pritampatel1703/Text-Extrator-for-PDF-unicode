"""
Application configuration using Pydantic Settings.
All environment variables are loaded and validated here.
"""

from pathlib import Path
from typing import List, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ──
    app_name: str = "PDF Search Platform"
    app_env: str = "development"
    debug: bool = True
    secret_key: str = "change-me-in-production"
    api_prefix: str = "/api/v1"

    # ── Backend Server ──
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000
    backend_workers: int = 4
    cors_origins: str = "http://localhost:3000,http://localhost:8000"

    @property
    def cors_origin_list(self) -> List[str]:
        return [origin.strip() for origin in self.cors_origins.split(",")]

    # ── PostgreSQL ──
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "pdf_platform"
    postgres_user: str = "pdf_admin"
    postgres_password: str = "pdf_secure_password_2024"
    database_url: Optional[str] = None

    @property
    def db_url(self) -> str:
        if self.database_url:
            return self.database_url
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def db_url_sync(self) -> str:
        """Sync database URL for Alembic migrations."""
        return self.db_url.replace("postgresql+asyncpg", "postgresql+psycopg2")

    # ── Elasticsearch ──
    elasticsearch_url: str = "http://localhost:9200"
    elasticsearch_index: str = "pdf_pages"

    # ── Redis ──
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"

    # ── File Storage ──
    upload_dir: str = "./uploads"
    max_file_size_mb: int = 200
    allowed_extensions: str = ".pdf"

    @property
    def upload_path(self) -> Path:
        path = Path(self.upload_dir)
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def max_file_size_bytes(self) -> int:
        return self.max_file_size_mb * 1024 * 1024

    # ── JWT Authentication ──
    jwt_secret_key: str = "jwt-secret-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7

    # ── Rate Limiting ──
    rate_limit_per_minute: int = 60
    rate_limit_upload_per_minute: int = 10

    # ── AI / Embeddings ──
    embedding_model: str = "BAAI/bge-m3"
    embedding_dimensions: int = 1024
    embedding_batch_size: int = 32
    enable_semantic_search: bool = True

    # ── Logging ──
    log_level: str = "INFO"


settings = Settings()
