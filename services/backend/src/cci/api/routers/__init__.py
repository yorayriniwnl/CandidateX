"""API routers package."""

from cci.api.routers.candidates import router as candidates_router
from cci.api.routers.dossier import router as dossier_router
from cci.api.routers.jobs import router as jobs_router
from cci.api.routers.pipeline_router import router as pipeline_router

__all__ = [
    "candidates_router",
    "dossier_router",
    "jobs_router",
    "pipeline_router",
]
