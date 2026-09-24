"""Coding profile evidence extraction and algorithm/problem-solving modeling (Fix 39).

Provides careful extraction and bounded attribution of competitive programming and coding platforms:
- Supported platforms: LeetCode, Codeforces, Kaggle, CodeChef, HackerRank, TopCoder, and generic profiles
- Stores structured metadata:
    * visible rating/rank
    * solved counts (total, easy, medium, hard where applicable)
    * contest history (contests attended, peak rating, rank)
    * profile timestamp
    * source URL
- Strictly enforces architectural invariants:
    * Do not convert a coding-platform rating directly into general engineering ability.
    * Use primarily for algorithm/problem-solving evidence (CapabilityKey.ALGORITHMS_PROBLEM_SOLVING).
    * General engineering capability is NEVER inferred from coding profiles alone.
"""

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import hashlib
import re
from typing import Any, Mapping, Sequence
from urllib.parse import urlparse
from uuid import UUID, uuid5, NAMESPACE_URL

from cci.domain.enums import CapabilityKey, SourceFamily
from cci.domain.contracts import EvidenceConfidenceFactors, EvidenceRecord
from cci.scoring.confidence import compute_confidence_from_factors
from cci.scoring.reliability import compute_source_reliability


CODING_PROFILE_LIMITATIONS = [
    "Competitive programming ratings reflect algorithmic exercise speed under test constraints; they do not establish production architecture, system design, maintainability, or team collaboration.",
    "Do not convert a coding-platform rating directly into general engineering ability.",
    "Used primarily for algorithm/problem-solving evidence.",
]


@dataclass
class CodingProfileEvidence:
    """Structured evidence derived from a publicly visible coding platform profile."""

    platform: str
    username: str
    source_url: str
    visible_rating: float | int | None = None
    visible_rank: str | int | None = None
    solved_counts: dict[str, int] = field(default_factory=dict)
    contest_history: list[dict[str, Any]] = field(default_factory=list)
    profile_timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    is_publicly_visible: bool = True
    evidence_scope: str = "algorithm_problem_solving"
    general_engineering_inferred: bool = False
    limitations: list[str] = field(default_factory=lambda: list(CODING_PROFILE_LIMITATIONS))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_evidence_record(self, candidate_id: UUID | None = None) -> EvidenceRecord | None:
        """Converts coding profile evidence into an EvidenceRecord for algorithm/problem-solving capability."""
        if not self.is_publicly_visible:
            return None

        # Conservative confidence mapping based strictly on solved count or rating
        total_solved = self.solved_counts.get("total", sum(self.solved_counts.values()) if self.solved_counts else 0)
        has_signal = (self.visible_rating is not None and self.visible_rating > 0) or total_solved > 0 or bool(self.contest_history)
        if not has_signal:
            return None

        # Compute bounded rule strength strictly for algorithm capability
        strength = 0.40
        if total_solved >= 300 or (self.visible_rating and self.visible_rating >= 1800):
            strength = 0.65
        elif total_solved >= 100 or (self.visible_rating and self.visible_rating >= 1500):
            strength = 0.55
        elif total_solved >= 30 or (self.visible_rating and self.visible_rating >= 1200):
            strength = 0.45

        evidence_id = uuid5(NAMESPACE_URL, f"{candidate_id}:{self.source_url}:{self.profile_timestamp}")
        fingerprint = hashlib.sha256(
            f"{self.source_url}:{self.profile_timestamp}:coding_profile_v1".encode("utf-8")
        ).hexdigest()

        reliability_mean = compute_source_reliability(SourceFamily.CODING).posterior_mean
        factors = EvidenceConfidenceFactors(
            artifact_integrity=1.0,
            ownership_score=0.85,
            recency_factor=1.0,
            verification_level=0.70,
            depth_specificity=0.60,
            source_reliability=reliability_mean,
        )
        confidence = float(compute_confidence_from_factors(factors))

        provenance = {
            "platform": self.platform,
            "username": self.username,
            "visible_rating": self.visible_rating,
            "visible_rank": self.visible_rank,
            "solved_counts": self.solved_counts,
            "contest_history": self.contest_history,
            "profile_timestamp": self.profile_timestamp,
            "candidate_id": str(candidate_id) if candidate_id else None,
            "general_engineering_inferred": False,
            "limitations": self.limitations,
            "signal_rule_id": "CODING_PROFILE_ALGORITHM_EVIDENCE",
            "signal_rule_version": "1.0.0",
            "rule_id": "CODING_PROFILE_ALGORITHM_EVIDENCE",
            "rule_strength": strength,
            "raw_support_text": (
                f"Public {self.platform.capitalize()} profile for '{self.username}' observed with "
                f"rating {self.visible_rating or 'unrated'}, rank {self.visible_rank or 'unranked'}, "
                f"and {total_solved} solved problems."
            ),
        }

        return EvidenceRecord(
            evidence_id=evidence_id,
            fingerprint=fingerprint,
            source_family=SourceFamily.CODING,
            source_locator=self.source_url,
            immutable_revision=self.profile_timestamp,
            target_capability=CapabilityKey.ALGORITHMS_PROBLEM_SOLVING,
            technical_signal_strength=strength * 100.0,
            confidence_factors=factors,
            confidence=confidence,
            provenance=provenance,
        )



class BaseCodingProfileExtractor(ABC):
    """Abstract base class for coding platform extractors."""

    platform_name: str = "generic"

    @abstractmethod
    def can_handle(self, url: str) -> bool:
        """Returns True if this extractor can parse the URL."""

    @abstractmethod
    def extract(self, url: str, source_data: Mapping[str, Any]) -> CodingProfileEvidence | None:
        """Extracts coding profile evidence from URL and source data."""


class LeetCodeExtractor(BaseCodingProfileExtractor):
    """Extractor for LeetCode public user profiles."""

    platform_name = "leetcode"

    def can_handle(self, url: str) -> bool:
        parsed = urlparse(url.lower())
        return "leetcode.com" in parsed.netloc

    def extract(self, url: str, source_data: Mapping[str, Any]) -> CodingProfileEvidence | None:
        parsed = urlparse(url)
        path = parsed.path.strip("/")
        # Matches /u/username or /username
        m_user = re.search(r"(?:u/)?([a-zA-Z0-9_-]+)(?:/.*)?$", path)
        if not m_user:
            return None
        username = m_user.group(1)
        if username in ("problems", "contest", "explore", "discuss"):
            return None

        title = str(source_data.get("title", ""))
        excerpt = str(source_data.get("excerpt", ""))
        text = f"{title} {excerpt}"

        # Extract solved counts
        solved_counts: dict[str, int] = {}
        m_total = re.search(r"\b(\d+)\s*/\s*\d+\s+solved\b|\bsolved:\s*(\d+)\b|\b(\d+)\s+problems?\s+solved\b", text, re.IGNORECASE)
        if m_total:
            val = next(g for g in m_total.groups() if g is not None)
            solved_counts["total"] = int(val)

        m_easy = re.search(r"\beasy\s*[:\s]\s*(\d+)\b", text, re.IGNORECASE)
        if m_easy:
            solved_counts["easy"] = int(m_easy.group(1))

        m_med = re.search(r"\bmedium\s*[:\s]\s*(\d+)\b", text, re.IGNORECASE)
        if m_med:
            solved_counts["medium"] = int(m_med.group(1))

        m_hard = re.search(r"\bhard\s*[:\s]\s*(\d+)\b", text, re.IGNORECASE)
        if m_hard:
            solved_counts["hard"] = int(m_hard.group(1))

        # Extract contest rating
        m_rating = re.search(r"\bcontest\s+rating\s*[:\s]\s*(\d+(?:\.\d+)?)\b|\brating\s*[:\s]\s*(\d+(?:\.\d+)?)\b", text, re.IGNORECASE)
        rating = float(m_rating.group(1) or m_rating.group(2)) if m_rating else None

        # Extract global rank
        m_rank = re.search(r"\b(?:global\s+)?ranking\s*[:\s~]\s*([0-9,]+)\b", text, re.IGNORECASE)
        rank = m_rank.group(1).replace(",", "") if m_rank else None

        # Extract contest history
        contest_history = []
        m_attended = re.search(r"\battended\s*[:\s]\s*(\d+)\s+contests?\b|\bcontests?\s*[:\s]\s*(\d+)\b", text, re.IGNORECASE)
        if m_attended:
            count = int(m_attended.group(1) or m_attended.group(2))
            contest_history.append({"contests_attended": count})

        timestamp = source_data.get("fetched_at") or datetime.now(timezone.utc).isoformat()
        return CodingProfileEvidence(
            platform=self.platform_name,
            username=username,
            source_url=url,
            visible_rating=rating,
            visible_rank=rank,
            solved_counts=solved_counts,
            contest_history=contest_history,
            profile_timestamp=timestamp,
        )


class CodeforcesExtractor(BaseCodingProfileExtractor):
    """Extractor for Codeforces competitive programming profiles."""

    platform_name = "codeforces"

    def can_handle(self, url: str) -> bool:
        parsed = urlparse(url.lower())
        return "codeforces.com" in parsed.netloc

    def extract(self, url: str, source_data: Mapping[str, Any]) -> CodingProfileEvidence | None:
        parsed = urlparse(url)
        path = parsed.path.strip("/")
        m_user = re.search(r"profile/([a-zA-Z0-9_-]+)", path)
        if not m_user:
            return None
        username = m_user.group(1)

        title = str(source_data.get("title", ""))
        excerpt = str(source_data.get("excerpt", ""))
        text = f"{title} {excerpt}"

        # Rating and rank
        m_rating = re.search(r"\brating\s*[:\s]\s*(\d+)\b", text, re.IGNORECASE)
        rating = int(m_rating.group(1)) if m_rating else None

        m_rank = re.search(r"\b(?:rank|title)\s*[:\s]\s*([A-Za-z ]+?)(?:,\s*max|\.|\n|$)", text, re.IGNORECASE)
        rank = m_rank.group(1).strip() if m_rank else None

        # Solved counts
        solved_counts: dict[str, int] = {}
        m_solved = re.search(r"\b(\d+)\s+problems?\s+solved\b|\bsolved\s+for\s+all\s+time\s*[:\s]\s*(\d+)\b", text, re.IGNORECASE)
        if m_solved:
            solved_counts["total"] = int(m_solved.group(1) or m_solved.group(2))

        # Contest history
        contest_history = []
        m_max = re.search(r"\bmax(?:imum)?\s+rating\s*[:\s]\s*(\d+)\b", text, re.IGNORECASE)
        if m_max:
            contest_history.append({"peak_rating": int(m_max.group(1))})

        timestamp = source_data.get("fetched_at") or datetime.now(timezone.utc).isoformat()
        return CodingProfileEvidence(
            platform=self.platform_name,
            username=username,
            source_url=url,
            visible_rating=rating,
            visible_rank=rank,
            solved_counts=solved_counts,
            contest_history=contest_history,
            profile_timestamp=timestamp,
        )


class KaggleExtractor(BaseCodingProfileExtractor):
    """Extractor for Kaggle data science / ML competition profiles."""

    platform_name = "kaggle"

    def can_handle(self, url: str) -> bool:
        parsed = urlparse(url.lower())
        return "kaggle.com" in parsed.netloc

    def extract(self, url: str, source_data: Mapping[str, Any]) -> CodingProfileEvidence | None:
        parsed = urlparse(url)
        username = parsed.path.strip("/").split("/")[0]
        if not username or username in ("competitions", "datasets", "code", "learn", "discussions"):
            return None

        title = str(source_data.get("title", ""))
        excerpt = str(source_data.get("excerpt", ""))
        text = f"{title} {excerpt}"

        # Tier / Rank
        m_tier = re.search(r"\b(Grandmaster|Master|Expert|Contributor|Novice)\b", text, re.IGNORECASE)
        rank = m_tier.group(1).capitalize() if m_tier else None

        # Competitions count
        solved_counts: dict[str, int] = {}
        m_comp = re.search(r"\b(\d+)\s+competitions?\b", text, re.IGNORECASE)
        if m_comp:
            solved_counts["competitions"] = int(m_comp.group(1))

        m_datasets = re.search(r"\b(\d+)\s+datasets?\b", text, re.IGNORECASE)
        if m_datasets:
            solved_counts["datasets"] = int(m_datasets.group(1))

        m_notebooks = re.search(r"\b(\d+)\s+notebooks?\b", text, re.IGNORECASE)
        if m_notebooks:
            solved_counts["notebooks"] = int(m_notebooks.group(1))

        timestamp = source_data.get("fetched_at") or datetime.now(timezone.utc).isoformat()
        return CodingProfileEvidence(
            platform=self.platform_name,
            username=username,
            source_url=url,
            visible_rank=rank,
            solved_counts=solved_counts,
            profile_timestamp=timestamp,
        )


class CodeChefExtractor(BaseCodingProfileExtractor):
    """Extractor for CodeChef competitive programming profiles."""

    platform_name = "codechef"

    def can_handle(self, url: str) -> bool:
        parsed = urlparse(url.lower())
        return "codechef.com" in parsed.netloc

    def extract(self, url: str, source_data: Mapping[str, Any]) -> CodingProfileEvidence | None:
        parsed = urlparse(url)
        m_user = re.search(r"users/([a-zA-Z0-9_-]+)", parsed.path)
        if not m_user:
            return None
        username = m_user.group(1)

        title = str(source_data.get("title", ""))
        excerpt = str(source_data.get("excerpt", ""))
        text = f"{title} {excerpt}"

        m_rating = re.search(r"\brating\s*[:\s]\s*(\d+)\b|\b(\d+)\s*★\b", text, re.IGNORECASE)
        rating = int(m_rating.group(1) or m_rating.group(2)) if m_rating else None

        m_rank = re.search(r"\bglobal\s+rank\s*[:\s]\s*([0-9,]+)\b", text, re.IGNORECASE)
        rank = m_rank.group(1).replace(",", "") if m_rank else None

        solved_counts: dict[str, int] = {}
        m_solved = re.search(r"\b(\d+)\s+problems?\s+solved\b|\bfully\s+solved\s*[:\s]\s*(\d+)\b", text, re.IGNORECASE)
        if m_solved:
            solved_counts["total"] = int(m_solved.group(1) or m_solved.group(2))

        timestamp = source_data.get("fetched_at") or datetime.now(timezone.utc).isoformat()
        return CodingProfileEvidence(
            platform=self.platform_name,
            username=username,
            source_url=url,
            visible_rating=rating,
            visible_rank=rank,
            solved_counts=solved_counts,
            profile_timestamp=timestamp,
        )


class GenericCodingProfileExtractor(BaseCodingProfileExtractor):
    """Fallback extractor for arbitrary public coding and problem-solving platforms."""

    platform_name = "generic"

    def can_handle(self, url: str) -> bool:
        return True

    def extract(self, url: str, source_data: Mapping[str, Any]) -> CodingProfileEvidence | None:
        parsed = urlparse(url)
        path = parsed.path.strip("/")
        parts = [p for p in path.split("/") if p]
        username = parts[-1] if parts else "unknown_user"
        domain = parsed.netloc.lower().removeprefix("www.")
        platform = domain.split(".")[0]

        title = str(source_data.get("title", ""))
        excerpt = str(source_data.get("excerpt", ""))
        text = f"{title} {excerpt}"

        m_rating = re.search(r"\brating\s*[:\s]\s*(\d+(?:\.\d+)?)\b|\bscore\s*[:\s]\s*(\d+(?:\.\d+)?)\b", text, re.IGNORECASE)
        rating = float(m_rating.group(1) or m_rating.group(2)) if m_rating else None

        m_rank = re.search(r"\brank(?:ing)?\s*[:\s]\s*([A-Za-z0-9,]+)\b", text, re.IGNORECASE)
        rank = m_rank.group(1).replace(",", "") if m_rank else None

        solved_counts: dict[str, int] = {}
        m_solved = re.search(r"\b(\d+)\s+(?:problems?|challenges?|tasks?)\s+solved\b", text, re.IGNORECASE)
        if m_solved:
            solved_counts["total"] = int(m_solved.group(1))

        timestamp = source_data.get("fetched_at") or datetime.now(timezone.utc).isoformat()
        return CodingProfileEvidence(
            platform=platform,
            username=username,
            source_url=url,
            visible_rating=rating,
            visible_rank=rank,
            solved_counts=solved_counts,
            profile_timestamp=timestamp,
        )


_EXTRACTORS: list[BaseCodingProfileExtractor] = [
    LeetCodeExtractor(),
    CodeforcesExtractor(),
    KaggleExtractor(),
    CodeChefExtractor(),
    GenericCodingProfileExtractor(),
]


def extract_coding_profile_evidence(url: str, source_data: Mapping[str, Any]) -> CodingProfileEvidence | None:
    """Extracts structured coding profile evidence from a single URL and its fetch receipt."""
    for extractor in _EXTRACTORS:
        if extractor.can_handle(url):
            return extractor.extract(url, source_data)
    return GenericCodingProfileExtractor().extract(url, source_data)


def inspect_coding_profiles(
    urls: Sequence[str],
    sources: Sequence[Mapping[str, Any]],
) -> list[CodingProfileEvidence]:
    """Inspects all candidate-declared or discovered coding profiles and returns verified evidence."""
    from cci.intake.canonicalizer import classify_url

    source_map = {s.get("url", "").rstrip("/").lower(): s for s in sources}
    results: list[CodingProfileEvidence] = []

    for raw_url in urls:
        norm_url = raw_url.rstrip("/").lower()
        source_data = source_map.get(norm_url, {})
        # If not directly matched, find by prefix
        if not source_data:
            for s_url, s_item in source_map.items():
                if norm_url in s_url or s_url in norm_url:
                    source_data = s_item
                    break

        evidence = extract_coding_profile_evidence(raw_url, source_data)
        if evidence:
            results.append(evidence)

    return results
