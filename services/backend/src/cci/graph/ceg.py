"""Candidate Evidence Graph (CEG) implementation.

INVARIANTS:
1. Multi-layered heterogeneous graph preserving exact immutable provenance from
   candidate/repository association and contribution through artifact, evidence,
   capability, and requirement. Repository-level contribution never implies
   artifact authorship.
2. Provenance backward tracing allows inspection of exact raw lines and commit SHAs
   for any capability score.
3. The CEG represents an actual semantic ontology, defining canonical nodes:
   Candidate, Identity, AnalysisRun, Claim, Skill, Project, Repository, Artifact,
   Deployment, Credential, AcademicRecord, ExperienceRecord, Publication,
   CodingProfile, Source, Organization, Capability, Observation.
4. Canonical edge relationships:
   DECLARES, DISCOVERED_FROM, CONTAINS, OBSERVED_IN, SUPPORTS, CONTRADICTS,
   CONTRIBUTES_TO, ATTRIBUTED_TO, DEPLOYED_AS, ISSUED_BY, VERIFIES, REFERENCES,
   USES_TECHNOLOGY, ASSOCIATED_WITH, DERIVED_FROM.
5. Invariant: Do not create AUTHORED_BY unless the evidence really supports line-level authorship.
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
    """Heterogeneous Candidate Evidence Graph (CEG) Ontology."""

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

    def add_edge(self, edge: CEGEdge, strict_authorship: bool = False) -> None:
        """Adds a directed edge to the graph.

        Invariant: Do not create AUTHORED_BY unless the evidence really supports line-level authorship.
        """
        if edge.source_id not in self.nodes:
            raise KeyError(f"Source node '{edge.source_id}' does not exist in graph")
        if edge.target_id not in self.nodes:
            raise KeyError(f"Target node '{edge.target_id}' does not exist in graph")

        if strict_authorship and edge.edge_type == GraphEdgeType.AUTHORED_BY:
            verified = (
                edge.properties.get("authorship_verified") is True
                or edge.properties.get("is_verified_author") is True
                or edge.properties.get("verified_authorship") is True
                or edge.properties.get("authorship_basis") in (
                    "verified_gpg_commit",
                    "author_email_verified",
                    "cryptographic_signature",
                    "direct_attestation",
                )
            )
            if not verified:
                raise ValueError(
                    f"Cannot create AUTHORED_BY edge '{edge.edge_id}' without verified line-level authorship evidence"
                )

        self.edges[edge.edge_id] = edge
        self._out_edges[edge.source_id].append(edge.edge_id)
        self._in_edges[edge.target_id].append(edge.edge_id)

    def get_node(self, node_id: str) -> CEGNode | None:
        """Retrieves a node by its identifier."""
        return self.nodes.get(node_id)

    def get_nodes_by_type(self, node_type: GraphNodeType | str) -> list[CEGNode]:
        """Queries all nodes matching the specified node type."""
        target_type = (
            node_type if isinstance(node_type, GraphNodeType) else GraphNodeType(node_type)
        )
        return [
            n for n in self.nodes.values()
            if n.node_type == target_type
            or (target_type == GraphNodeType.OBSERVATION and n.node_type == GraphNodeType.EVIDENCE)
            or (target_type == GraphNodeType.EVIDENCE and n.node_type == GraphNodeType.OBSERVATION)
        ]

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

    def get_in_edges(
        self, node_id: str, edge_type: GraphEdgeType | None = None
    ) -> list[CEGEdge]:
        """Returns all incoming edges directed into the node."""
        edge_ids = self._in_edges.get(node_id, [])
        edges = [self.edges[eid] for eid in edge_ids]
        if edge_type is not None:
            edges = [e for e in edges if e.edge_type == edge_type]
        return edges

    def get_out_edges(
        self, node_id: str, edge_type: GraphEdgeType | None = None
    ) -> list[CEGEdge]:
        """Returns all outgoing edges originating from the node."""
        edge_ids = self._out_edges.get(node_id, [])
        edges = [self.edges[eid] for eid in edge_ids]
        if edge_type is not None:
            edges = [e for e in edges if e.edge_type == edge_type]
        return edges

    def get_neighbors(
        self,
        node_id: str,
        direction: str = "both",
        edge_type: GraphEdgeType | None = None,
    ) -> list[CEGNode]:
        """Returns neighboring nodes connected via incoming, outgoing, or both edges."""
        neighbor_ids: set[str] = set()
        if direction in ("out", "both"):
            for e in self.get_out_edges(node_id, edge_type):
                neighbor_ids.add(e.target_id)
        if direction in ("in", "both"):
            for e in self.get_in_edges(node_id, edge_type):
                neighbor_ids.add(e.source_id)
        return [self.nodes[nid] for nid in neighbor_ids if nid in self.nodes]

    def get_predecessors(
        self, node_id: str, edge_type: GraphEdgeType | None = None
    ) -> list[CEGNode]:
        """Returns nodes with outgoing edges directed into node_id."""
        return self.get_neighbors(node_id, direction="in", edge_type=edge_type)

    def get_successors(
        self, node_id: str, edge_type: GraphEdgeType | None = None
    ) -> list[CEGNode]:
        """Returns nodes targeted by outgoing edges from node_id."""
        return self.get_neighbors(node_id, direction="out", edge_type=edge_type)

    def find_paths(
        self, source_id: str, target_id: str, max_depth: int = 5
    ) -> list[list[str]]:
        """Finds all directed paths between source_id and target_id up to max_depth."""
        if source_id not in self.nodes or target_id not in self.nodes:
            return []
        paths: list[list[str]] = []
        queue: list[list[str]] = [[source_id]]
        while queue:
            current_path = queue.pop(0)
            current_node = current_path[-1]
            if current_node == target_id and len(current_path) > 1:
                paths.append(current_path)
                continue
            if len(current_path) >= max_depth:
                continue
            for out_edge in self.get_out_edges(current_node):
                nxt = out_edge.target_id
                if nxt not in current_path:  # Avoid cycles
                    queue.append(current_path + [nxt])
        return paths

    def get_claim_corroboration(self, claim_id: str) -> dict[str, Any]:
        """Queries corroborating and contradicting evidence nodes for a claim."""
        cid_key = claim_id if claim_id in self.nodes else f"claim_{claim_id}"
        claim_node = self.nodes.get(cid_key)
        if not claim_node:
            return {"claim_id": claim_id, "found": False, "supporting": [], "contradicting": []}

        in_edges = self.get_in_edges(cid_key)
        supporting: list[dict[str, Any]] = []
        contradicting: list[dict[str, Any]] = []

        for e in in_edges:
            src_node = self.nodes.get(e.source_id)
            if not src_node:
                continue
            item = {
                "node_id": src_node.node_id,
                "node_type": src_node.node_type.value,
                "properties": src_node.properties,
            }
            if e.edge_type in (
                GraphEdgeType.SUPPORTS,
                GraphEdgeType.CORROBORATES,
                GraphEdgeType.SUPPORTS_CAPABILITY,
            ):
                supporting.append(item)
            elif e.edge_type == GraphEdgeType.CONTRADICTS:
                contradicting.append(item)

        return {
            "claim_id": claim_id,
            "found": True,
            "claim_node": {
                "node_id": claim_node.node_id,
                "properties": claim_node.properties,
            },
            "supporting": supporting,
            "contradicting": contradicting,
        }

    def validate_authorship_invariants(self) -> list[str]:
        """Audits graph to ensure AUTHORED_BY is never created without verified line-level authorship evidence."""
        violations = []
        for edge in self.edges.values():
            if edge.edge_type == GraphEdgeType.AUTHORED_BY:
                verified = (
                    edge.properties.get("authorship_verified") is True
                    or edge.properties.get("is_verified_author") is True
                    or edge.properties.get("verified_authorship") is True
                    or edge.properties.get("authorship_basis") in (
                        "verified_gpg_commit",
                        "author_email_verified",
                        "cryptographic_signature",
                        "direct_attestation",
                    )
                )
                if not verified:
                    violations.append(
                        f"Edge '{edge.edge_id}' uses AUTHORED_BY without verified line-level authorship evidence"
                    )
        return violations

    def trace_provenance(self, capability_key: CapabilityKey) -> list[dict[str, Any]]:
        """Traces backwards from a Capability node to all supporting Evidence, Artifacts, and Sources."""
        cap_node_id = f"cap_{capability_key.value}"
        if cap_node_id not in self.nodes:
            return []

        # Find all incoming SUPPORTS_CAPABILITY or SUPPORTS edges to this capability node
        evidence_edges = [
            e for e in self.get_edges(target_id=cap_node_id)
            if e.edge_type in (GraphEdgeType.SUPPORTS, GraphEdgeType.SUPPORTS_CAPABILITY)
        ]
        traces = []

        for e_edge in evidence_edges:
            ev_node = self.nodes.get(e_edge.source_id)
            if not ev_node or ev_node.node_type not in (GraphNodeType.EVIDENCE, GraphNodeType.OBSERVATION):
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
                    src_edges = [
                        e for e in self.get_edges(source_id=art_node.node_id)
                        if e.edge_type in (
                            GraphEdgeType.CONTRIBUTES_TO,
                            GraphEdgeType.DERIVED_FROM,
                            GraphEdgeType.OBSERVED_IN,
                            GraphEdgeType.CONTAINS,
                        )
                    ]
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
            CEGGraphResponse,
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
