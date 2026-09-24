"""Unit tests for Unified Configuration and Semantic Version Families (Fix 33)."""

from uuid import uuid4
from fastapi.testclient import TestClient

from cci.domain.contracts import Dossier
from cci.domain.enums import CanonicalRole
from cci.live_app import app as live_app
from cci.main import app as main_app
from cci.versioning import (
    API_VERSION,
    EVIDENCE_SCHEMA_VERSION,
    SCORING_MODEL_VERSION,
    ANALYZER_VERSION,
    ROLE_ONTOLOGY_VERSION,
    CLAIM_SCHEMA_VERSION,
    SOURCE_RELIABILITY_VERSION,
    PACKAGE_VERSION,
    REQUIRED_VERSION_FAMILIES,
    VersionFamilies,
    build_reproducibility_metadata,
    get_canonical_version_dict,
    validate_dossier_reproducibility,
)
from cci.api.routers.dossier import register_dossier, unregister_dossier
from cci.security.auth import create_access_token


def test_version_families_constants():
    """Validates that all 7 explicit version families are defined and non-empty."""
    assert API_VERSION == "1.0.0"
    assert EVIDENCE_SCHEMA_VERSION == "1.0.0"
    assert SCORING_MODEL_VERSION == "5.1.0"
    assert ANALYZER_VERSION == "1.0.0"
    assert ROLE_ONTOLOGY_VERSION == "1.0.0"
    assert CLAIM_SCHEMA_VERSION == "1.0.0"
    assert SOURCE_RELIABILITY_VERSION == "1.0.0"
    assert PACKAGE_VERSION == "0.1.0"
    assert len(REQUIRED_VERSION_FAMILIES) == 7


def test_version_families_model():
    """Validates VersionFamilies serialization and legacy fallbacks."""
    vf = VersionFamilies()
    d = vf.to_dict()
    assert set(d.keys()) == set(REQUIRED_VERSION_FAMILIES)

    legacy_dict = vf.to_legacy_compat_dict()
    assert legacy_dict["platform_version"] == PACKAGE_VERSION
    assert legacy_dict["scoring_config_version"] == SCORING_MODEL_VERSION
    assert legacy_dict["ontology_version"] == ROLE_ONTOLOGY_VERSION

    # Test reconstruction from pure legacy versions
    legacy_input = {
        "scoring_config_version": "5.0.0",
        "ontology_version": "0.9.0",
    }
    vf_legacy = VersionFamilies.from_dossier_versions(legacy_input)
    assert vf_legacy.scoring_model_version == "5.0.0"
    assert vf_legacy.role_ontology_version == "0.9.0"
    assert vf_legacy.api_version == API_VERSION


def test_validate_dossier_reproducibility():
    """Validates reproducibility checking for canonical and historical dossiers."""
    canonical = get_canonical_version_dict()
    is_rep, missing = validate_dossier_reproducibility(canonical)
    assert is_rep is True
    assert missing == []

    # Historical dossier with legacy keys
    historical = {
        "api_version": "1.0.0",
        "evidence_schema_version": "1.0.0",
        "scoring_config_version": "4.0.0",
        "analyzer_version": "1.0.0",
        "ontology_version": "1.0.0",
        "claim_schema_version": "1.0.0",
        "source_reliability_version": "1.0.0",
    }
    is_rep, missing = validate_dossier_reproducibility(historical)
    assert is_rep is True
    assert missing == []

    # Incomplete versions
    incomplete = {"scoring_model_version": "5.1.0"}
    is_rep, missing = validate_dossier_reproducibility(incomplete)
    assert is_rep is False
    assert len(missing) > 0


def test_dossier_metadata_and_version_families():
    """Verifies that Dossier instances expose explicit version families and audit metadata."""
    cand_id = uuid4()
    run_id = uuid4()
    dossier = Dossier(
        candidate_id=cand_id,
        analysis_run_id=run_id,
        role=CanonicalRole.BACKEND,
        coverage=0.85,
        is_insufficient_evidence=False,
        capability_estimates={},
        capability_conflicts={},
        role_requirements=[],
        ownership_assessments=[],
        claims_corroboration=[],
        interview_probes=[],
        interview_questions=[],
    )

    assert isinstance(dossier.version_families, VersionFamilies)
    assert dossier.version_families.scoring_model_version == SCORING_MODEL_VERSION

    metadata = dossier.metadata
    assert metadata["candidate_id"] == str(cand_id)
    assert metadata["analysis_run_id"] == str(run_id)
    assert metadata["is_reproducible"] is True
    assert "version_families" in metadata
    assert metadata["version_families"]["api_version"] == API_VERSION
    assert "reproducibility_contract" in metadata
    assert "scoring_engine" in metadata["reproducibility_contract"]


def test_health_endpoints_version_families():
    """Verifies that both live_app and main health endpoints report version families."""
    # Test live_app /health
    client_live = TestClient(live_app)
    resp = client_live.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["version"] == API_VERSION
    assert "version_families" in data
    assert data["version_families"]["scoring_model_version"] == SCORING_MODEL_VERSION

    # Test main_app /healthz
    client_main = TestClient(main_app)
    resp_main = client_main.get("/healthz")
    assert resp_main.status_code == 200
    data_main = resp_main.json()
    assert data_main["api_version"] == API_VERSION
    assert "version_families" in data_main
    assert data_main["version_families"]["api_version"] == API_VERSION


def test_dossier_metadata_api_endpoint():
    """Verifies the GET /api/v1/dossier/{candidate_id}/metadata endpoint."""
    cand_id = uuid4()
    org_id = uuid4()
    run_id = uuid4()

    dossier = Dossier(
        candidate_id=cand_id,
        analysis_run_id=run_id,
        role=CanonicalRole.BACKEND,
        coverage=0.9,
        is_insufficient_evidence=False,
        capability_estimates={},
        capability_conflicts={},
        role_requirements=[],
        ownership_assessments=[],
        claims_corroboration=[],
        interview_probes=[],
        interview_questions=[],
    )

    register_dossier(dossier, organization_id=org_id)
    try:
        client = TestClient(main_app)
        token = create_access_token(
            organization_id=org_id,
            user_id=uuid4(),
            role="admin",
        )
        headers = {"Authorization": f"Bearer {token}"}

        resp = client.get(f"/api/v1/dossier/{cand_id}/metadata", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["candidate_id"] == str(cand_id)
        assert data["is_reproducible"] is True
        assert data["version_families"]["scoring_model_version"] == SCORING_MODEL_VERSION
        assert data["reproducibility_contract"]["scoring_engine"] == f"cci-math-core@{SCORING_MODEL_VERSION}"
    finally:
        unregister_dossier(cand_id)
