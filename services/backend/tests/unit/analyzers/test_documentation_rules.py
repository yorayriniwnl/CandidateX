"""Stable metadata and scores for documentation evidence."""

import pytest

from cci.analyzers.documentation.architecture import (
    analyze_adr,
    analyze_layer_boundaries,
    analyze_openapi_spec,
    analyze_readme,
)

REPO_URL = "https://github.com/test/project"
COMMIT_SHA = "abc123"


@pytest.mark.parametrize("content, expected", [
    ("# Getting Started\n", {"candidatex.docs.readme_setup": 78.0}),
    ("```mermaid\ngraph TD\n```", {"candidatex.docs.readme_architecture_diagram": 85.0}),
    ("# Setup\n\n![architecture diagram](arch.png)", {
        "candidatex.docs.readme_setup": 78.0,
        "candidatex.docs.readme_architecture_diagram": 85.0,
    }),
])
def test_readme_rule_metadata_and_scores(content, expected):
    evidence = analyze_readme(content, "README.md", REPO_URL, COMMIT_SHA)
    assert {ev.signal_rule_id: ev.technical_signal_strength for ev in evidence} == expected
    assert all(ev.signal_rule_version == "1.0.0" for ev in evidence)


@pytest.mark.parametrize("analyzer, content, file_path, rule_id, strength", [
    (analyze_adr, "# Context\n\n# Decision\n", "docs/adr.md", "candidatex.docs.adr_structure", 90.0),
    (analyze_openapi_spec, '{"openapi":"3.0.0","paths":{"/users":{}}}', "openapi.json", "candidatex.docs.openapi_spec", 85.0),
    (analyze_openapi_spec, "openapi: 3.0.0\npaths:\n  /users: {}\n", "openapi.yaml", "candidatex.docs.openapi_spec", 85.0),
])
def test_document_rule_metadata_and_scores(analyzer, content, file_path, rule_id, strength):
    evidence = analyzer(content, file_path, REPO_URL, COMMIT_SHA)
    assert len(evidence) == 1
    assert (evidence[0].signal_rule_id, evidence[0].signal_rule_version, evidence[0].technical_signal_strength) == (
        rule_id, "1.0.0", strength
    )


def test_repository_layer_boundaries_rule_metadata_and_score():
    evidence = analyze_layer_boundaries(
        ["src/domain/user.py", "src/services/user.py", "src/adapters/db.py"],
        REPO_URL, COMMIT_SHA,
    )
    assert len(evidence) == 1
    assert (evidence[0].signal_rule_id, evidence[0].signal_rule_version, evidence[0].technical_signal_strength) == (
        "candidatex.docs.repository_layer_boundaries", "1.0.0", 82.0
    )
