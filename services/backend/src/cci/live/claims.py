"""Deterministic claim and academic-record extraction for live analysis.

This module converts resume declarations into stable, inspectable claim records. It
never upgrades a declaration to verified evidence on its own.
"""
from __future__ import annotations

import hashlib
import re
from typing import Any

from cci.live.contracts import ResumeIntake

YEAR_RE = re.compile(r"\b(?:19|20)\d{2}\b")
CGPA_RE = re.compile(
    r"\b(?:cgpa|gpa)\s*[:=-]?\s*(\d+(?:\.\d+)?)\s*(?:/\s*(\d+(?:\.\d+)?))?",
    re.IGNORECASE,
)
PERCENT_RE = re.compile(r"\b(\d{1,3}(?:\.\d+)?)\s*%")
DEGREE_RE = re.compile(
    r"\b(B\.?\s*Tech|B\.?\s*E\.?|B\.?\s*Sc|M\.?\s*Tech|M\.?\s*S\.?|M\.?\s*Sc|"
    r"Bachelor(?:'s)?|Master(?:'s)?|Ph\.?D\.?|Diploma)\b",
    re.IGNORECASE,
)


def _claim_id(category: str, section: str, text: str, ordinal: int) -> str:
    payload = f"{category}\0{section}\0{ordinal}\0{text.strip()}".encode("utf-8")
    return "clm_" + hashlib.sha256(payload).hexdigest()[:20]


def _record_id(text: str, ordinal: int) -> str:
    payload = f"academic\0{ordinal}\0{text.strip()}".encode("utf-8")
    return "acad_" + hashlib.sha256(payload).hexdigest()[:20]


def _quantified(text: str) -> bool:
    return bool(
        re.search(
            r"\d+(?:\.\d+)?\s*%|\b\d+[+-]?\s+(?:users|tests|projects|applications|"
            r"points|requests|transactions|tx|repositories|repos|commits|stars|hours|days)\b",
            text,
            re.IGNORECASE,
        )
    )


def build_claim_ledger(intake: ResumeIntake) -> list[dict[str, Any]]:
    """Return stable resume claims without asserting that any are true."""
    claims: list[dict[str, Any]] = []
    sections = intake.resume_review.sections

    def add(category: str, section: str, text: str, ordinal: int, **extra: Any) -> None:
        clean = re.sub(r"\s+", " ", text).strip()
        if not clean:
            return
        claims.append(
            {
                "claim_id": _claim_id(category, section, clean, ordinal),
                "category": category,
                "claim": clean,
                "source": "resume",
                "section": section,
                "status": "self_reported",
                "is_quantified": _quantified(clean),
                **extra,
            }
        )

    for i, skill in enumerate(intake.manifest.claimed_skills):
        add("skill", "skills", skill, i, normalized_subject=skill)

    for section, category in (
        ("education", "academic"),
        ("certifications", "credential"),
        ("experience", "experience"),
        ("achievements", "achievement"),
    ):
        for i, line in enumerate(sections.get(section, [])):
            add(category, section, line, i)

    for i, project in enumerate(intake.manifest.project_claims):
        title = str(project.get("title", "")).strip()
        description = str(project.get("description", "")).strip()
        add(
            "project",
            "projects",
            " — ".join(part for part in (title, description) if part),
            i,
            project_title=title,
        )

    return claims


def build_academic_records(intake: ResumeIntake) -> list[dict[str, Any]]:
    """Extract conservative structured fields from education declarations.

    The raw line remains authoritative. Regex-derived fields are labelled as
    resume-declared and are never converted into independent verification.
    """
    records: list[dict[str, Any]] = []
    for i, line in enumerate(intake.resume_review.sections.get("education", [])):
        clean = re.sub(r"\s+", " ", line).strip()
        if not clean:
            continue

        years = YEAR_RE.findall(clean)
        cgpa_match = CGPA_RE.search(clean)
        percentage_match = PERCENT_RE.search(clean)
        degree_match = DEGREE_RE.search(clean)

        cgpa = None
        if cgpa_match:
            cgpa = {
                "value": float(cgpa_match.group(1)),
                "scale": float(cgpa_match.group(2)) if cgpa_match.group(2) else None,
            }

        records.append(
            {
                "record_id": _record_id(clean, i),
                "raw_claim": clean,
                "status": "self_reported",
                "degree_text": degree_match.group(0) if degree_match else None,
                "years": years,
                "claimed_cgpa": cgpa,
                "claimed_percentage": float(percentage_match.group(1)) if percentage_match else None,
                "evidence_sources": [],
                "limitations": [
                    "Structured fields are parsed from the resume declaration only.",
                    "No institution, transcript, grade, or enrollment verification is implied.",
                ],
            }
        )
    return records
