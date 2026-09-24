"""Unit tests for Fix 41: Quantified Claim Verification and Artifact Grounding."""

import pytest

from cci.claims.quantified import (
    extract_and_verify_all_quantified_claims,
    extract_quantified_claims_from_text,
    verify_quantified_claim,
)
from cci.domain.contracts import QuantifiedClaim


class TestQuantifiedClaimsExtractionAndVerification:
    def test_extract_all_fix41_canonical_claims(self):
        text = (
            "Delivered recommendation engine with 95% accuracy serving 10k users with 5ms latency "
            "and 99.9% uptime. Managed 20 deployed projects processing 5B tokens, authored 500 tests, "
            "and achieved 40% optimization across services."
        )
        claims = extract_quantified_claims_from_text(text)
        assert len(claims) >= 8

        claim_by_metric = {c.metric: c for c in claims}

        # 1. 95% accuracy
        assert "accuracy" in claim_by_metric
        assert claim_by_metric["accuracy"].value == 95
        assert claim_by_metric["accuracy"].unit == "%"

        # 2. 10k users
        assert "users" in claim_by_metric
        assert claim_by_metric["users"].value == "10k"
        assert claim_by_metric["users"].unit == "users"

        # 3. 5ms latency
        assert "latency" in claim_by_metric
        assert claim_by_metric["latency"].value == 5
        assert claim_by_metric["latency"].unit == "ms"

        # 4. 99.9% uptime
        assert "uptime" in claim_by_metric
        assert claim_by_metric["uptime"].value == 99.9
        assert claim_by_metric["uptime"].unit == "%"

        # 5. 20 deployed projects
        assert "deployed_projects" in claim_by_metric or "projects" in claim_by_metric
        proj_claim = claim_by_metric.get("deployed_projects") or claim_by_metric.get("projects")
        assert "20" in str(proj_claim.value)

        # 6. 5B tokens
        assert "tokens" in claim_by_metric
        assert "5b" in str(claim_by_metric["tokens"].value).lower()

        # 7. 500 tests
        assert "tests" in claim_by_metric
        assert "500" in str(claim_by_metric["tests"].value)

        # 8. 40% optimization
        opt_claim = next((c for c in claims if "40" in str(c.value) or "optimization" in c.metric), None)
        assert opt_claim is not None

        # Verify all required fields from Fix 41 specification exist
        for c in claims:
            assert isinstance(c, QuantifiedClaim)
            assert c.metric
            assert c.value is not None
            assert c.unit
            assert c.context
            assert c.source == "resume"
            assert c.verification_status == "unverified"
            assert isinstance(c.supporting_artifacts, list)
            assert len(c.limitations) >= 2

    def test_invariant_do_not_verify_metric_merely_from_portfolio(self):
        """Hardening Invariant: Do not verify a metric merely because the same number appears on a portfolio."""
        claim = QuantifiedClaim(
            metric="users",
            value="10k",
            unit="users",
            context="Served 10k users across North America",
            source="resume",
        )

        sources = [
            {
                "url": "https://janedoe.dev/portfolio",
                "kind": "portfolio",
                "title": "Jane Doe Portfolio",
                "excerpt": "Architected high-scale system that served 10k users with high performance.",
            }
        ]

        verified = verify_quantified_claim(claim, sources)

        # Must NOT be marked as verified or supported_by_artifacts
        assert verified.verification_status != "supported_by_artifacts"
        assert verified.verification_status == "portfolio_mention_only"
        assert any("portfolio" in lim.lower() for lim in verified.limitations)
        assert len(verified.supporting_artifacts) == 0

    def test_technical_artifacts_provide_grounded_support(self):
        """Hardening Invariant: Look for independent or technical supporting artifact."""
        # 1. Tests claim supported by real test files in repo
        test_claim = QuantifiedClaim(
            metric="tests",
            value="500",
            unit="tests",
            context="Created 500 tests across suite",
            source="resume",
        )
        sources_with_tests = [
            {
                "url": "https://github.com/org/repo",
                "kind": "github",
                "observed_files": [
                    "tests/unit/test_api.py",
                    "tests/integration/test_db.py",
                    "pytest.ini",
                ],
            }
        ]
        verified_tests = verify_quantified_claim(test_claim, sources_with_tests)
        assert verified_tests.verification_status == "supported_by_artifacts"
        assert len(verified_tests.supporting_artifacts) >= 2
        assert "tests/unit/test_api.py" in verified_tests.supporting_artifacts

        # 2. Performance claim supported by benchmark script
        perf_claim = QuantifiedClaim(
            metric="latency",
            value=5,
            unit="ms",
            context="5ms latency under load",
            source="resume",
        )
        sources_with_benchmark = [
            {
                "url": "https://github.com/org/repo",
                "kind": "github",
                "observed_files": [
                    "benchmarks/locustfile.py",
                    "benchmarks/benchmark_latency.py",
                ],
            }
        ]
        verified_perf = verify_quantified_claim(perf_claim, sources_with_benchmark)
        assert verified_perf.verification_status == "supported_by_artifacts"
        assert "benchmarks/locustfile.py" in verified_perf.supporting_artifacts

        # 3. Deployed projects supported by live deployment source
        deploy_claim = QuantifiedClaim(
            metric="deployed_projects",
            value="20",
            unit="projects",
            context="20 deployed projects",
            source="resume",
        )
        sources_with_deploy = [
            {
                "url": "https://service.live.io",
                "kind": "deployment",
                "status": "observed",
            }
        ]
        verified_deploy = verify_quantified_claim(deploy_claim, sources_with_deploy)
        assert verified_deploy.verification_status == "supported_by_artifacts"
        assert "https://service.live.io" in verified_deploy.supporting_artifacts
