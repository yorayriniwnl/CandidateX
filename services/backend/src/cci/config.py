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
    DEBUG: bool = True
    API_PORT: int = 8000
    API_HOST: str = "127.0.0.1"
    API_V1_PREFIX: str = "/v1"

    # Semantic Version Families (Fix 33)
    API_VERSION: str = "1.0.0"
    EVIDENCE_SCHEMA_VERSION: str = "1.0.0"
    SCORING_MODEL_VERSION: str = "5.1.0"
    ANALYZER_VERSION: str = "1.0.0"
    ROLE_ONTOLOGY_VERSION: str = "1.0.0"
    CLAIM_SCHEMA_VERSION: str = "1.0.0"
    SOURCE_RELIABILITY_VERSION: str = "1.0.0"
    SECRET_KEY: str = (
        "cci_insecure_development_secret_key_change_in_production_min_32_bytes"
    )
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

    # Centralized System Limits & Operational Budgets (Fix 34)
    LIMIT_MAX_URLS: int = 24
    LIMIT_MAX_REPOSITORIES: int = 6
    LIMIT_MAX_FILES_PER_REPO: int = 100
    LIMIT_LINK_TIMEOUT_SECONDS: int = 20
    LIMIT_ACQUISITION_SECONDS: int = 45
    LIMIT_MAX_PAGE_BYTES: int = 512 * 1024
    LIMIT_MAX_TEXT_CHARS: int = 12000
    LIMIT_MAX_PDF_PAGES: int = 5
    LIMIT_MAX_RESUME_PAGES: int = 30
    LIMIT_MAX_UPLOAD_BYTES: int = 3 * 1024 * 1024
    LIMIT_MAX_REQUEST_BYTES: int = 512 * 1024

    # Production Abuse Controls (Fix 28)
    MAX_CONCURRENT_ANALYSES: int = 5
    MAX_CONCURRENT_ANALYSES_PER_CLIENT: int = 2
    RATE_LIMIT_INTAKE_PER_MINUTE: int = 20
    RATE_LIMIT_RUNS_PER_MINUTE: int = 15
    MAX_RUN_WALL_CLOCK_SECONDS: int = 60
    MAX_GITHUB_CALLS_PER_RUN: int = 50
    MAX_CRAWL_PAGES_PER_RUN: int = 24
    MAX_CRAWL_BYTES_PER_RUN: int = 5 * 1024 * 1024
    CIRCUIT_BREAKER_FAILURE_THRESHOLD: int = 5
    CIRCUIT_BREAKER_COOLDOWN_SECONDS: float = 30.0
    REQUIRE_SIGNED_ANALYSIS_TOKEN: bool = False

    # Authentication & Multi-Tenancy (Fix 29)
    AUTH_REQUIRED: bool = False
    DEFAULT_DEV_ORG_ID: str = "00000000-0000-0000-0000-000000000001"
    JWT_SECRET_KEY: str = "cci_jwt_secret_key_change_in_production_min_32_bytes_safe"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    # Privacy, PII Protection & Data Retention (Fix 31)
    RETENTION_RESUME_BYTES_HOURS: int = 24
    RETENTION_PARSED_TEXT_DAYS: int = 30
    RETENTION_ANALYSIS_ARTIFACTS_DAYS: int = 7
    RETENTION_CACHED_PAGES_HOURS: int = 24
    RETENTION_CANDIDATE_RECORDS_DAYS: int = 180
    RETENTION_LOGS_DAYS: int = 30
    RETENTION_EXPORTS_DAYS: int = 14
    PII_LOG_REDACTION_ENABLED: bool = True

    # Formal Scoring Parameters (Paper-aligned default v1)
    SCORING_CONFIG_VERSION: str = "1.0.0"
    DEFAULT_TEMPERATURE: float = 1.0
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
