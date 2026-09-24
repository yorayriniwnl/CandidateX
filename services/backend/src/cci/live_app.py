"""Public deployment surface: request-scoped analysis, no candidate directory APIs."""
from fastapi import FastAPI
from cci.api.routers.live import router
from cci.api.routers.research_demo import router as research_demo_router

from cci.versioning import API_VERSION, get_default_version_families

app = FastAPI(title='CandidateX Live Analysis', version=API_VERSION)
app.include_router(router)
app.include_router(research_demo_router)


@app.get('/health')
def health():
    return {
        'status': 'healthy',
        'service': 'candidatex-live-analysis',
        'version': API_VERSION,
        'api_version': API_VERSION,
        'version_families': get_default_version_families().to_dict(),
        'storage': 'request_only',
        'supported_sources': ['public_github', 'public_web_pages', 'credential_page_text'],
    }
