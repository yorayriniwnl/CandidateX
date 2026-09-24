"""Deterministic claim identity generation and duplicate-claim detection.

Under Fix 14, claim identity is strictly decoupled from document presentation order
or bullet ordinal. Identity is deterministically derived from:
1. Source document hash (e.g. SHA-256 of originating document);
2. Normalized claim type;
3. Normalized claim text and structured semantics.

Resume ordering and section locations are preserved as metadata.
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from typing import Any
from uuid import UUID, uuid5

# Deterministic namespace for Claim UUID generation
CLAIM_NAMESPACE = UUID("c1a10000-0000-0000-0000-000000000001")

METADATA_KEYS = {
    "ordinal",
    "resume_order",
    "section",
    "source_location",
    "status",
    "verification_state",
    "created_at",
    "duplicate_count",
    "occurrences",
}


def normalize_claim_text(text: str) -> str:
    """Normalize claim text for deterministic comparison and hashing.

    Collapses whitespace, normalizes Unicode (NFKC), and converts to lowercase.
    """
    if not text:
        return ""
    normalized = unicodedata.normalize("NFKC", str(text))
    collapsed = re.sub(r"\s+", " ", normalized).strip().lower()
    return collapsed


def normalize_claim_type(claim_type: str) -> str:
    """Normalize claim type / category."""
    if not claim_type:
        return "skill"
    raw = claim_type.strip().lower()
    aliases = {
        "skills": "skill",
        "projects": "project",
        "credentials": "credential",
        "certifications": "credential",
        "education": "academic",
        "academics": "academic",
        "experiences": "experience",
        "metrics": "metric",
    }
    return aliases.get(raw, raw)


def normalize_structured_semantics(structured: Any | None) -> str:
    """Serialize structured semantics deterministically, omitting positional metadata."""
    if structured is None:
        return ""
    if isinstance(structured, dict):
        cleaned = {
            k: v
            for k, v in structured.items()
            if k not in METADATA_KEYS and v is not None
        }
        if not cleaned:
            return ""
        return json.dumps(cleaned, sort_keys=True, separators=(",", ":"), default=str)
    if isinstance(structured, (list, tuple)):
        return json.dumps(list(structured), sort_keys=True, separators=(",", ":"), default=str)
    return str(structured).strip().lower()


def generate_deterministic_claim_id(
    source_document_hash: str | None,
    claim_type: str,
    text: str,
    structured_semantics: Any | None = None,
) -> str:
    """Generate a semantically stable claim identifier string (e.g. 'clm_<hash>').

    Moving bullet points or reordering resume sections will NOT alter the resulting ID.
    """
    doc_hash = (source_document_hash or "").strip().lower()
    norm_type = normalize_claim_type(claim_type)
    norm_text = normalize_claim_text(text)
    norm_struct = normalize_structured_semantics(structured_semantics)

    payload = f"{doc_hash}\0{norm_type}\0{norm_text}\0{norm_struct}".encode("utf-8")
    digest = hashlib.sha256(payload).hexdigest()
    return "clm_" + digest[:20]


def generate_deterministic_claim_uuid(
    source_document_hash: str | None,
    claim_type: str,
    text: str,
    structured_semantics: Any | None = None,
) -> UUID:
    """Generate a semantically stable RFC 4122 UUID5 for a claim."""
    doc_hash = (source_document_hash or "").strip().lower()
    norm_type = normalize_claim_type(claim_type)
    norm_text = normalize_claim_text(text)
    norm_struct = normalize_structured_semantics(structured_semantics)

    payload = f"{doc_hash}:{norm_type}:{norm_text}:{norm_struct}"
    return uuid5(CLAIM_NAMESPACE, payload)


def detect_duplicate_claims(
    claims: list[dict[str, Any] | Any],
) -> tuple[list[Any], list[dict[str, Any]]]:
    """Detect and consolidate duplicate claims within a collection.

    Returns:
        (unique_claims, duplicate_records)
    """
    seen: dict[str, Any] = {}
    duplicates: list[dict[str, Any]] = []

    for item in claims:
        if isinstance(item, dict):
            cid = item.get("claim_id")
            if not cid:
                cid = generate_deterministic_claim_id(
                    source_document_hash=item.get("source_document_hash"),
                    claim_type=item.get("claim_type") or item.get("category", "skill"),
                    text=item.get("original_text") or item.get("claim", ""),
                    structured_semantics=item.get("structured_value"),
                )
                item["claim_id"] = cid

            if cid in seen:
                primary = seen[cid]
                primary["duplicate_count"] = primary.get("duplicate_count", 0) + 1
                occ = {
                    "section": item.get("section"),
                    "ordinal": item.get("ordinal"),
                    "source_location": item.get("source_location"),
                }
                primary.setdefault("occurrences", []).append(occ)
                duplicates.append({
                    "claim_id": cid,
                    "duplicate_item": item,
                    "primary_location": primary.get("source_location"),
                    "duplicate_location": item.get("source_location"),
                })
            else:
                item.setdefault("duplicate_count", 0)
                item.setdefault("occurrences", [{
                    "section": item.get("section"),
                    "ordinal": item.get("ordinal"),
                    "source_location": item.get("source_location"),
                }])
                seen[cid] = item
        else:
            cid = getattr(item, "claim_id", None)
            cid_str = str(cid) if cid else ""
            if cid_str in seen:
                primary = seen[cid_str]
                if hasattr(primary, "duplicate_count"):
                    primary.duplicate_count += 1
                duplicates.append({
                    "claim_id": cid_str,
                    "duplicate_item": item,
                })
            else:
                seen[cid_str] = item

    return list(seen.values()), duplicates
