"""Vercel FastAPI entrypoint; deploy this backend directory as a separate project."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'src'))
from cci.live_app import app  # noqa: E402,F401
