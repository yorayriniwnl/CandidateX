#!/usr/bin/env python3
"""Turnkey Candidate Capability Intelligence (CCI) analysis CLI."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Optional
from uuid import uuid4

REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_SRC = REPO_ROOT / "services" / "backend" / "src"
if str(BACKEND_SRC) not in sys.path:
    sys.path.insert(0, str(BACKEND_SRC))

from cci.domain.contracts import Dossier
from cci.domain.enums import CanonicalRole, CapabilityKey
from cci.pipeline.orchestrator import execute_analysis_pipeline, rescore_dossier
from cci.reports.exporter import generate_html_brief


PROBE_FORMULA_LATEX = (
    r"I_k = w_k[\alpha(1-\mathrm{Cov}_k) + "
    r"\beta\,\mathrm{CIwidth}_k + \gamma\,\mathrm{Conf}_k]"
)


def load_text(path_or_text: Optional[str], default_path: Optional[Path] = None) -> str:
    """Load a text file when a path exists, otherwise treat the input as literal text."""
    if path_or_text:
        path = Path(path_or_text)
        if path.exists() and path.is_file():
            return path.read_text(encoding="utf-8")
        return path_or_text
    if default_path and default_path.exists():
        return default_path.read_text(encoding="utf-8")
    return ""


def format_dossier_markdown(dossier: Dossier, candidate_name: str = "Candidate") -> str:
    """Generate the CLI Markdown dossier using the submitted-paper equations."""
    lines = [
        f"# Technical Capability Dossier: {candidate_name}",
        f"**Analysis Run ID:** `{dossier.analysis_run_id}` | **Target Role:** `{dossier.role.value}`",
        "",
        "## 1. Executive Summary & Invariant Compliance",
        (
            f"- **Role Capability Index (RCI):** **{dossier.rci:.1f} / 100**"
            if dossier.rci is not None
            else "- **RCI:** UNKNOWN"
        ),
        f"- **Evidence Coverage:** **{dossier.coverage * 100.0:.1f}%**",
        f"- **Sufficiency Status:** {'INSUFFICIENT EVIDENCE' if dossier.is_insufficient_evidence else 'EVIDENCE SUFFICIENT'}",
        "- **Decision Support Invariant:** Human interviewer decision support only; no autonomous hire/reject determination.",
        "- **Missing-Evidence Invariant:** Unobserved capability is UNKNOWN, never an automatic zero.",
        "",
        "## 2. Capability Estimates & Uncertainty Bounds",
        "| Capability | Estimate | 95% CI | Effective Evidence | Raw Evidence | Coverage | Status |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]

    for capability, estimate in dossier.capability_estimates.items():
        name = capability.value.replace("_", " ").title()
        if estimate.is_observed and estimate.estimate is not None:
            ci = (
                f"[{estimate.ci_lower:.1f}, {estimate.ci_upper:.1f}]"
                if estimate.ci_lower is not None and estimate.ci_upper is not None
                else "N/A"
            )
            lines.append(
                f"| **{name}** | **{estimate.estimate:.1f}** | {ci} | "
                f"{estimate.effective_evidence_count:.1f} | {estimate.raw_evidence_count} | "
                f"{estimate.coverage_k * 100.0:.1f}% | OBSERVED |"
            )
        else:
            lines.append(
                f"| **{name}** | *UNKNOWN* | N/A | 0.0 | 0 | "
                f"{estimate.coverage_k * 100.0:.1f}% | UNKNOWN |"
            )

    lines.extend(
        [
            "",
            "## 3. Contradiction Diagnostics",
            "| Capability | D_k | Positive Support | Contradictory Support | Verification |",
            "|---|---:|---:|---:|---|",
        ]
    )
    for capability, conflict in dossier.capability_conflicts.items():
        name = capability.value.replace("_", " ").title()
        lines.append(
            f"| **{name}** | {conflict.contradiction_diagnostic:+.2f} | "
            f"{conflict.positive_support_sum:.2f} | {conflict.negative_support_sum:.2f} | "
            f"{'VERIFY' if conflict.has_meaningful_conflict else 'CLEAR'} |"
        )

    lines.extend(
        [
            "",
            "## 4. Prioritized Technical Interview Probes",
            f"Paper Eq. (11): ${PROBE_FORMULA_LATEX}$",
            "",
        ]
    )
    for index, probe in enumerate(dossier.interview_probes[:5], 1):
        name = probe.capability_key.value.replace("_", " ").title()
        lines.append(
            f"### Probe {index}: {name} (Priority Score: `{probe.priority_score:.3f}`)"
        )
        lines.append(
            f"Role weight `{probe.role_weight:.3f}` · coverage gap `{probe.coverage_gap_term:.3f}` · "
            f"uncertainty `{probe.uncertainty_term:.3f}` · contradiction `{probe.contradiction_term:.3f}`"
        )
        for question in dossier.interview_questions:
            if question.target_capability == probe.capability_key:
                lines.append(f"- **Suggested Inquiry:** {question.question_text}")
                lines.append(f"  - **Verification Focus:** {question.verification_guidance}")
        lines.append("")

    if dossier.claims_corroboration:
        lines.extend(
            [
                "## 5. Candidate Self-Claims Corroboration",
                "| Declared Claim | Status | Evidence Records |",
                "|---|---|---:|",
            ]
        )
        for claim in dossier.claims_corroboration:
            lines.append(
                f"| {claim.get('claim_text', '')} | {str(claim.get('status', 'unknown')).upper()} | "
                f"{len(claim.get('grounding_evidence_ids', []))} |"
            )

    return "\n".join(lines)


def print_cli_summary(dossier: Dossier, candidate_name: str) -> None:
    """Print a concise terminal summary."""
    print("\n" + "=" * 80)
    print(f"CCI TECHNICAL DOSSIER: {candidate_name}")
    print("=" * 80)
    rci = f"{dossier.rci:.1f}/100" if dossier.rci is not None else "UNKNOWN"
    print(
        f"Role: {dossier.role.value} | RCI: {rci} | Coverage: {dossier.coverage * 100.0:.1f}%"
    )
    print("Decision support only. Missing evidence is UNKNOWN, not zero capability.")
    print("-" * 80)
    for capability, estimate in dossier.capability_estimates.items():
        score = f"{estimate.estimate:.1f}" if estimate.estimate is not None else "UNKNOWN"
        print(
            f"{capability.value.replace('_', ' ').title():<30} "
            f"{score:<10} coverage={estimate.coverage_k * 100.0:>5.1f}%"
        )
    print("=" * 80)


def main() -> None:
    parser = argparse.ArgumentParser(description="Candidate Capability Intelligence analysis CLI")
    parser.add_argument("--cv", type=str, help="Candidate CV text or path")
    parser.add_argument("--jd", type=str, help="Job-description text or path")
    parser.add_argument(
        "--role",
        default="backend",
        choices=[role.value for role in CanonicalRole],
        help="Canonical target role",
    )
    parser.add_argument("--name", default=None, help="Candidate name")
    parser.add_argument(
        "--output-dir",
        default=str(REPO_ROOT / "reports"),
        help="Directory for JSON/Markdown/HTML dossier artifacts",
    )
    parser.add_argument(
        "--rescore-weights",
        help="JSON object mapping capability keys to replacement role weights",
    )
    args = parser.parse_args()

    cv_text = load_text(args.cv, REPO_ROOT / "examples" / "sample_backend_cv.txt")
    jd_text = load_text(args.jd, REPO_ROOT / "examples" / "sample_backend_jd.txt")
    role = CanonicalRole(args.role)
    candidate_id = uuid4()

    candidate_name = args.name
    if not candidate_name:
        first_line = cv_text.strip().splitlines()[0].strip() if cv_text.strip() else ""
        candidate_name = first_line[2:].strip() if first_line.startswith("# ") else "Candidate"

    started = time.time()
    state = execute_analysis_pipeline(
        candidate_id=candidate_id,
        role=role,
        jd_text=jd_text,
        cv_text=cv_text,
    )
    if state.status.value != "completed" or state.dossier is None:
        print(f"Pipeline failed: {state.error}")
        raise SystemExit(1)

    dossier = state.dossier
    print(f"Pipeline completed in {time.time() - started:.2f}s")
    print_cli_summary(dossier, candidate_name)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = f"dossier_{candidate_id}"
    (output_dir / f"{stem}.json").write_text(
        json.dumps(dossier.model_dump(mode="json"), indent=2),
        encoding="utf-8",
    )
    (output_dir / f"{stem}.md").write_text(
        format_dossier_markdown(dossier, candidate_name),
        encoding="utf-8",
    )
    (output_dir / f"{stem}.html").write_text(
        generate_html_brief(dossier, candidate_name),
        encoding="utf-8",
    )

    if args.rescore_weights:
        raw_weights = json.loads(args.rescore_weights)
        parsed_weights = {
            CapabilityKey(key): float(value) for key, value in raw_weights.items()
        }
        rescored = rescore_dossier(dossier, parsed_weights)
        original = f"{dossier.rci:.2f}" if dossier.rci is not None else "UNKNOWN"
        updated = f"{rescored.rci:.2f}" if rescored.rci is not None else "UNKNOWN"
        print(f"Functional rescore RCI: {original} -> {updated}")


if __name__ == "__main__":
    main()
