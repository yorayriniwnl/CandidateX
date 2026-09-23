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
