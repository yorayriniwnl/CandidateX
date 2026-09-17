"""Candidate self-claim verification and corroboration engine.

INVARIANTS:
1. Candidate CV claims are cross-referenced with strictly verified evidence in the CEG.
2. Missing evidence yields UNKNOWN status, never zero capability score.
3. Every corroborated or contradicted claim preserves explicit grounding evidence IDs.
"""

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID, uuid4

from cci.domain.contracts import EvidenceRecord
from cci.domain.enums import CapabilityKey, ClaimStatus


@dataclass
class ExtractedClaimInput:
    """A technical claim extracted from the candidate's CV or profile."""

    claim_id: UUID = field(default_factory=uuid4)
    claim_text: str = ""
    target_capability: CapabilityKey = CapabilityKey.BACKEND_ENGINEERING
    technology_keywords: list[str] = field(default_factory=list)


@dataclass
class ClaimCorroborationResult:
    """Result of cross-referencing a candidate self-claim against technical evidence."""

    claim_id: UUID
    claim_text: str
    target_capability: CapabilityKey
    status: ClaimStatus
    confidence: float
    grounding_evidence_ids: list[UUID]
    citation_urls: list[str]
    explanation: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "claim_id": str(self.claim_id),
            "claim_text": self.claim_text,
            "target_capability": self.target_capability.value,
            "status": self.status.value,
            "confidence": self.confidence,
            "grounding_evidence_ids": [str(eid) for eid in self.grounding_evidence_ids],
            "citation_urls": self.citation_urls,
            "explanation": self.explanation,
        }


def corroborate_candidate_claims(
    claims: list[ExtractedClaimInput],
    evidence_records: list[EvidenceRecord],
) -> list[ClaimCorroborationResult]:
    """Evaluates each candidate self-claim against registered technical evidence."""
    results: list[ClaimCorroborationResult] = []

    # Index evidence by capability for fast lookups
    evidence_by_cap: dict[CapabilityKey, list[EvidenceRecord]] = {}
    for ev in evidence_records:
        evidence_by_cap.setdefault(ev.target_capability, []).append(ev)

    for claim in claims:
        matching_ev = evidence_by_cap.get(claim.target_capability, [])

        if not matching_ev:
            results.append(
                ClaimCorroborationResult(
                    claim_id=claim.claim_id,
                    claim_text=claim.claim_text,
                    target_capability=claim.target_capability,
                    status=ClaimStatus.UNKNOWN,
                    confidence=0.0,
                    grounding_evidence_ids=[],
                    citation_urls=[],
                    explanation=f"No evidence observed across scanned repositories or deployments for capability '{claim.target_capability.value}'.",
                )
            )
            continue

        # Check for keyword-specific evidence or capability support
        matched_pos_evidence: list[EvidenceRecord] = []
        matched_neg_evidence: list[EvidenceRecord] = []

        keywords_lower = [k.lower() for k in claim.technology_keywords]

        for ev in matching_ev:
            prov = ev.provenance or {}
            raw_text = prov.get("raw_support_text", "")
            symbol = prov.get("symbol_or_line", "")
            art_path = prov.get("artifact_path", "")
            text_lower = f"{raw_text} {symbol} {art_path} {ev.source_locator}".lower()
            keyword_hit = (
                any(k in text_lower for k in keywords_lower) if keywords_lower else True
            )

            if keyword_hit:
                if ev.is_positive_support:
                    matched_pos_evidence.append(ev)
                else:
                    matched_neg_evidence.append(ev)

        # Fallback to capability-level evidence if keyword hits weren't found
        if not matched_pos_evidence and not matched_neg_evidence:
            matched_pos_evidence = [e for e in matching_ev if e.is_positive_support]
            matched_neg_evidence = [e for e in matching_ev if not e.is_positive_support]

        # Calculate corroboration metrics
        pos_confidence_sum = sum(e.confidence for e in matched_pos_evidence)
        neg_confidence_sum = sum(e.confidence for e in matched_neg_evidence)
        grounding_ids = [
            e.evidence_id for e in matched_pos_evidence + matched_neg_evidence
        ]
        citation_urls = list(
            dict.fromkeys(
                e.source_locator for e in matched_pos_evidence + matched_neg_evidence
            )
        )

        if matched_neg_evidence and neg_confidence_sum > pos_confidence_sum:
            status = ClaimStatus.CONTRADICTED
            conf = min(1.0, neg_confidence_sum)
            explanation = f"Observed artifacts contradict claim; negative support weight ({neg_confidence_sum:.2f}) exceeds positive ({pos_confidence_sum:.2f})."
        elif pos_confidence_sum >= 1.0:
            status = ClaimStatus.CORROBORATED
            conf = min(1.0, pos_confidence_sum / 2.0)
            explanation = f"Claim corroborated by {len(matched_pos_evidence)} verified technical observations (cumulative confidence: {pos_confidence_sum:.2f})."
        elif pos_confidence_sum > 0.0:
            status = ClaimStatus.PARTIAL
            conf = pos_confidence_sum
            explanation = f"Partially corroborated by {len(matched_pos_evidence)} observation(s); further verification recommended."
        else:
            status = ClaimStatus.UNKNOWN
            conf = 0.0
            explanation = (
                "Insufficient technical evidence to corroborate or contradict claim."
            )

        results.append(
            ClaimCorroborationResult(
                claim_id=claim.claim_id,
                claim_text=claim.claim_text,
                target_capability=claim.target_capability,
                status=status,
                confidence=round(conf, 3),
                grounding_evidence_ids=grounding_ids,
                citation_urls=citation_urls,
                explanation=explanation,
            )
        )

    return results
