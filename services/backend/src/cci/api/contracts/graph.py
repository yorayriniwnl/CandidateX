"""Candidate Evidence Graph (CEG) projection API schemas."""

from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, Field

from cci.domain.enums import GraphEdgeType, GraphNodeType


class CEGNode(BaseModel):
    """Node in the Candidate Evidence Graph."""
    id: str = Field(..., description="Unique node identifier")
    type: GraphNodeType
    label: str
    properties: Dict[str, Any] = Field(default_factory=dict)


class CEGEdge(BaseModel):
    """Directed edge in the Candidate Evidence Graph."""
    id: str = Field(..., description="Unique edge identifier")
    source: str = Field(..., description="Source node ID")
    target: str = Field(..., description="Target node ID")
    type: GraphEdgeType
    weight: float = Field(default=1.0)
    properties: Dict[str, Any] = Field(default_factory=dict)


class CEGGraphResponse(BaseModel):
    """Complete Candidate Evidence Graph projection payload."""
    candidate_id: UUID
    analysis_run_id: UUID
    nodes: List[CEGNode] = Field(default_factory=list)
    edges: List[CEGEdge] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
