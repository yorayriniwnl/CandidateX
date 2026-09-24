"""Unit tests for Fix 38: Upgraded Certificate Verification and Provider Adapters."""

import pytest

from cci.domain.enums import CredentialState
from cci.credentials.verification import (
    CredlyAdapter,
    CourseraAdapter,
    HackerRankAdapter,
    GenericPublicPageAdapter,
    verify_credential_claim,
    verify_all_credentials,
)


class TestCredentialStatesAndAdapters:
    def test_resume_only_state(self):
        # Claim with no sources or declared URLs
        res = verify_credential_claim(
            claim="AWS Certified Solutions Architect",
            candidate_name="Alice Chen",
            sources=[],
            declared_urls=[],
        )
        assert res.state == CredentialState.RESUME_ONLY
        assert res.training_and_exposure_only is True
        assert res.practical_mastery_inferred is False
        assert "training/exposure" in res.explanation

    def test_credly_adapter_issuer_verified(self):
        adapter = CredlyAdapter()
        url = "https://www.credly.com/badges/abc-1234-def567"
        assert adapter.can_handle(url) is True

        source = {
            "url": url,
            "status": "observed",
            "title": "AWS Certified Solutions Architect - Associate was issued by Amazon Web Services Training and Certification to Alice Chen",
            "excerpt": "This badge was issued to Alice Chen on Oct 10, 2024. Skills: Cloud Architecture, AWS Services.",
        }

        res = adapter.verify(url, source, candidate_name="Alice Chen", claim="AWS Certified Solutions Architect")
        assert res.state == CredentialState.ISSUER_VERIFIED
        assert res.provider == "credly"
        assert res.credential_id == "abc-1234-def567"
        assert res.recipient_name == "Alice Chen"
        assert res.issuer == "Credly"
        assert res.training_and_exposure_only is True
        assert res.practical_mastery_inferred is False

    def test_credly_adapter_expired(self):
        adapter = CredlyAdapter()
        url = "https://www.credly.com/badges/badge-expired-999"
        source = {
            "url": url,
            "status": "observed",
            "title": "CompTIA Security+ - Alice Chen",
            "excerpt": "Status: Expired on January 15, 2023. This certification is no longer active.",
        }

        res = adapter.verify(url, source, candidate_name="Alice Chen", claim="CompTIA Security+")
        assert res.state == CredentialState.EXPIRED
        assert res.expires_at == "January 15, 2023"

    def test_credly_adapter_revoked(self):
        adapter = CredlyAdapter()
        url = "https://www.credly.com/badges/badge-revoked-001"
        source = {
            "url": url,
            "status": "observed",
            "title": "Certified Developer - Alice Chen",
            "excerpt": "This badge was revoked by the issuing authority.",
        }

        res = adapter.verify(url, source, candidate_name="Alice Chen", claim="Certified Developer")
        assert res.state == CredentialState.REVOKED

    def test_credly_adapter_inaccessible(self):
        adapter = CredlyAdapter()
        url = "https://www.credly.com/badges/secret-badge"
        source = {
            "url": url,
            "status": "access_restricted",
            "detail": "Login gate prevents inspection.",
        }

        res = adapter.verify(url, source, candidate_name="Alice Chen", claim="Secret Cert")
        assert res.state == CredentialState.INACCESSIBLE

    def test_coursera_adapter_issuer_verified(self):
        adapter = CourseraAdapter()
        url = "https://www.coursera.org/verify/COURSE12345"
        assert adapter.can_handle(url) is True

        source = {
            "url": url,
            "status": "observed",
            "title": "Coursera Course Certificate | Deep Learning Specialization",
            "excerpt": "Coursera verifies that Alice Chen successfully completed Deep Learning Specialization.",
        }

        res = adapter.verify(url, source, candidate_name="Alice Chen", claim="Deep Learning Specialization")
        assert res.state == CredentialState.ISSUER_VERIFIED
        assert res.credential_id == "COURSE12345"
        assert res.recipient_name == "Alice Chen"
        assert res.issuer == "Coursera"

    def test_hackerrank_adapter(self):
        adapter = HackerRankAdapter()
        url = "https://www.hackerrank.com/certificates/abcd9876ef"
        assert adapter.can_handle(url) is True

        source = {
            "url": url,
            "status": "observed",
            "title": "HackerRank Skill Certification - Problem Solving",
            "excerpt": "This certifies that Alice Chen has passed the Problem Solving (Advanced) assessment.",
        }

        res = adapter.verify(url, source, candidate_name="Alice Chen", claim="Problem Solving Advanced")
        assert res.state == CredentialState.ISSUER_VERIFIED
        assert res.credential_id == "abcd9876ef"

    def test_generic_adapter_public_page_match_vs_recipient_match(self):
        adapter = GenericPublicPageAdapter()
        url = "https://example.org/cert-directory"

        # Topic match only (candidate name missing)
        source_topic_only = {
            "url": url,
            "status": "observed",
            "title": "Kubernetes Administrator Certification Exam Guide",
            "excerpt": "Comprehensive overview of the Certified Kubernetes Administrator exam requirements.",
        }
        res_topic = adapter.verify(url, source_topic_only, candidate_name="Alice Chen", claim="Certified Kubernetes Administrator")
        assert res_topic.state == CredentialState.PUBLIC_PAGE_MATCH

        # Recipient name match
        source_with_name = {
            "url": url,
            "status": "observed",
            "title": "Certified Kubernetes Administrator Verification Record",
            "excerpt": "Recipient: Alice Chen. Certification ID: CKA-98765432-ABCD. Passed in 2024.",
        }
        res_name = adapter.verify(url, source_with_name, candidate_name="Alice Chen", claim="Certified Kubernetes Administrator")
        assert res_name.state == CredentialState.RECIPIENT_MATCH
        assert res_name.credential_id == "CKA-98765432-ABCD"

    def test_generic_adapter_credential_id_match_only(self):
        adapter = GenericPublicPageAdapter()
        url = "https://issuer.com/verify?id=CKA-1122-3344"
        source = {
            "url": url,
            "status": "observed",
            "title": "Certificate Registry",
            "excerpt": "Showing status for credential identifier CKA-1122-3344. Active.",
        }
        res = adapter.verify(url, source, candidate_name="Bob Smith", claim="Certified Kubernetes Administrator")
        assert res.state == CredentialState.CREDENTIAL_ID_MATCH

    def test_verify_all_credentials_multiclaim(self):
        claims = [
            "AWS Certified Developer",
            "Certified Kubernetes Administrator",
            "Scrum Master",
        ]
        sources = [
            {
                "url": "https://www.credly.com/badges/aws-dev-1",
                "status": "observed",
                "title": "AWS Certified Developer - Alice Chen",
                "excerpt": "Issued to Alice Chen by Amazon Web Services.",
            },
            {
                "url": "https://example.com/cka",
                "status": "observed",
                "title": "CKA Overview",
                "excerpt": "Learn all about the CKA exam.",
            },
        ]
        results = verify_all_credentials(
            resume_claims=claims,
            candidate_name="Alice Chen",
            sources=sources,
            declared_urls=["https://www.credly.com/badges/aws-dev-1", "https://example.com/cka"],
        )
        assert len(results) == 3
        # 1. AWS -> ISSUER_VERIFIED
        assert results[0].state == CredentialState.ISSUER_VERIFIED
        # 2. CKA -> PUBLIC_PAGE_MATCH
        assert results[1].state == CredentialState.PUBLIC_PAGE_MATCH
        # 3. Scrum Master -> RESUME_ONLY
        assert results[2].state == CredentialState.RESUME_ONLY
