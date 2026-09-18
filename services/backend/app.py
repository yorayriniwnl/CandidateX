"""Vercel Services entrypoint for the CandidateX FastAPI backend."""

from pathlib import Path
import sys

SRC_DIR = Path(__file__).resolve().parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from cci.main import app  # noqa: E402,F401
