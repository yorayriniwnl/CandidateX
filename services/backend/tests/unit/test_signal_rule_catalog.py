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
