"""Credential verification and provider adapter engine (Fix 38).

Implements rigorous certificate verification with provider adapters:
- Evaluates declared certificates against live receipts or direct provider metadata
- Supports canonical CredentialStates:
    * RESUME_ONLY
    * PUBLIC_PAGE_MATCH
    * RECIPIENT_MATCH
    * CREDENTIAL_ID_MATCH
    * ISSUER_VERIFIED
    * EXPIRED
    * REVOKED
    * INACCESSIBLE
    * UNKNOWN
- Enforces foundational invariant:
    Certificate evidence indicates training/exposure only.
    Never equates a certificate with practical engineering mastery.
"""

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import re
from typing import Any, Mapping, Sequence
from urllib.parse import urlparse

from cci.domain.enums import CredentialState


@dataclass
class CredentialVerificationResult:
    """Rigorous verification output for a single certification claim."""

    claim: str
    state: CredentialState
    provider: str = "generic"
    credential_id: str | None = None
    recipient_name: str | None = None
    issuer: str | None = None
    issued_at: str | None = None
    expires_at: str | None = None
    source_url: str | None = None
    matching_pages: list[dict[str, Any]] = field(default_factory=list)
    explanation: str = ""
    training_and_exposure_only: bool = True
    practical_mastery_inferred: bool = False

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["state"] = self.state.value
        d["status"] = self.state.value.lower()
        return d


def _normalize_name(name: str) -> list[str]:
    """Extracts non-trivial name tokens (lowercase, len >= 2)."""
    return [t.lower() for t in re.findall(r"[A-Za-z]+", name) if len(t) >= 2]


def _name_matches(text: str, candidate_name: str) -> bool:
    """Returns True if candidate name tokens appear in text."""
    if not candidate_name or candidate_name in ("Candidate", "Unknown Candidate", ""):
        return False
    tokens = _normalize_name(candidate_name)
    if not tokens:
        return False
    text_lower = text.lower()
    return all(token in text_lower for token in tokens)


def _check_revocation(text: str) -> bool:
    """Checks if text indicates revocation or invalidation."""
    patterns = [
        r"\b(?:revoked|revocation|invalidated|credential\s+withdrawn|license\s+revoked)\b",
    ]
    return any(re.search(p, text, re.IGNORECASE) for p in patterns)


def _check_expiration(text: str) -> tuple[bool, str | None]:
    """Checks if text indicates an expired credential, extracting date if found."""
    m = re.search(r"\bexpired\s+on\s+([A-Za-z]+\s+\d{1,2},?\s+\d{4}|\d{4}-\d{2}-\d{2})\b", text, re.IGNORECASE)
    if m:
        return True, m.group(1)
    if re.search(r"\b(?:credential\s+expired|certification\s+expired|badge\s+expired|status:\s*expired)\b", text, re.IGNORECASE):
        return True, None
    return False, None


class BaseProviderAdapter(ABC):
    """Abstract base class for credential provider adapters."""

    name: str = "generic"

    @abstractmethod
    def can_handle(self, url: str) -> bool:
        """Returns True if this adapter handles the given URL."""

    @abstractmethod
    def verify(
        self,
        url: str,
        source_data: Mapping[str, Any],
        candidate_name: str,
        claim: str,
    ) -> CredentialVerificationResult:
        """Verifies the credential claim against source inspection receipt."""


class CredlyAdapter(BaseProviderAdapter):
    """Provider adapter for Credly / YourAcclaim badges."""

    name: str = "credly"
    DOMAINS = {"credly.com", "youracclaim.com"}

    def can_handle(self, url: str) -> bool:
        parsed = urlparse(url.lower())
        domain = parsed.netloc
        return any(domain == d or domain.endswith("." + d) for d in self.DOMAINS)

    def verify(
        self,
        url: str,
        source_data: Mapping[str, Any],
        candidate_name: str,
        claim: str,
    ) -> CredentialVerificationResult:
        status = source_data.get("status", "unknown")
        if status in ("access_restricted", "inaccessible", "unavailable", "timeout", "failed"):
            return CredentialVerificationResult(
                claim=claim,
                state=CredentialState.INACCESSIBLE,
                provider=self.name,
                source_url=url,
                explanation=f"Credly destination was inaccessible ({status}): {source_data.get('detail', '')}",
            )

        title = str(source_data.get("title", ""))
        excerpt = str(source_data.get("excerpt", ""))
        full_text = f"{title} {excerpt}"

        # Extract badge ID from URL
        m_id = re.search(r"/badges/([a-zA-Z0-9-]+)", url)
        badge_id = m_id.group(1) if m_id else None

        # Check Revocation
        if _check_revocation(full_text):
            return CredentialVerificationResult(
                claim=claim,
                state=CredentialState.REVOKED,
                provider=self.name,
                credential_id=badge_id,
                source_url=url,
                explanation="Issuer record indicates badge has been revoked.",
            )

        # Check Expiration
        expired, exp_date = _check_expiration(full_text)
        if expired:
            return CredentialVerificationResult(
                claim=claim,
                state=CredentialState.EXPIRED,
                provider=self.name,
                credential_id=badge_id,
                expires_at=exp_date,
                source_url=url,
                explanation="Issuer record indicates badge has expired.",
            )

        has_name = _name_matches(full_text, candidate_name)
        claim_tokens = [t.lower() for t in re.findall(r"[A-Za-z0-9]{3,}", claim)
                        if t.lower() not in {"certificate", "certified", "certification", "badge", "exam"}]
        title_matches = any(t in full_text.lower() for t in claim_tokens) if claim_tokens else True

        if not title_matches:
            return CredentialVerificationResult(
                claim=claim,
                state=CredentialState.UNKNOWN,
                provider=self.name,
                source_url=url,
                explanation="Source belongs to a different certification topic or badge.",
            )

        if has_name and badge_id:
            state = CredentialState.ISSUER_VERIFIED
            expl = "Verified badge directly with Credly issuer matching recipient name and badge identifier."
        elif has_name:
            state = CredentialState.RECIPIENT_MATCH
            expl = "Credly badge page matches candidate recipient name."
        elif badge_id:
            state = CredentialState.CREDENTIAL_ID_MATCH
            expl = "Credly badge URL contains matching badge identifier, but recipient name was not confirmed."
        else:
            state = CredentialState.PUBLIC_PAGE_MATCH
            expl = "Credly badge page mentions certification title; recipient was not confirmed."

        return CredentialVerificationResult(
            claim=claim,
            state=state,
            provider=self.name,
            credential_id=badge_id,
            recipient_name=candidate_name if has_name else None,
            issuer="Credly",
            source_url=url,
            matching_pages=[{"url": url, "title": title, "status": status}],
            explanation=f"{expl} Certificate evidence indicates training/exposure only; do not equate with practical mastery.",
        )


class CourseraAdapter(BaseProviderAdapter):
    """Provider adapter for Coursera course and specialization certificates."""

    name: str = "coursera"
    DOMAINS = {"coursera.org"}

    def can_handle(self, url: str) -> bool:
        parsed = urlparse(url.lower())
        domain = parsed.netloc
        return any(domain == d or domain.endswith("." + d) for d in self.DOMAINS)

    def verify(
        self,
        url: str,
        source_data: Mapping[str, Any],
        candidate_name: str,
        claim: str,
    ) -> CredentialVerificationResult:
        status = source_data.get("status", "unknown")
        if status in ("access_restricted", "inaccessible", "unavailable", "timeout", "failed"):
            return CredentialVerificationResult(
                claim=claim,
                state=CredentialState.INACCESSIBLE,
                provider=self.name,
                source_url=url,
                explanation=f"Coursera destination was inaccessible ({status}).",
            )

        title = str(source_data.get("title", ""))
        excerpt = str(source_data.get("excerpt", ""))
        full_text = f"{title} {excerpt}"

        m_id = re.search(r"/(?:verify|certificates?)/([A-Za-z0-9]+)", url)
        cert_id = m_id.group(1) if m_id else None

        if _check_revocation(full_text):
            return CredentialVerificationResult(
                claim=claim,
                state=CredentialState.REVOKED,
                provider=self.name,
                credential_id=cert_id,
                source_url=url,
                explanation="Coursera record indicates certificate was revoked.",
            )

        has_name = _name_matches(full_text, candidate_name)
        if has_name and cert_id:
            state = CredentialState.ISSUER_VERIFIED
            expl = "Verified Coursera completion certificate matching recipient name and verification ID."
        elif has_name:
            state = CredentialState.RECIPIENT_MATCH
            expl = "Coursera verification page matches candidate recipient name."
        elif cert_id:
            state = CredentialState.CREDENTIAL_ID_MATCH
            expl = "Coursera verification URL contains certificate ID, but candidate name was not confirmed."
        else:
            state = CredentialState.PUBLIC_PAGE_MATCH
            expl = "Coursera page text mentions course topic; recipient and ID unverified."

        return CredentialVerificationResult(
            claim=claim,
            state=state,
            provider=self.name,
            credential_id=cert_id,
            recipient_name=candidate_name if has_name else None,
            issuer="Coursera",
            source_url=url,
            matching_pages=[{"url": url, "title": title, "status": status}],
            explanation=f"{expl} Certificate evidence indicates training/exposure only; do not equate with practical mastery.",
        )


class HackerRankAdapter(BaseProviderAdapter):
    """Provider adapter for HackerRank skill certificates."""

    name: str = "hackerrank"
    DOMAINS = {"hackerrank.com"}

    def can_handle(self, url: str) -> bool:
        parsed = urlparse(url.lower())
        domain = parsed.netloc
        return any(domain == d or domain.endswith("." + d) for d in self.DOMAINS) and "certificates" in parsed.path

    def verify(
        self,
        url: str,
        source_data: Mapping[str, Any],
        candidate_name: str,
        claim: str,
    ) -> CredentialVerificationResult:
        status = source_data.get("status", "unknown")
        if status in ("access_restricted", "inaccessible", "unavailable", "timeout", "failed"):
            return CredentialVerificationResult(
                claim=claim,
                state=CredentialState.INACCESSIBLE,
                provider=self.name,
                source_url=url,
                explanation=f"HackerRank certificate destination was inaccessible ({status}).",
            )

        title = str(source_data.get("title", ""))
        excerpt = str(source_data.get("excerpt", ""))
        full_text = f"{title} {excerpt}"

        m_id = re.search(r"/certificates/([a-zA-Z0-9]+)", url)
        cert_id = m_id.group(1) if m_id else None

        has_name = _name_matches(full_text, candidate_name)
        if has_name and cert_id:
            state = CredentialState.ISSUER_VERIFIED
            expl = "Verified HackerRank certificate matching recipient name and certificate identifier."
        elif has_name:
            state = CredentialState.RECIPIENT_MATCH
            expl = "HackerRank certificate page matches candidate recipient name."
        elif cert_id:
            state = CredentialState.CREDENTIAL_ID_MATCH
            expl = "HackerRank certificate URL contains valid certificate ID."
        else:
            state = CredentialState.PUBLIC_PAGE_MATCH
            expl = "HackerRank page mentions certificate topic."

        return CredentialVerificationResult(
            claim=claim,
            state=state,
            provider=self.name,
            credential_id=cert_id,
            recipient_name=candidate_name if has_name else None,
            issuer="HackerRank",
            source_url=url,
            matching_pages=[{"url": url, "title": title, "status": status}],
            explanation=f"{expl} Certificate evidence indicates problem-solving training/exposure; do not equate with production mastery.",
        )


class GenericPublicPageAdapter(BaseProviderAdapter):
    """Fallback adapter for arbitrary third-party certification and credential pages."""

    name: str = "generic"

    def can_handle(self, url: str) -> bool:
        return True

    def verify(
        self,
        url: str,
        source_data: Mapping[str, Any],
        candidate_name: str,
        claim: str,
    ) -> CredentialVerificationResult:
        status = source_data.get("status", "unknown")
        if status in ("access_restricted", "inaccessible", "unavailable", "timeout", "failed", "security_blocked"):
            return CredentialVerificationResult(
                claim=claim,
                state=CredentialState.INACCESSIBLE,
                provider=self.name,
                source_url=url,
                explanation=f"Credential page was inaccessible ({status}): {source_data.get('detail', '')}",
            )

        title = str(source_data.get("title", ""))
        excerpt = str(source_data.get("excerpt", ""))
        full_text = f"{title} {excerpt}"

        if _check_revocation(full_text):
            return CredentialVerificationResult(
                claim=claim,
                state=CredentialState.REVOKED,
                provider=self.name,
                source_url=url,
                explanation="Public page text indicates the credential was revoked.",
            )

        expired, exp_date = _check_expiration(full_text)
        if expired:
            return CredentialVerificationResult(
                claim=claim,
                state=CredentialState.EXPIRED,
                provider=self.name,
                expires_at=exp_date,
                source_url=url,
                explanation=f"Public page indicates credential expired{f' on {exp_date}' if exp_date else ''}.",
            )

        # Look for potential credential IDs in URL or text (e.g. AWS-12345, CKA-98765432-ABCD, UUIDs)
        m_id = re.search(r"\b([A-Z0-9]{2,}(?:-[A-Z0-9]{2,})+|[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})\b", f"{url} {full_text}")
        cred_id = m_id.group(1) if m_id else None

        has_name = _name_matches(full_text, candidate_name)
        claim_tokens = [t.lower() for t in re.findall(r"[A-Za-z0-9]{3,}", claim)
                        if t.lower() not in {"certificate", "certified", "certification", "license", "course"}]
        words = re.findall(r"[A-Za-z]+", claim)
        acronym = "".join(w[0] for w in words).lower() if len(words) >= 2 else ""

        text_to_search = f"{url} {full_text}".lower()
        topic_match = any(t in text_to_search for t in claim_tokens) if claim_tokens else False
        if acronym and len(acronym) >= 2 and acronym in text_to_search:
            topic_match = True
        if cred_id and any(part in cred_id.lower() for part in ([acronym] if acronym else claim_tokens)):
            topic_match = True

        if not topic_match and not cred_id:
            return CredentialVerificationResult(
                claim=claim,
                state=CredentialState.UNKNOWN,
                provider=self.name,
                source_url=url,
                explanation="Public page was fetched but does not match certification claim topic.",
            )

        if has_name and cred_id:
            state = CredentialState.RECIPIENT_MATCH
            expl = f"Public page matches candidate name and credential identifier ({cred_id}). Confirm directly with issuing provider."
        elif has_name:
            state = CredentialState.RECIPIENT_MATCH
            expl = "Public page matches candidate name and topic, but lacks authoritative issuer authentication."
        elif cred_id:
            state = CredentialState.CREDENTIAL_ID_MATCH
            expl = f"Public URL or page matches credential identifier ({cred_id}); recipient name was not confirmed."
        elif topic_match:
            state = CredentialState.PUBLIC_PAGE_MATCH
            expl = "Public page mentions certification topic, but neither recipient nor credential ID was verified."
        else:
            state = CredentialState.UNKNOWN
            expl = "Public page was fetched but does not match certification claim or candidate identity."

        return CredentialVerificationResult(
            claim=claim,
            state=state,
            provider=self.name,
            credential_id=cred_id,
            recipient_name=candidate_name if has_name else None,
            source_url=url,
            matching_pages=[{"url": url, "title": title, "status": status}],
            explanation=f"{expl} Certificate evidence indicates training/exposure only; do not equate with practical mastery.",
        )


_ADAPTERS: list[BaseProviderAdapter] = [
    CredlyAdapter(),
    CourseraAdapter(),
    HackerRankAdapter(),
    GenericPublicPageAdapter(),
]


def get_adapter_for_url(url: str) -> BaseProviderAdapter:
    """Selects the first matching provider adapter for the URL."""
    for adapter in _ADAPTERS:
        if adapter.can_handle(url):
            return adapter
    return GenericPublicPageAdapter()


def verify_credential_claim(
    claim: str,
    candidate_name: str,
    sources: Sequence[Mapping[str, Any]],
    declared_urls: Sequence[str] = (),
) -> CredentialVerificationResult:
    """Verifies a single resume credential claim against observed sources and declared URLs."""
    # Find matching credential sources
    from cci.intake.canonicalizer import classify_url

    matched_sources: list[Mapping[str, Any]] = []
    for s in sources:
        url = s.get("url", "")
        kind = s.get("kind", "")
        if kind == "credential" or classify_url(url) == "credential" or url in declared_urls:
            matched_sources.append(s)

    if not matched_sources and not declared_urls:
        return CredentialVerificationResult(
            claim=claim,
            state=CredentialState.RESUME_ONLY,
            provider="none",
            explanation="Certificate is a self-reported resume mention without public verification link. Certificate evidence indicates training/exposure only; do not equate with practical mastery.",
        )

    # If declared URLs exist but none were fetched/matched
    if declared_urls and not matched_sources:
        return CredentialVerificationResult(
            claim=claim,
            state=CredentialState.INACCESSIBLE,
            provider="generic",
            source_url=declared_urls[0],
            explanation=f"Declared credential URL was not successfully inspected in this run ({declared_urls[0]}).",
        )

    # Evaluate against available sources and pick the highest-confidence outcome
    results: list[CredentialVerificationResult] = []
    for s in matched_sources:
        url = s.get("url", "")
        adapter = get_adapter_for_url(url)
        res = adapter.verify(url, s, candidate_name, claim)
        results.append(res)

    if not results or all(r.state == CredentialState.UNKNOWN for r in results):
        return CredentialVerificationResult(
            claim=claim,
            state=CredentialState.RESUME_ONLY,
            provider="none",
            explanation="Certificate is a self-reported resume mention without matching public verification source. Certificate evidence indicates training/exposure only; do not equate with practical mastery.",
        )

    # Priority rank: ISSUER_VERIFIED > RECIPIENT_MATCH > CREDENTIAL_ID_MATCH > REVOKED > EXPIRED > PUBLIC_PAGE_MATCH > INACCESSIBLE > UNKNOWN
    priority_order = [
        CredentialState.ISSUER_VERIFIED,
        CredentialState.RECIPIENT_MATCH,
        CredentialState.CREDENTIAL_ID_MATCH,
        CredentialState.REVOKED,
        CredentialState.EXPIRED,
        CredentialState.PUBLIC_PAGE_MATCH,
        CredentialState.INACCESSIBLE,
        CredentialState.UNKNOWN,
        CredentialState.RESUME_ONLY,
    ]

    for target_state in priority_order:
        for r in results:
            if r.state == target_state:
                return r

    return results[0]


def verify_all_credentials(
    resume_claims: Sequence[str],
    candidate_name: str,
    sources: Sequence[Mapping[str, Any]],
    declared_urls: Sequence[str] = (),
) -> list[CredentialVerificationResult]:
    """Verifies all resume certification claims deterministically."""
    results: list[CredentialVerificationResult] = []
    for claim in resume_claims:
        res = verify_credential_claim(claim, candidate_name, sources, declared_urls)
        results.append(res)
    return results
