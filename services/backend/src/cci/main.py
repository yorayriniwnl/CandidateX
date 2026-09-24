from typing import Any

"""FastAPI entrypoint for Candidate Capability Intelligence (CCI)."""

from datetime import datetime, timezone

from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware

from cci import __version__
from cci.api.routers import (
    auth_router,
    candidates_router,
    dossier_router,
    jobs_router,
    overrides_router,
    pipeline_router,
    privacy_router,
    research_router,
)
from cci.api.routers.live import router as live_router
from cci.api.routers.research_demo import router as research_demo_router
from cci.config import settings
from cci.security.privacy import configure_pii_safe_logging

# Guarantee PII-safe logging across the entire platform
configure_pii_safe_logging()

app = FastAPI(
    title=settings.APP_NAME,
    version=__version__,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    description="Candidate Capability Intelligence - Technical Decision Support API",
)

# CORS Middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(dossier_router)
app.include_router(pipeline_router)
app.include_router(jobs_router)
app.include_router(candidates_router)
app.include_router(overrides_router)
app.include_router(privacy_router)
app.include_router(research_router)
app.include_router(research_demo_router)
app.include_router(live_router)



from cci.versioning import API_VERSION, get_default_version_families


@app.get(
    "/healthz",
    status_code=status.HTTP_200_OK,
    tags=["System"],
    summary="Health check endpoint",
)
@app.get(
    "/health",
    status_code=status.HTTP_200_OK,
    tags=["System"],
    summary="Health check endpoint alias",
)
def healthz() -> Any:
    """Liveness and health check endpoint."""
    return {
        "status": "healthy",
        "service": "cci-backend",
        "version": __version__,
        "api_version": API_VERSION,
        "version_families": get_default_version_families().to_dict(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "environment": settings.APP_ENV,
    }


from cci.limits import get_system_limits


@app.get(
    "/api/v1/system/limits",
    status_code=status.HTTP_200_OK,
    tags=["System"],
    summary="Get centralized system limits and operational budgets",
)
def get_limits() -> Any:
    """Returns active operational budgets, hard security ceilings, and user-facing explanations."""
    limits = get_system_limits(settings)
    return {
        "limits": limits.to_dict(),
        "explanations": limits.get_user_visible_explanations(),
    }

