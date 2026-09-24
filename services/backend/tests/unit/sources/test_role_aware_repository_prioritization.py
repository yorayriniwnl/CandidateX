"""Unit tests for role-aware repository prioritization (Fix 23).

Verifies that the newest-repositories-first heuristic is completely replaced with
multidimensional priority scoring across the 10 core features:
1. explicitly supplied repo
2. resume-linked repo
3. project-title similarity
4. technology relevance
5. role relevance
6. deployment linkage
7. portfolio linkage
8. non-fork preference (and fork penalty)
9. engineering depth
10. recent meaningful activity

Invariants:
- selection_reason is stored for every selected repository.
- Every non-selected repository remains visible as inventory_only or deferred.
- No repository silently disappears.
"""

from datetime import datetime, timezone
import pytest

from cci.domain.contracts import CandidateManifest, RepositoryAssociation
from cci.domain.enums import CanonicalRole
from cci.live.prioritization import (
    compute_title_similarity,
    prioritize_repositories,
    score_repository_candidate,
)


def _repo(
    name: str,
    *,
    language: str = "Python",
    description: str = "",
    fork: bool = False,
    archived: bool = False,
    size_kb: int = 200,
    stars: int = 5,
    pushed_at: str = "2026-08-01T00:00:00Z",
    topics: list[str] | None = None,
) -> dict:
    return {
        "url": f"https://github.com/alice/{name}",
        "name": name,
        "language": language,
        "description": description,
        "fork": fork,
        "archived": archived,
        "size_kb": size_kb,
        "stars": stars,
        "pushed_at": pushed_at,
        "topics": topics or [],
    }


def test_explicitly_supplied_repo_has_top_priority():
    """Explicitly requested repository must be prioritized even if older than others."""
    repos = [
        _repo("old-explicit-repo", language="Python", pushed_at="2024-01-01T00:00:00Z"),
        _repo("new-unrelated-repo", language="CSS", pushed_at="2026-09-20T00:00:00Z"),
    ]
    results = prioritize_repositories(
        repos,
        max_repositories=1,
        target_role=CanonicalRole.BACKEND,
        explicit_urls={"https://github.com/alice/old-explicit-repo"},
    )
    assert len(results) == 2
    selected = [r for r in results if r.is_selected]
    assert len(selected) == 1
    assert selected[0].name == "old-explicit-repo"
    assert "explicitly supplied repository link" in selected[0].selection_reason


def test_role_relevance_breaks_newest_first():
    """Role-relevant backend repo must beat newer toy frontend/dotfile repos."""
    repos = [
        # Newest repo: simple dotfiles updated yesterday
        _repo("dotfiles", language="Shell", size_kb=3, pushed_at="2026-09-23T00:00:00Z"),
        # Older repo: substantial backend FastAPI microservice
        _repo(
            "billing-microservice",
            language="Python",
            description="Production distributed billing service",
            topics=["fastapi", "postgres", "docker", "api"],
            size_kb=450,
            pushed_at="2026-06-01T00:00:00Z",
        ),
    ]
    results = prioritize_repositories(
        repos,
        max_repositories=1,
        target_role=CanonicalRole.BACKEND,
    )
    assert results[0].name == "billing-microservice"
    assert results[0].is_selected is True
    assert "aligned with BACKEND role" in results[0].selection_reason
    assert results[1].name == "dotfiles"
    assert results[1].is_selected is False
    assert results[1].inspection_status == "deferred"
    assert results[1].deferral_reason is not None


def test_resume_linked_and_project_title_similarity():
    """Matches candidate resume project title and links."""
    repos = [
        _repo("unrelated-sandbox", language="Python"),
        _repo("payflow-core", language="Python", description="Core engine for PayFlow billing"),
    ]
    results = prioritize_repositories(
        repos,
        max_repositories=1,
        target_role=CanonicalRole.BACKEND,
        project_titles=["PayFlow Core Engine"],
        resume_urls={"https://github.com/alice/payflow-core"},
    )
    assert results[0].name == "payflow-core"
    assert "matches resume project" in results[0].selection_reason
    assert "linked in resume project citations" in results[0].selection_reason


def test_technology_relevance_from_skills_and_jd():
    """Matches claimed candidate skills and job description keywords."""
    repos = [
        _repo("general-tools", language="Java", topics=["utilities"]),
        _repo("data-crawler", language="Python", topics=["scrapy", "redis", "asyncio"]),
    ]
    results = prioritize_repositories(
        repos,
        max_repositories=1,
        target_role=CanonicalRole.BACKEND,
        candidate_skills=["Python", "Redis", "AsyncIO"],
        jd_keywords=["distributed", "redis", "crawler"],
    )
    assert results[0].name == "data-crawler"
    assert "matches claimed/required technologies" in results[0].selection_reason


def test_deployment_and_portfolio_linkage():
    """Bonus score for repositories linked to live deployments or portfolios."""
    repos = [
        _repo("task-tracker-api", language="Go", description="Live at https://tasks.alice.dev/api"),
        _repo("random-script", language="Go", description="CLI script"),
    ]
    results = prioritize_repositories(
        repos,
        max_repositories=1,
        target_role=CanonicalRole.BACKEND,
        deployment_urls=["https://tasks.alice.dev"],
        portfolio_urls=["https://alice.dev"],
    )
    assert results[0].name == "task-tracker-api"
    assert "linked to candidate deployment" in results[0].selection_reason


def test_non_fork_preference_and_fork_penalization():
    """Forks are penalised and kept as inventory_only when non-forks exist."""
    repos = [
        _repo("upstream-fastapi-fork", language="Python", fork=True, stars=1000, size_kb=5000),
        _repo("my-original-service", language="Python", fork=False, stars=1, size_kb=150),
    ]
    results = prioritize_repositories(
        repos,
        max_repositories=1,
        target_role=CanonicalRole.BACKEND,
    )
    assert results[0].name == "my-original-service"
    assert results[0].is_selected is True
    assert "original candidate repository (non-fork)" in results[0].selection_reason

    assert results[1].name == "upstream-fastapi-fork"
    assert results[1].is_selected is False
    assert results[1].inspection_status == "inventory_only"
    assert "Forked third-party repository" in results[1].deferral_reason


def test_engineering_depth_and_meaningful_activity():
    """Deep multi-topic active repository ranks higher than single-file stub."""
    repos = [
        _repo("toy-snippet", language="Python", size_kb=2, stars=0, topics=[]),
        _repo("distributed-cache", language="Python", size_kb=800, stars=12, topics=["distributed", "cache", "network"]),
    ]
    results = prioritize_repositories(
        repos,
        max_repositories=1,
        target_role=CanonicalRole.BACKEND,
    )
    assert results[0].name == "distributed-cache"
    assert "engineering depth" in results[0].selection_reason


def test_selection_reason_stored_for_all_selected_repos():
    """Every selected repository must have a clear, non-empty selection_reason."""
    repos = [
        _repo(f"repo-{i}", language="Python", size_kb=50 + i * 20)
        for i in range(5)
    ]
    results = prioritize_repositories(
        repos,
        max_repositories=3,
        target_role=CanonicalRole.BACKEND,
    )
    selected = [r for r in results if r.is_selected]
    assert len(selected) == 3
    for s in selected:
        assert isinstance(s.selection_reason, str)
        assert len(s.selection_reason) > 10


def test_no_repo_silently_disappears():
    """Every candidate repository appears in results with inspection_status and rationale."""
    repos = [
        _repo("selected-1", language="Python", size_kb=200),
        _repo("selected-2", language="Python", size_kb=180),
        _repo("deferred-3", language="Python", size_kb=20),
        _repo("fork-4", language="Python", fork=True),
        _repo("archived-5", language="Python", archived=True),
    ]
    results = prioritize_repositories(
        repos,
        max_repositories=2,
        target_role=CanonicalRole.BACKEND,
    )
    assert len(results) == 5

    res_by_name = {r.name: r for r in results}
    assert res_by_name["selected-1"].is_selected is True
    assert res_by_name["selected-1"].inspection_status == "observed"

    assert res_by_name["selected-2"].is_selected is True
    assert res_by_name["selected-2"].inspection_status == "observed"

    assert res_by_name["deferred-3"].is_selected is False
    assert res_by_name["deferred-3"].inspection_status == "deferred"
    assert res_by_name["deferred-3"].deferral_reason is not None

    assert res_by_name["fork-4"].is_selected is False
    assert res_by_name["fork-4"].inspection_status == "inventory_only"

    assert res_by_name["archived-5"].is_selected is False
    assert res_by_name["archived-5"].inspection_status == "inventory_only"


def test_acquire_sources_integration_with_prioritization(monkeypatch):
    """Full acquire_sources integration verifying role-aware repository selection and receipts."""
    import io
    import zipfile
    import httpx
    from cci.live import acquisition

    sha = "1" * 40
    archive_buf = io.BytesIO()
    with zipfile.ZipFile(archive_buf, "w") as z:
        z.writestr("app.py", "def main(): pass\n")
    archive_bytes = archive_buf.getvalue()

    def mock_handler(req: httpx.Request):
        url_str = str(req.url)
        path = req.url.path

        if path == "/users/alice":
            return httpx.Response(200, json={"login": "alice", "public_repos": 8})
        if path == "/users/alice/repos":
            return httpx.Response(200, json=[
                {"name": "fork-upstream", "fork": True, "archived": False, "size": 1000, "stargazers_count": 50},
                {"name": "backend-core", "fork": False, "language": "Python", "description": "FastAPI engine", "topics": ["fastapi", "postgres"], "size": 400},
                {"name": "payflow-app", "fork": False, "language": "Python", "description": "PayFlow service", "size": 350},
                {"name": "deploy-api", "fork": False, "language": "Python", "description": "Live deployment", "size": 300},
                {"name": "go-microservice", "fork": False, "language": "Go", "topics": ["grpc"], "size": 250},
                {"name": "data-pipeline", "fork": False, "language": "Python", "topics": ["redis"], "size": 200},
                {"name": "extra-tool", "fork": False, "language": "Python", "size": 150},
                {"name": "dotfiles", "fork": False, "language": "Shell", "size": 5},
            ])
        if "/commits" in path:
            return httpx.Response(200, json=[{
                "sha": sha,
                "author": {"login": "alice"},
                "commit": {"committer": {"date": "2026-09-01T00:00:00Z"}},
            }])
        if req.url.host == "codeload.github.com":
            return httpx.Response(200, content=archive_bytes)
        if path.startswith("/repos/alice/"):
            repo_name = path.split("/")[3]
            return httpx.Response(200, json={
                "name": repo_name,
                "private": False,
                "fork": repo_name == "fork-upstream",
                "default_branch": "main",
                "pushed_at": "2026-09-01T00:00:00Z",
                "size": 300,
            })
        return httpx.Response(404)

    monkeypatch.setattr(acquisition, "HTTP_TRANSPORT", httpx.MockTransport(mock_handler))

    manifest = CandidateManifest(
        display_name="Alice Smith",
        claimed_skills=["Python", "FastAPI", "PostgreSQL", "Go"],
        project_claims=[{"title": "PayFlow App", "description": "Core billing"}],
        deployment_urls=["https://deploy-api.example.com"],
    )

    records, ownership, receipts = acquisition.acquire_sources(
        urls=["https://github.com/alice"],
        identity="alice",
        target_role=CanonicalRole.BACKEND,
        manifest=manifest,
        deployment_urls=["https://deploy-api.example.com"],
    )

    # Verify profile receipt exists
    profile_receipts = [r for r in receipts if r.get("kind") == "github_profile"]
    assert len(profile_receipts) == 1
    inventory = profile_receipts[0]["inventory"]
    assert len(inventory) == 8

    # Fork was not selected and remains inventory_only
    fork_item = next(item for item in inventory if item["name"] == "fork-upstream")
    assert fork_item["inspection_status"] == "inventory_only"
    assert "Forked third-party repository" in fork_item["deferral_reason"]

    # Dotfiles was deferred due to scan budget
    dotfiles_item = next(item for item in inventory if item["name"] == "dotfiles")
    assert dotfiles_item["inspection_status"] == "deferred"
    assert dotfiles_item["deferral_reason"] is not None

    # Observed repositories must have selection_reason stored
    observed_receipts = [r for r in receipts if r.get("status") == "observed" and r.get("kind") == "repository"]
    assert len(observed_receipts) == 6
    for r in observed_receipts:
        assert isinstance(r["selection_reason"], str)
        assert len(r["selection_reason"]) > 0
        assert r["repository_association"]["selection_reason"] == r["selection_reason"]
        assert r["repository_association"]["priority_score"] is not None

    # Deferred receipts exist for repositories excluded by budget
    deferred_receipts = [r for r in receipts if r.get("status") == "deferred"]
    assert len(deferred_receipts) >= 1
    assert any(d["name"] == "dotfiles" for d in deferred_receipts)
    assert deferred_receipts[0]["inspection_status"] == "deferred"
    assert deferred_receipts[0]["deferral_reason"] is not None

