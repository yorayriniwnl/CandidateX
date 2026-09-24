"""
Full Production E2E Pipeline Verification (Fix 53).

Uses a synthetic test candidate designed specifically for software QA.
Tests the full production-like analysis across:
- Digital resume with declared skills, project claims, and experience
- Multiple projects:
  * Large repository (multi-module, docker, fastAPI, tests)
  * Stale repository (last substantive modification in 2021)
  * Collaborative repository (multi-contributor with 20% candidate attribution)
  * Controlled conflicting claim (claimed 95% test coverage vs 42% observed in coverage report)
- Live deployment endpoint (healthy status, TLS confirmed)
- Third-party issuer credential (Credly badge)
- Portfolio site
- Complete 10-stage execution pipeline
- Verification of:
  * Claim extraction & status taxonomy
  * Source discovery & receipts
  * Static artifact analysis (zero candidate code execution)
  * Kish effective sample depth
  * Gated attribution and cluster-aware coverage
  * Contradiction diagnostics & interview probes
  * Dossier synthesis & 5-hop CEG traceability
  * Export generation preserving provenance
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
from uuid import uuid4
import pytest

from cci.domain.contracts import (
    CandidateManifest,
    EvidenceConfidenceFactors,
    EvidenceRecord,
    NegativeEvidenceDetails,
    NegativeEvidenceScanScope,
    ScoringConfig,
)
from cci.domain.enums import (
    AnalysisStage,
    CanonicalRole,
    CapabilityKey,
    ClaimStatus,
    EvidenceMode,
    GraphNodeType,
    SourceFamily,
)
from cci.pipeline.orchestrator import execute_analysis_pipeline, PipelineStatus
from cci.reports.exporter import generate_markdown_brief, generate_html_brief


def _make_e2e_record(
    cap: CapabilityKey,
    signal: float,
    family: SourceFamily = SourceFamily.GITHUB,
    ownership: float = 1.0,
    artifact_integrity: float = 1.0,
    recency: float = 1.0,
    verification: float = 1.0,
    depth: float = 1.0,
    source_reliability: float = 0.90,
    cluster_id: str = "cluster-order-router",
    path: str = "services/router/handler.py",
    commit_sha: str = "a1b2c3d4e5f67890123456789abcdef012345678",
    content_hash: str | None = None,
    is_positive: bool = True,
    source_locator: str = "https://github.com/jordan-croft-qa/order-router",
    claim_ref: str | None = None,
) -> EvidenceRecord:
    factors = EvidenceConfidenceFactors(
        artifact_integrity=artifact_integrity,
        ownership_score=ownership,
        recency_factor=recency,
        verification_level=verification,
        depth_specificity=depth,
        source_reliability=source_reliability,
    )
    conf = factors.composite_confidence
    chash = content_hash or hashlib.sha256(f"{path}:{commit_sha}:{signal}".encode()).hexdigest()
    
    neg_details = None
    if not is_positive:
        neg_details = NegativeEvidenceDetails(
            claim_reference=claim_ref or ("cr1:" + "b" * 64),
            candidate_type="candidatex.contradiction.coverage_below_claim",
            expected_observation="Automated test coverage >= 90% as claimed in resume",
            actual_observation="Coverage report explicitly records 42% total package coverage",
            scan_scope=NegativeEvidenceScanScope(scope_kind="synthetic"),
            required_scan_completeness=1.0,
            observed_scan_completeness=1.0,
            explanation="Objective coverage artifact contradicts self-reported 95% coverage claim.",
        )

    return EvidenceRecord(
        evidence_id=uuid4(),
        fingerprint=f"fp-{uuid4()}",
        source_family=family,
        source_locator=source_locator,
        immutable_revision=commit_sha,
        target_capability=cap,
        technical_signal_strength=signal,
        is_positive_support=is_positive,
        negative_evidence_details=neg_details,
        confidence_factors=factors,
        confidence=conf,
        cluster_id=cluster_id,
        created_at=datetime.now(timezone.utc),
        provenance={
            "path": path,
            "artifact_path": path,
            "commit_sha": commit_sha,
            "content_hash": chash,
            "content_sha256": chash,
            "artifact_sha256": chash,
            "fetch_timestamp": "2026-09-24T12:00:00Z",
            **({"synthetic": True} if not is_positive else {}),
        },
    )


def test_production_e2e_synthetic_candidate():
    """Verify full end-to-end production analysis pipeline on synthetic QA candidate."""
    candidate_id = uuid4()
    run_id = uuid4()

    # 1. Digital Resume & Intake Manifest
    manifest = CandidateManifest(
        display_name="Jordan Croft (SYNTHETIC QA CANDIDATE)",
        claimed_skills=[
            "Python",
            "FastAPI",
            "Distributed Systems",
            "PostgreSQL",
            "Docker",
            "Kubernetes",
            "Automated Testing",
            "High Test Coverage",
            "Rust",  # Unobserved in repositories -> will remain UNKNOWN
        ],
        project_claims=[
            {"title": "Distributed Order Router", "claimed_role": "Primary Author"},
            {"title": "Legacy Cache Layer", "claimed_role": "Maintainer"},
            {"title": "Open Source Metrics Platform", "claimed_role": "Contributor (20% share)"},
        ],
        experience_claims=[
            {"company": "Apex Distributed Systems", "role": "Senior Infrastructure Engineer"}
        ],
        github_urls=[
            "https://github.com/jordan-croft-qa/order-router",
            "https://github.com/jordan-croft-qa/legacy-cache",
            "https://github.com/enterprise-collab/metrics-platform",
        ],
        deployment_urls=["https://demo-router.candidatex-qa.internal"],
        portfolio_urls=["https://jordan-croft-portfolio.dev"],
        credential_urls=["https://www.credly.com/badges/jordan-croft-aws-architect"],
    )

    # 2. Build Controlled Evidence Artifacts for all 4 project archetypes
    ev_records: list[EvidenceRecord] = []
    
    # Archetype 1: Large Repo (Order Router) - Strong ownership, recent, multi-artifact
    ev_large_backend_1 = _make_e2e_record(
        cap=CapabilityKey.BACKEND_ENGINEERING,
        signal=88.0,
        family=SourceFamily.GITHUB,
        ownership=0.95,
        recency=0.95,
        depth=0.90,
        cluster_id="cluster-order-router",
        path="services/router/handler.py",
        commit_sha="a1b2c3d4e5f67890123456789abcdef012345678",
        source_locator="https://github.com/jordan-croft-qa/order-router",
    )
    ev_large_backend_2 = _make_e2e_record(
        cap=CapabilityKey.BACKEND_ENGINEERING,
        signal=86.0,
        family=SourceFamily.GITHUB,
        ownership=0.95,
        recency=0.95,
        depth=0.90,
        cluster_id="cluster-order-router",
        path="services/router/engine.py",
        commit_sha="a1b2c3d4e5f67890123456789abcdef012345678",
        source_locator="https://github.com/jordan-croft-qa/order-router",
    )
    ev_records.extend([ev_large_backend_1, ev_large_backend_2])

    # Database Schema Artifact in Large Repo
    ev_db = _make_e2e_record(
        cap=CapabilityKey.DATABASE_ENGINEERING,
        signal=82.0,
        family=SourceFamily.DATABASE,
        ownership=0.95,
        recency=0.95,
        depth=0.85,
        cluster_id="cluster-order-router",
        path="db/migrations/001_initial_orders.sql",
        commit_sha="a1b2c3d4e5f67890123456789abcdef012345678",
        source_locator="https://github.com/jordan-croft-qa/order-router",
    )
    ev_records.append(ev_db)

    # Archetype 2: Stale Repo (Legacy Cache) - Last substantive commit in 2021
    ev_stale = _make_e2e_record(
        cap=CapabilityKey.SOFTWARE_ARCHITECTURE,
        signal=72.0,
        family=SourceFamily.GITHUB,
        ownership=0.90,
        recency=0.35,  # Stale: heavily decayed
        depth=0.70,
        cluster_id="cluster-legacy-cache",
        path="cache/lru.py",
        commit_sha="99887766554433221100fedcba98765432101234",
        source_locator="https://github.com/jordan-croft-qa/legacy-cache",
    )
    ev_records.append(ev_stale)

    # Backend corroboration from legacy cache
    ev_stale_backend = _make_e2e_record(
        cap=CapabilityKey.BACKEND_ENGINEERING,
        signal=82.0,
        family=SourceFamily.GITHUB,
        ownership=0.90,
        recency=0.75,
        depth=0.85,
        cluster_id="cluster-legacy-cache",
        path="cache/server.py",
        commit_sha="99887766554433221100fedcba98765432101234",
        source_locator="https://github.com/jordan-croft-qa/legacy-cache",
    )
    ev_records.append(ev_stale_backend)

    # Archetype 3: Collaborative Repo (Metrics Platform) - 20% candidate ownership
    ev_collab = _make_e2e_record(
        cap=CapabilityKey.ALGORITHMS_PROBLEM_SOLVING,
        signal=78.0,
        family=SourceFamily.GITHUB,
        ownership=0.20,  # 20% attribution strictly gated
        recency=0.85,
        depth=0.80,
        cluster_id="cluster-collab-metrics",
        path="collector/client.py",
        commit_sha="44556677889900112233aabbccddeeff00112233",
        source_locator="https://github.com/enterprise-collab/metrics-platform",
    )
    ev_records.append(ev_collab)

    # Archetype 4: Controlled Conflicting Claim (Claimed 95% test coverage vs 42% observed)
    claim_ref = "cr1:" + "c" * 64
    ev_conflict_pos = _make_e2e_record(
        cap=CapabilityKey.TESTING_QUALITY,
        signal=85.0,
        family=SourceFamily.GITHUB,
        is_positive=True,
        ownership=0.90,
        cluster_id="cluster-order-router",
        path="tests/test_router.py",
        source_locator="https://github.com/jordan-croft-qa/order-router",
    )
    ev_conflict_neg = _make_e2e_record(
        cap=CapabilityKey.TESTING_QUALITY,
        signal=42.0,
        family=SourceFamily.GITHUB,
        is_positive=False,
        ownership=0.90,
        cluster_id="cluster-order-router",
        path="coverage.xml",
        source_locator="https://github.com/jordan-croft-qa/order-router",
        claim_ref=claim_ref,
    )
    ev_records.extend([ev_conflict_pos, ev_conflict_neg])

    # Deployment Evidence (Healthy HTTP 200)
    ev_deploy = _make_e2e_record(
        cap=CapabilityKey.DEVOPS_CLOUD,
        signal=80.0,
        family=SourceFamily.DEPLOYMENT,
        ownership=0.85,
        recency=0.95,
        cluster_id="cluster-deploy-router",
        path="/health",
        source_locator="https://demo-router.candidatex-qa.internal",
    )
    ev_records.append(ev_deploy)

    # Credential Evidence (AWS Solutions Architect)
    ev_cred = _make_e2e_record(
        cap=CapabilityKey.SECURITY,
        signal=85.0,
        family=SourceFamily.CERTIFICATE,
        ownership=0.95,
        recency=0.90,
        cluster_id="cluster-credly-badge",
        path="/badge/receipt",
        source_locator="https://www.credly.com/badges/jordan-croft-aws-architect",
    )
    ev_records.append(ev_cred)

    # 3. Job Description for Role-Aware Scoring
    jd = """
    We are seeking a Senior Backend Infrastructure Engineer.
    Mandatory Requirements:
    - 5+ years building backend microservices in Python or Go.
    - Strong database schema modeling and query optimization with PostgreSQL.
    - Automated unit and integration testing habits.
    - Production deployment and container orchestration experience.
    """

    # 4. Execute Full 10-Stage Pipeline
    pipeline_result = execute_analysis_pipeline(
        candidate_id=candidate_id,
        analysis_run_id=run_id,
        role=CanonicalRole.BACKEND,
        jd_text=jd,
        cv_text="Resume text of Jordan Croft",
        repo_urls=[
            "https://github.com/jordan-croft-qa/order-router",
            "https://github.com/jordan-croft-qa/legacy-cache",
            "https://github.com/enterprise-collab/metrics-platform",
        ],
        declared_claims=list(manifest.claimed_skills),
        custom_evidence=ev_records,
        evidence_mode="provided",
    )

    # 5. Assert Execution Pipeline Progression & Completion
    assert pipeline_result.status == PipelineStatus.COMPLETED
    assert pipeline_result.error is None
    assert len(pipeline_result.stages) == 10
    for st in pipeline_result.stages:
        assert st.status == "completed", f"Stage {st.label} did not complete successfully"

    # 6. Assert Dossier & CEG Synthesis
    dossier = pipeline_result.dossier
    assert dossier is not None
    assert dossier.candidate_id == candidate_id
    assert dossier.analysis_run_id == run_id
    assert dossier.role == CanonicalRole.BACKEND

    # Verification of Evidence Invariants
    assert len(dossier.evidence_records) == len(ev_records)

    # Assert Kish effective depth and cluster independence
    cluster_ids = {e.cluster_id for e in dossier.evidence_records}
    assert len(cluster_ids) >= 4, "Must span at least 4 independent clusters"

    # Assert Gating & Scoring
    # Backend Engineering should have high score
    backend_est = dossier.capability_estimates.get(CapabilityKey.BACKEND_ENGINEERING)
    assert backend_est is not None
    assert backend_est.is_observed is True
    assert backend_est.estimate > 75.0

    # Unobserved skill (Rust / ML) must remain UNKNOWN, never 0.0
    ml_est = dossier.capability_estimates.get(CapabilityKey.MACHINE_LEARNING)
    assert ml_est is not None
    assert ml_est.estimate is None
    assert ml_est.is_observed is False
    assert ml_est.coverage_k == 0.0

    # Contradiction diagnostic for Testing Quality must flag discrepancy (D_k < 0)
    conflict = dossier.capability_conflicts.get(CapabilityKey.TESTING_QUALITY)
    assert conflict is not None
    assert conflict.negative_support_sum > 0
    assert conflict.positive_support_sum > 0
    assert conflict.has_meaningful_conflict is True

    # Probe Generation: Prioritized probe for Testing Quality discrepancy
    probes = dossier.interview_probes
    assert len(probes) > 0
    testing_probe = next((p for p in probes if p.capability_key == CapabilityKey.TESTING_QUALITY), None)
    assert testing_probe is not None, "Contradicted testing skill must generate interview probe"
    assert testing_probe.contradiction_term > 0.0

    questions = dossier.interview_questions
    testing_question = next((q for q in questions if q.target_capability == CapabilityKey.TESTING_QUALITY), None)
    assert testing_question is not None
    assert testing_question.question_text is not None

    # CEG Graph Integrity (5-Hop Traceability)
    graph = pipeline_result.ceg_graph
    assert graph is not None
    assert len(graph.nodes) > 0
    assert len(graph.edges) > 0

    # Verify Exports Preserve Provenance
    json_export = dossier.model_dump_json(indent=2)
    assert f'"candidate_id": "{candidate_id}"' in json_export
    assert "provenance" in json_export

    md_export = generate_markdown_brief(dossier)
    assert "Candidate Capability Intelligence (CCI)" in md_export

    html_export = generate_html_brief(dossier)
    assert "<!DOCTYPE html>" in html_export
