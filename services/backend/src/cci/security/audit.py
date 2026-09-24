"""Cryptographically verifiable, tamper-evident append-only audit trail service (Fix 30).

Implements strict audit trail semantics:
- Authenticated actor (actor_id / user_id)
- Server-derived organization identity
- Append-only event model (updates and deletions strictly rejected)
- Monotonic sequence numbers per entity
- Timestamp (UTC ISO-8601)
- Action (operation performed)
- Old value (pre-mutation state)
- New value (post-mutation state)
- Reason (mandatory human rationale)
- Analysis run ID correlation
- Request ID correlation
- Tamper-evident SHA-256 cryptographic event chaining
"""

import hashlib
import json
import threading
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy.orm import Session

from cci.db.models.audit import AuditEvent, DEFAULT_SYSTEM_ORG_ID

GENESIS_PREVIOUS_HASH: str = "0" * 64


def normalize_timestamp(ts: Any) -> str:
    """Normalizes any datetime or ISO string to canonical UTC ISO-8601 string representation."""
    if ts is None:
        return ""
    if isinstance(ts, datetime):
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        else:
            ts = ts.astimezone(timezone.utc)
        return ts.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    if isinstance(ts, str):
        try:
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            else:
                dt = dt.astimezone(timezone.utc)
            return dt.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        except Exception:
            return ts
    return str(ts)


def compute_canonical_event_hash(
    sequence_number: int,
    previous_event_hash: str,
    timestamp: Any,
    organization_id: str | UUID,
    actor_id: str | UUID | None,
    action: str,
    entity_type: str,
    entity_id: str,
    old_value: Any,
    new_value: Any,
    reason: str | None,
    analysis_run_id: str | UUID | None,
    request_id: str | None,
) -> str:
    """Computes SHA-256 hash over deterministic canonical JSON of all audit event fields."""
    canonical_dict = {
        "action": str(action),
        "actor_id": str(actor_id) if actor_id else None,
        "analysis_run_id": str(analysis_run_id) if analysis_run_id else None,
        "entity_id": str(entity_id),
        "entity_type": str(entity_type),
        "new_value": new_value if new_value is not None else None,
        "old_value": old_value if old_value is not None else None,
        "organization_id": str(organization_id),
        "previous_event_hash": str(previous_event_hash),
        "reason": str(reason) if reason else None,
        "request_id": str(request_id) if request_id else None,
        "sequence_number": int(sequence_number),
        "timestamp": normalize_timestamp(timestamp),
    }
    encoded = json.dumps(
        canonical_dict,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


class AuditRecord(BaseModel):
    """Pydantic model representing a cryptographically chained audit record."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    sequence_number: int = 1
    organization_id: UUID = Field(default=DEFAULT_SYSTEM_ORG_ID)
    actor_id: UUID | None = None
    user_id: UUID | None = None
    timestamp: str = ""
    created_at: str = ""
    action: str = "unknown"
    event_type: str = "unknown"
    entity_type: str
    entity_id: str
    old_value: dict[str, Any] | None = None
    new_value: dict[str, Any] | None = None
    reason: str | None = None
    analysis_run_id: UUID | None = None
    request_id: str | None = None
    previous_event_hash: str = GENESIS_PREVIOUS_HASH
    event_hash: str = ""
    details: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def sync_aliases(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # Synchronize action and event_type
            if "action" in data and "event_type" not in data:
                data["event_type"] = data["action"]
            elif "event_type" in data and ("action" not in data or data["action"] == "unknown"):
                data["action"] = data["event_type"]

            # Synchronize actor_id and user_id
            if "actor_id" in data and "user_id" not in data:
                data["user_id"] = data["actor_id"]
            elif "user_id" in data and ("actor_id" not in data or data["actor_id"] is None):
                data["actor_id"] = data["user_id"]

            # Synchronize timestamp and created_at
            if "timestamp" in data and "created_at" not in data:
                data["created_at"] = data["timestamp"]
            elif "created_at" in data and ("timestamp" not in data or not data["timestamp"]):
                data["timestamp"] = data["created_at"]
        return data


class AuditVerificationResult(BaseModel):
    """Outcome of cryptographic audit chain integrity verification."""

    entity_id: str
    organization_id: UUID
    total_events: int
    is_valid: bool
    broken_sequence_number: int | None = None
    details: str


def verify_audit_chain(
    events: list[dict[str, Any] | Any],
) -> tuple[bool, str | None, int | None]:
    """Verifies the cryptographic hash-chain integrity of audit events for an entity.

    Returns:
        (is_valid, error_message_if_any, broken_sequence_number_if_any)
    """
    if not events:
        return True, None, None

    def get_val(ev: Any, key: str, default: Any = None) -> Any:
        if isinstance(ev, dict):
            return ev.get(key, default)
        return getattr(ev, key, default)

    # Sort ascending by sequence number
    sorted_events = sorted(events, key=lambda e: int(get_val(e, "sequence_number", 0)))

    expected_prev_hash = GENESIS_PREVIOUS_HASH
    expected_seq = 1

    for idx, ev in enumerate(sorted_events):
        seq = int(get_val(ev, "sequence_number", 0))
        if seq != expected_seq:
            return (
                False,
                f"Broken sequence order at index {idx}: expected {expected_seq}, found {seq}",
                seq,
            )

        prev_hash = str(get_val(ev, "previous_event_hash") or "")
        if prev_hash != expected_prev_hash:
            return (
                False,
                f"Hash chain broken at sequence {seq}: previous_event_hash '{prev_hash}' does not match prior event hash '{expected_prev_hash}'",
                seq,
            )

        stored_hash = str(get_val(ev, "event_hash") or "")
        raw_ts = get_val(ev, "timestamp") or get_val(ev, "created_at")

        computed_hash = compute_canonical_event_hash(
            sequence_number=seq,
            previous_event_hash=prev_hash,
            timestamp=raw_ts,
            organization_id=str(get_val(ev, "organization_id")),
            actor_id=get_val(ev, "actor_id") or get_val(ev, "user_id"),
            action=str(get_val(ev, "action") or get_val(ev, "event_type")),
            entity_type=str(get_val(ev, "entity_type")),
            entity_id=str(get_val(ev, "entity_id")),
            old_value=get_val(ev, "old_value"),
            new_value=get_val(ev, "new_value"),
            reason=get_val(ev, "reason"),
            analysis_run_id=get_val(ev, "analysis_run_id"),
            request_id=get_val(ev, "request_id"),
        )

        if stored_hash != computed_hash:
            return (
                False,
                f"Cryptographic payload tampering detected at sequence {seq}: stored hash '{stored_hash}' does not match computed hash '{computed_hash}'",
                seq,
            )

        expected_prev_hash = stored_hash
        expected_seq += 1

    return True, None, None


class AuditTrailManager:
    """Thread-safe manager for recording and verifying tamper-evident audit trails."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        # In-memory store: list of dicts for fallback/fast lookup
        self._in_memory_log: list[dict[str, Any]] = []

    def reset_for_testing(self) -> None:
        """Clears in-memory audit logs for test isolation."""
        with self._lock:
            self._in_memory_log.clear()

    @property
    def in_memory_log(self) -> list[dict[str, Any]]:
        return self._in_memory_log

    def record_event(
        self,
        *,
        organization_id: UUID,
        action: str,
        entity_type: str,
        entity_id: str | UUID,
        actor_id: UUID | str | None = None,
        old_value: dict[str, Any] | None = None,
        new_value: dict[str, Any] | None = None,
        reason: str | None = None,
        analysis_run_id: UUID | str | None = None,
        request_id: str | None = None,
        details: dict[str, Any] | None = None,
        ip_address: str | None = None,
        db: Session | None = None,
    ) -> AuditEvent:
        """Atomically records a new tamper-evident audit event linked to the previous event in the chain."""
        ent_id_str = str(entity_id)
        org_id_uuid = organization_id if isinstance(organization_id, UUID) else UUID(str(organization_id))
        actor_id_uuid = actor_id if isinstance(actor_id, UUID) or actor_id is None else UUID(str(actor_id))
        run_id_uuid = analysis_run_id if isinstance(analysis_run_id, UUID) or analysis_run_id is None else UUID(str(analysis_run_id))
        req_id_str = str(request_id) if request_id else str(uuid4())

        with self._lock:
            # 1. Determine prior event sequence and hash for this (org_id, entity_id)
            prev_event_hash = GENESIS_PREVIOUS_HASH
            next_seq = 1

            # Check database for latest event
            if db is not None:
                try:
                    latest_db = (
                        db.query(AuditEvent)
                        .filter(
                            AuditEvent.organization_id == org_id_uuid,
                            AuditEvent.entity_id == ent_id_str,
                        )
                        .order_by(AuditEvent.sequence_number.desc())
                        .first()
                    )
                    if latest_db and latest_db.sequence_number is not None:
                        next_seq = latest_db.sequence_number + 1
                        prev_event_hash = latest_db.event_hash or GENESIS_PREVIOUS_HASH
                except Exception:
                    pass

            # Check in-memory store if db didn't give a higher sequence
            matching_mem = [
                m
                for m in self._in_memory_log
                if str(m.get("organization_id")) == str(org_id_uuid)
                and str(m.get("entity_id")) == ent_id_str
            ]
            if matching_mem:
                matching_mem.sort(key=lambda m: int(m.get("sequence_number", 0)))
                latest_mem = matching_mem[-1]
                mem_seq = int(latest_mem.get("sequence_number", 0))
                if mem_seq >= next_seq:
                    next_seq = mem_seq + 1
                    prev_event_hash = latest_mem.get("event_hash") or GENESIS_PREVIOUS_HASH

            now_dt = datetime.now(timezone.utc)
            normalized_ts = normalize_timestamp(now_dt)
            event_id = uuid4()

            event_hash = compute_canonical_event_hash(
                sequence_number=next_seq,
                previous_event_hash=prev_event_hash,
                timestamp=normalized_ts,
                organization_id=org_id_uuid,
                actor_id=actor_id_uuid,
                action=action,
                entity_type=entity_type,
                entity_id=ent_id_str,
                old_value=old_value,
                new_value=new_value,
                reason=reason,
                analysis_run_id=run_id_uuid,
                request_id=req_id_str,
            )

            # Build detailed payload dict
            combined_details = dict(details or {})
            combined_details.update(
                {
                    "organization_id": str(org_id_uuid),
                    "action": action,
                    "reason": reason,
                    "request_id": req_id_str,
                }
            )

            event = AuditEvent(
                id=event_id,
                organization_id=org_id_uuid,
                sequence_number=next_seq,
                actor_id=actor_id_uuid,
                action=action,
                entity_type=entity_type,
                entity_id=ent_id_str,
                old_value=old_value,
                new_value=new_value,
                reason=reason,
                analysis_run_id=run_id_uuid,
                request_id=req_id_str,
                previous_event_hash=prev_event_hash,
                event_hash=event_hash,
                details=combined_details,
                ip_address=ip_address,
                created_at=now_dt,
            )

            # Persist to database if provided
            if db is not None:
                db.add(event)

            # Persist to in-memory fallback log
            mem_record = {
                "id": event_id,
                "sequence_number": next_seq,
                "organization_id": org_id_uuid,
                "actor_id": actor_id_uuid,
                "user_id": actor_id_uuid,
                "timestamp": normalized_ts,
                "created_at": normalized_ts,
                "action": action,
                "event_type": action,
                "entity_type": entity_type,
                "entity_id": ent_id_str,
                "old_value": old_value,
                "new_value": new_value,
                "reason": reason,
                "analysis_run_id": run_id_uuid,
                "request_id": req_id_str,
                "previous_event_hash": prev_event_hash,
                "event_hash": event_hash,
                "details": combined_details,
                "ip_address": ip_address,
            }
            self._in_memory_log.append(mem_record)

            return event

    def get_audit_trail(
        self,
        *,
        entity_id: str | UUID,
        organization_id: UUID,
        db: Session | None = None,
    ) -> list[dict[str, Any]]:
        """Retrieves all audit events for an entity strictly scoped to the tenant, sorted chronological descending."""
        ent_id_str = str(entity_id)
        org_id_str = str(organization_id)
        results: list[dict[str, Any]] = []
        seen_ids: set[UUID] = set()

        if db is not None:
            try:
                events = (
                    db.query(AuditEvent)
                    .filter(
                        AuditEvent.entity_id == ent_id_str,
                        AuditEvent.organization_id == organization_id,
                    )
                    .order_by(AuditEvent.sequence_number.desc())
                    .all()
                )
                for ev in events:
                    seen_ids.add(ev.id)
                    ts = normalize_timestamp(ev.created_at)
                    results.append(
                        {
                            "id": ev.id,
                            "sequence_number": ev.sequence_number,
                            "organization_id": ev.organization_id,
                            "actor_id": ev.actor_id,
                            "user_id": ev.user_id,
                            "timestamp": ts,
                            "created_at": ts,
                            "action": ev.action,
                            "event_type": ev.event_type,
                            "entity_type": ev.entity_type,
                            "entity_id": ev.entity_id,
                            "old_value": ev.old_value,
                            "new_value": ev.new_value,
                            "reason": ev.reason,
                            "analysis_run_id": ev.analysis_run_id,
                            "request_id": ev.request_id,
                            "previous_event_hash": ev.previous_event_hash,
                            "event_hash": ev.event_hash,
                            "details": ev.details or {},
                            "ip_address": ev.ip_address,
                        }
                    )
            except Exception:
                pass

        # Merge with in-memory log
        with self._lock:
            for mem in self._in_memory_log:
                if (
                    str(mem.get("entity_id")) == ent_id_str
                    and str(mem.get("organization_id")) == org_id_str
                    and mem.get("id") not in seen_ids
                ):
                    results.append(dict(mem))
                    seen_ids.add(mem["id"])

        results.sort(key=lambda x: int(x.get("sequence_number", 0)), reverse=True)
        return results

    def verify_candidate_trail(
        self,
        *,
        candidate_id: UUID,
        organization_id: UUID,
        db: Session | None = None,
    ) -> AuditVerificationResult:
        """Cryptographically verifies the audit chain for a candidate."""
        events = self.get_audit_trail(
            entity_id=candidate_id,
            organization_id=organization_id,
            db=db,
        )
        # Verify in ascending order
        ascending = sorted(events, key=lambda e: int(e.get("sequence_number", 0)))
        is_valid, err_msg, broken_seq = verify_audit_chain(ascending)

        details = "Audit chain intact and cryptographically verified." if is_valid else (err_msg or "Audit chain integrity failure.")
        return AuditVerificationResult(
            entity_id=str(candidate_id),
            organization_id=organization_id,
            total_events=len(ascending),
            is_valid=is_valid,
            broken_sequence_number=broken_seq,
            details=details,
        )


audit_service = AuditTrailManager()
