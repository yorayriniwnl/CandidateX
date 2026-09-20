"""The HTTP application must start without optional offline experiment dependencies."""
import os
from pathlib import Path
import subprocess
import sys


def test_live_app_starts_without_scipy():
    source = str(Path(__file__).parents[1] / 'src')
    result = subprocess.run([sys.executable, '-c',
        "import sys; sys.modules['scipy'] = None; from cci.live_app import app; assert app.title == 'CandidateX Live Analysis'"],
        env={**os.environ, 'PYTHONPATH': source}, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
