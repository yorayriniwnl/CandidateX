"""Public FastAPI surface containing only health and synthetic-demo routes."""
from fastapi import FastAPI

from cci.api.routers.synthetic_demo import router as synthetic_demo_router

app = FastAPI(
    title="CandidateX Synthetic Demonstration",
    version="1.0.0",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)
app.include_router(synthetic_demo_router)


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "service": "candidatex-synthetic-demo",
        "version": "1.0.0",
        "data_mode": "synthetic_only",
    }
