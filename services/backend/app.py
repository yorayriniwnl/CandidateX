"""Vercel FastAPI entrypoint; public deployments are synthetic-only."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'src'))
from cci.synthetic_demo_app import app  # noqa: E402,F401
