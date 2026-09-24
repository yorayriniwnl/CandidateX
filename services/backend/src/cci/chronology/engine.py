"""Unified candidate chronology engine and inconsistency detection (Fix 42).

Enforces the core hardening invariants:
1. Builds a unified timeline using:
   - education dates;
   - work/internship dates;
   - repository activity;
   - deployment dates where available;
   - credential dates;
   - publication dates.
2. Detects potential chronological inconsistencies.
3. Invariant: Do not infer dishonesty.
   Strictly label: "timeline inconsistency requiring review".
4. Candidate code is NEVER executed.
"""

from __future__ import annotations

from datetime import datetime, timezone
import re
from typing import Any, Mapping, Sequence
from uuid import NAMESPACE_URL, uuid5

from cci.domain.contracts import (
    CandidateTimeline,
    TimelineEvent,
    TimelineInconsistency,
)

LABEL_TIMELINE_INCONSISTENCY = "timeline inconsistency requiring review"

TECH_RELEASE_YEARS: dict[str, int] = {
    "fastapi": 2018,
    "react": 2013,
    "next.js": 2016,
    "nextjs": 2016,
    "kubernetes": 2014,
    "docker": 2013,
    "pytorch": 2016,
    "tensorflow": 2015,
    "rust": 2015,
    "go": 2009,
    "golang": 2009,
    "svelte": 2016,
}


def _parse_year(val: Any) -> int | None:
    """Extracts an integer 4-digit year from string or int."""
    if val is None:
        return None
    if isinstance(val, int):
        return val if 1950 <= val <= 2100 else None
    s = str(val).strip()
    m = re.search(r"\b(19\d{2}|20\d{2})\b", s)
    return int(m.group(1)) if m else None


def _extract_date_range(text: str) -> tuple[str | None, str | None, bool]:
    """Extracts start_date, end_date, and is_ongoing from raw text."""
    # Look for patterns like "2020 - 2023", "Jan 2021 - Present", "05/2019 to 08/2022"
    m_range = re.search(
        r"\b((?:(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+)?(?:19|20)\d{2}|\d{1,2}/\d{4})\b"
        r"\s*(?:-|–|—|to)\s*"
        r"\b((?:(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+)?(?:19|20)\d{2}|\d{1,2}/\d{4}|Present|Current|Ongoing|Now)\b",
        text,
        re.IGNORECASE,
    )
    if m_range:
        start_str = m_range.group(1).strip()
        end_str = m_range.group(2).strip()
        is_ongoing = bool(re.search(r"present|current|ongoing|now", end_str, re.IGNORECASE))
        return start_str, (None if is_ongoing else end_str), is_ongoing

    # Single year pattern
    m_single = re.search(r"\b(19\d{2}|20\d{2})\b", text)
    if m_single:
        year_str = m_single.group(1)
        return year_str, year_str, False

    return None, None, False


def extract_timeline_events(
    intake_or_manifest: Any,
    sources: Sequence[Mapping[str, Any]] = (),
    credentials: Sequence[Any] = (),
) -> list[TimelineEvent]:
    """Extracts timeline events across education, work, repos, deployments, credentials, and publications."""
    events: list[TimelineEvent] = []

    manifest = getattr(intake_or_manifest, "manifest", intake_or_manifest)
    review = getattr(intake_or_manifest, "resume_review", None)
    sections = getattr(review, "sections", {}) if review else {}

    # 1. Education Dates
    edu_lines = sections.get("education", []) if isinstance(sections, Mapping) else []
    for i, line in enumerate(edu_lines):
        start_s, end_s, ongoing = _extract_date_range(line)
        event_id = str(uuid5(NAMESPACE_URL, f"edu:{i}:{line}"))
        events.append(
            TimelineEvent(
                event_id=event_id,
                category="education",
                title=line[:80].strip(),
                start_date=start_s,
                end_date=end_s,
                is_ongoing=ongoing,
                source="resume.education",
                details={"raw_text": line, "line_index": i},
            )
        )

    # 2. Work / Internship Dates
    exp_lines = sections.get("experience", []) if isinstance(sections, Mapping) else []
    for i, line in enumerate(exp_lines):
        start_s, end_s, ongoing = _extract_date_range(line)
        category = "internship" if re.search(r"\bintern(?:ship)?\b", line, re.I) else "work_experience"
        event_id = str(uuid5(NAMESPACE_URL, f"exp:{i}:{line}"))
        events.append(
            TimelineEvent(
                event_id=event_id,
                category=category,
                title=line[:80].strip(),
                start_date=start_s,
                end_date=end_s,
                is_ongoing=ongoing,
                source="resume.experience",
                details={"raw_text": line, "line_index": i},
            )
        )

    # 3. Repository Activity Dates
    for s in sources:
        url = str(s.get("url", ""))
        kind = str(s.get("kind", "")).lower()
        if kind == "github" or "github.com" in url.lower():
            last_act = s.get("last_activity") or s.get("fetched_at")
            first_commit = s.get("created_at")
            repo_name = url.strip("/").split("/")[-1] if "/" in url else "Repository"
            event_id = str(uuid5(NAMESPACE_URL, f"repo:{url}"))
            events.append(
                TimelineEvent(
                    event_id=event_id,
                    category="repository_activity",
                    title=f"GitHub Activity: {repo_name}",
                    start_date=str(first_commit) if first_commit else None,
                    end_date=str(last_act) if last_act else None,
                    source="github.repository",
                    source_url=url,
                    details={"status": s.get("status"), "last_activity": last_act},
                )
            )

    # 4. Deployment Dates
    for s in sources:
        url = str(s.get("url", ""))
        kind = str(s.get("kind", "")).lower()
        if kind == "deployment":
            fetched_at = s.get("fetched_at") or datetime.now(timezone.utc).isoformat()
            event_id = str(uuid5(NAMESPACE_URL, f"deploy:{url}"))
            events.append(
                TimelineEvent(
                    event_id=event_id,
                    category="deployment",
                    title=f"Deployment Observation: {url}",
                    start_date=str(fetched_at),
                    end_date=str(fetched_at),
                    source="deployment.inspection",
                    source_url=url,
                    details={"reachable": s.get("status") in ("observed", "reachable")},
                )
            )

    # 5. Credential Dates
    for i, cred in enumerate(credentials):
        c_dict = cred if isinstance(cred, dict) else (cred.to_dict() if hasattr(cred, "to_dict") else getattr(cred, "__dict__", {}))
        c_name = c_dict.get("credential_name") or c_dict.get("title") or c_dict.get("claim", f"Credential {i}")
        issue_d = c_dict.get("issue_date") or c_dict.get("issued_at") or c_dict.get("issued_date")
        exp_d = c_dict.get("expiration_date") or c_dict.get("expires_at")
        event_id = str(uuid5(NAMESPACE_URL, f"cred:{i}:{c_name}"))
        events.append(
            TimelineEvent(
                event_id=event_id,
                category="credential",
                title=f"Credential: {c_name}",
                start_date=str(issue_d) if issue_d else None,
                end_date=str(exp_d) if exp_d else None,
                source="credential.verification",
                details=c_dict,
            )
        )

    # 6. Publication Dates
    proj_claims = getattr(manifest, "project_claims", [])
    if isinstance(proj_claims, Sequence):
        for i, proj in enumerate(proj_claims):
            if isinstance(proj, Mapping):
                text = f"{proj.get('title', '')} {proj.get('description', '')}"
                m_arxiv = re.search(r"\barxiv\b(?::\s*|\.org/(?:abs|pdf)/)(\d{2})(\d{2})\.\d+", text, re.I)
                m_year = re.search(r"\b(published in|conference paper|ieee|acm|neurips|icml|cvpr)[^\n.]*\b(19\d{2}|20\d{2})\b", text, re.I)
                pub_year = None
                ref = "Publication"
                if m_arxiv:
                    # YYMM format in arXiv
                    pub_year = f"20{m_arxiv.group(1)}"
                    ref = f"arXiv:{m_arxiv.group(1)}{m_arxiv.group(2)}"
                elif m_year:
                    pub_year = m_year.group(2)
                    ref = m_year.group(0)[:60]

                if pub_year:
                    event_id = str(uuid5(NAMESPACE_URL, f"pub:{i}:{ref}"))
                    events.append(
                        TimelineEvent(
                            event_id=event_id,
                            category="publication",
                            title=f"Publication: {ref}",
                            start_date=pub_year,
                            end_date=pub_year,
                            source="resume.publication",
                            details={"project_title": proj.get("title")},
                        )
                    )

    return events


def detect_timeline_inconsistencies(
    events: Sequence[TimelineEvent],
    current_year: int = 2026,
) -> list[TimelineInconsistency]:
    """Identifies potential timeline inconsistencies without inferring dishonesty.

    Hardening Invariant:
    Strictly label: "timeline inconsistency requiring review".
    Do not infer dishonesty.
    """
    inconsistencies: list[TimelineInconsistency] = []

    for event in events:
        start_y = _parse_year(event.start_date)
        end_y = _parse_year(event.end_date)

        # 1. Inverted date range (start year > end year for non-credentials)
        if event.category != "credential" and start_y and end_y and start_y > end_y and not event.is_ongoing:
            inc_id = str(uuid5(NAMESPACE_URL, f"inv:{event.event_id}"))
            inconsistencies.append(
                TimelineInconsistency(
                    inconsistency_id=inc_id,
                    label=LABEL_TIMELINE_INCONSISTENCY,
                    inconsistency_type="inverted_date_range",
                    event_ids=[event.event_id],
                    explanation=(
                        f"In {event.category} declaration '{event.title}', start year ({start_y}) "
                        f"is observed after end year ({end_y}). Labeled as timeline inconsistency requiring review; "
                        f"do not infer dishonesty."
                    ),
                    severity="requires_review",
                )
            )

        # 2. Future dates (claimed dates past current year)
        future_year = start_y if (start_y and start_y > current_year) else (end_y if (end_y and end_y > current_year) else None)
        if future_year:
            inc_id = str(uuid5(NAMESPACE_URL, f"fut:{event.event_id}"))
            inconsistencies.append(
                TimelineInconsistency(
                    inconsistency_id=inc_id,
                    label=LABEL_TIMELINE_INCONSISTENCY,
                    inconsistency_type="future_date",
                    event_ids=[event.event_id],
                    explanation=(
                        f"Event '{event.title}' specifies a future year ({future_year} > {current_year}). "
                        f"Labeled as timeline inconsistency requiring review; do not infer dishonesty."
                    ),
                    severity="requires_review",
                )
            )

        # 3. Credential expired before issued
        if event.category == "credential" and start_y and end_y and end_y < start_y:
            inc_id = str(uuid5(NAMESPACE_URL, f"cred_exp:{event.event_id}"))
            inconsistencies.append(
                TimelineInconsistency(
                    inconsistency_id=inc_id,
                    label=LABEL_TIMELINE_INCONSISTENCY,
                    inconsistency_type="expired_before_issue",
                    event_ids=[event.event_id],
                    explanation=(
                        f"Credential '{event.title}' indicates expiration year ({end_y}) prior to issue year ({start_y}). "
                        f"Labeled as timeline inconsistency requiring review; do not infer dishonesty."
                    ),
                    severity="requires_review",
                )
            )

        # 4. Known technology release anachronisms
        raw_text = str(event.details.get("raw_text", "")).lower()
        if event.end_date and not event.is_ongoing:
            period_end_year = end_y or start_y
            if period_end_year:
                for tech, rel_year in TECH_RELEASE_YEARS.items():
                    if re.search(r"\b" + re.escape(tech) + r"\b", raw_text) and period_end_year < rel_year:
                        inc_id = str(uuid5(NAMESPACE_URL, f"anach:{event.event_id}:{tech}"))
                        inconsistencies.append(
                            TimelineInconsistency(
                                inconsistency_id=inc_id,
                                label=LABEL_TIMELINE_INCONSISTENCY,
                                inconsistency_type="anachronism",
                                event_ids=[event.event_id],
                                explanation=(
                                    f"Declaration '{event.title}' references '{tech}' in a timeframe ending in {period_end_year}, "
                                    f"prior to the technology's initial public release ({rel_year}). "
                                    f"Labeled as timeline inconsistency requiring review; do not infer dishonesty."
                                ),
                                severity="requires_review",
                            )
                        )

    return inconsistencies


def build_candidate_timeline(
    intake_or_manifest: Any,
    sources: Sequence[Mapping[str, Any]] = (),
    credentials: Sequence[Any] = (),
    current_year: int = 2026,
) -> CandidateTimeline:
    """Builds a complete candidate chronology, ordered chronologically, with inconsistency detection."""
    events = extract_timeline_events(
        intake_or_manifest=intake_or_manifest,
        sources=sources,
        credentials=credentials,
    )

    # Sort events by earliest available year or date string
    def sort_key(e: TimelineEvent) -> tuple[int, str]:
        y = _parse_year(e.start_date) or _parse_year(e.end_date) or 9999
        return (y, e.start_date or "")

    sorted_events = sorted(events, key=sort_key)

    inconsistencies = detect_timeline_inconsistencies(sorted_events, current_year=current_year)

    years = [_parse_year(e.start_date) for e in sorted_events if _parse_year(e.start_date)]
    earliest = str(min(years)) if years else None
    latest = str(max(years)) if years else None

    return CandidateTimeline(
        events=sorted_events,
        inconsistencies=inconsistencies,
        earliest_date=earliest,
        latest_date=latest,
    )
