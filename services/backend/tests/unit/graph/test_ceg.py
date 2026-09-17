"""Unit tests for Candidate Evidence Graph (CEG) construction and provenance tracing."""

from uuid import uuid4
import pytest
from cci.domain.enums import CapabilityKey, GraphEdgeType, GraphNodeType
from cci.graph.ceg import CandidateEvidenceGraph, CEGEdge, CEGNode


def test_ceg_construction_and_querying():
    """Verify adding nodes and querying directed edges."""
    graph = CandidateEvidenceGraph()

    cand_node = CEGNode(node_id="cand_1", node_type=GraphNodeType.CANDIDATE, properties={"name": "Alice"})
    src_node = CEGNode(node_id="src_gh", node_type=GraphNodeType.SOURCE, properties={"url": "https://github.com/alice/repo"})
    art_node = CEGNode(node_id="art_1", node_type=GraphNodeType.ARTIFACT, properties={"path": "src/main.py"})

    graph.add_node(cand_node)
    graph.add_node(src_node)
    graph.add_node(art_node)

    assert graph.get_node("cand_1") is not None
    assert graph.get_node("nonexistent") is None

    # Connect nodes
    graph.add_edge(CEGEdge(edge_id="e1", source_id="src_gh", target_id="cand_1", edge_type=GraphEdgeType.AUTHORED_BY))
    graph.add_edge(CEGEdge(edge_id="e2", source_id="art_1", target_id="src_gh", edge_type=GraphEdgeType.CONTRIBUTES_TO))

    # Query edges
    out_edges = graph.get_edges(source_id="art_1")
    assert len(out_edges) == 1
    assert out_edges[0].edge_type == GraphEdgeType.CONTRIBUTES_TO

    in_edges = graph.get_edges(target_id="cand_1")
    assert len(in_edges) == 1
    assert in_edges[0].edge_type == GraphEdgeType.AUTHORED_BY


def test_backward_provenance_tracing():
    """Verify tracing backward from a Capability score to exact Evidence, Artifacts, and Sources."""
    graph = CandidateEvidenceGraph()

    # Build layered graph:
    # Source (repo) <- Artifact (routes.py) <- Evidence (ev_1) -> Capability (Backend)
    src_id = "src_repo"
    art_id = "art_routes"
    ev_id = "ev_backend_route"
    cap_id = f"cap_{CapabilityKey.BACKEND_ENGINEERING.value}"

    graph.add_node(CEGNode(node_id=src_id, node_type=GraphNodeType.SOURCE, properties={"repo_url": "https://github.com/alice/app"}))
    graph.add_node(CEGNode(node_id=art_id, node_type=GraphNodeType.ARTIFACT, properties={"path": "src/routes.py"}))
    graph.add_node(CEGNode(node_id=ev_id, node_type=GraphNodeType.EVIDENCE, properties={"score": 85.0, "line": 42}))
    graph.add_node(CEGNode(node_id=cap_id, node_type=GraphNodeType.CAPABILITY, properties={"key": CapabilityKey.BACKEND_ENGINEERING.value}))

    graph.add_edge(CEGEdge(edge_id="e_art_src", source_id=art_id, target_id=src_id, edge_type=GraphEdgeType.CONTRIBUTES_TO))
    graph.add_edge(CEGEdge(edge_id="e_ev_art", source_id=ev_id, target_id=art_id, edge_type=GraphEdgeType.DERIVED_FROM))
    graph.add_edge(CEGEdge(edge_id="e_ev_cap", source_id=ev_id, target_id=cap_id, edge_type=GraphEdgeType.SUPPORTS_CAPABILITY))

    # Trace provenance for BACKEND_ENGINEERING
    traces = graph.trace_provenance(CapabilityKey.BACKEND_ENGINEERING)
    assert len(traces) == 1
    trace = traces[0]
    assert trace["capability"] == CapabilityKey.BACKEND_ENGINEERING.value
    assert trace["evidence_id"] == ev_id
    assert len(trace["artifacts"]) == 1
    assert trace["artifacts"][0]["artifact_id"] == art_id
    assert len(trace["sources"]) == 1
    assert trace["sources"][0]["source_id"] == src_id


def test_graph_serialization_roundtrip():
    """Verify graph to_dict and from_dict roundtrip."""
    graph = CandidateEvidenceGraph()
    graph.add_node(CEGNode("n1", GraphNodeType.CANDIDATE, {"name": "Bob"}))
    graph.add_node(CEGNode("n2", GraphNodeType.IDENTITY, {"handle": "bobdev"}))
    graph.add_edge(CEGEdge("e1", "n2", "n1", GraphEdgeType.AUTHORED_BY, {"weight": 1.0}))

    data = graph.to_dict()
    assert len(data["nodes"]) == 2
    assert len(data["edges"]) == 1

    restored = CandidateEvidenceGraph.from_dict(data)
    assert restored.get_node("n1") is not None
    assert restored.get_node("n2") is not None
    assert len(restored.get_edges()) == 1


def test_api_projection():
    """Verify to_api_response generates contract-compliant CEGGraphResponse."""
    graph = CandidateEvidenceGraph()
    graph.add_node(CEGNode("cand_99", GraphNodeType.CANDIDATE, {"label": "Alice"}))
    graph.add_node(CEGNode("src_99", GraphNodeType.SOURCE, {"label": "Repo"}))
    graph.add_edge(CEGEdge("e_99", "src_99", "cand_99", GraphEdgeType.AUTHORED_BY))

    cand_id = uuid4()
    run_id = uuid4()
    api_resp = graph.to_api_response(candidate_id=cand_id, analysis_run_id=run_id)

    assert api_resp.candidate_id == cand_id
    assert api_resp.analysis_run_id == run_id
    assert len(api_resp.nodes) == 2
    assert len(api_resp.edges) == 1
    assert api_resp.nodes[0].label in ("Alice", "Repo")
