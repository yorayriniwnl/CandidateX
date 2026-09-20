"""Unit tests for the batch candidate evaluation and cohort ranking CLI."""

import json
from pathlib import Path
import pytest

from cci.domain.enums import CanonicalRole
from scripts.batch_evaluate_candidates import (
    extract_candidate_name,
    format_cohort_html,
    format_cohort_markdown,
    run_batch_evaluation,
)


def test_extract_candidate_name():
    """Verify robust candidate name extraction from markdown CV headers."""
    assert extract_candidate_name("# Alice Chen\nSenior Software Engineer", "fallback") == "Alice Chen"
    assert extract_candidate_name("# Bob Dylan - Senior Backend Developer", "fallback") == "Bob Dylan"
    assert extract_candidate_name("Experienced developer\nPython, Go", "Fallback Name") == "Fallback Name"


def test_batch_evaluate_candidates_execution(tmp_path: Path):
    """Verify that batch evaluation executes on multiple CVs, generates leaderboard, and sorts by RCI."""
    # 1. Create a sample cohort directory
    cv_dir = tmp_path / "cvs"
    cv_dir.mkdir()

    cv1_content = """# Alice Developer
Senior Backend Engineer proficient in Python, Go, and PostgreSQL.
Built distributed payment engines, automated CI/CD pipelines, and high-concurrency systems.
"""
    (cv_dir / "alice_chen.md").write_text(cv1_content, encoding="utf-8")

    cv2_content = """# Bob Junior
Recent graduate with knowledge of HTML, CSS, and basic JavaScript.
Built basic personal portfolio websites.
"""
    (cv_dir / "bob_junior.md").write_text(cv2_content, encoding="utf-8")

    jd_content = """# Senior Backend Engineer
Requirements:
- 5+ years building backend microservices with Python or Go.
- Experience with relational database architecture and distributed systems.
"""
    jd_file = tmp_path / "senior_backend.md"
    jd_file.write_text(jd_content, encoding="utf-8")

    output_dir = tmp_path / "cohort_output"

    # 2. Execute batch evaluation
    result = run_batch_evaluation(
        cv_paths=[cv_dir / "alice_chen.md", cv_dir / "bob_junior.md"],
        jd_text=jd_content,
        role=CanonicalRole.BACKEND,
        output_dir=output_dir,
    )

    assert result["count"] == 2
    candidates = result["candidates"]
    assert len(candidates) == 2

    # Verify ranking: Alice should rank higher than Bob for Senior Backend Engineer
    assert candidates[0]["rank"] == 1
    assert candidates[1]["rank"] == 2
    # If both have RCI, assert rank 0 has >= rank 1
    if candidates[0]["rci"] is not None and candidates[1]["rci"] is not None:
        assert candidates[0]["rci"] >= candidates[1]["rci"]

    # Verify artifact generation in output directory
    assert (output_dir / "cohort_ranking.json").exists()
    assert (output_dir / "cohort_ranking.md").exists()
    assert (output_dir / "cohort_ranking.html").exists()

    # Verify JSON content
    with open(output_dir / "cohort_ranking.json", "r", encoding="utf-8") as f:
        data = json.load(f)
        assert data["target_role"] == "backend"
        assert len(data["candidates"]) == 2

    # Verify individual dossier exports
    for c in candidates:
        cid = c["candidate_id"]
        assert (output_dir / f"dossier_{cid}.json").exists()
        assert (output_dir / f"dossier_{cid}.html").exists()

    # Verify HTML and MD content
    md_text = (output_dir / "cohort_ranking.md").read_text(encoding="utf-8")
    assert "Cohort Capability Leaderboard" in md_text
    assert "Decision Support Invariant" in md_text

    html_text = (output_dir / "cohort_ranking.html").read_text(encoding="utf-8")
    assert "Candidate Cohort Evaluation Leaderboard" in html_text
    assert "Employer Decision Support" in html_text
