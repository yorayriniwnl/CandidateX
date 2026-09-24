"""Tests for Fix 18: Canonical Artifact Identity and Deduplication."""

from uuid import uuid4
import pytest

from cci.artifacts.identity import (
    compute_canonical_artifact_id,
    compute_canonical_artifact_uuid,
    normalize_artifact_path,
)
from cci.domain.contracts import (
    CapabilityEstimate,
    Dossier,
    EvidenceConfidenceFactors,
    EvidenceRecord,
)
from cci.domain.enums import (
    CanonicalRole,
    CapabilityKey,
    GraphEdgeType,
    GraphNodeType,
    SourceFamily,
)
from cci.graph.builder import build_dossier_graph


def test_artifact_path_normalization():
    """Verify path normalization handles slashes, leading/trailing spaces, and OS differences."""
    assert normalize_artifact_path("src\\api\\routes.py") == "src/api/routes.py"
    assert normalize_artifact_path("/src/api/routes.py") == "src/api/routes.py"
    assert normalize_artifact_path("src/api/routes.py/") == "src/api/routes.py"
    assert normalize_artifact_path("src//api///routes.py") == "src/api/routes.py"
    assert normalize_artifact_path("  src/api/routes.py  ") == "src/api/routes.py"


def test_canonical_artifact_id_determinism_and_snapshot_stability():
    """Artifact identity must remain stable within an immutable snapshot."""
    repo = "https://github.com/candidate/app"
    rev = "4eed784ebfd95b64249abcde8d2378220157db33"
    path_posix = "services/backend/src/main.py"
    path_win = "services\\backend\\src\\main.py"
    content_hash = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"

    id1 = compute_canonical_artifact_id(repo, rev, path_posix, content_hash)
    id2 = compute_canonical_artifact_id(repo, rev, path_win, content_hash)
    id3 = compute_canonical_artifact_id(repo.upper(), rev, path_posix, content_hash)

    assert id1 == id2, "Windows and POSIX paths for the same file must yield identical artifact ID"
    assert id1 == id3, "Repository URL casing must be normalized"
    assert id1.startswith("artifact_")

    # UUID derivation is also stable
    uuid1 = compute_canonical_artifact_uuid(repo, rev, path_posix, content_hash)
    uuid2 = compute_canonical_artifact_uuid(repo, rev, path_win, content_hash)
    assert uuid1 == uuid2


def test_different_files_or_revisions_yield_different_artifact_ids():
    """Different files or different commit revisions produce distinct artifact IDs."""
    repo = "https://github.com/candidate/app"
    rev1 = "1111111111111111111111111111111111111111"
    rev2 = "2222222222222222222222222222222222222222"

    id_file_a = compute_canonical_artifact_id(repo, rev1, "src/a.py")
    id_file_b = compute_canonical_artifact_id(repo, rev1, "src/b.py")
    id_rev2_a = compute_canonical_artifact_id(repo, rev2, "src/a.py")

    assert id_file_a != id_file_b, "Different paths must yield different artifact IDs"
    assert id_file_a != id_rev2_a, "Different revisions must yield different artifact IDs"


def test_one_file_producing_five_observations_yields_one_artifact_node():
    """Specification requirement: One file produces five technical observations.

    Expected:
    1 artifact node
    5 observation/evidence nodes
    NOT five artifacts.
    """
    cid = uuid4()
    run_id = uuid4()
    repo_url = "https://github.com/candidatex/api-service"
    revision = "c1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0"
    file_path = "services/backend/src/routes/api.py"
    content_hash = "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08"

    factors = EvidenceConfidenceFactors(
        artifact_integrity=1.0,
        ownership_score=1.0,
        recency_factor=1.0,
        verification_level=1.0,
        depth_specificity=1.0,
        source_reliability=1.0,
    )

    capabilities = [
        CapabilityKey.BACKEND_ENGINEERING,
        CapabilityKey.DATABASE_ENGINEERING,
        CapabilityKey.SOFTWARE_ARCHITECTURE,
        CapabilityKey.SECURITY,
        CapabilityKey.TESTING_QUALITY,
    ]

    records = []
    for i, cap in enumerate(capabilities):
        rec = EvidenceRecord(
            evidence_id=uuid4(),
            fingerprint=f"obs_fingerprint_{i}_{'a' * 46}",
            source_family=SourceFamily.GITHUB,
            source_locator=repo_url,
            immutable_revision=revision,
            target_capability=cap,
            support_score=80.0 + i,
            confidence_factors=factors,
            confidence=0.85,
            observation_type=f"pattern_{i}",
            provenance={
                "artifact_path": file_path,
                "content_sha256": content_hash,
                "line_start": 10 * i + 1,
                "line_end": 10 * i + 10,
            },
        )
        records.append(rec)

    assert len(records) == 5

    dossier = Dossier(
        candidate_id=cid,
        analysis_run_id=run_id,
        role=CanonicalRole.BACKEND,
        coverage=0.8,
        is_insufficient_evidence=False,
        capability_estimates={
            cap: CapabilityEstimate(
                capability_key=cap,
                estimate=80.0,
                is_observed=True,
                effective_evidence_count=1.0,
                raw_evidence_count=1,
                cluster_count=1,
                standard_error=0.0,
                dispersion=0.0,
                coverage_k=0.8,
            )
            for cap in capabilities
        },
        capability_conflicts={},
        role_requirements=[],
        ownership_assessments=[],
        claims_corroboration=[],
        interview_probes=[],
        interview_questions=[],
        evidence_records=records,
    )

    graph = build_dossier_graph(dossier)

    # Count artifact nodes vs evidence/observation nodes
    artifact_nodes = graph.get_nodes_by_type(GraphNodeType.ARTIFACT)
    evidence_nodes = [
        n for n in graph.nodes.values()
        if n.node_type in (GraphNodeType.EVIDENCE, GraphNodeType.OBSERVATION)
    ]

    # Acceptance verification: EXACTLY 1 artifact node, EXACTLY 5 observation nodes
    assert len(artifact_nodes) == 1, (
        f"Expected exactly 1 artifact node for the single physical file, but got {len(artifact_nodes)}: "
        f"{[a.node_id for a in artifact_nodes]}"
    )
    assert len(evidence_nodes) == 5, (
        f"Expected exactly 5 observation/evidence nodes, but got {len(evidence_nodes)}"
    )

    # Verify all 5 evidence nodes connect to the ONE artifact node via DERIVED_FROM
    art_node = artifact_nodes[0]
    expected_art_id = compute_canonical_artifact_id(repo_url, revision, file_path, content_hash)
    assert art_node.node_id == expected_art_id

    derived_edges = [
        e for e in graph.edges.values()
        if e.edge_type == GraphEdgeType.DERIVED_FROM and e.target_id == art_node.node_id
    ]
    assert len(derived_edges) == 5, (
        f"Expected 5 DERIVED_FROM edges pointing from the 5 observations to the 1 artifact, got {len(derived_edges)}"
    )
    obs_sources = {e.source_id for e in derived_edges}
    assert obs_sources == {str(r.evidence_id) for r in records}


def test_multiple_files_produce_distinct_artifact_nodes():
    """Multiple distinct files in the same repo produce distinct artifact nodes, each with their own observations."""
    cid = uuid4()
    run_id = uuid4()
    repo_url = "https://github.com/candidatex/api-service"
    revision = "c1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0"

    factors = EvidenceConfidenceFactors(
        artifact_integrity=1.0,
        ownership_score=1.0,
        recency_factor=1.0,
        verification_level=1.0,
        depth_specificity=1.0,
        source_reliability=1.0,
    )

    # 3 observations from file1.py, 2 observations from file2.py
    records = []
    for i in range(3):
        records.append(
            EvidenceRecord(
                evidence_id=uuid4(),
                fingerprint=f"fp_file1_{i}_{'b' * 50}",
                source_family=SourceFamily.GITHUB,
                source_locator=repo_url,
                immutable_revision=revision,
                target_capability=CapabilityKey.BACKEND_ENGINEERING,
                support_score=75.0,
                confidence_factors=factors,
                confidence=0.8,
                provenance={"artifact_path": "src/file1.py"},
            )
        )
    for j in range(2):
        records.append(
            EvidenceRecord(
                evidence_id=uuid4(),
                fingerprint=f"fp_file2_{j}_{'c' * 50}",
                source_family=SourceFamily.GITHUB,
                source_locator=repo_url,
                immutable_revision=revision,
                target_capability=CapabilityKey.SOFTWARE_ARCHITECTURE,
                support_score=85.0,
                confidence_factors=factors,
                confidence=0.9,
                provenance={"artifact_path": "src/file2.py"},
            )
        )

    dossier = Dossier(
        candidate_id=cid,
        analysis_run_id=run_id,
        role=CanonicalRole.BACKEND,
        coverage=0.8,
        is_insufficient_evidence=False,
        capability_estimates={},
        capability_conflicts={},
        role_requirements=[],
        ownership_assessments=[],
        claims_corroboration=[],
        interview_probes=[],
        interview_questions=[],
        evidence_records=records,
    )

    graph = build_dossier_graph(dossier)
    artifact_nodes = graph.get_nodes_by_type(GraphNodeType.ARTIFACT)
    assert len(artifact_nodes) == 2

    # Verify file1 has 3 incoming DERIVED_FROM edges, file2 has 2
    art1_id = compute_canonical_artifact_id(repo_url, revision, "src/file1.py")
    art2_id = compute_canonical_artifact_id(repo_url, revision, "src/file2.py")

    edges_to_art1 = [e for e in graph.edges.values() if e.target_id == art1_id]
    edges_to_art2 = [e for e in graph.edges.values() if e.target_id == art2_id]
    assert len(edges_to_art1) == 3
    assert len(edges_to_art2) == 2
