"""Live path contracts: real document parsing and static acquisition, mocked only at HTTP."""
import io
import zipfile
from datetime import datetime

import httpx
import pymupdf
import pytest
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


def readme_only_repository_transport(path_history_status=200, backend_file_count=1, requested_paths=None,
                                    duplicate_repository_commit=False,
                                    latest_repository_activity='2026-09-22T00:00:00Z'):
    def commit(number, login, date='2026-09-01T00:00:00Z'):
        return {
            'sha': f'{number:040x}',
            'author': {'login': login},
            'commit': {'committer': {'date': date}},
        }

    repository_commits = [commit(1, 'example', latest_repository_activity)] + [
        commit(i, 'maintainer') for i in range(2, 31)
    ]
    if duplicate_repository_commit:
        duplicate = repository_commits[0].copy()
        duplicate['sha'] = duplicate['sha'].upper()
        repository_commits.insert(1, duplicate)
    backend_paths = ['app.py'] + [f'app_{i}.py' for i in range(1, backend_file_count)]
    path_commits = {
        'README.md': [commit(1, 'example', '2026-09-22T00:00:00Z')]
    }
    path_commits.update({path: [
        commit(10, 'maintainer', '2023-06-01T00:00:00Z'),
        commit(11, 'maintainer', '2022-12-01T00:00:00Z'),
    ]
                         for path in backend_paths})
    archive_data = io.BytesIO()
    with zipfile.ZipFile(archive_data, 'w') as z:
        z.writestr('api-main/README.md', '# Candidate notes\n')
        for path in backend_paths:
            z.writestr(f'api-main/{path}', '@app.get("/items")\nasync def items():\n    return []\n')

    def handler(request):
        if request.url.path == '/repos/example/api':
            return httpx.Response(200, json={'private': False, 'fork': False, 'owner': {'login': 'example'}})
        if request.url.path == '/repos/example/api/commits':
            requested_path = request.url.params.get('path')
            if requested_path is not None and requested_paths is not None:
                requested_paths.append(requested_path)
            if requested_path is not None and path_history_status != 200:
                return httpx.Response(path_history_status, json={'message': 'temporarily unavailable'})
            commits = repository_commits if requested_path is None else path_commits.get(requested_path, [])
            return httpx.Response(200, json=commits)
        if request.url.host == 'codeload.github.com':
            return httpx.Response(200, content=archive_data.getvalue())
        raise AssertionError(f'Unexpected outbound request: {request.url}')

    return httpx.MockTransport(handler)


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


def test_live_fetch_keeps_provenance_and_withholds_undercovered_candidate_score(monkeypatch):
    from cci.live import acquisition
    monkeypatch.setattr(acquisition, 'HTTP_TRANSPORT', httpx.MockTransport(transport))
    response = client.post('/api/v1/live/analyze', json={'intake': intake().json(), 'role': 'backend', 'github_urls': ['https://github.com/example/api'], 'github_identity': 'example'})
    assert response.status_code == 200, response.text
    data = response.json()
    assert data['sources'][0]['status'] == 'observed'
    assert data['sources'][0]['commit_sha'] == SHA
    assert data['dossier']['rci'] is None
    assert data['dossier']['is_insufficient_evidence'] is True
    assert data['dossier']['coverage'] > 0.0
    backend_estimate = data['dossier']['capability_estimates']['backend_engineering']
    assert backend_estimate['estimate'] is None
    assert backend_estimate['is_observed'] is False
    assert backend_estimate['raw_evidence_count'] > 0
    assert data['dossier']['ownership_assessments'][0]['feature_vector']['sampled_commits'] == 1
    for record in data['dossier']['evidence_records']:
        assert record['immutable_revision'] == SHA
        assert len(record['fingerprint']) == 64
        assert record['provenance']['verification_status'] == 'live_static_inspection'
        assert record['provenance']['artifact_sha256']
    assert data['graph']['candidate_id'] == data['dossier']['candidate_id']


def test_readme_only_repository_contribution_does_not_attribute_backend_artifacts(monkeypatch):
    from cci.live import acquisition
    monkeypatch.setattr(acquisition, 'HTTP_TRANSPORT', readme_only_repository_transport())
    response = client.post('/api/v1/live/analyze', json={
        'intake': intake().json(),
        'role': 'backend',
        'github_urls': ['https://github.com/example/api'],
        'github_identity': 'example',
    })

    assert response.status_code == 200, response.text
    data = response.json()
    backend_records = [
        record for record in data['dossier']['evidence_records']
        if record['provenance'].get('artifact_path') == 'app.py'
    ]
    assert backend_records
    assert all(record['confidence_factors']['ownership_score'] == 0 for record in backend_records)
    assert all(record['confidence'] == 0 for record in backend_records)
    assert all(record['artifact_attribution']['state'] == 'UNATTRIBUTED' for record in backend_records)
    assert data['dossier']['capability_estimates']['backend_engineering']['estimate'] is None

    association = data['dossier']['repository_associations'][0]
    contribution = data['dossier']['repository_contributions'][0]
    assert association['identity_verified'] is False
    assert contribution['candidate_commit_count'] == 1
    assert contribution['sampled_commit_count'] == 30
    assert contribution['candidate_commit_ratio'] == 1 / 30

    app_artifacts = {
        node['id'] for node in data['graph']['nodes']
        if node['type'] == 'Artifact' and node['label'] == 'app.py'
    }
    assert app_artifacts
    assert not any(
        edge['type'] == 'AUTHORED_BY' and edge['source'] in app_artifacts
        for edge in data['graph']['edges']
    )
    repository_sources = {
        node['id'] for node in data['graph']['nodes']
        if node['type'] == 'Source' and node['properties'].get('locator') == 'https://github.com/example/api'
    }
    candidate_id = data['dossier']['candidate_id']
    assert repository_sources
    source_nodes = {node['id']: node for node in data['graph']['nodes']}
    assert all(source_nodes[source]['properties'].get('source_kind') == 'repository'
               for source in repository_sources)
    assert any(
        edge['source'] == candidate_id and edge['target'] in repository_sources and edge['type'] == 'ASSOCIATED_WITH'
        for edge in data['graph']['edges']
    )
    assert any(
        edge['source'] == candidate_id and edge['target'] in repository_sources and edge['type'] == 'CONTRIBUTES_TO'
        for edge in data['graph']['edges']
    )

    python_skill = next(skill for skill in data['analysis']['skills'] if skill['skill'] == 'Python')
    assert python_skill['status'] == 'repository_only'


def test_artifact_recency_uses_path_history_instead_of_recent_repository_activity(monkeypatch):
    from cci.live import acquisition
    from cci.scoring.recency import calculate_elapsed_years, compute_recency_factor
    from cci.domain.enums import CapabilityKey

    monkeypatch.setattr(acquisition, 'HTTP_TRANSPORT', readme_only_repository_transport())
    response = client.post('/api/v1/live/analyze', json={
        'intake': intake().json(),
        'role': 'backend',
        'github_urls': ['https://github.com/example/api'],
        'github_identity': 'example',
    })

    assert response.status_code == 200, response.text
    data = response.json()
    backend_record = next(
        record for record in data['dossier']['evidence_records']
        if record['provenance'].get('artifact_path') == 'app.py'
    )
    recency = backend_record['artifact_recency']
    assert recency['state'] == 'known'
    assert recency['last_meaningful_modification_at'].startswith('2023-06-01')
    assert recency['last_meaningful_revision_sha'] == f'{10:040x}'
    assert recency['repository_last_activity'].startswith('2026-09-22')

    artifact_factor = compute_recency_factor(
        calculate_elapsed_years(
            datetime.fromisoformat(
                recency['last_meaningful_modification_at'].replace('Z', '+00:00')
            ),
        ),
        CapabilityKey.BACKEND_ENGINEERING,
    )
    repository_factor = compute_recency_factor(
        calculate_elapsed_years(
            datetime.fromisoformat(
                recency['repository_last_activity'].replace('Z', '+00:00')
            ),
        ),
        CapabilityKey.BACKEND_ENGINEERING,
    )
    assert backend_record['confidence_factors']['recency_factor'] == pytest.approx(artifact_factor)
    assert backend_record['confidence_factors']['recency_factor'] < repository_factor


def test_artifact_recency_keeps_candidate_touch_separate_from_latest_modification():
    from cci.live.acquisition import build_artifact_recency

    history = [
        {
            'sha': 'a' * 40,
            'author': {'login': 'maintainer'},
            'commit': {'committer': {'date': '2023-06-01T00:00:00Z'}},
        },
        {
            'sha': 'b' * 40,
            'author': {'login': 'example'},
            'commit': {'committer': {'date': '2023-03-01T00:00:00Z'}},
        },
    ]

    recency = build_artifact_recency(
        history,
        'example',
        datetime.fromisoformat('2026-09-22T00:00:00+00:00'),
    )

    assert recency.state == 'known'
    assert recency.last_meaningful_revision_sha == 'a' * 40
    assert recency.last_meaningful_modification_at.isoformat().startswith('2023-06-01')
    assert recency.candidate_contribution_revision_sha == 'b' * 40
    assert recency.candidate_contribution_at.isoformat().startswith('2023-03-01')


def test_bad_repository_activity_does_not_block_known_artifact_recency(monkeypatch):
    from cci.live import acquisition

    monkeypatch.setattr(
        acquisition,
        'HTTP_TRANSPORT',
        readme_only_repository_transport(latest_repository_activity='not-a-date'),
    )
    response = client.post('/api/v1/live/analyze', json={
        'intake': intake().json(),
        'role': 'backend',
        'github_urls': ['https://github.com/example/api'],
        'github_identity': '',
    })

    assert response.status_code == 200, response.text
    data = response.json()
    record = next(
        item for item in data['dossier']['evidence_records']
        if item['provenance'].get('artifact_path') == 'app.py'
    )
    assert record['artifact_recency']['state'] == 'known'
    assert record['artifact_recency']['last_meaningful_modification_at'].startswith('2023-06-01')
    assert record['artifact_recency']['repository_last_activity'] is None


def test_malformed_artifact_history_remains_explicitly_unknown():
    from cci.live.acquisition import build_artifact_recency

    recency = build_artifact_recency(
        [{
            'sha': 'a' * 40,
            'author': {'login': 'example'},
            'commit': {'committer': {'date': 'not-a-date'}},
        }],
        'example',
        datetime.fromisoformat('2026-09-22T00:00:00+00:00'),
    )

    assert recency.state == 'artifact_recency_unknown'
    assert recency.last_meaningful_modification_at is None
    assert recency.last_meaningful_revision_sha is None
    assert any('Repository last activity is retained separately' in item
               for item in recency.limitations)


def test_path_history_failure_does_not_fall_back_to_repository_commit_share(monkeypatch):
    from cci.live import acquisition
    monkeypatch.setattr(acquisition, 'HTTP_TRANSPORT', readme_only_repository_transport(path_history_status=403))

    response = client.post('/api/v1/live/analyze', json={
        'intake': intake().json(),
        'role': 'backend',
        'github_urls': ['https://github.com/example/api'],
        'github_identity': 'example',
    })

    assert response.status_code == 200, response.text
    data = response.json()
    backend_records = [
        record for record in data['dossier']['evidence_records']
        if record['provenance'].get('artifact_path') == 'app.py'
    ]
    assert backend_records
    assert all(record['confidence_factors']['ownership_score'] == 0 for record in backend_records)
    assert all(record['artifact_attribution']['state'] == 'UNKNOWN' for record in backend_records)
    assert all(record['artifact_recency']['state'] == 'artifact_recency_unknown' for record in backend_records)
    assert all(record['artifact_recency']['last_meaningful_modification_at'] is None for record in backend_records)
    assert all(record['artifact_recency']['repository_last_activity'].startswith('2026-09-22')
               for record in backend_records)
    assert data['sources'][0]['status'] == 'observed'


def test_large_repository_attribution_budget_leaves_unqueried_paths_unknown(monkeypatch):
    from cci.live import acquisition
    requested_paths = []
    monkeypatch.setattr(acquisition, 'HTTP_TRANSPORT', readme_only_repository_transport(
        backend_file_count=30, requested_paths=requested_paths,
    ))

    response = client.post('/api/v1/live/analyze', json={
        'intake': intake().json(),
        'role': 'backend',
        'github_urls': ['https://github.com/example/api'],
        'github_identity': 'example',
    })

    assert response.status_code == 200, response.text
    data = response.json()
    receipt = data['sources'][0]
    assert receipt['attribution_paths_considered'] == 30
    assert receipt['attribution_paths_requested'] == 24
    assert receipt['artifact_recency_paths_requested'] == 24
    assert receipt['attribution_paths_deferred'] == 6
    assert len(requested_paths) == 24
    assert all('confidence_factors' in record and record['confidence_factors']['ownership_score'] == 0
               for record in data['dossier']['evidence_records'])
    deferred = [item for item in receipt['artifact_attributions'] if item['artifact_path'] not in requested_paths]
    assert len(deferred) == 6
    assert all(item['state'] == 'UNKNOWN' and item['ownership_score'] == 0 for item in deferred)
    deferred_recency = [
        item for item in receipt['artifact_recencies']
        if item['artifact_path'] not in requested_paths
    ]
    assert len(deferred_recency) == 6
    assert all(item['state'] == 'artifact_recency_unknown' for item in deferred_recency)


def test_missing_github_identity_fetches_recency_without_claiming_attribution(monkeypatch):
    from cci.live import acquisition
    requested_paths = []
    monkeypatch.setattr(acquisition, 'HTTP_TRANSPORT', readme_only_repository_transport(
        requested_paths=requested_paths,
    ))

    response = client.post('/api/v1/live/analyze', json={
        'intake': intake().json(),
        'role': 'backend',
        'github_urls': ['https://github.com/example/api'],
        'github_identity': '',
    })

    assert response.status_code == 200, response.text
    data = response.json()
    assert requested_paths == ['app.py']
    assert data['sources'][0]['attribution_paths_requested'] == 0
    assert data['sources'][0]['artifact_recency_paths_requested'] == 1
    assert all(item['state'] == 'UNKNOWN' and item['ownership_score'] == 0
               for item in data['sources'][0]['artifact_attributions'])
    backend_records = [
        record for record in data['dossier']['evidence_records']
        if record['provenance'].get('artifact_path') == 'app.py'
    ]
    assert backend_records
    assert all(record['artifact_attribution']['state'] == 'UNKNOWN' for record in backend_records)
    assert all(record['artifact_recency']['state'] == 'known' for record in backend_records)


def test_malformed_path_history_stays_unknown_without_repository_fallback():
    from cci.live.acquisition import get_artifact_attribution

    class MalformedFetcher:
        def get(self, endpoint):
            assert 'path=app.py' in endpoint
            assert f'sha={SHA}' in endpoint
            return [{'sha': 'not-an-immutable-sha', 'author': {'login': 'example'}}]

    attribution, stop_requests = get_artifact_attribution(
        MalformedFetcher(), 'example', 'api', SHA, 'app.py', 'example',
    )

    assert stop_requests is False
    assert attribution.state == 'UNKNOWN'
    assert attribution.ownership_score == 0
    assert attribution.attribution_confidence == 0
    assert attribution.candidate_commit_count == 0


def test_duplicate_path_commit_rows_do_not_inflate_attribution():
    from cci.live.acquisition import get_artifact_attribution

    candidate_commit = {'sha': 'b' * 40, 'author': {'login': 'example'}}
    duplicate_candidate_commit = {**candidate_commit, 'sha': 'B' * 40}
    maintainer_commit = {'sha': 'c' * 40, 'author': {'login': 'maintainer'}}

    class DuplicateFetcher:
        def get(self, endpoint):
            return [candidate_commit, duplicate_candidate_commit, maintainer_commit]

    attribution, stop_requests = get_artifact_attribution(
        DuplicateFetcher(), 'example', 'api', SHA, 'app.py', 'example',
    )

    assert stop_requests is False
    assert attribution.candidate_commit_count == 1
    assert attribution.sampled_path_commit_count == 2
    assert attribution.ownership_score == 0.5
    assert attribution.candidate_commit_shas == ['b' * 40]


def test_duplicate_repository_commit_rows_do_not_inflate_repository_contribution(monkeypatch):
    from cci.live import acquisition
    monkeypatch.setattr(acquisition, 'HTTP_TRANSPORT', readme_only_repository_transport(
        duplicate_repository_commit=True,
    ))

    response = client.post('/api/v1/live/analyze', json={
        'intake': intake().json(),
        'role': 'backend',
        'github_urls': ['https://github.com/example/api'],
        'github_identity': 'example',
    })

    assert response.status_code == 200, response.text
    contribution = response.json()['dossier']['repository_contributions'][0]
    assert contribution['sampled_commit_count'] == 29
    assert contribution['candidate_commit_count'] == 1
    assert contribution['candidate_commit_ratio'] == 1 / 29


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
