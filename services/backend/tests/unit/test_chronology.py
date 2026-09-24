"""Unit tests for Fix 42: Candidate Chronology Engine and Inconsistency Detection."""

import pytest

from cci.chronology.engine import (
    LABEL_TIMELINE_INCONSISTENCY,
    build_candidate_timeline,
    detect_timeline_inconsistencies,
    extract_timeline_events,
)
from cci.domain.contracts import CandidateTimeline, TimelineEvent, TimelineInconsistency


class DummyIntake:
    def __init__(self, sections=None, project_claims=None):
        self.resume_review = type("Review", (), {"sections": sections or {}})()
        self.manifest = type("Manifest", (), {"project_claims": project_claims or []})()


class TestChronologyEngine:
    def test_build_timeline_across_all_6_sources(self):
        sections = {
            "education": [
                "B.Tech in Computer Science, State University, 2016 - 2020",
            ],
            "experience": [
                "Software Engineer, Tech Corp, 2020 - 2023",
                "Frontend Engineering Intern, Startup Labs, May 2019 - Aug 2019",
            ],
        }
        project_claims = [
            {
                "title": "Machine Learning Research Engine",
                "description": "Published in IEEE Conference on AI 2021. Distributed clustering model.",
            }
        ]
        sources = [
            {
                "url": "https://github.com/alice/ml-engine",
                "kind": "github",
                "created_at": "2021-01-15T00:00:00Z",
                "last_activity": "2023-05-10T00:00:00Z",
                "status": "observed",
            },
            {
                "url": "https://ml-engine.app",
                "kind": "deployment",
                "fetched_at": "2026-09-24T12:00:00Z",
                "status": "observed",
            },
        ]
        credentials = [
            {
                "credential_name": "AWS Certified Solutions Architect",
                "issued_date": "2022-03-01",
                "expiration_date": "2025-03-01",
            }
        ]

        intake = DummyIntake(sections=sections, project_claims=project_claims)
        timeline = build_candidate_timeline(intake, sources=sources, credentials=credentials)

        assert isinstance(timeline, CandidateTimeline)
        assert len(timeline.events) >= 6

        categories = {e.category for e in timeline.events}
        # 1. Education dates
        assert "education" in categories
        # 2. Work / internship dates
        assert "work_experience" in categories
        assert "internship" in categories
        # 3. Repository activity
        assert "repository_activity" in categories
        # 4. Deployment dates
        assert "deployment" in categories
        # 5. Credential dates
        assert "credential" in categories
        # 6. Publication dates
        assert "publication" in categories

        # Verify sorted chronologically
        start_years = [int(e.start_date[:4]) for e in timeline.events if e.start_date and e.start_date[:4].isdigit()]
        assert start_years == sorted(start_years)

    def test_detect_inconsistencies_and_enforce_non_judgmental_label(self):
        """Hardening Invariant:
        Do not infer dishonesty.
        Label: timeline inconsistency requiring review.
        """
        events = [
            # 1. Inverted date range
            TimelineEvent(
                category="work_experience",
                title="Lead Backend Engineer, Past Corp",
                start_date="2024",
                end_date="2022",
                details={"raw_text": "Lead Backend Engineer 2024 - 2022"},
            ),
            # 2. Future date
            TimelineEvent(
                category="education",
                title="M.S. Advanced Robotics",
                start_date="2032",
                end_date="2034",
                details={"raw_text": "M.S. Advanced Robotics 2032 - 2034"},
            ),
            # 3. Credential expired before issue
            TimelineEvent(
                category="credential",
                title="Kubernetes Administrator",
                start_date="2024",
                end_date="2021",
                details={"raw_text": "Issued 2024, Expired 2021"},
            ),
            # 4. Technology anachronism (FastAPI released in 2018; claimed 2010 - 2012)
            TimelineEvent(
                category="work_experience",
                title="Python Developer at Early Startup",
                start_date="2010",
                end_date="2012",
                details={"raw_text": "Built production REST APIs using FastAPI and Pydantic from 2010 to 2012"},
            ),
        ]

        inconsistencies = detect_timeline_inconsistencies(events, current_year=2026)
        assert len(inconsistencies) == 4

        types = {i.inconsistency_type for i in inconsistencies}
        assert "inverted_date_range" in types
        assert "future_date" in types
        assert "expired_before_issue" in types
        assert "anachronism" in types

        # Strict Invariant Verification:
        for inc in inconsistencies:
            assert isinstance(inc, TimelineInconsistency)
            # Label MUST be exactly the required string
            assert inc.label == LABEL_TIMELINE_INCONSISTENCY
            assert inc.label == "timeline inconsistency requiring review"

            # Must NEVER accuse candidate of lying, fraud, or intentional dishonesty
            text = (inc.label + " " + inc.explanation).lower()
            assert "fraud" not in text
            assert "fake" not in text
            assert "liar" not in text
            assert "dishonest candidate" not in text
            assert "candidate is dishonest" not in text
            assert "do not infer dishonesty" in inc.explanation
