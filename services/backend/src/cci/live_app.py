"""Public deployment surface: request-scoped analysis, no candidate directory APIs."""
from fastapi import FastAPI
from cci.api.routers.live import router
from cci.api.routers.research_demo import router as research_demo_router

app = FastAPI(title='CandidateX Live Analysis', version='0.2.0')
app.include_router(router)
app.include_router(research_demo_router)


@app.get('/health')
def health():
    return {'status': 'healthy', 'service': 'candidatex-live-analysis', 'version': '0.2.0',
            'storage': 'request_only', 'supported_sources': ['public_github']}
