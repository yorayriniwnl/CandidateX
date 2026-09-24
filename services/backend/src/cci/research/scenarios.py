"""Versioned, explicitly synthetic observations for the interactive paper demo.

These pedagogical scenarios are not the manuscript benchmark or real people.
Inputs are independent of target role; every modification is inspectable.
"""
import hashlib
import json
from datetime import datetime, timezone
from typing import Literal
from uuid import NAMESPACE_URL, UUID, uuid5

from pydantic import BaseModel, Field
from cci.domain.contracts import (
    EvidenceConfidenceFactors,
    EvidenceRecord,
    NegativeEvidenceDetails,
    NegativeEvidenceScanScope,
)
from cci.domain.enums import CanonicalRole, CapabilityKey, SourceFamily
from cci.domain.evidence_families import build_evidence_family_identity
from cci.scoring.reliability import compute_source_reliability

VERSION = "research-scenarios-1.0"
EPOCH = datetime(2026, 1, 1, tzinfo=timezone.utc)


class DemoRequest(BaseModel):
    candidate_id: UUID
    scenario: Literal["consistent", "sparse", "low_ownership", "conflicting", "empty"] = "consistent"
    role: CanonicalRole = CanonicalRole.BACKEND
    jd_text: str = Field(default="", max_length=20000)
    excluded_sources: list[SourceFamily] = Field(default_factory=list, max_length=7)
    ownership_multiplier: float = Field(default=1, ge=0, le=1)
    reliability_false_positives: int = Field(default=0, ge=0, le=100)


def make_scenario(request: DemoRequest):
    """Return evidence and Beta snapshots from declared simulated review counts."""
    reliability = {s: compute_source_reliability(s, true_positives=8,
                   false_positives=request.reliability_false_positives)
                   for s in SourceFamily}
    records = []
    # Deliberately asymmetric profile makes role conditioning observable.
    strengths = [88, 42, 83, 70, 31, 65, 72, 80, 67, 79, 74, 76]
    for source_index, family in enumerate(SourceFamily):
        if family in request.excluded_sources or request.scenario == "empty":
            continue
        if request.scenario == "sparse" and family != SourceFamily.GITHUB:
            continue
        for index, cap in enumerate(CapabilityKey):
            if request.scenario == "sparse" and index not in (0, 2, 7):
                continue
            ownership = 0.9 * request.ownership_multiplier
            if request.scenario == "low_ownership" and family == SourceFamily.GITHUB:
                ownership *= 0.05
            negative = request.scenario == "conflicting" and index in (0, 2) and source_index in (1, 2, 3)
            score = max(0, min(100, strengths[index] + (source_index % 3 - 1) * 5))
            if negative:
                score = 25
            cluster_id = (
                f"synthetic://scenario/{request.scenario}/project-"
                f"{source_index % 3}/{family.value}"
            )
            locator = f"{cluster_id}/{cap.value}"
            semantic_subject = f"{request.scenario}:{cap.value}:technical-signal"
            observation_type = "simulation:scenario_capability_signal"
            family_identity = build_evidence_family_identity(
                source_family=family,
                cluster_id=cluster_id,
                capability=cap,
                fact_domain="simulation",
                subject=semantic_subject,
            )
            raw = {"capability": cap.value, "support_score": score,
                   "positive": not negative, "source": family.value,
                   "description": "Simulated observation for method demonstration; no external artifact inspected."}
            normalized = json.dumps(raw, sort_keys=True, separators=(",", ":"))
            revision = hashlib.sha256(normalized.encode()).hexdigest()
            fingerprint = hashlib.sha256((normalized + locator + revision + VERSION).encode()).hexdigest()
            factors = EvidenceConfidenceFactors(
                artifact_integrity=0.95, ownership_score=ownership,
                recency_factor=0.9, verification_level=0.65 if family in (SourceFamily.RESUME, SourceFamily.LINKEDIN) else 0.9,
                depth_specificity=0.85, source_reliability=reliability[family].posterior_mean)
            negative_details = (
                NegativeEvidenceDetails(
                    claim_reference="cr1:" + hashlib.sha256(
                        f"synthetic:{request.candidate_id}:{cap.value}".encode()
                    ).hexdigest(),
                    candidate_type="candidatex.contradiction.coverage_below_claim",
                    expected_observation=f"Demonstrated proficiency in {cap.value}",
                    actual_observation=f"Simulated contradictory signal for {cap.value}",
                    scan_scope=NegativeEvidenceScanScope(
                        scope_kind="synthetic",
                    ),
                    required_scan_completeness=1.0,
                    observed_scan_completeness=1.0,
                    explanation=f"Simulated conflict fixture for {cap.value} demonstration.",
                )
                if negative
                else None
            )
            records.append(EvidenceRecord(
                evidence_id=uuid5(request.candidate_id, fingerprint), fingerprint=fingerprint,
                source_family=family, source_locator=locator, immutable_revision=revision,
                artifact_id=uuid5(
                    NAMESPACE_URL,
                    f"cci-scenario:artifact:{request.scenario}:{family.value}:"
                    f"{source_index % 3}:{index}",
                ),
                target_capability=cap, technical_signal_strength=score, is_positive_support=not negative,
                negative_evidence_details=negative_details,
                confidence_factors=factors, confidence=factors.composite_confidence,
                cluster_id=cluster_id,
                evidence_family_id=family_identity.evidence_family_id,
                observation_type=observation_type,
                evidence_family_basis=family_identity.basis,
                created_at=EPOCH,
                provenance={"synthetic": True, "candidate_id": str(request.candidate_id),
                            "source_locator": locator, "artifact_path": f"{family.value}/{cap.value}.json",
                            "raw_support_text": normalized, "extractor_version": VERSION,
                            "semantic_subject": semantic_subject,
                            "evidence_family_basis": family_identity.basis,
                            "observed_at": EPOCH.isoformat(), "verification_status": "simulated",
                            "review_counts": {"true_positive": 8, "false_positive": request.reliability_false_positives}}))
    return records, reliability


def evidence_digest(records: list[EvidenceRecord]) -> str:
    """Includes identity, scope, and factor changes in the synthetic evidence digest."""
    content = [
        {
            "fingerprint": record.fingerprint,
            "evidence_family_id": record.evidence_family_id,
            "observation_type": record.observation_type,
            "cluster_id": record.cluster_id,
            "artifact_id": str(record.artifact_id) if record.artifact_id else None,
            "evidence_family_basis": record.evidence_family_basis,
            "factors": record.confidence_factors.model_dump(),
        }
        for record in records
    ]
    return hashlib.sha256(json.dumps(content, sort_keys=True).encode()).hexdigest()
