"""Tests for Fix 17: Rebuild the Candidate Evidence Graph (CEG) Ontology."""

from uuid import uuid4
import pytest

from cci.domain.contracts import (
    CapabilityEstimate,
    Dossier,
    EvidenceConfidenceFactors,
    EvidenceRecord,
    RepositoryAssociation,
    RepositoryContribution,
)
from cci.domain.enums import (
    CanonicalRole,
    CapabilityKey,
    ClaimStatus,
    GraphEdgeType,
    GraphNodeType,
    SourceFamily,
)
from cci.graph.builder import build_dossier_graph
from cci.graph.ceg import CandidateEvidenceGraph, CEGEdge, CEGNode


def test_canonical_node_types_defined():
    """Requirement: GraphNodeType must define all canonical ontology node types."""
    required_canonical_types = {
        "CANDIDATE": "Candidate",
        "IDENTITY": "Identity",
        "ANALYSIS_RUN": "AnalysisRun",
        "CLAIM": "Claim",
        "SKILL": "Skill",
        "PROJECT": "Project",
        "REPOSITORY": "Repository",
        "ARTIFACT": "Artifact",
        "DEPLOYMENT": "Deployment",
        "CREDENTIAL": "Credential",
        "ACADEMIC_RECORD": "AcademicRecord",
        "EXPERIENCE_RECORD": "ExperienceRecord",
        "PUBLICATION": "Publication",
        "CODING_PROFILE": "CodingProfile",
        "SOURCE": "Source",
        "ORGANIZATION": "Organization",
        "CAPABILITY": "Capability",
        "OBSERVATION": "Observation",
    }
    for attr, expected_val in required_canonical_types.items():
        assert hasattr(GraphNodeType, attr), f"GraphNodeType missing canonical member: {attr}"
        member = getattr(GraphNodeType, attr)
        assert member.value == expected_val

        # Case-insensitive resolution
        assert GraphNodeType(expected_val) == member
        assert GraphNodeType(expected_val.lower()) == member


def test_canonical_edge_types_defined():
    """Requirement: GraphEdgeType must define all canonical ontology edge types."""
    required_canonical_edges = [
        "DECLARES",
        "DISCOVERED_FROM",
        "CONTAINS",
        "OBSERVED_IN",
        "SUPPORTS",
        "CONTRADICTS",
        "CONTRIBUTES_TO",
        "ATTRIBUTED_TO",
        "DEPLOYED_AS",
        "ISSUED_BY",
        "VERIFIES",
        "REFERENCES",
        "USES_TECHNOLOGY",
        "ASSOCIATED_WITH",
        "DERIVED_FROM",
    ]
    for edge_name in required_canonical_edges:
        assert hasattr(GraphEdgeType, edge_name), f"GraphEdgeType missing canonical member: {edge_name}"
        member = getattr(GraphEdgeType, edge_name)
        assert member.value == edge_name

        # Case-insensitive resolution
        assert GraphEdgeType(edge_name) == member
        assert GraphEdgeType(edge_name.lower()) == member


def test_strict_authorship_invariant_enforcement():
    """Invariant: Do not create AUTHORED_BY unless the evidence really supports authorship."""
    graph = CandidateEvidenceGraph()
    cand_id = "cand_1"
    art_id = "art_1"
    graph.add_node(CEGNode(cand_id, GraphNodeType.CANDIDATE))
    graph.add_node(CEGNode(art_id, GraphNodeType.ARTIFACT))

    # Reject AUTHORED_BY without verified authorship evidence when strict
    unverified_edge = CEGEdge(
        edge_id="e_unverified",
        source_id=cand_id,
        target_id=art_id,
        edge_type=GraphEdgeType.AUTHORED_BY,
        properties={"git_account": "alice"},
    )
    with pytest.raises(
        ValueError,
        match=r"Cannot create AUTHORED_BY edge.*without verified line-level authorship",
    ):
        graph.add_edge(unverified_edge, strict_authorship=True)

    # Permit AUTHORED_BY when line-level / cryptographic authorship is verified
    verified_edge = CEGEdge(
        edge_id="e_verified",
        source_id=cand_id,
        target_id=art_id,
        edge_type=GraphEdgeType.AUTHORED_BY,
        properties={"authorship_verified": True, "authorship_basis": "verified_gpg_commit"},
    )
    graph.add_edge(verified_edge, strict_authorship=True)
    assert graph.get_node(cand_id) is not None
    assert len(graph.get_edges(source_id=cand_id)) == 1


def test_authorship_audit_detects_violations():
    """Requirement: validate_authorship_invariants audits graph for unverified AUTHORED_BY edges."""
    graph = CandidateEvidenceGraph()
    cand_id = "cand_1"
    art_id = "art_1"
    art2_id = "art_2"
    graph.add_node(CEGNode(cand_id, GraphNodeType.CANDIDATE))
    graph.add_node(CEGNode(art_id, GraphNodeType.ARTIFACT))
    graph.add_node(CEGNode(art2_id, GraphNodeType.ARTIFACT))

    # Add unverified AUTHORED_BY (legacy/lenient mode)
    graph.add_edge(CEGEdge("e_bad", cand_id, art_id, GraphEdgeType.AUTHORED_BY, {}))
    # Add verified AUTHORED_BY
    graph.add_edge(
        CEGEdge("e_good", cand_id, art2_id, GraphEdgeType.AUTHORED_BY, {"authorship_verified": True})
    )

    violations = graph.validate_authorship_invariants()
    assert len(violations) == 1
    assert "e_bad" in violations[0]
    assert "e_good" not in violations[0]


def test_ontology_node_and_edge_traversal_queries():
    """Verify ontology queries: get_nodes_by_type, get_neighbors, find_paths."""
    graph = CandidateEvidenceGraph()
    cand = CEGNode("cand_alice", GraphNodeType.CANDIDATE, {"name": "Alice"})
    repo = CEGNode("repo_app", GraphNodeType.REPOSITORY, {"name": "alice/app"})
    art = CEGNode("art_main", GraphNodeType.ARTIFACT, {"path": "main.py"})
    obs = CEGNode("obs_route", GraphNodeType.OBSERVATION, {"kind": "fastapi_route"})
    cap = CEGNode("cap_backend", GraphNodeType.CAPABILITY, {"name": "Backend"})

    for n in (cand, repo, art, obs, cap):
        graph.add_node(n)

    # Candidate ASSOCIATED_WITH Repo
    graph.add_edge(CEGEdge("e1", "cand_alice", "repo_app", GraphEdgeType.ASSOCIATED_WITH))
    # Repo CONTAINS Artifact
    graph.add_edge(CEGEdge("e2", "repo_app", "art_main", GraphEdgeType.CONTAINS))
    # Observation OBSERVED_IN Artifact
    graph.add_edge(CEGEdge("e3", "obs_route", "art_main", GraphEdgeType.OBSERVED_IN))
    # Observation SUPPORTS Capability
    graph.add_edge(CEGEdge("e4", "obs_route", "cap_backend", GraphEdgeType.SUPPORTS))

    # Query nodes by type
    assert len(graph.get_nodes_by_type(GraphNodeType.CANDIDATE)) == 1
    assert len(graph.get_nodes_by_type(GraphNodeType.REPOSITORY)) == 1
    assert len(graph.get_nodes_by_type("Artifact")) == 1
    assert len(graph.get_nodes_by_type(GraphNodeType.OBSERVATION)) == 1

    # Neighbors
    repo_neighbors = graph.get_neighbors("repo_app", direction="both")
    repo_neighbor_ids = {n.node_id for n in repo_neighbors}
    assert repo_neighbor_ids == {"cand_alice", "art_main"}

    # Path finding
    paths = graph.find_paths("cand_alice", "art_main")
    assert len(paths) == 1
    assert paths[0] == ["cand_alice", "repo_app", "art_main"]


def test_claim_corroboration_lookup():
    """Verify get_claim_corroboration retrieves supporting and contradicting observations."""
    graph = CandidateEvidenceGraph()
    cand = CEGNode("cand_bob", GraphNodeType.CANDIDATE)
    claim = CEGNode("claim_1", GraphNodeType.CLAIM, {"text": "Built Kafka cluster"})
    obs_sup = CEGNode("obs_kafka_code", GraphNodeType.OBSERVATION, {"file": "kafka.py"})
    obs_contra = CEGNode("obs_negative_scan", GraphNodeType.OBSERVATION, {"file": "tests.py"})

    for n in (cand, claim, obs_sup, obs_contra):
        graph.add_node(n)

    graph.add_edge(CEGEdge("e_dec", "cand_bob", "claim_1", GraphEdgeType.DECLARES))
    graph.add_edge(CEGEdge("e_sup", "obs_kafka_code", "claim_1", GraphEdgeType.SUPPORTS))
    graph.add_edge(CEGEdge("e_contra", "obs_negative_scan", "claim_1", GraphEdgeType.CONTRADICTS))

    corrob = graph.get_claim_corroboration("claim_1")
    assert corrob["found"] is True
    assert len(corrob["supporting"]) == 1
    assert corrob["supporting"][0]["node_id"] == "obs_kafka_code"
    assert len(corrob["contradicting"]) == 1
    assert corrob["contradicting"][0]["node_id"] == "obs_negative_scan"


def test_build_dossier_graph_generates_rich_ontology():
    """Verify build_dossier_graph populates canonical ontology nodes and edges."""
    cid = uuid4()
    run_id = uuid4()
    claim_id = uuid4()
    ev_id = uuid4()

    evidence = EvidenceRecord(
        evidence_id=ev_id,
        fingerprint="f" * 64,
        source_family=SourceFamily.GITHUB,
        source_locator="https://github.com/alice/engine",
        immutable_revision="a" * 40,
        target_capability=CapabilityKey.BACKEND_ENGINEERING,
        support_score=85.0,
        is_positive_support=True,
        confidence_factors=EvidenceConfidenceFactors(
            artifact_integrity=1.0,
            ownership_score=0.9,
            recency_factor=1.0,
            verification_level=1.0,
            depth_specificity=1.0,
            source_reliability=1.0,
        ),
        confidence=0.9,
        provenance={"artifact_path": "engine/server.go"},
    )

    dossier = Dossier(
        candidate_id=cid,
        analysis_run_id=run_id,
        role=CanonicalRole.BACKEND,
        coverage=0.8,
        is_insufficient_evidence=False,
        capability_estimates={
            CapabilityKey.BACKEND_ENGINEERING: CapabilityEstimate(
                capability_key=CapabilityKey.BACKEND_ENGINEERING,
                estimate=85.0,
                is_observed=True,
                effective_evidence_count=1.0,
                raw_evidence_count=1,
                cluster_count=1,
                standard_error=0.0,
                dispersion=0.0,
                coverage_k=0.8,
            )
        },
        capability_conflicts={},
        role_requirements=[],
        ownership_assessments=[],
        repository_associations=[
            RepositoryAssociation(
                repository_url="https://github.com/alice/engine",
                basis="manifest_url",
                identity_verified=False,
            )
        ],
        repository_contributions=[
            RepositoryContribution(
                repository_url="https://github.com/alice/engine",
                method="author_email",
                candidate_commit_ratio=0.75,
                candidate_commit_count=15,
                sampled_commit_count=20,
            )
        ],
        claims_corroboration=[
            {
                "claim_id": str(claim_id),
                "original_text": "Expert in Go concurrency patterns",
                "normalized_subject": "Go",
                "claim_type": "skill",
                "status": ClaimStatus.SUPPORTED.value,
                "target_capability": "backend_engineering",
                "grounding_evidence_ids": [str(ev_id)],
            }
        ],
        interview_probes=[],
        interview_questions=[],
        evidence_records=[evidence],
    )

    graph = build_dossier_graph(dossier)

    # 1. Candidate and Identity
    assert graph.get_node(str(cid)) is not None
    assert graph.get_node(str(cid)).node_type == GraphNodeType.CANDIDATE

    # 2. Repository and Source nodes
    repo_nodes = graph.get_nodes_by_type(GraphNodeType.REPOSITORY)
    assert len(repo_nodes) >= 1
    assert any("https://github.com/alice/engine" in r.properties.get("repository_url", "") for r in repo_nodes)

    # 3. Candidate -> Repository is ASSOCIATED_WITH and CONTRIBUTES_TO, never unverified AUTHORED_BY
    edges = list(graph.edges.values())
    assert any(e.edge_type == GraphEdgeType.ASSOCIATED_WITH for e in edges)
    assert any(e.edge_type == GraphEdgeType.CONTRIBUTES_TO for e in edges)
    # Check authorship invariant: no unverified AUTHORED_BY edge
    assert len(graph.validate_authorship_invariants()) == 0

    # 4. Claim and Skill nodes
    claim_node = graph.get_node(f"claim_{claim_id}")
    assert claim_node is not None
    assert claim_node.node_type == GraphNodeType.CLAIM

    skill_nodes = graph.get_nodes_by_type(GraphNodeType.SKILL)
    assert len(skill_nodes) >= 1
    assert any(s.properties.get("skill_name") == "Go" for s in skill_nodes)

    # 5. Candidate DECLARES Claim
    declares_edges = [
        e for e in edges if e.source_id == str(cid) and e.target_id == f"claim_{claim_id}"
    ]
    assert len(declares_edges) == 1
    assert declares_edges[0].edge_type == GraphEdgeType.DECLARES

    # 6. Evidence corroborates Claim
    corrob = graph.get_claim_corroboration(str(claim_id))
    assert corrob["found"] is True
    assert len(corrob["supporting"]) == 1
    assert corrob["supporting"][0]["node_id"] == str(ev_id)
