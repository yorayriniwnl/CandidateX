"""Candidate evidence manifest builder implementing the paper-mandated extraction pipeline."""

import re
from typing import Any

from cci.domain.contracts import CandidateManifest
from cci.intake.canonicalizer import classify_url, deduplicate_urls
from cci.intake.parsers import ParsedDocument

EMAIL_REGEX = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")

# Standard resume section headers
SECTION_PATTERNS = {
    "skills": re.compile(
        r"^(?:technical\s+)?skills\b|^(?:core\s+)?technologies\b|^competencies\b",
        re.IGNORECASE,
    ),
    "projects": re.compile(
        r"^(?:personal\s+|academic\s+|selected\s+)?projects\b", re.IGNORECASE
    ),
    "experience": re.compile(
        r"^(?:work\s+|professional\s+)?experience\b|^employment\b|^history\b",
        re.IGNORECASE,
    ),
    "education": re.compile(r"^education\b|^academics\b", re.IGNORECASE),
    "summary": re.compile(r"^(?:(?:professional|personal|career)\s+)?(?:summary|profile|objective)\b", re.IGNORECASE),
    "certifications": re.compile(r"^(?:certifications?|certificates?|credentials|licenses)(?:\s|$)", re.IGNORECASE),
    "achievements": re.compile(r"^(?:achievements?|awards?|honors?|publications?|volunteering|languages|interests)(?:\s|$)", re.IGNORECASE),
}


def extract_candidate_name(text: str) -> str:
    """Extracts candidate display name from top header lines of CV."""
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    if not lines:
        return "Unknown Candidate"

    # Take first non-empty line that does not look like an email, phone, or URL
    for line in lines[:15]:
        if any(pattern.match(line) for pattern in SECTION_PATTERNS.values()):
            # Do not use section content as a person's identity.
            break
        if EMAIL_REGEX.search(line):
            continue
        if re.search(r"https?://|www\.|\+?\d[\d\s-]{7,}", line):
            continue
        # Clean potential title or label noise
        clean_name = re.sub(
            r"^(resume|curriculum vitae|cv)[:\s-]*", "", line, flags=re.IGNORECASE
        ).strip()
        if len(clean_name) > 1 and len(clean_name.split()) <= 5:
            return clean_name

    return 'Unknown Candidate'


def extract_candidate_email(text: str) -> str | None:
    """Extracts primary contact email."""
    match = EMAIL_REGEX.search(text)
    if match:
        return match.group(0).lower()
    return None


def segment_sections(text: str) -> dict[str, list[str]]:
    """Segments resume text into standard sections based on detected headings."""
    sections: dict[str, list[str]] = {
        "header": [],
        "skills": [],
        "projects": [],
        "experience": [],
        "education": [],
        "other": [],
        "summary": [],
        "certifications": [],
        "achievements": [],
    }

    current_section = "header"
    lines = [line.strip() for line in text.split("\n") if line.strip()]

    for line in lines:
        matched_section = None
        for sec_name, pattern in SECTION_PATTERNS.items():
            if pattern.match(line) and len(line.split()) <= 4:
                matched_section = sec_name
                break

        if matched_section:
            current_section = matched_section
        else:
            sections[current_section].append(line)

    return sections


def extract_skills_from_section(skill_lines: list[str]) -> list[str]:
    """Extracts normalized technical skill tokens from skills section."""
    skills = []
    for line in skill_lines:
        # Preserve parenthesized groups and CI/CD; strip category labels first.
        line = re.sub(r'^[A-Za-z &/+-]+:\s*', '', line)
        parts = re.split(r'[,•|;\t]+(?![^()]*\))', line)
        for part in parts:
            clean = part.strip()
            # Remove category labels like "Languages:", "Frameworks:"
            clean = re.sub(r"^[A-Za-z\s]+:\s*", "", clean).strip()
            if 1 <= len(clean) <= 120 and not re.match(r"^\d+$", clean):
                if clean not in skills:
                    skills.append(clean)
    return skills


def extract_project_claims(project_lines: list[str]) -> list[dict[str, Any]]:
    """Groups project lines into structured project claim records."""
    claims: list[dict[str, Any]] = []
    current_proj: dict[str, Any] | None = None

    for line in project_lines:
        # Project titles are typically short or contain bullet indicators
        has_date = bool(re.search(r'\b(?:19|20)\d{2}\b|\bPresent\b', line))
        title = not re.search(r'https?://|github\.com|\s\|\s|^(?:Founder|Role|Contributor)\b', line, re.I) and not line.startswith(('-', '*', '•'))
        if title and (('\t' in line and has_date) or (len(line.split()) <= 6 and not line.endswith('.'))):
            if current_proj:
                claims.append(current_proj)
            current_proj = {
                "title": line,
                "description": "",
                "technologies": [],
            }
        else:
            if current_proj is not None:
                if current_proj["description"]:
                    current_proj["description"] += " " + line
                else:
                    current_proj["description"] = line

    if current_proj:
        claims.append(current_proj)

    return claims


def build_candidate_manifest(
    document: ParsedDocument,
    display_name_override: str | None = None,
) -> CandidateManifest:
    """Builds a verified CandidateManifest following the paper-mandated order:

    1. Embedded hyperlinks
    2. Visible URLs
    3. Deterministic URL/platform classification
    4. Structured extraction & normalization
    5. Validation
    6. Canonicalization / deduplication
    """
    # 1 & 2. Gather URLs: embedded first, then visible
    raw_urls = list(document.embedded_urls) + list(document.visible_urls)

    # 3 & 6. Canonicalize and deduplicate
    canonical_urls = deduplicate_urls(raw_urls)

    # Classify URLs strictly by platform
    github_urls: list[str] = []
    linkedin_urls: list[str] = []
    coding_profile_urls: list[str] = []
    credential_urls: list[str] = []
    deployment_urls: list[str] = []
    portfolio_urls: list[str] = []
    project_links: list[str] = []

    for url in canonical_urls:
        cat = classify_url(url)
        if cat == "github":
            github_urls.append(url)
        elif cat == "linkedin":
            linkedin_urls.append(url)
        elif cat == "coding_profile":
            coding_profile_urls.append(url)
        elif cat == "credential":
            credential_urls.append(url)
        elif cat == "deployment":
            deployment_urls.append(url)
        elif cat == "portfolio":
            portfolio_urls.append(url)
        else:
            project_links.append(url)

    # 4. Structured extraction from parsed text
    name = display_name_override or extract_candidate_name(document.raw_text)
    email = extract_candidate_email(document.raw_text)

    sections = segment_sections(document.raw_text)
    claimed_skills = extract_skills_from_section(sections.get("skills", []))
    project_claims = extract_project_claims(sections.get("projects", []))
    experience_claims = [{"text": line} for line in sections.get("experience", [])[:10]]

    # 5. Build and validate against frozen domain contract
    return CandidateManifest(
        display_name=name,
        email=email,
        github_urls=github_urls,
        project_links=project_links,
        deployment_urls=deployment_urls,
        portfolio_urls=portfolio_urls,
        coding_profile_urls=coding_profile_urls,
        credential_urls=credential_urls,
        linkedin_urls=linkedin_urls,
        claimed_skills=claimed_skills,
        project_claims=project_claims,
        experience_claims=experience_claims,
    )
