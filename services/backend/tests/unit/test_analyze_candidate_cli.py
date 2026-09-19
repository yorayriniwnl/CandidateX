"""Unit tests for the turnkey candidate analysis CLI."""

import json
from pathlib import Path
import pytest

from cci.domain.enums import CanonicalRole
from scripts.analyze_candidate import (
    execute_analysis_pipeline,
    format_dossier_markdown,
    load_text,
    rescore_dossier,
)


def test_analyze_candidate_turnkey_execution(tmp_path: Path):
    """Verify that turnkey candidate analysis executes end-to-end and formats reports."""
    cv_content = """# Alice Developer
Experienced Senior Backend Engineer proficient in Python, Go, and PostgreSQL.
Built distributed payment engines and managed high-scale databases.
"""
    jd_content = """# Senior Backend Engineer
Requirements:
- 5+ years building backend systems in Python or Go.
- Deep expertise in PostgreSQL indexing and transaction architecture.
"""
    from uuid import uuid4
    candidate_id = uuid4()

    state = execute_analysis_pipeline(
        candidate_id=candidate_id,
        role=CanonicalRole.BACKEND,
        jd_text=jd_content,
        cv_text=cv_content,
    )

    assert state.status.value == "completed"
    assert state.dossier is not None
    dossier = state.dossier

    # Check that dossier contracts are populated
    assert dossier.rci is None  # CV claims alone do not establish observed capability
    assert 0.0 <= dossier.coverage <= 1.0
    assert len(dossier.capability_estimates) == 12
    assert len(dossier.interview_probes) > 0
    assert len(dossier.interview_questions) > 0

    # Format markdown report
    md_report = format_dossier_markdown(dossier, "Alice Developer")
    assert "# Technical Capability Dossier: Alice Developer" in md_report
    assert "## 2. Capability Estimates" in md_report
    assert "## 4. Prioritized Technical Interview Probes" in md_report

    # Save artifacts in tmp_path
    json_path = tmp_path / "dossier.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(dossier.model_dump(mode="json"), f, indent=2)
    assert json_path.exists()

    # Functional rescore
    rescored = rescore_dossier(dossier, {"backend_engineering": 0.5, "database_engineering": 0.5})
    assert rescored.rci is None
    assert rescored.dossier_id != dossier.dossier_id
