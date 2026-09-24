from typing import Any

"""FastAPI entrypoint for Candidate Capability Intelligence (CCI)."""

from datetime import datetime, timezone

from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware

from cci import __version__
from cci.api.routers import (
    candidates_router,
    dossier_router,
    jobs_router,
    overrides_router,
    pipeline_router,
    research_router,
)
from cci.config import settings
from cci.api.routers.research_demo import router as research_demo_router
from cci.api.routers.live import router as live_router
from cci.api.routers.synthetic_demo import router as synthetic_demo_router

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

app.include_router(dossier_router)
app.include_router(pipeline_router)
app.include_router(jobs_router)
app.include_router(candidates_router)
app.include_router(overrides_router)
app.include_router(research_router)
app.include_router(research_demo_router)
app.include_router(live_router)
app.include_router(synthetic_demo_router)


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
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "environment": settings.APP_ENV,
    }
