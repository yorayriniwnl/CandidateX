from uuid import uuid4

from cci.domain.contracts import EvidenceConfidenceFactors, EvidenceRecord, NormalizedRequirement
from cci.domain.enums import CapabilityKey, RequirementPriority, SourceFamily
from cci.scoring.role_fit import build_role_fit


def requirement(text, capabilities, technologies):
    return NormalizedRequirement(
        source_text=text,
        normalized_name=text,
        priority=RequirementPriority.MANDATORY,
        capability_mappings=capabilities,
        technology_mentions=technologies,
    )


def python_evidence_record():
    factors = EvidenceConfidenceFactors(
        artifact_integrity=1.0,
        ownership_score=0.8,
        recency_factor=1.0,
        verification_level=0.8,
        depth_specificity=0.8,
        source_reliability=0.8,
    )
    return EvidenceRecord(
        evidence_id=uuid4(),
        fingerprint="a" * 64,
        source_family=SourceFamily.GITHUB,
        source_locator="https://github.com/example/api",
        immutable_revision="a" * 40,
        target_capability=CapabilityKey.BACKEND_ENGINEERING,
        support_score=80.0,
        confidence=factors.composite_confidence,
        confidence_factors=factors,
        cluster_id="repo-1",
        provenance={
            "artifact_path": "app.py",
            "symbol_or_line": "Line 1: FastAPI app",
            "raw_support_text": "Python source implementation",
        },
    )


def test_role_fit_reports_requirement_status_and_mandatory_gaps():
    requirements = [
        requirement("Must have Python", [CapabilityKey.BACKEND_ENGINEERING], ["python"]),
        requirement("Must have PostgreSQL", [CapabilityKey.DATABASE_ENGINEERING], ["postgresql"]),
        requirement("Must have synergistic paradigms", [], []),
    ]

    result = build_role_fit(requirements, [python_evidence_record()])

    assert [match.status for match in result.requirement_matches] == ["observed", "unknown", "unresolved"]
    assert result.mandatory_observed == 1
    assert result.mandatory_unknown == 1
    assert result.mandatory_unresolved == 1
    assert "Must have PostgreSQL" in result.critical_gaps


def test_role_fit_keeps_evidence_ids_on_exact_matches():
    evidence = python_evidence_record()
    result = build_role_fit(
        [requirement("Must have Python", [CapabilityKey.BACKEND_ENGINEERING], ["python"])],
        [evidence],
    )

    assert result.requirement_matches[0].evidence_ids == [evidence.evidence_id]
    assert "exact" in result.requirement_matches[0].explanation.lower()
