"""Public deployment surface: request-scoped analysis, no candidate directory APIs."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from cci.api.routers.live import router
from cci.api.routers.research_demo import router as research_demo_router
from cci.api.routers.jobs import router as jobs_router
from cci.api.routers.auth import router as auth_router
from cci.api.routers.billing import router as billing_router
from cci.config import settings
from cci.middleware.request_context import RequestContextMiddleware

app = FastAPI(title='CandidateX Live Analysis', version='0.3.0')

app.add_middleware(RequestContextMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(billing_router)
app.include_router(router)
app.include_router(research_demo_router)
app.include_router(jobs_router)


@app.get('/health')
def health():
    return {'status': 'healthy', 'service': 'candidatex-live-analysis', 'version': '0.3.0',
            'storage': 'request_only', 'supported_sources': ['public_github', 'public_web_pages', 'credential_page_text']}
