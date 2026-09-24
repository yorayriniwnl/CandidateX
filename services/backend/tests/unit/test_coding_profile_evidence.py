"""Unit tests for Fix 39: Coding Profile Evidence and Algorithm/Problem-Solving Modeling."""

from uuid import uuid4
import pytest

from cci.domain.enums import CapabilityKey, SourceFamily
from cci.profiles.coding import (
    CodingProfileEvidence,
    LeetCodeExtractor,
    CodeforcesExtractor,
    KaggleExtractor,
    CodeChefExtractor,
    extract_coding_profile_evidence,
    inspect_coding_profiles,
)


class TestCodingProfileExtractors:
    def test_leetcode_extractor(self):
        extractor = LeetCodeExtractor()
        url = "https://leetcode.com/u/alice_coder/"
        assert extractor.can_handle(url) is True

        source_data = {
            "url": url,
            "title": "alice_coder - LeetCode Profile",
            "excerpt": "450/3000 solved. Easy: 120, Medium: 250, Hard: 80. Contest Rating: 1950.4. Global Ranking: 12,450. Attended: 24 contests.",
            "fetched_at": "2026-09-24T12:00:00Z",
        }

        evidence = extractor.extract(url, source_data)
        assert evidence is not None
        assert evidence.platform == "leetcode"
        assert evidence.username == "alice_coder"
        assert evidence.visible_rating == 1950.4
        assert evidence.visible_rank == "12450"
        assert evidence.solved_counts == {"total": 450, "easy": 120, "medium": 250, "hard": 80}
        assert evidence.contest_history == [{"contests_attended": 24}]
        assert evidence.general_engineering_inferred is False
        assert "algorithm_problem_solving" in evidence.evidence_scope

    def test_codeforces_extractor(self):
        extractor = CodeforcesExtractor()
        url = "https://codeforces.com/profile/bob_tourist"
        assert extractor.can_handle(url) is True

        source_data = {
            "url": url,
            "title": "bob_tourist - Codeforces",
            "excerpt": "Rating: 1720. Rank: Candidate Master. Maximum rating: 1810. 520 problems solved.",
            "fetched_at": "2026-09-24T12:00:00Z",
        }

        evidence = extractor.extract(url, source_data)
        assert evidence is not None
        assert evidence.platform == "codeforces"
        assert evidence.username == "bob_tourist"
        assert evidence.visible_rating == 1720
        assert evidence.visible_rank == "Candidate Master"
        assert evidence.solved_counts == {"total": 520}
        assert evidence.contest_history == [{"peak_rating": 1810}]

    def test_kaggle_extractor(self):
        extractor = KaggleExtractor()
        url = "https://www.kaggle.com/carol_ml"
        assert extractor.can_handle(url) is True

        source_data = {
            "url": url,
            "title": "Carol ML | Kaggle",
            "excerpt": "Competitions Grandmaster. 14 competitions, 5 datasets, 22 notebooks.",
        }

        evidence = extractor.extract(url, source_data)
        assert evidence is not None
        assert evidence.platform == "kaggle"
        assert evidence.username == "carol_ml"
        assert evidence.visible_rank == "Grandmaster"
        assert evidence.solved_counts["competitions"] == 14
        assert evidence.solved_counts["datasets"] == 5
        assert evidence.solved_counts["notebooks"] == 22

    def test_codechef_extractor(self):
        extractor = CodeChefExtractor()
        url = "https://www.codechef.com/users/coder_david"
        assert extractor.can_handle(url) is True

        source_data = {
            "url": url,
            "title": "coder_david | CodeChef",
            "excerpt": "Rating: 2150 (5★). Global Rank: 850. Fully Solved: 320.",
        }

        evidence = extractor.extract(url, source_data)
        assert evidence is not None
        assert evidence.platform == "codechef"
        assert evidence.username == "coder_david"
        assert evidence.visible_rating == 2150
        assert evidence.visible_rank == "850"
        assert evidence.solved_counts == {"total": 320}


class TestCodingProfileEvidenceConversion:
    def test_evidence_record_targeted_at_algorithm_capability_only(self):
        candidate_id = uuid4()
        evidence = CodingProfileEvidence(
            platform="leetcode",
            username="expert_solver",
            source_url="https://leetcode.com/u/expert_solver",
            visible_rating=2100.0,
            visible_rank="4500",
            solved_counts={"total": 600, "easy": 100, "medium": 350, "hard": 150},
        )

        record = evidence.to_evidence_record(candidate_id)
        assert record is not None
        # Must target algorithms_problem_solving ONLY
        assert record.capability == CapabilityKey.ALGORITHMS_PROBLEM_SOLVING
        assert record.source_family == SourceFamily.CODING
        assert record.candidate_id == candidate_id
        assert record.rule_id == "CODING_PROFILE_ALGORITHM_EVIDENCE"
        assert record.rule_strength <= 0.70  # Bounded, conservative prior

        # Invariant check: general engineering is not inferred
        context = record.context
        assert context["general_engineering_inferred"] is False
        assert any("Do not convert a coding-platform rating directly into general engineering ability" in lim for lim in context["limitations"])

    def test_inspect_coding_profiles_integration(self):
        urls = [
            "https://leetcode.com/u/alice_coder",
            "https://codeforces.com/profile/bob_tourist",
        ]
        sources = [
            {
                "url": "https://leetcode.com/u/alice_coder",
                "title": "Alice - LeetCode",
                "excerpt": "350 solved. Contest rating: 1820.",
                "status": "observed",
            },
            {
                "url": "https://codeforces.com/profile/bob_tourist",
                "title": "Bob - Codeforces",
                "excerpt": "Rating: 1900. Rank: Master. 400 problems solved.",
                "status": "observed",
            },
        ]

        results = inspect_coding_profiles(urls, sources)
        assert len(results) == 2
        assert results[0].platform == "leetcode"
        assert results[1].platform == "codeforces"
