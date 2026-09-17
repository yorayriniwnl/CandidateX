"""Unit tests for Job Description (JD) parser and requirement extraction."""

import pytest
from cci.domain.enums import CapabilityKey, RequirementPriority
from cci.jobs.parser import extract_requirements_from_jd


SAMPLE_JD = """
Senior Backend Engineer - Core Platform

Requirements (Must Have):
- Strong expertise in Python and FastAPI microservices.
- Solid experience with PostgreSQL database design, schema migrations, and complex SQL indexing.
- Proficiency with Docker and Kubernetes for container deployment.
- Experience with unit testing using pytest.

Preferred Qualifications (Nice to Have):
- Familiarity with PyTorch or machine learning model deployment.
- Experience with AWS or Terraform infrastructure as code.
- Basic understanding of React or TypeScript frontend components.

Other Responsibilities:
- Facilitate cross-silo synergistic ideation and paradigm disruption.
"""


def test_jd_parser_mandatory_vs_preferred():
    """Verify that mandatory and preferred sections are accurately captured."""
    requirements = extract_requirements_from_jd(SAMPLE_JD)
    assert len(requirements) >= 6

    # Python & FastAPI must be MANDATORY
    py_req = next(r for r in requirements if "python" in r.technology_mentions)
    assert py_req.priority == RequirementPriority.MANDATORY
    assert CapabilityKey.BACKEND_ENGINEERING in py_req.capability_mappings

    # PostgreSQL must be MANDATORY
    pg_req = next(r for r in requirements if "postgresql" in r.technology_mentions)
    assert pg_req.priority == RequirementPriority.MANDATORY
    assert CapabilityKey.DATABASE_ENGINEERING in pg_req.capability_mappings

    # PyTorch must be PREFERRED
    ml_req = next(r for r in requirements if "pytorch" in r.technology_mentions)
    assert ml_req.priority == RequirementPriority.PREFERRED
    assert CapabilityKey.MACHINE_LEARNING in ml_req.capability_mappings

    # React / TypeScript must be PREFERRED
    fe_req = next(r for r in requirements if "react" in r.technology_mentions or "typescript" in r.technology_mentions)
    assert fe_req.priority == RequirementPriority.PREFERRED
    assert CapabilityKey.FRONTEND_ENGINEERING in fe_req.capability_mappings


def test_unknown_wording_represented_as_uncertainty():
    """Vague or unmapped requirements must have lower confidence, not invented certainty."""
    requirements = extract_requirements_from_jd(SAMPLE_JD)
    vague_req = next(r for r in requirements if "synergistic ideation" in r.source_text)

    # Must be marked with lower confidence and unresolved method
    assert vague_req.mapping_confidence < 0.6
    assert vague_req.mapping_method == "unresolved_ambiguity_fallback"
    assert vague_req.semantic_specificity < 0.5


def test_jd_parser_never_produces_role_weights():
    """INVARIANT: JD parser produces NormalizedRequirement, never final numeric role weights."""
    requirements = extract_requirements_from_jd(SAMPLE_JD)
    for req in requirements:
        # Check requirement attributes: there must be NO numeric final role weights
        assert not hasattr(req, "role_weight")
        assert not hasattr(req, "final_weight")
        assert not hasattr(req, "softmax_weight")
        # Mention frequency must be an integer >= 1
        assert req.mention_frequency >= 1
        # Specificity in [0, 1]
        assert 0.0 <= req.semantic_specificity <= 1.0
