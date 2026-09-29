from typing import Any
import sys
from pathlib import Path

# Ensure backend src is on sys.path
_SRC_DIR = Path(__file__).resolve().parent.parent
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

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
from cci.api.routers.auth import router as auth_router
from cci.api.routers.billing import router as billing_router
from cci.api.routers.webhooks import router as webhooks_router
from cci.middleware.request_context import RequestContextMiddleware

app = FastAPI(
    title=settings.APP_NAME,
    version=__version__,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    description="Candidate Capability Intelligence - Technical Decision Support API",
)

# Request context and timing middleware (outermost)
app.add_middleware(RequestContextMiddleware)

# CORS Middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(billing_router)
app.include_router(webhooks_router)
app.include_router(dossier_router)
app.include_router(pipeline_router)
app.include_router(jobs_router)
app.include_router(candidates_router)
app.include_router(overrides_router)
app.include_router(research_router)
app.include_router(research_demo_router)
app.include_router(live_router)


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


if __name__ == "__main__":
    import socket
    import sys
    import uvicorn

    port = 8000
    try:
        sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
        sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
        sock.bind(("::", port))
        sock.listen(128)
        config = uvicorn.Config(app, log_level="info")
        server = uvicorn.Server(config)
        server.run(sockets=[sock])
    except Exception:
        uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")

