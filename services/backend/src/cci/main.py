"""FastAPI entrypoint for Candidate Capability Intelligence (CCI)."""

from datetime import datetime, timezone
from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware

from cci import __version__
from cci.config import settings

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


from cci.api.routers import dossier_router

app.include_router(dossier_router)


@app.get(
    "/healthz",
    status_code=status.HTTP_200_OK,
    tags=["System"],
    summary="Health check endpoint",
)
def healthz():
    """Liveness and health check endpoint."""
    return {
        "status": "healthy",
        "service": "cci-backend",
        "version": __version__,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "environment": settings.APP_ENV,
    }
