"""Live path contracts: real document parsing and static acquisition, mocked only at HTTP."""
import io
import zipfile

import httpx
import pymupdf
from fastapi.testclient import TestClient

from cci.main import app

client = TestClient(app)
SHA = 'a' * 40


def resume_bytes():
    with pymupdf.open() as doc:
        page = doc.new_page()
        page.insert_text((50, 50), 'Example Candidate\nSkills\nPython, SQL\nProjects\nPublic API')
        page.insert_link({'kind': pymupdf.LINK_URI, 'from': pymupdf.Rect(50, 100, 160, 120),
                          'uri': 'https://github.com/example/api'})
        return doc.tobytes()


def intake():
    return client.post('/api/v1/live/intake', content=resume_bytes(), headers={'X-Filename': 'resume.pdf'})


def archive(path='api-main/app.py', content='@app.get("/items")\nasync def items():\n    return []\n'):
    data = io.BytesIO()
    with zipfile.ZipFile(data, 'w') as z:
        z.writestr(path, content)
    return data.getvalue()


def transport(request):
    path = request.url.path
    if path == '/repos/example/api':
        return httpx.Response(200, json={'private': False, 'fork': False, 'default_branch': 'main', 'owner': {'login': 'example'}})
    if path == '/repos/example/api/commits':
        return httpx.Response(200, json=[{'sha': SHA, 'author': {'login': 'example'}, 'commit': {'committer': {'date': '2026-09-01T00:00:00Z'}}}])
    if request.url.host == 'codeload.github.com':
        return httpx.Response(200, content=archive())
    raise AssertionError(f'Unexpected outbound request: {request.url}')


def test_upload_extracts_pdf_text_and_embedded_links_without_retaining_file():
    response = intake()
    assert response.status_code == 200
    data = response.json()
    assert data['manifest']['display_name'] == 'Example Candidate'
    assert data['manifest']['github_urls'] == ['https://github.com/example/api']
    assert data['manifest']['claimed_skills'] == ['Python', 'SQL']
    assert len(data['document_sha256']) == 64
    assert data['storage'] == 'request_only'


def test_invalid_and_oversized_documents_are_rejected():
    assert client.post('/api/v1/live/intake', content=b'bad', headers={'X-Filename': 'bad.pdf'}).status_code == 422
    assert client.post('/api/v1/live/intake', content=b'x' * (3 * 1024 * 1024 + 1), headers={'X-Filename': 'big.pdf'}).status_code == 413
    assert client.post('/api/v1/live/intake', content=b'hello', headers={'X-Filename': 'run.exe'}).status_code == 415


def test_resume_claims_alone_do_not_invent_capability():
    response = client.post('/api/v1/live/analyze', json={'intake': intake().json(), 'role': 'backend', 'github_urls': [], 'github_identity': ''})
    assert response.status_code == 200
    data = response.json()
    assert data['dossier']['rci'] is None
    assert data['dossier']['coverage'] == 0
    assert data['dossier']['evidence_mode'] == 'live'
    assert data['dossier']['evidence_records'] == []


def test_live_fetch_scores_artifacts_and_keeps_commit_and_content_provenance(monkeypatch):
    from cci.live import acquisition
    monkeypatch.setattr(acquisition, 'HTTP_TRANSPORT', httpx.MockTransport(transport))
    response = client.post('/api/v1/live/analyze', json={'intake': intake().json(), 'role': 'backend', 'github_urls': ['https://github.com/example/api'], 'github_identity': 'example'})
    assert response.status_code == 200, response.text
    data = response.json()
    assert data['sources'][0]['status'] == 'observed'
    assert data['sources'][0]['commit_sha'] == SHA
    assert data['dossier']['rci'] is not None
    assert data['dossier']['ownership_assessments'][0]['feature_vector']['sampled_commits'] == 1
    for record in data['dossier']['evidence_records']:
        assert record['immutable_revision'] == SHA
        assert len(record['fingerprint']) == 64
        assert record['provenance']['verification_status'] == 'live_static_inspection'
        assert record['provenance']['artifact_sha256']
    assert data['graph']['candidate_id'] == data['dossier']['candidate_id']


def test_source_failure_is_explicit_and_no_sample_is_substituted(monkeypatch):
    from cci.live import acquisition
    monkeypatch.setattr(acquisition, 'HTTP_TRANSPORT', httpx.MockTransport(lambda req: httpx.Response(403, json={'message': 'API rate limit exceeded'})))
    response = client.post('/api/v1/live/analyze', json={'intake': intake().json(), 'github_urls': ['https://github.com/example/api'], 'github_identity': 'example'})
    data = response.json()
    assert data['sources'][0]['status'] == 'rate_limited'
    assert data['dossier']['rci'] is None


def test_disallowed_urls_never_reach_network(monkeypatch):
    from cci.live import acquisition
    def forbidden(req):
        raise AssertionError('Invalid URL reached network')
    monkeypatch.setattr(acquisition, 'HTTP_TRANSPORT', httpx.MockTransport(forbidden))
    for url in ['http://127.0.0.1/private', 'https://github.com@evil.example/a/b', 'https://github.com/a/../search', 'https://github.com:444/a/b']:
        response = client.post('/api/v1/live/analyze', json={'intake': intake().json(), 'github_urls': [url]})
        assert response.status_code == 422, response.text


def test_archive_traversal_rejected(monkeypatch):
    from cci.live import acquisition
    def malicious(req):
        if req.url.host == 'codeload.github.com':
            return httpx.Response(200, content=archive('root/../../escape.py'))
        return transport(req)
    monkeypatch.setattr(acquisition, 'HTTP_TRANSPORT', httpx.MockTransport(malicious))
    data = client.post('/api/v1/live/analyze', json={'intake': intake().json(), 'github_urls': ['https://github.com/example/api']}).json()
    assert data['sources'][0]['status'] == 'security_blocked'
    assert data['dossier']['evidence_records'] == []
