"""Contract tests for the stable heuristic rule registry."""

import ast
from collections import Counter
from pathlib import Path
import re

import pytest

from cci.domain.signal_rules import SIGNAL_RULE_VERSIONS, signal_rule_fields


BACKEND_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = BACKEND_ROOT.parents[1]
CATALOG = REPO_ROOT / "docs/contracts/technical-signal-rules.md"


def _catalog_rows():
    rows = {}
    for line in CATALOG.read_text(encoding="utf-8").splitlines():
        if line.startswith("| `candidatex."):
            cells = [
                cell.strip().replace(r"\|", "|")
                for cell in re.split(r"(?<!\\)\|", line.strip().strip("|"))
            ]
            assert len(cells) == 7, line
            rule_id = cells[0].strip("`")
            assert rule_id not in rows, rule_id
            rows[rule_id] = cells
    return rows


def test_catalog_has_one_complete_row_per_registered_rule():
    rows = _catalog_rows()
    assert len(rows) == 52
    assert set(rows) == set(SIGNAL_RULE_VERSIONS)
    assert all(all(cells) for cells in rows.values())
    assert all(cells[1].strip("`") == SIGNAL_RULE_VERSIONS[rule_id] for rule_id, cells in rows.items())


@pytest.mark.parametrize("rule_id, condition", [
    (
        "candidatex.database.sql_foreign_key",
        "One line contains case-insensitive `FOREIGN KEY` with no further syntax required, or `REFERENCES` followed by an identifier and `(`",
    ),
    (
        "candidatex.testing.javascript_supertest",
        "Content regex `\\b(request\\(app\\)|supertest)\\b` detects `supertest`; ordinary `request(app)` followed by punctuation or whitespace misses the trailing word boundary",
    ),
    (
        "candidatex.infra.docker_compose",
        "Parsed YAML is a mapping with a `services` key whose value is a mapping (including an empty mapping); non-mapping `services` values are unsupported",
    ),
])
def test_catalog_states_detector_boundaries(rule_id, condition):
    assert _catalog_rows()[rule_id][3] == condition


@pytest.mark.parametrize("rule_id, strength", [
    ("candidatex.database.sql_index", "`86.0` for more than one comma-separated column; otherwise `82.0` if unique; otherwise `78.0`"),
    ("candidatex.database.prisma_schema", "Base `72.0`; add `6.0` for `@relation` and `8.0` for `@@index` or `@@unique`; `min(score, 90.0)`. Possible values: `72.0`, `78.0`, `80.0`, `86.0`"),
    ("candidatex.infra.dockerfile", "Base `72.0`; add `12.0` for multistage or `COPY --from=`, `6.0` for non-root `USER`, and `4.0` for `HEALTHCHECK`; `min(score, 92.0)`"),
    ("candidatex.infra.docker_compose", "Base `74.0`; add `5.0` for networks, `4.0` for volumes, and `5.0` for healthchecks; `min(score, 90.0)`"),
    ("candidatex.infra.ci_workflow", "Base `75.0`; add `6.0` for tests, `7.0` for matrix, `4.0` for cache, and `5.0` for deploy; `min(score, 94.0)`"),
    ("candidatex.deployment.security_headers", "Base `65.0`; add `8.0` for HSTS, `10.0` for CSP, `5.0` for nosniff, `4.0` for the frame option, and `3.0` if Referrer-Policy or Permissions-Policy is present; `min(score, 95.0)`"),
    ("candidatex.deployment.responsive_dom", "Base `70.0`; add `8.0` for viewport, `7.0` for any semantic tag, and `5.0` for OpenGraph; `min(score, 90.0)`"),
    ("candidatex.testing.go_suite", "`84.0` if table marker; otherwise `80.0` if subtests; otherwise `74.0`"),
])
def test_catalog_states_conditional_strengths_and_caps(rule_id, strength):
    assert _catalog_rows()[rule_id][4] == strength


def test_each_analyzer_emission_expands_one_registered_rule_mapping():
    emitted = []
    for path in (BACKEND_ROOT / "src/cci/analyzers").rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name):
                continue
            if node.func.id != "EvidenceInput":
                continue
            mappings = [
                keyword.value
                for keyword in node.keywords
                if keyword.arg is None
            ]
            assert len(mappings) == 1, f"{path}:{node.lineno}"
            mapping = mappings[0]
            assert isinstance(mapping, ast.Call), f"{path}:{node.lineno}"
            assert isinstance(mapping.func, ast.Name) and mapping.func.id == "signal_rule_fields"
            assert len(mapping.args) == 1 and isinstance(mapping.args[0], ast.Constant)
            emitted.append(mapping.args[0].value)

    assert len(emitted) == 52
    assert Counter(emitted) == Counter({rule_id: 1 for rule_id in SIGNAL_RULE_VERSIONS})


def test_contract_describes_observed_index_as_evidence_summary():
    contract = (REPO_ROOT / "docs/contracts/interfaces.md").read_text(encoding="utf-8")
    description = contract.split("5. **Separation of the Observed Capability Index and Coverage**:", 1)[1].split("6. **No Code Execution**", 1)[0]
    assert "observed-evidence summary" in description
    assert "reflects proficiency" not in description


def test_signal_rule_fields_returns_current_version():
    assert signal_rule_fields("candidatex.code.python.async_function") == {
        "signal_rule_id": "candidatex.code.python.async_function",
        "signal_rule_version": "1.0.0",
    }


def test_signal_rule_fields_rejects_unknown_id():
    with pytest.raises(ValueError, match="Unknown signal rule"):
        signal_rule_fields("candidatex.unknown")


@pytest.mark.parametrize("rule_id", [
    "candidatex.database.sql_table",
    "candidatex.database.sql_index",
    "candidatex.database.sql_foreign_key",
    "candidatex.database.sql_advanced_feature",
    "candidatex.database.alembic_migration",
    "candidatex.database.prisma_schema",
    "candidatex.docs.readme_setup",
    "candidatex.docs.readme_architecture_diagram",
    "candidatex.docs.adr_structure",
    "candidatex.docs.openapi_spec",
    "candidatex.docs.repository_layer_boundaries",
])
def test_database_and_documentation_rules_are_registered(rule_id):
    assert signal_rule_fields(rule_id) == {
        "signal_rule_id": rule_id,
        "signal_rule_version": "1.0.0",
    }


@pytest.mark.parametrize("rule_id", [
    "candidatex.deployment.live_service",
    "candidatex.deployment.security_headers",
    "candidatex.deployment.responsive_dom",
    "candidatex.deployment.tls_certificate",
    "candidatex.infra.dockerfile",
    "candidatex.infra.docker_compose",
    "candidatex.infra.ci_workflow",
    "candidatex.infra.kubernetes_manifest",
    "candidatex.infra.terraform_hcl",
    "candidatex.testing.python_suite",
    "candidatex.testing.python_fixtures",
    "candidatex.testing.python_parameterized",
    "candidatex.testing.python_mocks",
    "candidatex.testing.python_property_based",
    "candidatex.testing.python_regex_fallback",
    "candidatex.testing.javascript_suite",
    "candidatex.testing.javascript_lifecycle",
    "candidatex.testing.javascript_mocks",
    "candidatex.testing.javascript_supertest",
    "candidatex.testing.go_suite",
])
def test_deployment_infrastructure_and_testing_rules_are_registered(rule_id):
    assert signal_rule_fields(rule_id) == {
        "signal_rule_id": rule_id,
        "signal_rule_version": "1.0.0",
    }
