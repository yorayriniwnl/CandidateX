"""Tests for Fix 14: Semantically Stable Claim IDs, Duplicate Detection, and Section Reordering."""

import io
from uuid import UUID, uuid4
import pytest

from cci.claims.identity import (
    CLAIM_NAMESPACE,
    detect_duplicate_claims,
    generate_deterministic_claim_id,
    generate_deterministic_claim_uuid,
    normalize_claim_text,
    normalize_claim_type,
    normalize_structured_semantics,
)
from cci.domain.contracts import CandidateManifest, Claim
from cci.live.claims import _claim_id, build_claim_ledger
from cci.live.contracts import ResumeIntake, ResumeReview


DOC_HASH_A = "a" * 64
DOC_HASH_B = "b" * 64


def test_deterministic_claim_id_stable_across_invocations():
    """Requirement: Deterministic identity based on doc hash, claim type, text/semantics."""
    id1 = generate_deterministic_claim_id(DOC_HASH_A, "skill", "Distributed systems in Go")
    id2 = generate_deterministic_claim_id(DOC_HASH_A, "skill", "Distributed systems in Go")
    assert id1 == id2
    assert id1.startswith("clm_")
    assert len(id1) == 24  # 'clm_' + 20 hex chars

    uuid1 = generate_deterministic_claim_uuid(DOC_HASH_A, "skill", "Distributed systems in Go")
    uuid2 = generate_deterministic_claim_uuid(DOC_HASH_A, "skill", "Distributed systems in Go")
    assert uuid1 == uuid2
    assert isinstance(uuid1, UUID)


def test_moving_bullet_does_not_change_claim_id():
    """Requirement: Moving a bullet can change ordinal, but MUST NOT change identity."""
    # Bullet at ordinal 0
    id_at_0 = _claim_id(
        category="experience",
        section="experience",
        text="Architected high-throughput message bus",
        ordinal=0,
        source_document_hash=DOC_HASH_A,
    )

    # Same bullet moved to ordinal 5
    id_at_5 = _claim_id(
        category="experience",
        section="experience",
        text="Architected high-throughput message bus",
        ordinal=5,
        source_document_hash=DOC_HASH_A,
    )

    assert id_at_0 == id_at_5, "Moving a bullet must not change claim identity"


def test_reordered_resume_sections_produce_identical_claim_ids():
    """Requirement: Test reordered resume sections.

    Resume order is metadata, not identity.
    """
    skills = ["Python", "PostgreSQL", "Kafka"]
    exp_bullets = [
        "Led team of 6 backend engineers building payments service",
        "Decreased p99 query latency from 850ms to 45ms",
    ]
    edu_bullets = ["B.S. in Computer Science, State University, 2020"]
    proj_claims = [{"title": "Cloud Ledger", "description": "High integrity double-entry ledger"}]

    # Layout 1: Skills -> Experience -> Education -> Projects
    intake_layout_1 = ResumeIntake(
        manifest=CandidateManifest(
            display_name="Jane Doe",
            claimed_skills=skills,
            project_claims=proj_claims,
        ),
        document_sha256=DOC_HASH_A,
        filename="resume_1.pdf",
        resume_review=ResumeReview(
            sections={
                "skills": skills,
                "experience": exp_bullets,
                "education": edu_bullets,
            }
        ),
    )

    # Layout 2: Education -> Projects -> Skills -> Experience (Completely reordered sections and bullets)
    intake_layout_2 = ResumeIntake(
        manifest=CandidateManifest(
            display_name="Jane Doe",
            claimed_skills=list(reversed(skills)),  # reversed bullets
            project_claims=proj_claims,
        ),
        document_sha256=DOC_HASH_A,
        filename="resume_2.pdf",
        resume_review=ResumeReview(
            sections={
                "education": edu_bullets,
                "experience": list(reversed(exp_bullets)),  # reversed bullets
                "skills": list(reversed(skills)),
            }
        ),
    )

    ledger_1 = build_claim_ledger(intake_layout_1)
    ledger_2 = build_claim_ledger(intake_layout_2)

    # Extract mapping from claim text to claim_id for both layouts
    map_1 = {c["claim"]: c["claim_id"] for c in ledger_1}
    map_2 = {c["claim"]: c["claim_id"] for c in ledger_2}

    assert set(map_1.keys()) == set(map_2.keys()), "Both layouts extract the same claims"
    for claim_text in map_1:
        assert map_1[claim_text] == map_2[claim_text], (
            f"Claim ID for '{claim_text}' must remain identical across section reordering"
        )


def test_resume_order_preserved_as_metadata_not_identity():
    """Requirement: Resume order should be metadata, not identity."""
    intake = ResumeIntake(
        manifest=CandidateManifest(
            display_name="Jane Doe",
            claimed_skills=["Rust"],
            project_claims=[],
        ),
        document_sha256=DOC_HASH_A,
        filename="resume.pdf",
        resume_review=ResumeReview(
            sections={
                "experience": ["Worked as Rust engineer", "Optimized memory safety"],
            }
        ),
    )

    ledger = build_claim_ledger(intake)
    for claim in ledger:
        assert "ordinal" in claim
        assert "resume_order" in claim
        assert "source_location" in claim
        assert isinstance(claim["ordinal"], int)
        assert claim["source_location"].startswith(claim["section"])


def test_duplicate_claim_detection_in_same_section():
    """Requirement: Implement duplicate-claim detection."""
    intake = ResumeIntake(
        manifest=CandidateManifest(display_name="Jane Doe", claimed_skills=[], project_claims=[]),
        document_sha256=DOC_HASH_A,
        filename="resume.pdf",
        resume_review=ResumeReview(
            sections={
                "experience": [
                    "Maintained 99.99% uptime for core API gateway",
                    "Wrote automated test suites",
                    "Maintained 99.99% uptime for core API gateway",  # duplicate bullet
                ]
            }
        ),
    )

    ledger = build_claim_ledger(intake)

    # Ledger should contain only 2 unique claims (not 3)
    assert len(ledger) == 2

    # Find the duplicate claim
    dup_claim = next(c for c in ledger if c["claim"] == "Maintained 99.99% uptime for core API gateway")
    assert dup_claim["duplicate_count"] == 1
    assert len(dup_claim["occurrences"]) == 2
    assert dup_claim["occurrences"][0]["ordinal"] == 0
    assert dup_claim["occurrences"][1]["ordinal"] == 2


def test_duplicate_claim_detection_across_skills_and_sections():
    """Requirement: Duplicate claims across skills manifest and section lines detected."""
    intake = ResumeIntake(
        manifest=CandidateManifest(
            display_name="Jane Doe",
            claimed_skills=["Python"],
            project_claims=[],
        ),
        document_sha256=DOC_HASH_A,
        filename="resume.pdf",
        resume_review=ResumeReview(
            sections={
                "skills": ["Python", "FastAPI"],  # "Python" duplicated from manifest
            }
        ),
    )

    ledger = build_claim_ledger(intake)
    python_claim = next(c for c in ledger if c["claim"] == "Python")
    assert python_claim["duplicate_count"] == 1
    assert len(python_claim["occurrences"]) == 2


def test_different_document_hashes_produce_different_claim_ids():
    """Requirement: Identity is scoped to source document hash."""
    id_doc_a = generate_deterministic_claim_id(DOC_HASH_A, "skill", "Kubernetes cluster administration")
    id_doc_b = generate_deterministic_claim_id(DOC_HASH_B, "skill", "Kubernetes cluster administration")
    assert id_doc_a != id_doc_b


def test_different_claim_types_produce_different_claim_ids():
    """Requirement: Normalized claim type affects identity."""
    id_skill = generate_deterministic_claim_id(DOC_HASH_A, "skill", "PostgreSQL database optimization")
    id_exp = generate_deterministic_claim_id(DOC_HASH_A, "experience", "PostgreSQL database optimization")
    assert id_skill != id_exp


def test_whitespace_and_case_normalization_stability():
    """Requirement: Normalized text and semantics ensure formatting variations don't break identity."""
    id_norm = generate_deterministic_claim_id(DOC_HASH_A, "skill", "redis caching layer")
    id_spaces = generate_deterministic_claim_id(DOC_HASH_A, "skill", "   Redis   Caching   Layer  \n\t")
    assert id_norm == id_spaces


def test_structured_semantics_influence_identity():
    """Requirement: Structured values are part of semantic identity, while metadata is excluded."""
    id_5yr = generate_deterministic_claim_id(
        DOC_HASH_A, "metric", "Years of experience", structured_semantics={"years": 5}
    )
    id_10yr = generate_deterministic_claim_id(
        DOC_HASH_A, "metric", "Years of experience", structured_semantics={"years": 10}
    )
    assert id_5yr != id_10yr

    # Metadata keys do not affect semantic identity
    id_with_meta1 = generate_deterministic_claim_id(
        DOC_HASH_A, "metric", "Years of experience",
        structured_semantics={"years": 5, "ordinal": 0, "section": "experience"}
    )
    assert id_5yr == id_with_meta1


def test_claim_contract_create_deterministic():
    """Requirement: Canonical Claim contract provides create_deterministic factory."""
    claim = Claim.create_deterministic(
        original_text="Built distributed telemetry pipeline",
        claim_type="project",
        source_document_hash=DOC_HASH_A,
        section="projects",
        source_location="line 15",
    )
    expected_uuid = generate_deterministic_claim_uuid(
        source_document_hash=DOC_HASH_A,
        claim_type="project",
        text="Built distributed telemetry pipeline",
    )
    assert claim.claim_id == expected_uuid
    assert claim.original_text == "Built distributed telemetry pipeline"
    assert claim.section == "projects"
    assert claim.source_location == "line 15"


def test_adversarial_duplicate_flooding_attack():
    """Attack: Flooding resume with 50 duplicate claims does not pollute ledger with 50 duplicate IDs."""
    duplicate_skill = "Containerization with Docker"
    intake = ResumeIntake(
        manifest=CandidateManifest(
            display_name="Jane Doe",
            claimed_skills=[duplicate_skill] * 50,
            project_claims=[],
        ),
        document_sha256=DOC_HASH_A,
        filename="flood_attack.pdf",
        resume_review=ResumeReview(sections={}),
    )

    ledger = build_claim_ledger(intake)
    assert len(ledger) == 1, "Flooding duplicates must result in exactly 1 unique ledger entry"
    assert ledger[0]["duplicate_count"] == 49
    assert len(ledger[0]["occurrences"]) == 50


def test_adversarial_reordering_with_newlines_and_spaces():
    """Attack: Attacker attempts to change identity by injecting whitespace and moving sections."""
    text_clean = "Designed CQRS event sourcing architecture"
    text_noisy = "  Designed   CQRS\n  event\tsourcing   architecture  "

    id_clean = generate_deterministic_claim_id(DOC_HASH_A, "experience", text_clean)
    id_noisy = generate_deterministic_claim_id(DOC_HASH_A, "experience", text_noisy)
    assert id_clean == id_noisy
