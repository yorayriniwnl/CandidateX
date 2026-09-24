"""Tests for Fix 16: Unify Source Lifecycle Semantics and Identity Verification Invariants."""

from uuid import uuid4
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from cci.db.base import Base
from cci.db import models
from cci.db.repository import save_candidate
from cci.domain.contracts import CandidateManifest
from cci.domain.enums import SourceState


def test_source_state_exact_fourteen_canonical_states():
    """Acceptance gate: SourceState must define exactly the 14 canonical lifecycle states."""
    expected_names = {
        "DECLARED",
        "DISCOVERED",
        "QUEUED",
        "FETCHING",
        "FETCHED",
        "PARSED",
        "OBSERVED",
        "CORROBORATED",
        "VERIFIED",
        "ACCESS_RESTRICTED",
        "INACCESSIBLE",
        "FAILED",
        "DEFERRED",
        "NOT_SCANNED",
    }
    actual_names = {s.name for s in SourceState if s.name in expected_names}
    assert actual_names == expected_names

    for name in expected_names:
        assert hasattr(SourceState, name)
        member = getattr(SourceState, name)
        assert member.value == name.lower()
        # Case-insensitive resolution
        assert SourceState(name) == member
        assert SourceState(name.lower()) == member


def test_source_state_backward_compatibility_aliases():
    """Verify legacy source states map to canonical lifecycle states without breaking."""
    assert SourceState("unavailable") == SourceState.INACCESSIBLE
    assert SourceState("rate_limited") == SourceState.ACCESS_RESTRICTED
    assert SourceState("security_blocked") == SourceState.ACCESS_RESTRICTED
    assert SourceState("unsupported") == SourceState.INACCESSIBLE
    assert SourceState("parse_failed") == SourceState.FAILED
    assert SourceState("timeout") == SourceState.INACCESSIBLE
    assert SourceState("too_large") == SourceState.ACCESS_RESTRICTED

    assert SourceState.UNAVAILABLE == SourceState.INACCESSIBLE
    assert SourceState.RATE_LIMITED == SourceState.ACCESS_RESTRICTED
    assert SourceState.SECURITY_BLOCKED == SourceState.ACCESS_RESTRICTED
    assert SourceState.UNSUPPORTED == SourceState.INACCESSIBLE
    assert SourceState.PARSE_FAILED == SourceState.FAILED
    assert SourceState.TIMEOUT == SourceState.INACCESSIBLE
    assert SourceState.TOO_LARGE == SourceState.ACCESS_RESTRICTED


def test_db_persistence_marks_manifest_sources_as_declared_not_observed():
    """Requirement: Candidate sources must be marked DECLARED, not OBSERVED before verification."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    manifest = CandidateManifest(
        display_name="Alice Developer",
        claimed_skills=["Python", "FastAPI"],
        github_urls=["https://github.com/alicedev/project"],
        portfolio_urls=["https://alicedev.com"],
        deployment_urls=["https://api.alicedev.com"],
        project_claims=[],
    )

    candidate = save_candidate(session, uuid4(), manifest)

    sources = session.query(models.CandidateSource).filter_by(candidate_id=candidate.id).all()
    assert len(sources) == 3
    for src in sources:
        assert src.state == SourceState.DECLARED.value, (
            f"Source {src.source_url} must have state 'declared', got '{src.state}'"
        )
        assert src.state != SourceState.OBSERVED.value


def test_db_persistence_marks_supplied_github_identity_as_unverified():
    """Requirement: Supplying a GitHub URL does NOT mark identity as verified.

    Never mark declared identity verified merely because the URL exists.
    """
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    manifest = CandidateManifest(
        display_name="Alice Developer",
        claimed_skills=["Go"],
        github_urls=["https://github.com/alicedev"],
        project_claims=[],
    )

    candidate = save_candidate(session, uuid4(), manifest)

    identities = session.query(models.Identity).filter_by(candidate_id=candidate.id).all()
    assert len(identities) == 1
    ident = identities[0]
    assert ident.platform == "github"
    assert ident.identifier == "alicedev"
    assert ident.is_verified is False, "Supplied GitHub identity must not be marked verified on intake"


def test_identity_verification_is_separate_from_source_accessibility():
    """Requirement: Identity verification must be separate from source accessibility.

    A public repository being accessible or observed does not verify candidate identity.
    """
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    manifest = CandidateManifest(
        display_name="Bob Engineer",
        github_urls=["https://github.com/bobeng/repo"],
        project_claims=[],
    )

    candidate = save_candidate(session, uuid4(), manifest)

    # Simulate source transitioning from DECLARED to OBSERVED during acquisition
    source = session.query(models.CandidateSource).filter_by(candidate_id=candidate.id).first()
    source.state = SourceState.OBSERVED.value
    session.flush()

    # Identity must REMAIN unverified
    ident = session.query(models.Identity).filter_by(candidate_id=candidate.id).first()
    assert ident.is_verified is False, (
        "Observing source code in a public repository does not verify human authorship or identity"
    )


def test_candidate_source_model_default_state_is_declared():
    """Requirement: CandidateSource model default state must be 'declared'."""
    src = models.CandidateSource(
        candidate_id=uuid4(),
        source_family="github",
        source_url="https://github.com/test/repo",
    )
    assert src.state == SourceState.DECLARED.value
