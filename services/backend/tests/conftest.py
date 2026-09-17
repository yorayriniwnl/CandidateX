"""Pytest configuration and shared fixtures for CCI backend tests."""

import os
import sys

# Add backend src directory to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))
