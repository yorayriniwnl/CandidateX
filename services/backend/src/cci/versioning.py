"""Unified configuration, semantic version families, and dossier reproducibility (Fix 33).

Centralizes all version concepts across the Candidate Capability Intelligence platform:
- api_version: Public HTTP REST API version
- evidence_schema_version: CEG evidence node and confidence factor decomposition schema
- scoring_model_version: Mathematical core and RCI aggregation algorithm version
- analyzer_version: Static AST parsers, rule catalog, and extraction engine version
- role_ontology_version: Canonical roles, 12 capabilities, and JD mapping ontology version
- claim_schema_version: CV self-claim decomposition and verification state schema
- source_reliability_version: Empirical source reliability priors and calibration baseline version

Eliminates version and config drift, ensuring that every historical dossier remains
fully reproducible.
"""

from datetime import datetime, timezone
from typing import Any
from pydantic import BaseModel, ConfigDict, Field


# Canonical Core Package Version
PACKAGE_VERSION: str = "0.1.0"

# Explicit Version Families (Fix 33)
API_VERSION: str = "1.0.0"
EVIDENCE_SCHEMA_VERSION: str = "1.0.0"
SCORING_MODEL_VERSION: str = "5.1.0"
ANALYZER_VERSION: str = "1.0.0"
ROLE_ONTOLOGY_VERSION: str = "1.0.0"
CLAIM_SCHEMA_VERSION: str = "1.0.0"
SOURCE_RELIABILITY_VERSION: str = "1.0.0"

# Required family keys for complete reproducibility
REQUIRED_VERSION_FAMILIES: tuple[str, ...] = (
    "api_version",
    "evidence_schema_version",
    "scoring_model_version",
    "analyzer_version",
    "role_ontology_version",
    "claim_schema_version",
    "source_reliability_version",
)


class VersionFamilies(BaseModel):
    """Explicit version families guaranteeing historical dossier reproducibility."""

    model_config = ConfigDict(frozen=True)

    api_version: str = Field(
        default=API_VERSION,
        description="Public HTTP REST API version",
    )
    evidence_schema_version: str = Field(
        default=EVIDENCE_SCHEMA_VERSION,
        description="CEG evidence and confidence decomposition schema version",
    )
    scoring_model_version: str = Field(
        default=SCORING_MODEL_VERSION,
        description="Paper math core and RCI aggregation algorithm version",
    )
    analyzer_version: str = Field(
        default=ANALYZER_VERSION,
        description="Static AST parsers and extraction engine version",
    )
    role_ontology_version: str = Field(
        default=ROLE_ONTOLOGY_VERSION,
        description="Role taxonomy and capability mapping ontology version",
    )
    claim_schema_version: str = Field(
        default=CLAIM_SCHEMA_VERSION,
        description="CV self-claim decomposition and verification state schema version",
    )
    source_reliability_version: str = Field(
        default=SOURCE_RELIABILITY_VERSION,
        description="Empirical source reliability priors and calibration baseline version",
    )

    def to_dict(self) -> dict[str, str]:
        """Dictionary of explicit version families."""
        return {
            "api_version": self.api_version,
            "evidence_schema_version": self.evidence_schema_version,
            "scoring_model_version": self.scoring_model_version,
            "analyzer_version": self.analyzer_version,
            "role_ontology_version": self.role_ontology_version,
            "claim_schema_version": self.claim_schema_version,
            "source_reliability_version": self.source_reliability_version,
        }

    def to_legacy_compat_dict(self) -> dict[str, str]:
        """Provides backward-compatibility mappings alongside explicit version families."""
        d = self.to_dict()
        d["platform_version"] = PACKAGE_VERSION
        d["scoring_config_version"] = self.scoring_model_version
        d["ontology_version"] = self.role_ontology_version
        return d

    @classmethod
    def from_dossier_versions(cls, versions: dict[str, Any] | None) -> "VersionFamilies":
        """Instantiates VersionFamilies from a dossier versions mapping, resolving legacy fallbacks."""
        if not versions:
            return cls()
        return cls(
            api_version=str(versions.get("api_version", API_VERSION)),
            evidence_schema_version=str(versions.get("evidence_schema_version", EVIDENCE_SCHEMA_VERSION)),
            scoring_model_version=str(
                versions.get(
                    "scoring_model_version",
                    versions.get("scoring_config_version", SCORING_MODEL_VERSION),
                )
            ),
            analyzer_version=str(versions.get("analyzer_version", ANALYZER_VERSION)),
            role_ontology_version=str(
                versions.get(
                    "role_ontology_version",
                    versions.get("ontology_version", ROLE_ONTOLOGY_VERSION),
                )
            ),
            claim_schema_version=str(versions.get("claim_schema_version", CLAIM_SCHEMA_VERSION)),
            source_reliability_version=str(
                versions.get("source_reliability_version", SOURCE_RELIABILITY_VERSION)
            ),
        )


def get_default_version_families() -> VersionFamilies:
    """Returns the default active VersionFamilies."""
    return VersionFamilies()


def get_canonical_version_dict() -> dict[str, str]:
    """Returns the unified version mapping containing all explicit families and legacy aliases."""
    return get_default_version_families().to_legacy_compat_dict()


def validate_dossier_reproducibility(versions: dict[str, Any] | None) -> tuple[bool, list[str]]:
    """Checks whether a dossier contains the necessary version families for full historical reproducibility."""
    if not versions or not isinstance(versions, dict):
        return False, ["Missing or empty versions mapping"]

    missing: list[str] = []
    for family in REQUIRED_VERSION_FAMILIES:
        if family not in versions:
            # Check legacy fallbacks
            if family == "scoring_model_version" and "scoring_config_version" in versions:
                continue
            if family == "role_ontology_version" and "ontology_version" in versions:
                continue
            missing.append(family)

    is_reproducible = len(missing) == 0
    return is_reproducible, missing


def build_reproducibility_metadata(dossier: Any) -> dict[str, Any]:
    """Constructs comprehensive audit and reproducibility metadata for a Dossier."""
    raw_versions = getattr(dossier, "versions", {}) or {}
    families = VersionFamilies.from_dossier_versions(raw_versions)
    is_reproducible, missing_families = validate_dossier_reproducibility(raw_versions)

    dossier_id = getattr(dossier, "dossier_id", None)
    candidate_id = getattr(dossier, "candidate_id", None)
    analysis_run_id = getattr(dossier, "analysis_run_id", None)
    role_val = getattr(dossier, "role", None)
    if hasattr(role_val, "value"):
        role_str = role_val.value
    else:
        role_str = str(role_val) if role_val else None

    gen_at = getattr(dossier, "generated_at", None)
    if hasattr(gen_at, "isoformat"):
        gen_str = gen_at.isoformat()
    else:
        gen_str = str(gen_at) if gen_at else datetime.now(timezone.utc).isoformat()

    return {
        "dossier_id": str(dossier_id) if dossier_id else None,
        "candidate_id": str(candidate_id) if candidate_id else None,
        "analysis_run_id": str(analysis_run_id) if analysis_run_id else None,
        "role": role_str,
        "generated_at": gen_str,
        "version_families": families.to_dict(),
        "is_reproducible": is_reproducible,
        "missing_version_families": missing_families,
        "reproducibility_contract": {
            "scoring_engine": f"cci-math-core@{families.scoring_model_version}",
            "evidence_schema": f"ceg-schema@{families.evidence_schema_version}",
            "analyzer_suite": f"cci-analyzers@{families.analyzer_version}",
            "role_ontology": f"cci-ontology@{families.role_ontology_version}",
            "claim_schema": f"claim-schema@{families.claim_schema_version}",
            "calibration_priors": f"source-reliability@{families.source_reliability_version}",
            "api_surface": f"cci-api@{families.api_version}",
        },
    }
