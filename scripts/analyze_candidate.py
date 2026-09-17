#!/usr/bin/env python3
"""Candidate Capability Intelligence (CCI) - Turnkey Candidate Analysis CLI.

Executes the formal 10-stage analysis pipeline on candidate CV materials and Job Descriptions,
synthesizing the Candidate Evidence Graph (CEG), capability estimates, contradiction diagnostics,
and prioritized technical interview probes.
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

# Ensure backend package is importable
REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_SRC = REPO_ROOT / "services" / "backend" / "src"
if str(BACKEND_SRC) not in sys.path:
    sys.path.insert(0, str(BACKEND_SRC))

from cci.domain.contracts import CapabilityEstimate, Dossier
from cci.domain.enums import CanonicalRole, CapabilityKey
from cci.pipeline.orchestrator import execute_analysis_pipeline, rescore_dossier


def load_text(path_or_text: Optional[str], default_path: Optional[Path] = None) -> str:
    """Loads file contents if path exists, otherwise returns text or loads default."""
    if path_or_text:
        p = Path(path_or_text)
        if p.exists() and p.is_file():
            with open(p, "r", encoding="utf-8") as f:
                return f.read()
        return path_or_text
    if default_path and default_path.exists():
        with open(default_path, "r", encoding="utf-8") as f:
            return f.read()
    return ""


def format_dossier_markdown(dossier: Dossier, candidate_name: str = "Candidate") -> str:
    """Generates a publication-quality Markdown technical dossier report."""
    lines = [
        f"# Technical Capability Dossier: {candidate_name}",
        f"**Analysis Run ID:** `{dossier.analysis_run_id}` | **Target Role:** `{dossier.role.value}`",
        f"**Generated At:** `{dossier.generated_at}`",
        "",
        "## 1. Executive Summary & Invariant Compliance",
        f"- **Role Capability Index (RCI):** **{dossier.rci:.1f} / 100**" if dossier.rci is not None else "- **RCI:** UNKNOWN",
        f"- **Evidence Coverage:** **{dossier.coverage * 100.0:.1f}%**",
        f"- **Sufficiency Status:** {'INSUFFICIENT EVIDENCE' if dossier.is_insufficient_evidence else 'EVIDENCE SUFFICIENT'}",
        "- **Decision Support Invariant:** Evaluator decision support only (no autonomous hire/reject determination).",
        "- **Execution Invariant:** Candidate code was analyzed strictly via static AST and infra inspection (never executed).",
        "",
        "## 2. Capability Estimates & Uncertainty Bounds",
        "| Capability | Estimate | 95% Bootstrap CI | Effective Count ($n_{\\text{eff}}$) | Raw Evidence | Status |",
        "| :--- | :---: | :---: | :---: | :---: | :---: |",
    ]

    for cap_key, est in dossier.capability_estimates.items():
        cap_name = cap_key.value.replace("_", " ").title()
        if est.is_observed and est.estimate is not None:
            ci_str = f"[{est.ci_lower:.1f}, {est.ci_upper:.1f}]" if est.ci_lower is not None else "N/A"
            lines.append(
                f"| **{cap_name}** | **{est.estimate:.1f}** | {ci_str} | "
                f"{est.effective_evidence_count:.1f} | {est.raw_evidence_count} | OBSERVED |"
            )
        else:
            lines.append(f"| **{cap_name}** | *UNKNOWN* | N/A | 0.0 | 0 | UNKNOWN |")

    lines.extend([
        "",
        "## 3. Contradiction Diagnostics ($D_k \\in [-1, 1]$)",
        "| Capability | Diagnostic $D_k$ | Positive Support ($P_k$) | Contradictory Support ($N_k$) | Consensus Interpretation |",
        "| :--- | :---: | :---: | :---: | :--- |",
    ])

    for cap_key, conflict in dossier.capability_conflicts.items():
        cap_name = cap_key.value.replace("_", " ").title()
        d_val = conflict.contradiction_diagnostic
        interpretation = "Strong Consensus" if d_val > 0.4 else "Moderate Consensus" if d_val > 0.0 else "Contradiction Warning"
        lines.append(
            f"| **{cap_name}** | `{d_val:+.2f}` | {conflict.positive_support_sum:.2f} | "
            f"{conflict.negative_support_sum:.2f} | {interpretation} |"
        )

    lines.extend([
        "",
        "## 4. Prioritized Technical Interview Probes",
        "Targeted technical inquiries ranked by information gain $I_k = w_k \\cdot \\sigma_k \\cdot (1 + \\gamma |D_k|)$:",
        "",
    ])

    for idx, probe in enumerate(dossier.interview_probes[:5], 1):
        cap_name = probe.capability_key.value.replace("_", " ").title()
        lines.append(f"### Probe {idx}: {cap_name} (Priority Score: `{probe.priority_score:.2f}`)")
        lines.append(f"**Target Capability:** `{probe.capability_key.value}` | **Coverage Gap:** `{probe.coverage_gap_term:.2f}`")
        # Find matching questions
        matched_qs = [q for q in dossier.interview_questions if q.target_capability == probe.capability_key]
        if matched_qs:
            for q in matched_qs:
                lines.append(f"- **Suggested Inquiry:** {q.question_text}")
                lines.append(f"  - *Verification Focus:* {q.verification_guidance}")
        lines.append("")

    lines.extend([
        "## 5. Candidate Self-Claims Corroboration",
        "| Declared Resume Claim | Status | Corroborating Evidence |",
        "| :--- | :---: | :--- |",
    ])

    for claim in dossier.claims_corroboration:
        c_text = claim.get("claim_text", "")
        status_badge = str(claim.get("status", "unknown")).upper()
        ev_count = len(claim.get("grounding_evidence_ids", []))
        lines.append(f"| {c_text} | **{status_badge}** | {ev_count} records |")

    return "\n".join(lines)


def print_cli_summary(dossier: Dossier, candidate_name: str) -> None:
    """Prints a clean, concise terminal report."""
    print("\n" + "=" * 80)
    print(f"CCI TECHNICAL DOSSIER SUMMARY: {candidate_name.upper()}")
    print("=" * 80)
    rci_display = f"{dossier.rci:.1f}/100" if dossier.rci is not None else "UNKNOWN"
    print(f"Role: {dossier.role.value.upper():<20} | RCI Score: {rci_display:<10} | Evidence Coverage: {dossier.coverage * 100:.1f}%")
    print("-" * 80)
    print(f"{'CAPABILITY':<30} | {'SCORE':<7} | {'95% CI':<14} | {'N_EFF':<6} | {'STATUS'}")
    print("-" * 80)

    for cap_key, est in dossier.capability_estimates.items():
        name = cap_key.value.replace("_", " ").title()[:28]
        if est.is_observed and est.estimate is not None:
            ci = f"[{est.ci_lower:.1f}, {est.ci_upper:.1f}]" if est.ci_lower is not None else "N/A"
            print(f"{name:<30} | {est.estimate:<7.1f} | {ci:<14} | {est.effective_evidence_count:<6.1f} | OBSERVED")
        else:
            print(f"{name:<30} | {'UNKNOWN':<7} | {'N/A':<14} | {'0.0':<6} | UNKNOWN")

    print("-" * 80)
    print("TOP PRIORITIZED INTERVIEW PROBES:")
    for idx, p in enumerate(dossier.interview_probes[:3], 1):
        cap_title = p.capability_key.value.replace("_", " ").title()
        print(f"  {idx}. [{cap_title}] Priority Score: {p.priority_score:.2f} (Gap: {p.coverage_gap_term:.0%})")
        matching = [q for q in dossier.interview_questions if q.target_capability == p.capability_key]
        if matching:
            print(f"     Inquiry: \"{matching[0].question_text}\"")

    print("=" * 80 + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Candidate Capability Intelligence (CCI) Analysis CLI"
    )
    parser.add_argument("--cv", type=str, help="Path to candidate CV text or text file")
    parser.add_argument("--jd", type=str, help="Path to Job Description text or text file")
    parser.add_argument(
        "--role",
        type=str,
        default="backend",
        choices=[r.value for r in CanonicalRole],
        help="Target canonical engineering role (default: backend)",
    )
    parser.add_argument(
        "--name",
        type=str,
        default="Alice Chen",
        help="Candidate full name (default: Alice Chen)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=str(REPO_ROOT / "reports"),
        help="Output directory for generated dossier reports (default: reports/)",
    )
    parser.add_argument(
        "--rescore-weights",
        type=str,
        help="JSON string of capability weight overrides to demonstrate instantaneous functional rescore",
    )

    args = parser.parse_args()

    default_cv = REPO_ROOT / "examples" / "sample_backend_cv.txt"
    default_jd = REPO_ROOT / "examples" / "sample_backend_jd.txt"

    cv_content = load_text(args.cv, default_cv)
    jd_content = load_text(args.jd, default_jd)
    role = CanonicalRole(args.role)
    candidate_id = uuid4()

    print(f"================================================================================")
    print(f"CANDIDATE CAPABILITY INTELLIGENCE: PIPELINE ORCHESTRATION")
    print(f"Candidate: {args.name} | Role: {role.value} | Candidate ID: {candidate_id}")
    print(f"================================================================================")

    t0 = time.time()
    state = execute_analysis_pipeline(
        candidate_id=candidate_id,
        role=role,
        jd_text=jd_content,
        cv_text=cv_content,
    )
    exec_duration = time.time() - t0

    if state.status.value != "completed" or state.dossier is None:
        print(f"[!] Pipeline failed: {state.error}")
        sys.exit(1)

    print(f"[+] 10-Stage Pipeline successfully completed in {exec_duration:.2f}s.")
    for stage in state.stages:
        status_indicator = "[x]" if stage.status == "completed" else "[ ]"
        print(f"    {status_indicator} {stage.label:<35} -> {stage.status.upper()}")

    dossier = state.dossier
    print_cli_summary(dossier, args.name)

    # Save output artifacts
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    json_path = out_dir / f"dossier_{candidate_id}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(dossier.model_dump(mode="json"), f, indent=2)
    print(f"[+] Saved Dossier JSON:     {json_path}")

    md_report = format_dossier_markdown(dossier, args.name)
    md_path = out_dir / f"dossier_{candidate_id}.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_report)
    print(f"[+] Saved Dossier Markdown: {md_path}")

    # Optional functional rescore demonstration
    if args.rescore_weights:
        print("\n" + "-" * 80)
        print("DEMONSTRATING PURE FUNCTIONAL RESCORE WITHOUT RE-CRAWLING:")
        try:
            overrides = json.loads(args.rescore_weights)
            parsed_overrides = {CapabilityKey(k): float(v) for k, v in overrides.items()}
            t_rescore = time.time()
            rescored_dossier = rescore_dossier(dossier, parsed_overrides)
            rescore_ms = (time.time() - t_rescore) * 1000.0

            print(f"[+] Functional rescore completed in {rescore_ms:.2f}ms!")
            print(f"    Original RCI: {dossier.rci:.2f} -> Rescored RCI: {rescored_dossier.rci:.2f}")
            print(f"    Original Coverage: {dossier.coverage:.1%} -> Rescored Coverage: {rescored_dossier.coverage:.1%}")
        except Exception as e:
            print(f"[!] Rescore failed: {e}")
        print("-" * 80 + "\n")


if __name__ == "__main__":
    main()
