"""Stable semantic identities for correlated evidence observations."""

from dataclasses import dataclass
import hashlib
import json
from urllib.parse import urlsplit

from cci.domain.enums import CapabilityKey, SourceFamily


@dataclass(frozen=True)
class EvidenceFamilyIdentity:
    """A stable family ID plus the semantic inputs needed to audit its basis."""

    evidence_family_id: str
    basis: dict[str, str]


def normalize_source_cluster(
    source_family: SourceFamily,
    identity: str,
) -> str:
    """Canonicalizes a source-family and cluster pair for scoring and identity."""
    family = getattr(source_family, "value", source_family)
    normalized_identity = (identity or "").strip()
    try:
        parsed = urlsplit(normalized_identity)
        if parsed.scheme and parsed.netloc:
            host = (parsed.hostname or parsed.netloc).casefold()
            port = parsed.port
            if port and not (
                (parsed.scheme.casefold() == "https" and port == 443)
                or (parsed.scheme.casefold() == "http" and port == 80)
            ):
                host = f"{host}:{port}"
            path = parsed.path.rstrip("/")
            if host.casefold().split(":", 1)[0] in {"github.com", "www.github.com"}:
                host = "github.com"
                path = path.casefold()
                if path.endswith(".git"):
                    path = path[:-4]
            normalized_identity = f"{host}{path}"
        else:
            normalized_identity = normalized_identity.casefold()
    except ValueError:
        normalized_identity = normalized_identity.casefold()

    return f"{family}:{normalized_identity}"


def normalize_family_subject(fact_domain: str, subject: str) -> str:
    """Normalizes only distinctions that are semantically irrelevant in a domain."""
    domain = fact_domain.strip().casefold()
    value = subject.strip()
    if domain == "dependency":
        return value.casefold()
    if domain == "route":
        parts = value.split("|", 2)
        if len(parts) == 3:
            method, path, source_construct = parts
            return f"{method.strip().upper()}|{path.strip()}|{source_construct.strip()}"
    return value


def build_evidence_family_identity(
    *,
    source_family: SourceFamily,
    cluster_id: str,
    capability: CapabilityKey,
    fact_domain: str,
    subject: str,
) -> EvidenceFamilyIdentity:
    """Builds a versioned digest from source scope and a domain-normalized fact."""
    normalized_domain = fact_domain.strip().casefold()
    normalized_subject = normalize_family_subject(normalized_domain, subject)
    canonical = {
        "schema": "ef1",
        "source_family": getattr(source_family, "value", source_family),
        "cluster": normalize_source_cluster(source_family, cluster_id),
        "capability": getattr(capability, "value", capability),
        "domain": normalized_domain,
        "subject": normalized_subject,
    }
    serialized = json.dumps(
        canonical,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    family_id = "ef1:" + hashlib.sha256(serialized).hexdigest()
    return EvidenceFamilyIdentity(
        evidence_family_id=family_id,
        basis={
            "schema": "ef1",
            "domain": normalized_domain,
            "subject": normalized_subject,
        },
    )


def build_fallback_evidence_family_identity(
    *,
    source_family: SourceFamily,
    cluster_id: str,
    artifact_path: str | None,
    capability: CapabilityKey,
    observation_type: str,
    fingerprint: str,
) -> EvidenceFamilyIdentity:
    """Builds a conservative family for one analyzer observation identity."""
    normalized_path = (artifact_path or "").replace("\\", "/").strip("/")
    fallback_subject = json.dumps(
        [normalized_path, observation_type.strip(), fingerprint.strip().casefold()],
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return build_evidence_family_identity(
        source_family=source_family,
        cluster_id=cluster_id,
        capability=capability,
        fact_domain="observation_fallback",
        subject=fallback_subject,
    )
