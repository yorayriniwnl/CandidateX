"""Public deployment surface: request-scoped analysis, no candidate directory APIs."""
from fastapi import FastAPI
from cci.api.routers.live import router

app = FastAPI(title='CandidateX Live Analysis', version='0.3.0')
app.include_router(router)


@app.get('/health')
def health():
    return {'status': 'healthy', 'service': 'candidatex-live-analysis', 'version': '0.3.0',
            'storage': 'request_only', 'supported_sources': ['public_github', 'public_web_pages', 'credential_page_text']}
