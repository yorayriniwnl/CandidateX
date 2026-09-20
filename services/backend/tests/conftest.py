"""Pytest configuration and shared fixtures for CCI backend tests."""

import os
import sys
import tempfile
from pathlib import Path

# Configure before application imports; never run API tests against a user's database.
_test_database = tempfile.TemporaryDirectory(prefix="candidatex-tests-")
os.environ["DATABASE_URL"] = "sqlite:///" + (Path(_test_database.name) / "test.db").as_posix()

# Add backend src directory to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))


def pytest_sessionstart(session):
    from cci.db.repository import init_db
    from cci.db.session import engine
    init_db(engine)


def pytest_sessionfinish(session, exitstatus):
    from cci.db.session import engine
    engine.dispose()
    _test_database.cleanup()
