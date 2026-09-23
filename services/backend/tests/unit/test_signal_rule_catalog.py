"""Contract tests for the stable heuristic rule registry."""

import pytest

from cci.domain.signal_rules import signal_rule_fields


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
