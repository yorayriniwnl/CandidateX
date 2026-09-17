"""Integrity regressions for evidence-free pipeline runs."""

from uuid import uuid4

from cci.domain.enums import CanonicalRole
from cci.pipeline.orchestrator import PipelineStatus, execute_analysis_pipeline


def test_repo_url_without_extracted_evidence_stays_unknown() -> None:
    """A declared repository URL must never manufacture capability evidence."""
    state = execute_analysis_pipeline(
        candidate_id=uuid4(),
        role=CanonicalRole.BACKEND,
        repo_urls=["https://github.com/example/project"],
    )

    assert state.status == PipelineStatus.COMPLETED
    assert state.dossier is not None
    assert state.dossier.rci is None
    assert state.dossier.coverage == 0.0
    assert state.dossier.is_insufficient_evidence is True
    assert state.dossier.ownership_assessments == []
    assert all(
        estimate.estimate is None and estimate.is_observed is False
        for estimate in state.dossier.capability_estimates.values()
    )
