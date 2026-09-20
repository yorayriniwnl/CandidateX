"""Integration tests for GitHub acquisition, classifier, and artifact indexing."""

import json
import os
import pytest
import httpx

from cci.domain.contracts import CandidateManifest
from cci.domain.enums import ScanDepth
from cci.sources.classifier import classify_repository_scan_depth
from cci.github.client import BoundedGitHubClient, GitHubRateLimitError
from cci.security.repository_workspace import SafeRepositoryWorkspace
from cci.analyzers.repository.indexer import (
    categorize_file,
    index_repository_artifacts,
)


def test_deep_vs_light_scan_classification():
    """Verify deep vs light scan classification rules:
    - Explicit CV project repo -> DEEP
    - Profile repo not cited in CV -> LIGHT
    - Unrelated / organization repo -> LIGHT (ambiguous)
    """
    manifest = CandidateManifest(
        display_name="Alice Candidate",
        github_urls=[
            "https://github.com/alice",
            "https://github.com/alice/flagship-project",
        ],
        project_links=[
            "https://github.com/alice/flagship-project",
            "https://github.com/company/super-tool",
        ],
        project_claims=[
            {"title": "Flagship Project", "url": "https://github.com/alice/flagship-project"},
        ],
    )

    # 1. Explicit CV project repo -> DEEP
    res1 = classify_repository_scan_depth("https://github.com/alice/flagship-project", manifest)
    assert res1.scan_depth == ScanDepth.DEEP
    assert not res1.is_ambiguous

    # Another explicit project link in CV -> DEEP
    res2 = classify_repository_scan_depth("https://github.com/company/super-tool", manifest)
    assert res2.scan_depth == ScanDepth.DEEP
    assert not res2.is_ambiguous

    # 2. Other repo on supplied account -> LIGHT
    res3 = classify_repository_scan_depth("https://github.com/alice/small-experiment", manifest)
    assert res3.scan_depth == ScanDepth.LIGHT
    assert not res3.is_ambiguous

    # 3. Third-party org repo not in CV -> LIGHT (Ambiguous)
    res4 = classify_repository_scan_depth("https://github.com/stranger/random-repo", manifest)
    assert res4.scan_depth == ScanDepth.LIGHT
    assert res4.is_ambiguous


def test_github_client_blocks_search_endpoints():
    """Invariant: GitHub client must reject any attempt to call search endpoints."""
    client = BoundedGitHubClient()
    with pytest.raises(ValueError, match="Forbidden: Candidate identity discovery via search is strictly prohibited"):
        client._request("/search/users?q=Alice")


def test_github_client_mock_transport():
    """Verify GitHub client parsing with mock transport."""
    def mock_handler(request: httpx.Request) -> httpx.Response:
        url_path = request.url.path
        if url_path == "/repos/alice/project1":
            return httpx.Response(
                200,
                json={"name": "project1", "default_branch": "main", "stargazers_count": 42},
                headers={"ETag": '"etag_proj1_123"'},
            )
        elif url_path == "/repos/alice/project1/languages":
            return httpx.Response(200, json={"Python": 45000, "TypeScript": 15000})
        elif url_path == "/repos/alice/project1/commits":
            return httpx.Response(200, json=[{"sha": "c1", "commit": {"message": "Initial commit"}}])
        elif url_path == "/repos/alice/project1/pulls":
            return httpx.Response(200, json=[{"id": 1, "title": "Feature PR"}])
        return httpx.Response(404, json={"message": "Not Found"})

    transport = httpx.MockTransport(mock_handler)
    client = BoundedGitHubClient(transport=transport)

    meta = client.get_repository_metadata("alice", "project1")
    assert meta["name"] == "project1"
    assert meta["default_branch"] == "main"

    langs = client.get_languages("alice", "project1")
    assert langs["Python"] == 45000

    commits = client.get_commits("alice", "project1")
    assert len(commits) == 1
    assert commits[0]["sha"] == "c1"


def test_artifact_indexer_categorization_and_fingerprinting():
    """Verify safe workspace artifact categorization, SHA-256 generation, and composite fingerprinting."""
    with SafeRepositoryWorkspace() as ws:
        # Create representative artifact structure
        os.makedirs(os.path.join(ws.root, "src"), exist_ok=True)
        os.makedirs(os.path.join(ws.root, "tests"), exist_ok=True)
        os.makedirs(os.path.join(ws.root, ".github", "workflows"), exist_ok=True)
        os.makedirs(os.path.join(ws.root, "migrations"), exist_ok=True)
        os.makedirs(os.path.join(ws.root, "docs"), exist_ok=True)

        with open(os.path.join(ws.root, "package.json"), "w") as f:
            f.write('{"name": "test-pkg"}')

        with open(os.path.join(ws.root, "src", "app.py"), "w") as f:
            f.write("def main(): pass")

        with open(os.path.join(ws.root, "tests", "test_app.py"), "w") as f:
            f.write("def test_main(): assert True")

        with open(os.path.join(ws.root, ".github", "workflows", "ci.yml"), "w") as f:
            f.write("name: CI\non: [push]")

        with open(os.path.join(ws.root, "migrations", "001_init.sql"), "w") as f:
            f.write("CREATE TABLE users (id INT);")

        with open(os.path.join(ws.root, "Dockerfile"), "w") as f:
            f.write("FROM python:3.11\nCMD python app.py")

        with open(os.path.join(ws.root, "docs", "README.md"), "w") as f:
            f.write("# Project Docs")

        with open(os.path.join(ws.root, "openapi.yaml"), "w") as f:
            f.write("openapi: 3.0.0")

        metadata, artifacts = index_repository_artifacts(
            workspace=ws,
            repo_url="https://github.com/alice/test-repo",
            commit_sha="a1b2c3d4",
            scan_depth=ScanDepth.DEEP,
        )

        assert metadata.total_artifacts == 8
        assert metadata.repo_url == "https://github.com/alice/test-repo"
        assert metadata.commit_sha == "a1b2c3d4"
        assert len(metadata.snapshot_fingerprint) == 64  # SHA-256

        by_cat = {a.relative_path: a.category for a in artifacts}
        assert by_cat["package.json"] == "manifests"
        assert by_cat["src/app.py"] == "source"
        assert by_cat["tests/test_app.py"] == "tests"
        assert by_cat[".github/workflows/ci.yml"] == "ci"
        assert by_cat["migrations/001_init.sql"] == "database"
        assert by_cat["Dockerfile"] == "infra"
        assert by_cat["docs/README.md"] == "docs"
        assert by_cat["openapi.yaml"] == "openapi"

        # Content hash verified
        for a in artifacts:
            assert len(a.content_sha256) == 64
