from cci.intake.manifest import extract_candidate_name, extract_skills_from_section
from cci.intake.technology import contains_technology


def test_technology_matching_respects_token_boundaries():
    assert contains_technology("JavaScript and TypeScript", "JavaScript")
    assert not contains_technology("JavaScript", "Java")
    assert contains_technology("Built with C++ and CI/CD", "C++")
    assert contains_technology("Built with C++ and CI/CD", "CI/CD")


def test_candidate_name_rejects_job_title_header():
    assert extract_candidate_name("Senior Software Engineer\nSkills\nPython") == "Unknown Candidate"


def test_skill_extraction_deduplicates_aliases_without_losing_display_text():
    skills = extract_skills_from_section(["React.js, React, C++, CI/CD"])
    assert skills == ["React.js", "C++", "CI/CD"]
