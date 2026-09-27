"""Application configuration using Pydantic Settings."""

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration for Candidate Capability Intelligence."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Application
    APP_NAME: str = "Candidate Capability Intelligence"
    APP_ENV: str = "development"
    DEBUG: bool = False
    API_PORT: int = 8000
    API_HOST: str = "127.0.0.1"
    API_V1_PREFIX: str = "/v1"
    SECRET_KEY: str | None = None
    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    # Database
    DATABASE_URL: str = "sqlite:///./local_dev.db"
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20

    # Redis / Celery
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/1"

    # Security & Execution Limits (Safeguards)
    MAX_REPOSITORY_SIZE_MB: int = 500
    MAX_REPOSITORY_PATHS: int = 100000
    MAX_FILE_SIZE_MB: int = 5
    ANALYSIS_TIMEOUT_SECONDS: int = 300

    # Formal Scoring Parameters (Paper-aligned default v1)
    SCORING_CONFIG_VERSION: str = "1.0.0"
    DEFAULT_TEMPERATURE: float = 1.0
    LOW_COVERAGE_THRESHOLD: float = 0.35
    CONTRADICTION_EPSILON: float = 1e-5
    PROBE_ALPHA: float = 0.40  # Coverage gap weight
    PROBE_BETA: float = 0.35  # CI width / uncertainty weight
    PROBE_GAMMA: float = 0.25  # Contradiction weight

    # Optional External Integrations
    GITHUB_TOKEN: str | None = None

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, list):
            return v
        import json

        try:
            return list(json.loads(v))
        except Exception:
            return ["http://localhost:3000"]


settings = Settings()
