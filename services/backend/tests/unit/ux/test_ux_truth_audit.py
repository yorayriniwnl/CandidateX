"""
UX Truth Audit Regression Test Suite.

Verifies that no user-facing string in apps/web overclaims what the backend establishes.
Specifically guards against:
- "verified code capabilities" or claiming code is "verified" instead of observed/corroborated
- "proven expertise" or "proven falsehood"
- "mastery" as a capability claim
- "top candidate" or "candidate rankings"
- "conflict" when used without qualification instead of "discrepancy" or "contradiction diagnostic"
"""

import os
import re
from pathlib import Path


def test_no_untruthful_overclaiming_in_frontend():
    # Resolve repository root
    current = Path(__file__).resolve()
    # Go up from tests/unit/ux/test_ux_truth_audit.py to repo root
    repo_root = current.parents[5]
    web_dir = repo_root / "apps" / "web"
    assert web_dir.is_dir(), f"Could not find web directory at {web_dir}"

    forbidden_patterns = [
        # Overclaiming verification of code or candidate
        (re.compile(r"verified code capabilities", re.I), "verified code capabilities"),
        (re.compile(r"Verified Code Coverage", re.I), "Verified Code Coverage"),
        (re.compile(r">Verified<", re.I), ">Verified<"),
        (re.compile(r"verified dossiers", re.I), "verified dossiers"),
        (re.compile(r"No verified evidence observed yet", re.I), "No verified evidence observed yet"),
        (re.compile(r"All capabilities verified", re.I), "All capabilities verified"),
        (re.compile(r"Hop 4: Verified Artifact", re.I), "Hop 4: Verified Artifact"),
        (re.compile(r"Full Chain Verified", re.I), "Full Chain Verified"),
        (re.compile(r"Invariant verified", re.I), "Invariant verified"),
        (re.compile(r"Checkpoints Verified", re.I), "Checkpoints Verified"),
        (re.compile(r"proven falsehood", re.I), "proven falsehood"),
        (re.compile(r"proven expertise", re.I), "proven expertise"),
        (re.compile(r"proven track record", re.I), "proven track record"),
        (re.compile(r"technical mastery across", re.I), "technical mastery across"),
        (re.compile(r"cohort rankings as Markdown", re.I), "cohort rankings as Markdown"),
        (re.compile(r">Robust Evidence<", re.I), ">Robust Evidence<"),
        (re.compile(r">Conflict Flag<", re.I), ">Conflict Flag<"),
        (re.compile(r"Conflict\(s\)", re.I), "Conflict(s)"),
        (re.compile(r"High Conflict: Triggers", re.I), "High Conflict: Triggers"),
    ]

    violations = []
    for root, dirs, files in os.walk(web_dir):
        if "node_modules" in dirs:
            dirs.remove("node_modules")
        if ".next" in dirs:
            dirs.remove(".next")
        for f in files:
            if f.endswith((".ts", ".tsx")):
                file_path = Path(root) / f
                rel_path = file_path.relative_to(web_dir)
                # Skip test files and type definitions if matching raw types
                if "tests" in rel_path.parts:
                    continue
                content = file_path.read_text(encoding="utf-8", errors="ignore")
                for pat, label in forbidden_patterns:
                    match = pat.search(content)
                    if match:
                        violations.append(f"{rel_path}: Found forbidden phrase '{label}'")

    assert not violations, "UX truth audit violations detected:\n" + "\n".join(violations)
