"""Candidate Evidence Graph (CEG) implementation.

INVARIANTS:
1. Multi-layered heterogeneous graph preserving exact immutable provenance from
   Candidate -> Identity -> Source -> Artifact -> Evidence -> Capability -> Requirement.
2. Provenance backward tracing allows inspection of exact raw lines and commit SHAs
   for any capability score.
"""

from dataclasses import dataclass, field
from typing import Any

from cci.domain.enums import CapabilityKey, GraphEdgeType, GraphNodeType


@dataclass
class CEGNode:
    """A node in the Candidate Evidence Graph."""

    node_id: str
    node_type: GraphNodeType
    properties: dict[str, Any] = field(default_factory=dict)


@dataclass
class CEGEdge:
    """A directed edge in the Candidate Evidence Graph."""

    edge_id: str
    source_id: str
    target_id: str
    edge_type: GraphEdgeType
    properties: dict[str, Any] = field(default_factory=dict)


class CandidateEvidenceGraph:
    """Heterogeneous Candidate Evidence Graph (CEG)."""

    def __init__(self, evidence_records: list[Any] | None = None) -> None:
        self.nodes: dict[str, CEGNode] = {}
        self.edges: dict[str, CEGEdge] = {}
        self._out_edges: dict[str, list[str]] = {}
        self._in_edges: dict[str, list[str]] = {}

    def add_node(self, node: CEGNode) -> None:
        """Adds a node to the graph."""
        self.nodes[node.node_id] = node
        if node.node_id not in self._out_edges:
            self._out_edges[node.node_id] = []
        if node.node_id not in self._in_edges:
            self._in_edges[node.node_id] = []

    def add_edge(self, edge: CEGEdge) -> None:
        """Adds a directed edge to the graph."""
        if edge.source_id not in self.nodes:
            raise KeyError(f"Source node '{edge.source_id}' does not exist in graph")
        if edge.target_id not in self.nodes:
            raise KeyError(f"Target node '{edge.target_id}' does not exist in graph")

        self.edges[edge.edge_id] = edge
        self._out_edges[edge.source_id].append(edge.edge_id)
        self._in_edges[edge.target_id].append(edge.edge_id)

    def get_node(self, node_id: str) -> CEGNode | None:
        """Retrieves a node by its identifier."""
        return self.nodes.get(node_id)

    def get_edges(
        self,
        source_id: str | None = None,
        target_id: str | None = None,
        edge_type: GraphEdgeType | None = None,
    ) -> list[CEGEdge]:
        """Queries edges by source, target, and/or type."""
        candidates = []
        if source_id is not None:
            edge_ids = self._out_edges.get(source_id, [])
            candidates = [self.edges[eid] for eid in edge_ids]
        elif target_id is not None:
            edge_ids = self._in_edges.get(target_id, [])
            candidates = [self.edges[eid] for eid in edge_ids]
        else:
            candidates = list(self.edges.values())

        results = []
        for e in candidates:
            if source_id is not None and e.source_id != source_id:
                continue
            if target_id is not None and e.target_id != target_id:
                continue
            if edge_type is not None and e.edge_type != edge_type:
                continue
            results.append(e)

        return results

    def trace_provenance(self, capability_key: CapabilityKey) -> list[dict[str, Any]]:
        """Traces backwards from a Capability node to all supporting Evidence, Artifacts, and Sources."""
        cap_node_id = f"cap_{capability_key.value}"
        if cap_node_id not in self.nodes:
            return []

        # Find all incoming SUPPORTS_CAPABILITY edges to this capability node
        evidence_edges = self.get_edges(
            target_id=cap_node_id, edge_type=GraphEdgeType.SUPPORTS_CAPABILITY
        )
        traces = []

        for e_edge in evidence_edges:
            ev_node = self.nodes.get(e_edge.source_id)
            if not ev_node:
                continue

            trace_entry: dict[str, Any] = {
                "capability": capability_key.value,
                "evidence_id": ev_node.node_id,
                "evidence_properties": ev_node.properties,
                "artifacts": [],
                "sources": [],
            }

            # Find incoming DERIVED_FROM edges to evidence
            artifact_edges = self.get_edges(
                source_id=ev_node.node_id, edge_type=GraphEdgeType.DERIVED_FROM
            )
            for art_edge in artifact_edges:
                art_node = self.nodes.get(art_edge.target_id)
                if art_node:
                    trace_entry["artifacts"].append(
                        {
                            "artifact_id": art_node.node_id,
                            "properties": art_node.properties,
                        }
                    )
                    # Trace artifact -> source
                    src_edges = self.get_edges(
                        source_id=art_node.node_id,
                        edge_type=GraphEdgeType.CONTRIBUTES_TO,
                    )
                    for src_edge in src_edges:
                        src_node = self.nodes.get(src_edge.target_id)
                        if src_node:
                            trace_entry["sources"].append(
                                {
                                    "source_id": src_node.node_id,
                                    "properties": src_node.properties,
                                }
                            )

            traces.append(trace_entry)

        return traces

    def to_dict(self) -> dict[str, Any]:
        """Serializes graph to a JSON-compatible dictionary."""
        return {
            "nodes": [
                {
                    "node_id": n.node_id,
                    "node_type": n.node_type.value,
                    "properties": n.properties,
                }
                for n in self.nodes.values()
            ],
            "edges": [
                {
                    "edge_id": e.edge_id,
                    "source_id": e.source_id,
                    "target_id": e.target_id,
                    "edge_type": e.edge_type.value,
                    "properties": e.properties,
                }
                for e in self.edges.values()
            ],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CandidateEvidenceGraph":
        """Reconstructs graph from serialized dictionary."""
        graph = cls()
        for nd in data.get("nodes", []):
            graph.add_node(
                CEGNode(
                    node_id=nd["node_id"],
                    node_type=GraphNodeType(nd["node_type"]),
                    properties=nd.get("properties", {}),
                )
            )
        for ed in data.get("edges", []):
            graph.add_edge(
                CEGEdge(
                    edge_id=ed["edge_id"],
                    source_id=ed["source_id"],
                    target_id=ed["target_id"],
                    edge_type=GraphEdgeType(ed["edge_type"]),
                    properties=ed.get("properties", {}),
                )
            )
        return graph

    def to_api_response(self, candidate_id: Any, analysis_run_id: Any) -> Any:
        """Projects CEG to the API contract CEGGraphResponse schema."""
        from uuid import UUID

        from cci.api.contracts.graph import (
            CEGEdge as ApiEdge,
        )
        from cci.api.contracts.graph import (
            CEGGraphResponse,
        )
        from cci.api.contracts.graph import (
            CEGNode as ApiNode,
        )

        cand_uuid = (
            candidate_id if isinstance(candidate_id, UUID) else UUID(str(candidate_id))
        )
        run_uuid = (
            analysis_run_id
            if isinstance(analysis_run_id, UUID)
            else UUID(str(analysis_run_id))
        )

        nodes = [
            ApiNode(
                id=n.node_id,
                type=n.node_type,
                label=str(n.properties.get("label", n.node_id)),
                properties=n.properties,
            )
            for n in self.nodes.values()
        ]
        edges = [
            ApiEdge(
                id=e.edge_id,
                source=e.source_id,
                target=e.target_id,
                type=e.edge_type,
                weight=float(e.properties.get("weight", 1.0)),
                properties=e.properties,
            )
            for e in self.edges.values()
        ]
        return CEGGraphResponse(
            candidate_id=cand_uuid,
            analysis_run_id=run_uuid,
            nodes=nodes,
            edges=edges,
            metadata={"total_nodes": len(nodes), "total_edges": len(edges)},
        )
