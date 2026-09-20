"""Deterministic job-requirement matching over immutable evidence records."""

from pathlib import PurePosixPath

from cci.domain.contracts import (
    EvidenceRecord,
    NormalizedRequirement,
    RequirementEvidenceMatch,
    RoleFitSummary,
)
from cci.domain.enums import RequirementPriority
from cci.intake.technology import contains_technology


_LANGUAGE_BY_SUFFIX = {
    ".py": "python",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".js": "javascript",
    ".jsx": "javascript",
    ".java": "java",
    ".go": "go",
    ".rs": "rust",
    ".cpp": "c++",
    ".cc": "c++",
    ".c": "c",
}


def _evidence_text(evidence: EvidenceRecord) -> str:
    provenance = evidence.provenance or {}
    artifact_path = str(provenance.get("artifact_path", ""))
    suffix = PurePosixPath(artifact_path.replace("\\", "/")).suffix.lower()
    language = _LANGUAGE_BY_SUFFIX.get(suffix, "")
    return " ".join(
        str(value)
        for value in (
            provenance.get("raw_support_text", ""),
            provenance.get("symbol_or_line", ""),
            artifact_path,
            language,
        )
        if value
    )


def _matching_evidence(
    requirement: NormalizedRequirement,
    evidence_records: list[EvidenceRecord],
) -> tuple[list[EvidenceRecord], list[EvidenceRecord], list[str]]:
    relevant = [
        evidence
        for evidence in evidence_records
        if evidence.target_capability in requirement.capability_mappings
        and evidence.is_positive_support
        and evidence.confidence > 0.0
    ]
    exact: list[EvidenceRecord] = []
    matched_technologies: list[str] = []
    for evidence in relevant:
        text = _evidence_text(evidence)
        matched = [
            technology
            for technology in requirement.technology_mentions
            if contains_technology(text, technology)
        ]
        if matched:
            exact.append(evidence)
            for technology in matched:
                if technology not in matched_technologies:
                    matched_technologies.append(technology)
    return relevant, exact, matched_technologies


def build_role_fit(
    requirements: list[NormalizedRequirement],
    evidence_records: list[EvidenceRecord],
) -> RoleFitSummary:
    """Build requirement statuses without changing formal capability scores."""
    matches: list[RequirementEvidenceMatch] = []
    counts = {
        "mandatory": {"total": 0, "observed": 0, "related": 0, "unknown": 0, "unresolved": 0},
        "preferred": {"total": 0, "observed": 0, "related": 0, "unknown": 0, "unresolved": 0},
    }
    critical_gaps: list[str] = []

    for requirement in requirements:
        bucket = "mandatory" if requirement.priority == RequirementPriority.MANDATORY else "preferred"
        counts[bucket]["total"] += 1
        if not requirement.capability_mappings:
            status = "unresolved"
            usable, exact, matched_technologies = [], [], []
            explanation = "The requirement could not be mapped to the controlled capability ontology."
        else:
            usable, exact, matched_technologies = _matching_evidence(requirement, evidence_records)
            if exact:
                status = "observed"
                explanation = (
                    "Exact technology evidence was observed in supplied artifacts; "
                    "review the cited files for depth and ownership."
                )
            elif usable:
                status = "related"
                explanation = (
                    "The mapped capability has evidence, but the exact requested technology "
                    "was not observed in the bounded scan."
                )
            else:
                status = "unknown"
                explanation = (
                    "No usable evidence for this requirement was observed. This is unknown, "
                    "not evidence that the candidate lacks the capability."
                )

        counts[bucket][status] += 1
        if bucket == "mandatory" and status in {"unknown", "unresolved"}:
            critical_gaps.append(requirement.source_text)
        matches.append(
            RequirementEvidenceMatch(
                requirement_id=requirement.requirement_id,
                normalized_name=requirement.normalized_name,
                source_text=requirement.source_text,
                priority=requirement.priority,
                capability_mappings=requirement.capability_mappings,
                status=status,
                evidence_ids=[evidence.evidence_id for evidence in (exact or usable)],
                matching_technologies=matched_technologies,
                explanation=explanation,
            )
        )

    return RoleFitSummary(
        requirement_matches=matches,
        mandatory_total=counts["mandatory"]["total"],
        mandatory_observed=counts["mandatory"]["observed"],
        mandatory_related=counts["mandatory"]["related"],
        mandatory_unknown=counts["mandatory"]["unknown"],
        mandatory_unresolved=counts["mandatory"]["unresolved"],
        preferred_total=counts["preferred"]["total"],
        preferred_observed=counts["preferred"]["observed"],
        preferred_related=counts["preferred"]["related"],
        preferred_unknown=counts["preferred"]["unknown"],
        preferred_unresolved=counts["preferred"]["unresolved"],
        critical_gaps=critical_gaps,
    )
