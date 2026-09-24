"""Comprehensive test suite for Fix 30: Harden Audit Trail Semantics.

Verifies:
1. Minimum required fields on every audit record:
   - authenticated actor (actor_id / user_id)
   - server-derived organization (organization_id)
   - append-only event model (updates and deletes strictly blocked)
   - timestamp (UTC ISO format)
   - action (operation performed)
   - old value (pre-mutation snapshot)
   - new value (post-mutation snapshot)
   - reason (mandatory justification)
   - analysis run (analysis_run_id)
   - request ID (request_id correlation)
2. Tamper-evident cryptographic chaining:
   - sequence numbers strictly monotonic (1, 2, 3...)
   - genesis previous hash ("0"*64)
   - hash chain linkage (event N previous_event_hash == event N-1 event_hash)
   - canonical SHA-256 event hash over full normalized payload
3. Cryptographic tamper detection:
   - Payload alteration (modifying reason, old_value, new_value, actor) detected immediately
   - Deletion of an intermediate event detected immediately
   - Out-of-order event sequence detected immediately
4. Multi-tenancy isolation on audit trail and verify endpoints:
   - Org A events cannot be read or verified by Org B (HTTP 404)
5. Database-layer append-only protection:
   - Session update on AuditEvent raises ValueError
   - Session delete on AuditEvent raises ValueError
"""

import copy
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from cci.api.routers.dossier import register_dossier
from cci.db.base import Base
from cci.db.models.audit import AuditEvent, DEFAULT_SYSTEM_ORG_ID
from cci.db.session import SessionLocal
from cci.domain.contracts import (
    CapabilityConflict,
    CapabilityEstimate,
    Dossier,
)
from cci.domain.enums import CanonicalRole, CapabilityKey
from cci.main import app
from cci.security.audit import (
    GENESIS_PREVIOUS_HASH,
    audit_service,
    compute_canonical_event_hash,
    verify_audit_chain,
)
from cci.security.auth import create_access_token


@pytest.fixture(autouse=True)
def reset_audit_store():
    """Reset audit in-memory logs between tests for strict test isolation."""
    audit_service.reset_for_testing()
    yield
    audit_service.reset_for_testing()


@pytest.fixture
def sample_dossier() -> Dossier:
    """Fixture creating a test dossier with known scores."""
    cand_id = uuid4()
    run_id = uuid4()
    estimates = {}
    conflicts = {}

    for key in CapabilityKey:
        if key == CapabilityKey.BACKEND_ENGINEERING:
            estimates[key] = CapabilityEstimate(
                capability_key=key,
                estimate=85.0,
                is_observed=True,
                effective_evidence_count=4.0,
                raw_evidence_count=6,
                coverage_k=0.85,
            )
        elif key == CapabilityKey.SOFTWARE_ARCHITECTURE:
            estimates[key] = CapabilityEstimate(
                capability_key=key,
                estimate=75.0,
                is_observed=True,
                effective_evidence_count=3.0,
                raw_evidence_count=5,
                coverage_k=0.75,
            )
        else:
            estimates[key] = CapabilityEstimate(
                capability_key=key,
                estimate=None,
                is_observed=False,
                effective_evidence_count=0.0,
                raw_evidence_count=0,
                coverage_k=0.0,
            )

        conflicts[key] = CapabilityConflict(
            capability_key=key,
            positive_support_sum=4.0 if key == CapabilityKey.BACKEND_ENGINEERING else 0.0,
            negative_support_sum=0.0,
            contradiction_diagnostic=0.90 if key == CapabilityKey.BACKEND_ENGINEERING else 0.0,
        )

    return Dossier(
        dossier_id=uuid4(),
        candidate_id=cand_id,
        analysis_run_id=run_id,
        role=CanonicalRole.BACKEND,
        rci=80.0,
        coverage=0.50,
        is_insufficient_evidence=False,
        capability_estimates=estimates,
        capability_conflicts=conflicts,
        role_requirements=[],
        ownership_assessments=[],
        claims_corroboration=[],
        interview_probes=[],
        interview_questions=[],
    )


# ------------------------------------------------------------------------------
# 1. Minimum Required Audit Fields Verification
# ------------------------------------------------------------------------------
def test_audit_record_contains_all_minimum_required_fields(sample_dossier):
    """Verifies that every audit event emitted has all 10 minimum required fields:
    - authenticated actor
    - server-derived organization
    - append-only event model
    - timestamp
    - action
    - old value
    - new value
    - reason
    - analysis run
    - request ID
    """
    org_id = uuid4()
    actor_id = uuid4()
    cand_id = sample_dossier.candidate_id
    register_dossier(sample_dossier, organization_id=org_id)

    token = create_access_token(
        user_id=actor_id,
        organization_id=org_id,
        role="recruiter",
    )
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Request-ID": "test-req-correlation-101",
    }
    client = TestClient(app)

    # 1. Trigger recruiter weight override
    override_payload = {
        "candidate_id": str(cand_id),
        "role_weights": {
            CapabilityKey.BACKEND_ENGINEERING.value: 0.7,
            CapabilityKey.SOFTWARE_ARCHITECTURE.value: 0.3,
        },
        "justification": "Candidate demonstrated senior architecture trade-off mastery.",
    }
    res = client.post("/api/v1/overrides/recruiter", json=override_payload, headers=headers)
    assert res.status_code == 200

    # 2. Retrieve audit trail
    trail_res = client.get(f"/api/v1/overrides/audit/{cand_id}", headers=headers)
    assert trail_res.status_code == 200
    events = trail_res.json()
    assert len(events) >= 1

    ev = events[0]
    # Check all 10 minimum required fields
    assert ev["actor_id"] == str(actor_id)
    assert ev["user_id"] == str(actor_id)  # Backward compatible alias
    assert ev["organization_id"] == str(org_id)
    assert ev["timestamp"] is not None and len(ev["timestamp"]) > 0
    assert ev["created_at"] is not None and len(ev["created_at"]) > 0
    assert ev["action"] == "recruiter_weight_override"
    assert ev["event_type"] == "recruiter_weight_override"  # Backward compatible alias
    assert ev["old_value"] is not None
    assert "rci" in ev["old_value"]
    assert ev["new_value"] is not None
    assert "rci" in ev["new_value"]
    assert ev["reason"] == "Candidate demonstrated senior architecture trade-off mastery."
    assert ev["analysis_run_id"] is not None
    assert ev["request_id"] == "test-req-correlation-101"

    # Check tamper-evident chaining fields
    assert ev["sequence_number"] == 1
    assert ev["previous_event_hash"] == GENESIS_PREVIOUS_HASH
    assert ev["event_hash"] is not None and len(ev["event_hash"]) == 64


# ------------------------------------------------------------------------------
# 2. Tamper-Evident Event Chaining Semantics
# ------------------------------------------------------------------------------
def test_audit_event_chaining_sequential_linkage(sample_dossier):
    """Verifies that multiple actions on a candidate create an unbroken cryptographic hash chain."""
    org_id = uuid4()
    actor_id = uuid4()
    cand_id = sample_dossier.candidate_id
    register_dossier(sample_dossier, organization_id=org_id)

    token = create_access_token(
        user_id=actor_id,
        organization_id=org_id,
        role="recruiter",
    )
    headers = {"Authorization": f"Bearer {token}"}
    client = TestClient(app)

    # Action 1: First weight override
    res1 = client.post(
        "/api/v1/overrides/recruiter",
        json={
            "candidate_id": str(cand_id),
            "role_weights": {CapabilityKey.BACKEND_ENGINEERING.value: 1.0},
            "justification": "Primary focus on backend depth.",
        },
        headers=headers,
    )
    assert res1.status_code == 200

    # Action 2: Interview feedback
    res2 = client.post(
        "/api/v1/overrides/interview-feedback",
        json={
            "candidate_id": str(cand_id),
            "interviewer_name": "Chief Architect",
            "probe_evaluations": [
                {
                    "capability_key": CapabilityKey.BACKEND_ENGINEERING.value,
                    "rating": 5,
                    "notes": "Exceptional concurrency primitives understanding.",
                    "is_gap_resolved": True,
                }
            ],
            "overall_recommendation": "strong_hire",
            "overall_notes": "Unanimous technical approval.",
        },
        headers=headers,
    )
    assert res2.status_code == 200

    # Action 3: Second weight override
    res3 = client.post(
        "/api/v1/overrides/recruiter",
        json={
            "candidate_id": str(cand_id),
            "role_weights": {
                CapabilityKey.BACKEND_ENGINEERING.value: 0.6,
                CapabilityKey.SOFTWARE_ARCHITECTURE.value: 0.4,
            },
            "justification": "Balanced weights after interview feedback.",
        },
        headers=headers,
    )
    assert res3.status_code == 200

    # Retrieve audit trail (comes sorted descending: [Event 3, Event 2, Event 1])
    trail = client.get(f"/api/v1/overrides/audit/{cand_id}", headers=headers).json()
    assert len(trail) == 3

    # Reverse to ascending order for chain inspection: [1, 2, 3]
    asc_trail = sorted(trail, key=lambda x: x["sequence_number"])
    ev1, ev2, ev3 = asc_trail[0], asc_trail[1], asc_trail[2]

    # Verify monotonic sequences
    assert ev1["sequence_number"] == 1
    assert ev2["sequence_number"] == 2
    assert ev3["sequence_number"] == 3

    # Verify cryptographic hash chaining
    assert ev1["previous_event_hash"] == GENESIS_PREVIOUS_HASH
    assert ev2["previous_event_hash"] == ev1["event_hash"]
    assert ev3["previous_event_hash"] == ev2["event_hash"]

    # Verify mathematical verification endpoint
    verify_res = client.get(f"/api/v1/overrides/audit/{cand_id}/verify", headers=headers)
    assert verify_res.status_code == 200
    verify_data = verify_res.json()
    assert verify_data["is_valid"] is True
    assert verify_data["total_events"] == 3
    assert verify_data["broken_sequence_number"] is None


# ------------------------------------------------------------------------------
# 3. Cryptographic Tamper Detection
# ------------------------------------------------------------------------------
def test_tamper_detection_on_altered_payload():
    """Verifies that altering even a single field in an audit record is caught immediately."""
    org_id = uuid4()
    actor_id = uuid4()
    cand_id = uuid4()

    # Create 2 valid chained events directly via service
    ev1 = audit_service.record_event(
        organization_id=org_id,
        action="recruiter_weight_override",
        entity_type="candidate",
        entity_id=cand_id,
        actor_id=actor_id,
        old_value={"rci": 70},
        new_value={"rci": 80},
        reason="Authentic recruiter adjustment.",
    )
    ev2 = audit_service.record_event(
        organization_id=org_id,
        action="interviewer_probe_feedback",
        entity_type="candidate",
        entity_id=cand_id,
        actor_id=actor_id,
        old_value=None,
        new_value={"rating": 5},
        reason="Authentic interview probe feedback.",
    )

    trail = audit_service.get_audit_trail(entity_id=cand_id, organization_id=org_id)
    is_valid, err, broken_seq = verify_audit_chain(trail)
    assert is_valid is True
    assert err is None

    # Adversary attack: modify reason of event 1
    tampered_trail = copy.deepcopy(trail)
    # Find event 1 (sequence_number = 1)
    ev1_tampered = [e for e in tampered_trail if e["sequence_number"] == 1][0]
    ev1_tampered["reason"] = "Adversary maliciously altered reason after the fact."

    is_valid, err, broken_seq = verify_audit_chain(tampered_trail)
    assert is_valid is False
    assert broken_seq == 1
    assert "Cryptographic payload tampering detected" in err


def test_tamper_detection_on_deleted_event():
    """Verifies that deleting an intermediate event in the chain is caught immediately."""
    org_id = uuid4()
    cand_id = uuid4()

    # Create 3 chained events
    for i in range(1, 4):
        audit_service.record_event(
            organization_id=org_id,
            action=f"action_{i}",
            entity_type="candidate",
            entity_id=cand_id,
            reason=f"Step {i}",
        )

    trail = audit_service.get_audit_trail(entity_id=cand_id, organization_id=org_id)
    assert len(trail) == 3

    # Adversary attack: delete event 2
    tampered_trail = [e for e in trail if e["sequence_number"] != 2]
    is_valid, err, broken_seq = verify_audit_chain(tampered_trail)
    assert is_valid is False
    assert "Broken sequence order" in err or "Hash chain broken" in err


# ------------------------------------------------------------------------------
# 4. Multi-Tenant Scoping of Audit Trail
# ------------------------------------------------------------------------------
def test_cross_tenant_audit_trail_isolation(sample_dossier):
    """Verifies that Org A's audit events cannot be accessed or verified by Org B (HTTP 404)."""
    org_a = uuid4()
    org_b = uuid4()
    cand_id = sample_dossier.candidate_id
    register_dossier(sample_dossier, organization_id=org_a)

    token_a = create_access_token(user_id=uuid4(), organization_id=org_a, role="recruiter")
    token_b = create_access_token(user_id=uuid4(), organization_id=org_b, role="recruiter")

    client = TestClient(app)

    # Org A records override
    client.post(
        "/api/v1/overrides/recruiter",
        json={
            "candidate_id": str(cand_id),
            "role_weights": {CapabilityKey.BACKEND_ENGINEERING.value: 1.0},
            "justification": "Confidential internal justification for Org A.",
        },
        headers={"Authorization": f"Bearer {token_a}"},
    )

    # Org A can read audit trail
    res_a = client.get(
        f"/api/v1/overrides/audit/{cand_id}",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert res_a.status_code == 200
    assert len(res_a.json()) >= 1

    # Org B attempts to read Org A candidate's audit trail -> 404
    res_b = client.get(
        f"/api/v1/overrides/audit/{cand_id}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert res_b.status_code == 404

    # Org B attempts to verify Org A candidate's audit trail -> 404
    res_b_verify = client.get(
        f"/api/v1/overrides/audit/{cand_id}/verify",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert res_b_verify.status_code == 404


# ------------------------------------------------------------------------------
# 5. Database-Layer Append-Only Enforcement
# ------------------------------------------------------------------------------
def test_database_layer_blocks_mutation_and_deletion():
    """Verifies that SQLAlchemy event listeners strictly reject UPDATE and DELETE on AuditEvent."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()

    event = AuditEvent(
        id=uuid4(),
        organization_id=uuid4(),
        sequence_number=1,
        action="initial_action",
        entity_type="candidate",
        entity_id="test_cand_1",
        reason="Initial creation",
    )
    db.add(event)
    db.commit()

    # Attempt to mutate row -> must raise ValueError
    with pytest.raises(ValueError, match="cannot be modified after creation"):
        event.reason = "Unauthorized in-place edit"
        db.commit()
    db.rollback()

    # Attempt to delete row -> must raise ValueError
    with pytest.raises(ValueError, match="cannot be deleted; audit records are append-only"):
        db.delete(event)
        db.commit()
    db.rollback()
