"""Demo fixtures must never expose plausible real candidate identities."""

import re
from pathlib import Path
from urllib.parse import urlsplit

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from cci.db.models import Candidate


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def _is_reserved_demo_url(value: str) -> bool:
    host = urlsplit(value.rstrip(".,;:)")).hostname
    return bool(host and host.endswith(".invalid"))


def test_sample_resume_fixtures_use_synthetic_names_emails_and_urls():
    fixtures = sorted((REPOSITORY_ROOT / "examples").glob("sample_*_cv.txt"))
    assert len(fixtures) == 5
    expected_identity = {
        "sample_backend_cv.txt": "Demo Candidate 01",
        "sample_frontend_cv.txt": "Demo Candidate 02",
        "sample_ml_cv.txt": "Demo Candidate 03",
        "sample_devops_cv.txt": "Demo Candidate 04",
        "sample_fullstack_cv.txt": "Demo Candidate 05",
    }

    for fixture in fixtures:
        content = fixture.read_text(encoding="utf-8")
        assert content.startswith(f"# {expected_identity[fixture.name]}\n")
        assert "SYNTHETIC DEMO DATA" in content

        emails = re.findall(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", content, re.I)
        assert emails
        assert all(email.lower().endswith("@example.invalid") for email in emails)

        urls = re.findall(r"https?://[^\s|<>]+", content)
        assert urls
        assert all(_is_reserved_demo_url(url) for url in urls)


def test_database_seed_candidates_use_synthetic_identity_and_reserved_sources(tmp_path):
    from scripts.seed_db import seed_database

    database_path = (tmp_path / "demo-seed.sqlite").as_posix()
    database_url = f"sqlite:///{database_path}"
    seed_database(db_url=database_url, reset=True, samples_count=6)

    engine = create_engine(database_url)
    try:
        with Session(engine) as session:
            candidates = session.scalars(select(Candidate)).all()

        assert len(candidates) == 6
        for candidate in candidates:
            assert re.fullmatch(r"Demo Candidate \d{2}", candidate.display_name)
            assert candidate.primary_email
            assert candidate.primary_email.endswith("@example.invalid")

            supplied_urls = candidate.manifest_data["github_urls"]
            assert supplied_urls
            assert all(_is_reserved_demo_url(url) for url in supplied_urls)
    finally:
        engine.dispose()
