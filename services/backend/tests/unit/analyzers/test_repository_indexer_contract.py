"""Regression tests for the repository artifact indexer contract."""

from cci.analyzers.repository.indexer import categorize_file


def test_top_level_sql_is_database_artifact() -> None:
    """A root-level SQL schema is database evidence, not generic source code."""
    assert categorize_file("schema.sql") == "database"


def test_nested_sql_is_database_artifact() -> None:
    assert categorize_file("db/schema.sql") == "database"
