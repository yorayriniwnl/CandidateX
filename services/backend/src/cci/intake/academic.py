"""Multi-line academic record parsing and conservative entity extraction.

Under Fix 15:
- Education is parsed as grouped multi-line `AcademicRecord` entities instead of disconnected lines.
- Grouped fields include institution, degree, branch, start_year, end_year, cgpa, scale,
  percentage, coursework, honors, source_lines, and verification_state.
- Strict Invariants:
  1. Do not infer grade conversions (e.g. CGPA to percentage or scale conversions).
  2. Do not infer degree equivalence (e.g. B.Tech is not rewritten as B.S.).
  3. Do not verify institution attendance without evidence (verification_state remains unverified).
"""

from __future__ import annotations

import hashlib
import re
from typing import Any

from cci.domain.contracts import AcademicRecord

YEAR_RE = re.compile(r"\b(?:19|20)\d{2}\b")
YEAR_RANGE_RE = re.compile(
    r"\b((?:19|20)\d{2})\s*(?:-|–|—|to)\s*((?:19|20)\d{2}|present|current|expected)\b",
    re.IGNORECASE,
)
CGPA_RE = re.compile(
    r"\b(?:cgpa|gpa|grade)\s*[:=-]?\s*(\d+(?:\.\d+)?)\s*(?:/\s*(\d+(?:\.\d+)?))?\b",
    re.IGNORECASE,
)
FRACTION_CGPA_RE = re.compile(
    r"\b(\d+(?:\.\d+)?)\s*/\s*(\d+(?:\.\d+)?)\s*(?:cgpa|gpa)?\b",
    re.IGNORECASE,
)
PERCENT_RE = re.compile(r"\b(\d{1,3}(?:\.\d+)?)\s*%")
PERCENT_EXPLICIT_RE = re.compile(
    r"\bpercentage\s*[:=-]?\s*(\d{1,3}(?:\.\d+)?)\b",
    re.IGNORECASE,
)

DEGREE_PATTERNS = [
    # Explicit full titles
    re.compile(r"\b(?:Bachelor(?:\s+of\s+[A-Za-z\s]+)?|B\.?\s*Tech\.?|B\.?\s*E\.?|B\.?\s*Sc\.?|B\.?\s*S\.?|B\.?\s*A\.?|BBA|BCA|B\.?\s*Com\.?)(?!\w)", re.IGNORECASE),
    re.compile(r"\b(?:Master(?:\s+of\s+[A-Za-z\s]+)?|M\.?\s*Tech\.?|M\.?\s*E\.?|M\.?\s*Sc\.?|M\.?\s*S\.?|M\.?\s*A\.?|MBA|MCA)(?!\w)", re.IGNORECASE),
    re.compile(r"\b(?:Doctor(?:\s+of\s+Philosophy)?|Ph\.?\s*D\.?|PhD|Doctorate)(?!\w)", re.IGNORECASE),
    re.compile(r"\b(?:Associate(?:\s+of\s+[A-Za-z\s]+)?|Associate\s+Degree)(?!\w)", re.IGNORECASE),
    re.compile(r"\b(?:Diploma|High\s+School|Secondary\s+School|Senior\s+Secondary|CBSE|ICSE|A-Levels|IB\s+Diploma)(?!\w)", re.IGNORECASE),
]

INSTITUTION_INDICATORS = re.compile(
    r"\b(?:University|College|Institute|School|Academy|Polytechnic|Campus|Faculty|"
    r"MIT|IIT|BITS|Stanford|Harvard|Caltech|Oxford|Cambridge|CMU|UCLA|NYU|Columbia|"
    r"Princeton|Yale|Cornell|Purdue|Berkeley)\b",
    re.IGNORECASE,
)

COURSEWORK_RE = re.compile(
    r"^(?:relevant\s+)?(?:coursework|courses|core\s+subjects)\s*[:=-]?\s*(.*)",
    re.IGNORECASE,
)
HONORS_RE = re.compile(
    r"^(?:honors?|awards?|distinctions?|scholarships?)\s*[:=-]?\s*(.*)",
    re.IGNORECASE,
)
HONORS_KEYWORDS = re.compile(
    r"\b(?:Dean'?s\s+List|Dean'?s\s+Honor\s+Roll|Cum\s+Laude|Magna\s+Cum\s+Laude|"
    r"Summa\s+Cum\s+Laude|First\s+Class(?:\s+with\s+Distinction)?|Gold\s+Medal(?:ist)?|"
    r"Merit\s+Scholar(?:ship)?)\b",
    re.IGNORECASE,
)

KNOWN_BRANCHES = [
    "Computer Science and Engineering",
    "Computer Science & Engineering",
    "Computer Science",
    "Information Technology",
    "Software Engineering",
    "Electrical and Electronics Engineering",
    "Electrical Engineering",
    "Electronics and Communication",
    "Mechanical Engineering",
    "Civil Engineering",
    "Data Science",
    "Artificial Intelligence",
    "Machine Learning",
    "Cybersecurity",
    "Information Systems",
    "Mathematics",
    "Physics",
    "Chemistry",
    "Economics",
    "Business Administration",
    "Finance",
    "Biotechnology",
]


def _match_degree(text: str) -> str | None:
    """Find verbatim degree mention without inferring equivalence."""
    for pattern in DEGREE_PATTERNS:
        match = pattern.search(text)
        if match:
            return match.group(0).strip()
    return None


def _is_institution_line(text: str) -> bool:
    """Check if line designates an educational institution."""
    clean = re.sub(r"^[•\-\*|\s]+", "", text).strip()
    if INSTITUTION_INDICATORS.search(clean):
        # Ensure it is not merely a degree line mentioning a university in passing
        # e.g. "B.Tech from Stanford University" has both; it's acceptable
        return True
    return False


def _has_degree(text: str) -> bool:
    return _match_degree(text) is not None


def _extract_branch(text: str, degree_text: str | None = None) -> str | None:
    """Extract branch / major without degree equivalence."""
    clean = text
    if degree_text:
        # Avoid matching words inside the degree title
        clean = clean.replace(degree_text, "")

    # Look for "in <Branch>" or "Major: <Branch>"
    in_match = re.search(
        r"\b(?:in|major(?:ing)?\s+in|specialization\s+in|branch\s*[:=-]?|department\s+of)\s+([^,|;–—\n]+)",
        clean,
        re.IGNORECASE,
    )
    if in_match:
        cand = in_match.group(1).strip()
        # Clean off trailing dates, gpa, or keywords
        cand = re.sub(r"\b(?:19|20)\d{2}\b.*", "", cand).strip()
        cand = re.sub(r"\b(?:cgpa|gpa|grade|with|honors?).*", "", cand, flags=re.IGNORECASE).strip()
        if len(cand) > 1:
            return cand

    # Match known branches
    for branch in KNOWN_BRANCHES:
        if re.search(rf"\b{re.escape(branch)}\b", clean, re.IGNORECASE):
            return branch

    return None


def _clean_field(val: str | None) -> str | None:
    if not val:
        return None
    cleaned = re.sub(r"^[•\-\*|:,\s]+|[•\-\*|:,\s]+$", "", val).strip()
    return cleaned if cleaned else None


def _generate_record_id(
    source_document_hash: str | None,
    institution: str | None,
    degree: str | None,
    start_year: int | None,
    end_year: int | None,
    raw_lines: list[str],
) -> str:
    doc_hash = (source_document_hash or "").strip().lower()
    inst = (institution or "").strip().lower()
    deg = (degree or "").strip().lower()
    sy = str(start_year or "")
    ey = str(end_year or "")
    text_sample = raw_lines[0].strip().lower() if raw_lines else ""

    payload = f"{doc_hash}\0{inst}\0{deg}\0{sy}\0{ey}\0{text_sample}".encode("utf-8")
    return "acad_" + hashlib.sha256(payload).hexdigest()[:20]


def group_education_lines(lines: list[str]) -> list[list[str]]:
    """Group sequential lines into distinct academic entity chunks."""
    cleaned = [re.sub(r"\s+", " ", l).strip() for l in lines if l.strip()]
    if not cleaned:
        return []

    chunks: list[list[str]] = []
    current_chunk: list[str] = []
    chunk_has_inst = False
    chunk_has_deg = False

    for line in cleaned:
        is_inst = _is_institution_line(line)
        is_deg = _has_degree(line)

        # A new entity starts if current chunk already has an institution and this line is an institution,
        # or if current chunk already has a degree and this line is a degree.
        is_boundary = False
        if current_chunk:
            if is_inst and chunk_has_inst:
                is_boundary = True
            elif is_deg and chunk_has_deg:
                is_boundary = True

        if is_boundary:
            chunks.append(current_chunk)
            current_chunk = [line]
            chunk_has_inst = is_inst
            chunk_has_deg = is_deg
        else:
            current_chunk.append(line)
            if is_inst:
                chunk_has_inst = True
            if is_deg:
                chunk_has_deg = True

    if current_chunk:
        chunks.append(current_chunk)

    return chunks


def parse_academic_record_chunk(
    chunk_lines: list[str],
    source_document_hash: str | None = None,
) -> AcademicRecord:
    """Parse a multi-line chunk into a unified AcademicRecord."""
    combined_text = " | ".join(chunk_lines)

    institution: str | None = None
    degree: str | None = None
    branch: str | None = None
    start_year: int | None = None
    end_year: int | None = None
    cgpa: float | None = None
    scale: float | None = None
    percentage: float | None = None
    coursework: list[str] = []
    honors: list[str] = []

    # 1. Coursework extraction
    for line in chunk_lines:
        cw_match = COURSEWORK_RE.match(line)
        if cw_match:
            raw_courses = cw_match.group(1)
            parts = [re.sub(r"^[•\-\*|\s]+", "", p).strip() for p in re.split(r"[,;•|]", raw_courses) if p.strip()]
            coursework.extend(parts)

    # 2. Honors extraction
    for line in chunk_lines:
        h_match = HONORS_RE.match(line)
        if h_match:
            raw_honors = h_match.group(1)
            parts = [p.strip() for p in re.split(r"[,;•|]", raw_honors) if p.strip()]
            honors.extend(parts)
        else:
            hk_matches = HONORS_KEYWORDS.findall(line)
            for hk in hk_matches:
                if hk not in honors:
                    honors.append(hk)

    # 3. Year extraction (range or individual years)
    range_match = YEAR_RANGE_RE.search(combined_text)
    if range_match:
        start_year = int(range_match.group(1))
        end_str = range_match.group(2)
        if end_str.isdigit():
            end_year = int(end_str)
    else:
        all_years = [int(y) for y in YEAR_RE.findall(combined_text)]
        if len(all_years) >= 2:
            start_year = min(all_years)
            end_year = max(all_years)
        elif len(all_years) == 1:
            end_year = all_years[0]

    # 4. CGPA and Scale extraction (DO NOT infer grade conversions)
    cgpa_match = CGPA_RE.search(combined_text)
    if cgpa_match:
        cgpa = float(cgpa_match.group(1))
        if cgpa_match.group(2):
            scale = float(cgpa_match.group(2))
    else:
        frac_match = FRACTION_CGPA_RE.search(combined_text)
        if frac_match:
            cgpa = float(frac_match.group(1))
            scale = float(frac_match.group(2))

    # 5. Percentage extraction (DO NOT infer grade conversions to/from CGPA)
    pct_explicit = PERCENT_EXPLICIT_RE.search(combined_text)
    if pct_explicit:
        percentage = float(pct_explicit.group(1))
    else:
        pct_match = PERCENT_RE.search(combined_text)
        if pct_match:
            percentage = float(pct_match.group(1))

    # 6. Degree extraction (verbatim; NO degree equivalence)
    for line in chunk_lines:
        deg = _match_degree(line)
        if deg:
            degree = deg
            break

    # 7. Branch extraction
    for line in chunk_lines:
        b = _extract_branch(line, degree)
        if b:
            branch = b
            break

    # 8. Institution extraction
    for line in chunk_lines:
        if _is_institution_line(line):
            # If the line contains pipes or delimiters, pick the institution part
            parts = [p.strip() for p in re.split(r"[|–—]", line) if p.strip()]
            for p in parts:
                if INSTITUTION_INDICATORS.search(p) and not _has_degree(p):
                    institution = _clean_field(p)
                    break
            if not institution and INSTITUTION_INDICATORS.search(line):
                # Clean off degree/dates if mixed on one line
                inst_cand = line
                if degree:
                    inst_cand = inst_cand.replace(degree, "")
                if branch:
                    inst_cand = inst_cand.replace(branch, "")
                inst_cand = re.sub(r"\b(?:19|20)\d{2}\b.*", "", inst_cand)
                inst_cand = re.sub(r"\b(?:cgpa|gpa|grade|\d+(?:\.\d+)?\s*%).*", "", inst_cand, flags=re.IGNORECASE)
                institution = _clean_field(inst_cand)
            if institution:
                break

    # Fallback: If line 0 looks like an institution name (without degree keywords)
    if not institution and chunk_lines:
        first_line = chunk_lines[0].strip()
        if not _has_degree(first_line) and not YEAR_RE.search(first_line) and not CGPA_RE.search(first_line):
            institution = _clean_field(first_line)

    # 9. Clean branch if identical to degree or institution
    if branch and institution and branch.lower() in institution.lower():
        branch = None

    record_id = _generate_record_id(
        source_document_hash=source_document_hash,
        institution=institution,
        degree=degree,
        start_year=start_year,
        end_year=end_year,
        raw_lines=chunk_lines,
    )

    return AcademicRecord(
        record_id=record_id,
        institution=institution,
        degree=degree,
        branch=branch,
        start_year=start_year,
        end_year=end_year,
        cgpa=cgpa,
        scale=scale,
        percentage=percentage,
        coursework=coursework,
        honors=honors,
        source_lines=chunk_lines,
        verification_state="unverified",
        status="self_reported",
    )


def parse_academic_records(
    lines: list[str],
    source_document_hash: str | None = None,
) -> list[AcademicRecord]:
    """Parse raw resume education section lines into unified AcademicRecord entities."""
    chunks = group_education_lines(lines)
    records: list[AcademicRecord] = []
    for chunk in chunks:
        record = parse_academic_record_chunk(chunk, source_document_hash=source_document_hash)
        records.append(record)
    return records
