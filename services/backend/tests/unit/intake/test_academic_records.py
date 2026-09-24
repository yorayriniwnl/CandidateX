"""Tests for Fix 15: Rebuild Academic Record Parsing into Multi-line Entities."""

import pytest

from cci.domain.contracts import AcademicRecord, CandidateManifest
from cci.intake.academic import (
    group_education_lines,
    parse_academic_record_chunk,
    parse_academic_records,
)
from cci.live.claims import build_academic_records
from cci.live.contracts import ResumeIntake, ResumeReview


DOC_HASH = "f" * 64


def test_multiline_academic_entity_grouped_into_one():
    """Requirement: Support multi-line academic entities such as University, Degree, Branch, 2023-2027, CGPA 7.0/10."""
    lines = [
        "State University",
        "Bachelor of Technology",
        "Computer Science & Engineering",
        "2023-2027",
        "CGPA 7.0/10",
    ]

    records = parse_academic_records(lines, source_document_hash=DOC_HASH)
    assert len(records) == 1, "Multi-line education must be grouped into exactly ONE AcademicRecord"

    record = records[0]
    assert record.institution == "State University"
    assert record.degree == "Bachelor of Technology"
    assert record.branch == "Computer Science & Engineering"
    assert record.start_year == 2023
    assert record.end_year == 2027
    assert record.years == ["2023", "2027"]
    assert record.cgpa == 7.0
    assert record.scale == 10.0
    assert record.claimed_cgpa == {"value": 7.0, "scale": 10.0}
    assert record.source_lines == lines
    assert record.verification_state == "unverified"
    assert record.status == "self_reported"


def test_single_line_pipe_separated_backward_compatibility():
    """Verify single-line pipe separated format from test_comprehensive_live.py continues to work."""
    lines = ["B.Tech Computer Science | Example University | CGPA: 8.4/10 | 2023 - 2027"]
    intake = ResumeIntake(
        manifest=CandidateManifest(display_name="Jane Doe", claimed_skills=[], project_claims=[]),
        document_sha256=DOC_HASH,
        filename="resume.docx",
        resume_review=ResumeReview(sections={"education": lines}),
    )

    academic_dicts = build_academic_records(intake)
    assert len(academic_dicts) == 1

    academic = academic_dicts[0]
    assert academic["status"] == "self_reported"
    assert academic["degree_text"].lower().replace(" ", "").startswith("b.tech")
    assert academic["claimed_cgpa"] == {"value": 8.4, "scale": 10.0}
    assert academic["years"] == ["2023", "2027"]
    assert academic["institution"] == "Example University"
    assert "Computer Science" in (academic["branch"] or "")


def test_multiple_degrees_in_resume():
    """Requirement: Multiple degrees (e.g. Master's + Bachelor's) must be grouped into separate records."""
    lines = [
        "Massachusetts Institute of Technology (MIT)",
        "Master of Science in Electrical Engineering",
        "2021 - 2023",
        "Stanford University",
        "Bachelor of Science in Computer Science",
        "2017 - 2021",
        "CGPA: 3.92/4.0",
    ]

    records = parse_academic_records(lines, source_document_hash=DOC_HASH)
    assert len(records) == 2, "Must produce 2 distinct academic records"

    ms = records[0]
    assert "MIT" in ms.institution or "Technology" in ms.institution
    assert "Master" in ms.degree
    assert ms.start_year == 2021
    assert ms.end_year == 2023

    bs = records[1]
    assert "Stanford" in bs.institution
    assert "Bachelor" in bs.degree
    assert bs.start_year == 2017
    assert bs.end_year == 2021
    assert bs.cgpa == 3.92
    assert bs.scale == 4.0


def test_do_not_infer_grade_conversions():
    """Invariant: Do not infer grade conversions (e.g. CGPA to percentage, scale 10 to 4)."""
    # 1. CGPA 7.0/10 must NOT infer percentage
    lines_cgpa = [
        "Example College",
        "B.Sc in Mathematics",
        "2020 - 2023",
        "CGPA 7.0/10",
    ]
    rec1 = parse_academic_records(lines_cgpa)[0]
    assert rec1.cgpa == 7.0
    assert rec1.scale == 10.0
    assert rec1.percentage is None, "CGPA must not be converted to percentage"

    # 2. 85.5% must NOT infer CGPA
    lines_pct = [
        "Example College",
        "B.Sc in Mathematics",
        "2020 - 2023",
        "Percentage: 85.5%",
    ]
    rec2 = parse_academic_records(lines_pct)[0]
    assert rec2.percentage == 85.5
    assert rec2.cgpa is None, "Percentage must not be converted to CGPA"
    assert rec2.scale is None


def test_do_not_infer_degree_equivalence():
    """Invariant: Do not infer degree equivalence (preserve verbatim degree declaration)."""
    lines_btech = ["Indian Institute of Technology", "B.Tech in Computer Science", "2019-2023"]
    lines_bs = ["University of Washington", "Bachelor of Science in Informatics", "2019-2023"]
    lines_diploma = ["City Polytechnic", "Diploma in Mechanical Engineering", "2016-2019"]

    r1 = parse_academic_records(lines_btech)[0]
    r2 = parse_academic_records(lines_bs)[0]
    r3 = parse_academic_records(lines_diploma)[0]

    assert r1.degree == "B.Tech", "B.Tech must not be rewritten as Bachelor of Science"
    assert "Bachelor of Science" in r2.degree
    assert r3.degree == "Diploma", "Diploma must not be promoted to degree"


def test_do_not_verify_institution_attendance_without_evidence():
    """Invariant: Do not verify institution attendance without independent evidence."""
    lines = [
        "Harvard University",
        "Bachelor of Arts in Economics",
        "2018 - 2022",
        "CGPA: 3.95/4.0",
    ]
    record = parse_academic_records(lines)[0]
    assert record.verification_state == "unverified"
    assert record.status == "self_reported"
    assert record.evidence_sources == []
    assert any("No institution, transcript" in lim for lim in record.limitations)


def test_coursework_and_honors_extraction():
    """Verify coursework and honors are parsed and preserved in structured fields."""
    lines = [
        "University of Illinois Urbana-Champaign",
        "B.S. in Computer Science",
        "2019 - 2023",
        "CGPA: 3.8/4.0",
        "Honors: Dean's List, Magna Cum Laude",
        "Coursework: Distributed Systems, Operating Systems, Computer Architecture",
    ]
    record = parse_academic_records(lines)[0]
    assert record.cgpa == 3.8
    assert record.scale == 4.0
    assert len(record.honors) >= 2
    assert any("Dean's List" in h for h in record.honors)
    assert any("Magna Cum Laude" in h for h in record.honors)
    assert len(record.coursework) == 3
    assert "Distributed Systems" in record.coursework
    assert "Operating Systems" in record.coursework
    assert "Computer Architecture" in record.coursework


def test_adversarial_layout_separated_by_blank_lines():
    """Adversarial: Multi-line layout with empty lines between fields."""
    lines = [
        "State University",
        "",
        "B.Tech in Artificial Intelligence",
        "",
        "2020 - 2024",
        "",
        "CGPA: 9.1/10.0",
    ]
    records = parse_academic_records(lines)
    assert len(records) == 1
    assert records[0].institution == "State University"
    assert records[0].cgpa == 9.1
    assert records[0].scale == 10.0


def test_adversarial_layout_noisy_delimiters_and_case():
    """Adversarial: Mixed delimiters, lowercase words, and irregular spacing."""
    lines = [
        "--- california institute of technology ---",
        "ph.d. in physics | 2018 - 2023",
        "relevant coursework: quantum mechanics, statistical field theory",
    ]
    records = parse_academic_records(lines)
    assert len(records) == 1
    rec = records[0]
    assert "california institute of technology" in rec.institution.lower()
    assert "ph.d." in rec.degree.lower()
    assert rec.start_year == 2018
    assert rec.end_year == 2023
    assert len(rec.coursework) == 2


def test_adversarial_secondary_school_alongside_university():
    """Adversarial: High school CBSE/ICSE board exam alongside University degree."""
    lines = [
        "National Institute of Technology",
        "B.Tech in Electrical Engineering",
        "2020 - 2024",
        "CGPA: 8.2/10",
        "Delhi Public School",
        "Senior Secondary (CBSE Class XII)",
        "2018 - 2020",
        "Percentage: 94.6%",
    ]
    records = parse_academic_records(lines)
    assert len(records) == 2

    nit = records[0]
    assert "National Institute of Technology" in nit.institution
    assert nit.degree == "B.Tech"
    assert nit.cgpa == 8.2

    school = records[1]
    assert "Delhi Public School" in school.institution
    assert school.percentage == 94.6
    assert school.cgpa is None  # no grade conversion
