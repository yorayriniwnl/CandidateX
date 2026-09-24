"""Source independence modeling and provenance family classification (Fix 43).

Enforces the core hardening invariants:
1. Evidence from:
   - resume
   - candidate portfolio
   - candidate README
   - candidate GitHub profile
   may all originate from the candidate; they must NOT be counted as independent confirmations.
2. Models the eight canonical provenance families:
   - CANDIDATE_DECLARATION
   - CANDIDATE_CONTROLLED_ARTIFACT
   - PLATFORM_METADATA
   - INDEPENDENT_PLATFORM
   - ISSUER_CONTROLLED
   - ORGANIZATION_CONTROLLED
   - PUBLICATION_INDEX
   - UNKNOWN
3. Applies source independence when computing claim corroboration strength.
4. Candidate code is NEVER executed.
"""

from __future__ import annotations

import re
from typing import Any, Mapping, Sequence
from urllib.parse import urlparse

from cci.domain.contracts import EvidenceRecord
from cci.domain.enums import ClaimStatus, ProvenanceFamily, SourceFamily

CANDIDATE_ORIGIN_FAMILIES = {
    ProvenanceFamily.CANDIDATE_DECLARATION,
    ProvenanceFamily.CANDIDATE_CONTROLLED_ARTIFACT,
}

INDEPENDENT_PROVENANCE_FAMILIES = {
    ProvenanceFamily.INDEPENDENT_PLATFORM,
    ProvenanceFamily.ISSUER_CONTROLLED,
    ProvenanceFamily.ORGANIZATION_CONTROLLED,
    ProvenanceFamily.PUBLICATION_INDEX,
    ProvenanceFamily.PLATFORM_METADATA,
}


def classify_provenance_family(
    record_or_data: EvidenceRecord | Mapping[str, Any],
    candidate_identifier: str | None = None,
) -> ProvenanceFamily:
    """Classifies an observation or source into its canonical ProvenanceFamily."""
    if isinstance(record_or_data, EvidenceRecord):
        source_fam = record_or_data.source_family
        source_locator = str(record_or_data.source_locator).lower()
        prov = record_or_data.provenance or {}
        art_path = str(prov.get("artifact_path", "")).lower()
        obs_type = str(record_or_data.observation_type).lower()
    else:
        source_fam = record_or_data.get("source_family") or record_or_data.get("kind", "")
        source_locator = str(record_or_data.get("url") or record_or_data.get("source_locator", "")).lower()
        prov = record_or_data.get("provenance") or {}
        art_path = str(record_or_data.get("artifact_path") or prov.get("artifact_path", "")).lower()
        obs_type = str(record_or_data.get("observation_type", "")).lower()

    # 1. Publication Index (arXiv, IEEE, ACM, DOI, research indices)
    if any(k in source_locator for k in ("arxiv.org", "doi.org", "ieee.org", "acm.org", "springer.com")):
        return ProvenanceFamily.PUBLICATION_INDEX

    # 2. Candidate Declaration (Resume, CV, bio text, self-claims)
    if source_fam in (SourceFamily.RESUME, "resume") or obs_type in ("self_reported", "cv_text"):
        return ProvenanceFamily.CANDIDATE_DECLARATION

    # 3. Issuer Controlled (Credly badges, Coursera verified credentials, educational registrars)
    if source_fam in (SourceFamily.CERTIFICATE, "certificate"):
        if any(issuer in source_locator for issuer in ("credly.com", "coursera.org", "hackerrank.com", "verify", "badge")):
            return ProvenanceFamily.ISSUER_CONTROLLED
        return ProvenanceFamily.CANDIDATE_DECLARATION

    # 4. Independent Platform (Competitive programming judges: LeetCode, Codeforces, Kaggle, CodeChef, or deployment)
    if source_fam in (SourceFamily.CODING, "coding") or any(cp in source_locator for cp in ("leetcode.com", "codeforces.com", "kaggle.com", "codechef.com")):
        return ProvenanceFamily.INDEPENDENT_PLATFORM
    if source_fam in (SourceFamily.DEPLOYMENT, "deployment"):
        return ProvenanceFamily.INDEPENDENT_PLATFORM

    # 5. Platform Metadata (Account activity, commit stats, git logs, platform timestamps)
    if any(m in obs_type for m in ("metadata", "stat", "commit_history", "git_blame", "author_attribution", "pr_review")):
        return ProvenanceFamily.PLATFORM_METADATA

    # 6. Candidate Controlled Portfolio / Personal Website
    if any(k in source_locator for k in ("portfolio", "github.io", "vercel.app", "netlify.app", "pages.dev")):
        return ProvenanceFamily.CANDIDATE_CONTROLLED_ARTIFACT

    # 7. Organization Controlled (Company or organization multi-contributor repository on git host)
    if source_fam in (SourceFamily.GITHUB, "github"):
        parsed = urlparse(source_locator)
        parts = [p for p in parsed.path.strip("/").split("/") if p]
        owner = parts[0] if parts else ""
        cand_id = (candidate_identifier or "").lower().strip()
        # Organization repository requires at least owner/repo and owner != candidate_id
        if len(parts) >= 2 and owner and cand_id and owner.lower() != cand_id and owner not in ("u", "users"):
            return ProvenanceFamily.ORGANIZATION_CONTROLLED
        return ProvenanceFamily.CANDIDATE_CONTROLLED_ARTIFACT

    return ProvenanceFamily.UNKNOWN


def is_candidate_self_declaration(
    record_or_data: EvidenceRecord | Mapping[str, Any],
) -> bool:
    """Returns True if evidence is declarative text from resume, portfolio, README, or profile.
    
    Per Fix 43 design specification:
    Evidence from:
    - resume
    - candidate portfolio
    - candidate README
    - candidate GitHub profile
    may all originate from the candidate; they must not be counted as independent confirmations.
    """
    if isinstance(record_or_data, EvidenceRecord):
        source_fam = record_or_data.source_family
        source_locator = str(record_or_data.source_locator).lower()
        prov = record_or_data.provenance or {}
        art_path = str(prov.get("artifact_path", "")).lower()
        obs_type = str(record_or_data.observation_type).lower()
    else:
        source_fam = record_or_data.get("source_family") or record_or_data.get("kind", "")
        source_locator = str(record_or_data.get("url") or record_or_data.get("source_locator", "")).lower()
        prov = record_or_data.get("provenance") or {}
        art_path = str(record_or_data.get("artifact_path") or prov.get("artifact_path", "")).lower()
        obs_type = str(record_or_data.get("observation_type", "")).lower()

    # Resume / CV
    if source_fam in (SourceFamily.RESUME, "resume") or obs_type in ("self_reported", "cv_text"):
        return True

    # README
    if "readme" in art_path or "readme" in obs_type:
        return True

    # Profile / bio
    if "profile" in art_path or "profile" in obs_type or "bio" in obs_type:
        return True

    # Portfolio text (when not actual code/tests/schema)
    is_portfolio = any(p in source_locator for p in ("portfolio", "github.io", "vercel.app", "netlify.app", "pages.dev"))
    code_exts = (".py", ".ts", ".js", ".go", ".rs", ".java", ".sql", ".c", ".cpp", ".rb", ".php")
    has_code_ext = any(art_path.endswith(ext) for ext in code_exts)
    if is_portfolio and not has_code_ext:
        return True

    return False


def compute_source_independence(
    evidence_records: Sequence[EvidenceRecord],
    candidate_identifier: str | None = None,
) -> dict[str, Any]:
    """Analyzes a collection of evidence records for source independence."""
    family_counts: dict[ProvenanceFamily, int] = {}
    record_families: dict[str, ProvenanceFamily] = {}
    self_declaration_flags: dict[str, bool] = {}

    for ev in evidence_records:
        fam = classify_provenance_family(ev, candidate_identifier=candidate_identifier)
        family_counts[fam] = family_counts.get(fam, 0) + 1
        record_families[str(ev.evidence_id)] = fam
        self_declaration_flags[str(ev.evidence_id)] = is_candidate_self_declaration(ev)

    candidate_origin_count = sum(family_counts.get(f, 0) for f in CANDIDATE_ORIGIN_FAMILIES)
    independent_count = sum(family_counts.get(f, 0) for f in INDEPENDENT_PROVENANCE_FAMILIES)
    distinct_families = len(family_counts)
    distinct_independent_families = len([f for f in family_counts if f in INDEPENDENT_PROVENANCE_FAMILIES])

    has_independent_confirmation = distinct_independent_families >= 1
    only_candidate_origin = (candidate_origin_count > 0) and (independent_count == 0)
    all_candidate_self_declarations = bool(evidence_records) and all(self_declaration_flags.values())

    return {
        "family_counts": {f.value: c for f, c in family_counts.items()},
        "record_families": {eid: f.value for eid, f in record_families.items()},
        "candidate_origin_count": candidate_origin_count,
        "independent_count": independent_count,
        "distinct_families_count": distinct_families,
        "distinct_independent_families_count": distinct_independent_families,
        "has_independent_confirmation": has_independent_confirmation,
        "only_candidate_origin": only_candidate_origin,
        "all_candidate_self_declarations": all_candidate_self_declarations,
    }


def evaluate_corroboration_with_source_independence(
    matched_pos_evidence: Sequence[EvidenceRecord],
    matched_neg_evidence: Sequence[EvidenceRecord],
    candidate_identifier: str | None = None,
    family_weights: Mapping[Any, float] | None = None,
) -> tuple[ClaimStatus, float, str, dict[str, Any]]:
    """Computes claim corroboration status and confidence respecting source independence (Fix 43).

    Hardening Rules:
    1. Evidence from resume, portfolio, README, and personal GitHub profile may all originate
       from the candidate; do not count them as four independent confirmations.
    2. If all matching observations originate from the candidate's self-declarations
       (all_candidate_self_declarations), status CANNOT exceed PARTIALLY_SUPPORTED and confidence is discounted.
    3. Independent confirmation requires observations from at least one independent provenance family
       (INDEPENDENT_PLATFORM, ISSUER_CONTROLLED, ORGANIZATION_CONTROLLED, PUBLICATION_INDEX, PLATFORM_METADATA)
       or verified technical code artifacts.
    """
    if not matched_pos_evidence and not matched_neg_evidence:
        return (
            ClaimStatus.NOT_OBSERVED,
            0.0,
            "No qualifying evidence was observed in the available scope.",
            {
                "provenance_families": [],
                "has_independent_confirmation": False,
                "all_candidate_self_declarations": False,
            },
        )

    # Analyze source independence
    independence = compute_source_independence(
        [*matched_pos_evidence, *matched_neg_evidence],
        candidate_identifier=candidate_identifier,
    )
    pos_independence = compute_source_independence(
        matched_pos_evidence,
        candidate_identifier=candidate_identifier,
    )
    all_self_decl = pos_independence["all_candidate_self_declarations"]
    has_indep = independence["has_independent_confirmation"]
    prov_families = list(independence["family_counts"].keys())

    # Precomputed evidence family weights check
    has_precomputed_weights = family_weights is not None and any(w < 1.0 for w in family_weights.values())

    # Apply diminishing returns per provenance family
    family_seen_counts: dict[ProvenanceFamily, int] = {}
    pos_confidence_sum = 0.0

    for ev in matched_pos_evidence:
        fam = classify_provenance_family(ev, candidate_identifier=candidate_identifier)
        seen = family_seen_counts.get(fam, 0)
        family_seen_counts[fam] = seen + 1

        fw = family_weights.get(ev.evidence_id, 1.0) if family_weights else 1.0
        # If precomputed weights are uniform or absent, apply provenance-family decay
        decay = (1.0 / (1.0 + 0.5 * seen)) if not has_precomputed_weights else 1.0
        pos_confidence_sum += ev.confidence * fw * decay

    neg_confidence_sum = 0.0
    for ev in matched_neg_evidence:
        fw = family_weights.get(ev.evidence_id, 1.0) if family_weights else 1.0
        neg_confidence_sum += ev.confidence * fw

    metadata = {
        "provenance_families": prov_families,
        "has_independent_confirmation": has_indep,
        "all_candidate_self_declarations": all_self_decl,
        "source_independence": independence,
    }

    if matched_neg_evidence and neg_confidence_sum > pos_confidence_sum:
        return (
            ClaimStatus.CONTRADICTED,
            round(min(1.0, neg_confidence_sum), 3),
            f"Observed artifacts contradict claim; negative support weight ({neg_confidence_sum:.2f}) exceeds positive ({pos_confidence_sum:.2f}).",
            metadata,
        )

    if pos_confidence_sum <= 0.0:
        return (
            ClaimStatus.NOT_OBSERVED,
            0.0,
            "No qualifying evidence was observed in the available scope.",
            metadata,
        )

    # Core Invariant Enforcement (Fix 43):
    # Candidate-controlled declarative evidence alone (resume, portfolio, README, profile)
    # cannot establish full SUPPORTED status.
    if all_self_decl:
        discounted_conf = min(0.50, round(pos_confidence_sum * 0.5, 3))
        explanation = (
            f"Evidence from resume, portfolio, README, or personal profile originates from the candidate; "
            f"cannot count as independent confirmation. Status capped at PARTIALLY_SUPPORTED "
            f"({len(matched_pos_evidence)} candidate-controlled observation(s))."
        )
        return (ClaimStatus.PARTIALLY_SUPPORTED, discounted_conf, explanation, metadata)

    # When cumulative confidence >= 1.0
    if pos_confidence_sum >= 1.0:
        conf = min(1.0, round(pos_confidence_sum / 2.0, 3))
        distinct_indep = independence["distinct_independent_families_count"]
        if has_indep:
            explanation = (
                f"Claim corroborated by {len(matched_pos_evidence)} verified observations with independent confirmation "
                f"across {distinct_indep} independent provenance family/families (cumulative confidence: {pos_confidence_sum:.2f})."
            )
        else:
            explanation = (
                f"Claim corroborated by {len(matched_pos_evidence)} verified technical observations "
                f"(cumulative confidence: {pos_confidence_sum:.2f})."
            )
        return (ClaimStatus.SUPPORTED, conf, explanation, metadata)

    # Positive evidence exists with some independent support or lower weight
    conf = min(1.0, round(pos_confidence_sum, 3))
    explanation = (
        f"Partially corroborated by {len(matched_pos_evidence)} observation(s); "
        f"further independent verification recommended."
    )
    return (ClaimStatus.PARTIALLY_SUPPORTED, conf, explanation, metadata)
