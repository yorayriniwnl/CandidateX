"""Unit tests for Fix 40: Rebuilding Project Dossiers into Traceable Entities."""

from uuid import uuid4
import pytest

from cci.domain.contracts import EvidenceConfidenceFactors, EvidenceRecord, ProjectEntity
from cci.domain.enums import CapabilityKey, SourceFamily
from cci.projects.dossier import (
    build_project_entities,
    extract_quantitative_claims,
)


class TestProjectEntityRebuild:
    def test_extract_quantitative_claims(self):
        text = (
            "Built distributed payment gateway handling 10k users and 5B tokens with 99.9% uptime. "
            "Achieved 5ms latency, reduced latency by 40%, and created 500 tests across 20 deployed projects."
        )
        claims = extract_quantitative_claims(text)
        assert len(claims) >= 5

        metrics = {c["metric"]: c for c in claims}
        assert "uptime" in metrics
        assert metrics["uptime"]["value"] == 99.9
        assert metrics["uptime"]["unit"] == "%"

        assert "users" in metrics
        assert "10k" in str(metrics["users"]["value"])

        assert "tokens" in metrics
        assert "5b" in str(metrics["tokens"]["value"]).lower()

        assert "latency" in metrics
        assert metrics["latency"]["value"] == 5
        assert metrics["latency"]["unit"] == "ms"

        assert any("40%" in str(c["value"]) for c in claims)
        for c in claims:
            assert c["verification_status"] == "unverified"
            assert c["source"] == "resume_project_claim"

    def test_project_entity_with_all_16_facets(self):
        project_claims = [
            {
                "title": "Cloud Billing Service",
                "description": (
                    "High-performance billing engine with FastAPI and PostgreSQL. Live at https://billing.demo.dev. "
                    "Docker containerized, 95% test coverage with pytest. Published in IEEE paper. arXiv:2401.99999. "
                    "Processed 500k transactions at 15ms latency."
                ),
                "technologies": ["Python", "FastAPI", "PostgreSQL", "Docker", "pytest"],
            }
        ]

        sources = [
            {
                "url": "https://github.com/alice/cloud-billing",
                "kind": "github",
                "status": "observed",
                "is_fork": False,
                "default_branch": "main",
                "repository_review": {
                    "technologies": [
                        {"name": "FastAPI", "path": "src/api/routes.py"},
                        {"name": "PostgreSQL", "path": "src/db/models.py"},
                        {"name": "pytest", "path": "tests/test_billing.py"},
                    ]
                },
                "observed_files": [
                    "README.md",
                    "Dockerfile",
                    "docker-compose.yml",
                    "src/api/routes.py",
                    "src/db/models.py",
                    "src/db/migrations/001_init.sql",
                    "tests/test_billing.py",
                ],
                "artifact_attributions": [
                    {
                        "artifact_path": "src/api/routes.py",
                        "state": "STRONG_ATTRIBUTION",
                        "ownership_score": 0.95,
                    },
                    {
                        "artifact_path": "src/db/models.py",
                        "state": "STRONG_ATTRIBUTION",
                        "ownership_score": 0.90,
                    },
                ],
                "last_activity": "2026-09-20T00:00:00Z",
            },
            {
                "url": "https://billing.demo.dev",
                "kind": "deployment",
                "status": "observed",
            },
        ]

        evidence_records = [
            EvidenceRecord(
                evidence_id=uuid4(),
                fingerprint="fp123456",
                source_family=SourceFamily.GITHUB,
                source_locator="https://github.com/alice/cloud-billing",
                immutable_revision="main_sha_123",
                target_capability=CapabilityKey.BACKEND_ENGINEERING,
                technical_signal_strength=80.0,
                confidence_factors=EvidenceConfidenceFactors(
                    artifact_integrity=1.0,
                    ownership_score=0.95,
                    recency_factor=1.0,
                    verification_level=0.8,
                    depth_specificity=0.7,
                    source_reliability=0.85,
                ),
                confidence=0.82,
                provenance={
                    "artifact_path": "src/api/routes.py",
                    "technology": "FastAPI",
                },
                observation_type="ast_service_routes",
            )
        ]

        credentials = [
            {"credential_name": "AWS Certified Developer", "title": "AWS Certified Developer"}
        ]

        contradictions = [
            {
                "candidate_type": "candidatex.contradiction.coverage_below_claim",
                "scan_scope": {
                    "repository_scope": "https://github.com/alice/cloud-billing",
                },
                "explanation": "Claimed 100% test coverage; observed 95%.",
            }
        ]

        entities = build_project_entities(
            project_claims=project_claims,
            sources=sources,
            evidence_records=evidence_records,
            credentials=credentials,
            contradictions=contradictions,
            candidate_identifier="alice",
        )

        assert len(entities) == 1
        proj = entities[0]
        assert isinstance(proj, ProjectEntity)

        # 1. Resume claim
        assert proj.name == "Cloud Billing Service"
        assert proj.resume_claim["title"] == "Cloud Billing Service"
        assert "FastAPI" in proj.resume_claim["technologies"]

        # 2. Repository
        assert proj.repository is not None
        assert proj.repository["url"] == "https://github.com/alice/cloud-billing"
        assert proj.repository["name"] == "cloud-billing"

        # 3. Deployment
        assert proj.deployment is not None
        assert proj.deployment["url"] == "https://billing.demo.dev"
        assert proj.deployment["reachable"] is True

        # 4. Documentation
        assert proj.documentation["has_readme"] is True
        assert proj.documentation["readme_path"] == "README.md"

        # 5. Technologies
        assert "FastAPI" in proj.technologies
        assert "PostgreSQL" in proj.technologies
        assert "Docker" in proj.technologies

        # 6. DB
        assert len(proj.db) > 0
        db_techs = [d["technology"] for d in proj.db]
        assert "PostgreSQL" in db_techs

        # 7. Backend
        assert len(proj.backend) > 0
        assert any(b["framework"] == "FastAPI" for b in proj.backend)

        # 8. Frontend
        assert isinstance(proj.frontend, list)

        # 9. Tests
        assert proj.tests["has_automated_tests"] is True
        assert proj.tests["test_file_count"] == 1
        assert "tests/test_billing.py" in proj.tests["test_files"]

        # 10. Infrastructure
        assert len(proj.infrastructure) > 0
        infra_components = [i["component"] for i in proj.infrastructure]
        assert "Docker" in infra_components

        # 11. Candidate Attribution
        assert proj.candidate_attribution["attribution_state"] == "STRONG_ATTRIBUTION"
        assert proj.candidate_attribution["ownership_score"] > 0.90
        assert proj.candidate_attribution["author_login"] == "alice"

        # 12. Recency
        assert proj.recency["last_activity"] == "2026-09-20T00:00:00Z"

        # 13. Credentials / Publication relationship
        assert len(proj.credentials_or_publication_relationship) >= 2
        rel_types = [r["type"] for r in proj.credentials_or_publication_relationship]
        assert "publication" in rel_types

        # 14. Quantitative claims
        assert len(proj.quantitative_claims) >= 2
        quant_metrics = {q["metric"]: q for q in proj.quantitative_claims}
        assert "transactions" in quant_metrics
        assert "latency" in quant_metrics

        # 15. Contradictions
        assert len(proj.contradictions) == 1
        assert "coverage_below_claim" in proj.contradictions[0]["candidate_type"]

        # 16. Limitations
        assert len(proj.limitations) >= 3
        assert any("Candidate repository code is inspected statically and never executed" in lim for lim in proj.limitations)

        # Traceability: claim -> source -> artifact -> observation
        assert len(proj.trace) >= 4
        hop_types = [t.link_type for t in proj.trace]
        assert "claim_to_source" in hop_types
        assert "source_to_artifact" in hop_types
        assert "artifact_to_observation" in hop_types

        # Compatibility accessor for report
        d = proj.to_dict()
        assert d["title"] == "Cloud Billing Service"
        assert d["status"] == "linked_sources"
        assert len(d["source_urls"]) == 2

    def test_unlinked_project_remains_declaration_only(self):
        project_claims = [
            {
                "title": "Old University Prototype",
                "description": "Built simple CLI script in C++.",
                "technologies": ["C++"],
            }
        ]
        entities = build_project_entities(
            project_claims=project_claims,
            sources=[],
        )
        assert len(entities) == 1
        proj = entities[0]
        assert proj.repository is None
        assert proj.deployment is None
        assert proj.status == "declaration_only"
        assert proj.candidate_attribution["attribution_state"] == "UNATTRIBUTED"
        assert proj.tests["has_automated_tests"] is False
