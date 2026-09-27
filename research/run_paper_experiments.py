#!/usr/bin/env python3
"""Candidate Capability Intelligence (CCI) supplementary implementation ablation.

This module exercises the repository implementation across deterministic synthetic,
role-specific cohorts. It is useful for regression testing and architecture ablations,
but it is NOT an exact regeneration of the submitted paper benchmark.

The submitted paper reports a different controlled benchmark design:
16 seeds x 300 candidates per seed x 6 target roles = 28,800 candidate-role
evaluations, plus separate missingness, corruption, negative-control, and randomized
regime experiments. Those publication values are preserved in
``research/paper_benchmark_manifest.json`` with explicit provenance.

This repository harness currently samples candidates independently per role and reports
4,800 candidate-role samples at the default settings (16 seeds x 6 roles x 50 samples).
Keeping the two evidence layers separate prevents accidental academic overclaiming.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
from scipy import stats

REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_SRC = REPO_ROOT / "services" / "backend" / "src"
if str(BACKEND_SRC) not in sys.path:
    sys.path.insert(0, str(BACKEND_SRC))

from cci.domain.enums import CanonicalRole, CapabilityKey
from cci.research.ablation import AblationMode, evaluate_candidate_ablation
from cci.research.simulation import ROLE_CAPABILITY_PROFILES, generate_synthetic_cohort
from cci.research.statistics import (
    compute_wilcoxon_comparison,
    format_latex_ablation_table,
    format_markdown_ablation_table,
)
from cci.scoring.weights import compute_softmax_weights

PAPER_REPORTED_CANDIDATE_ROLE_EVALUATIONS = 28_800
PAPER_MANIFEST_PATH = REPO_ROOT / "research" / "paper_benchmark_manifest.json"


def get_role_weights(role: CanonicalRole) -> Dict[CapabilityKey, float]:
    """Compute target role softmax weights for a canonical engineering role."""
    raw_importances = {k: 1.0 for k in CapabilityKey}
    profile = ROLE_CAPABILITY_PROFILES.get(role, {})
    for capability, (mean_value, _) in profile.items():
        raw_importances[capability] = mean_value / 50.0
    return compute_softmax_weights(raw_importances, temperature=1.0)


def run_full_simulation_study(
    seeds: List[int],
    candidates_per_role: int = 50,
    roles: Optional[List[CanonicalRole]] = None,
) -> Dict[str, Any]:
    """Run the repository supplementary implementation ablation harness.

    ``total_candidates`` is retained for backward compatibility with existing UI/tests,
    but the actual unit is a role-specific candidate sample, i.e. a candidate-role
    evaluation generated independently inside each role cohort.
    """
    if roles is None:
        roles = list(CanonicalRole)

    total_samples_planned = len(seeds) * len(roles) * candidates_per_role
    print("=" * 80)
    print("CCI SUPPLEMENTARY IMPLEMENTATION ABLATION HARNESS")
    print(
        f"Seeds: {len(seeds)} | Roles: {len(roles)} | "
        f"Role-specific samples/seed: {candidates_per_role}"
    )
    print(f"Planned candidate-role samples: N = {total_samples_planned:,}")
    print(
        "Publication benchmark is separate: "
        f"{PAPER_REPORTED_CANDIDATE_ROLE_EVALUATIONS:,} candidate-role evaluations."
    )
    print("=" * 80)

    role_weights_map = {role: get_role_weights(role) for role in roles}
    uniform_weights = {capability: 1.0 / len(CapabilityKey) for capability in CapabilityKey}

    mode_estimates: Dict[AblationMode, List[float]] = {mode: [] for mode in AblationMode}
    mode_true_rcis: Dict[AblationMode, List[float]] = {mode: [] for mode in AblationMode}
    mode_errors: Dict[AblationMode, List[float]] = {mode: [] for mode in AblationMode}
    mode_cap_errors: Dict[AblationMode, List[float]] = {mode: [] for mode in AblationMode}

    role_metrics: Dict[str, Dict[str, List[float]]] = {
        role.value: {"errors": [], "est": [], "true": []} for role in roles
    }

    started = time.time()
    samples_processed = 0

    for seed in seeds:
        for role in roles:
            cohort = generate_synthetic_cohort(
                role=role,
                count=candidates_per_role,
                seed=seed,
            )
            target_weights = role_weights_map[role]

            for candidate in cohort:
                samples_processed += 1
                for mode in AblationMode:
                    evaluation_weights = (
                        uniform_weights
                        if mode == AblationMode.UNIFORM_WEIGHTS
                        else target_weights
                    )
                    rci_est, rci_true, q_hats = evaluate_candidate_ablation(
                        candidate=candidate,
                        mode=mode,
                        role_weights=evaluation_weights,
                        true_weights=target_weights,
                    )

                    if rci_est is None:
                        continue

                    error = abs(rci_est - rci_true)
                    mode_estimates[mode].append(rci_est)
                    mode_true_rcis[mode].append(rci_true)
                    mode_errors[mode].append(error)

                    for capability, estimated_capability in q_hats.items():
                        true_capability = candidate.ground_truth_capabilities[capability]
                        mode_cap_errors[mode].append(
                            abs(estimated_capability - true_capability)
                        )

                    if mode == AblationMode.FULL_CCI:
                        role_metrics[role.value]["errors"].append(error)
                        role_metrics[role.value]["est"].append(rci_est)
                        role_metrics[role.value]["true"].append(rci_true)

    elapsed_time = time.time() - started
    print(
        f"Supplementary ablation completed in {elapsed_time:.2f}s "
        f"({samples_processed:,} candidate-role samples per mode)."
    )

    ablation_summary: Dict[str, Dict[str, float]] = {}
    for mode in AblationMode:
        estimates = mode_estimates[mode]
        truths = mode_true_rcis[mode]
        errors = mode_errors[mode]
        capability_errors = mode_cap_errors[mode]

        mae = float(np.mean(errors)) if errors else 0.0
        rmse = (
            float(np.sqrt(np.mean([(estimate - truth) ** 2 for estimate, truth in zip(estimates, truths)])))
            if errors
            else 0.0
        )
        spearman_rho, _ = (
            stats.spearmanr(estimates, truths) if len(estimates) > 1 else (0.0, 0.0)
        )
        kendall_tau, _ = (
            stats.kendalltau(estimates, truths) if len(estimates) > 1 else (0.0, 0.0)
        )
        capability_mae = float(np.mean(capability_errors)) if capability_errors else 0.0

        ablation_summary[mode.value] = {
            "rci_mae": round(mae, 4),
            "rci_rmse": round(rmse, 4),
            "spearman_rho": round(float(spearman_rho), 4),
            "kendall_tau": round(float(kendall_tau), 4),
            "capability_mae": round(capability_mae, 4),
            "sample_count": len(errors),
        }

    full_errors = mode_errors[AblationMode.FULL_CCI]
    statistical_tests: Dict[str, Dict[str, Any]] = {}
    for mode in AblationMode:
        if mode == AblationMode.FULL_CCI:
            continue
        statistical_tests[mode.value] = compute_wilcoxon_comparison(
            full_errors,
            mode_errors[mode],
        )

    per_role_summary: Dict[str, Dict[str, float]] = {}
    for role_name, data in role_metrics.items():
        role_errors = data["errors"]
        role_estimates = data["est"]
        role_truths = data["true"]
        role_mae = float(np.mean(role_errors)) if role_errors else 0.0
        role_rmse = (
            float(
                np.sqrt(
                    np.mean(
                        [
                            (estimate - truth) ** 2
                            for estimate, truth in zip(role_estimates, role_truths)
                        ]
                    )
                )
            )
            if role_errors
            else 0.0
        )
        role_rho, _ = (
            stats.spearmanr(role_estimates, role_truths)
            if len(role_estimates) > 1
            else (0.0, 0.0)
        )
        per_role_summary[role_name] = {
            "rci_mae": round(role_mae, 4),
            "rci_rmse": round(role_rmse, 4),
            "spearman_rho": round(float(role_rho), 4),
            "sample_count": len(role_errors),
        }

    return {
        "metadata": {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
            "evidence_layer": "supplementary_implementation_ablation",
            "evaluation_unit": "candidate_role_sample",
            "paper_exact_reproduction": False,
            "paper_manifest": str(PAPER_MANIFEST_PATH.relative_to(REPO_ROOT)),
            "paper_reported_candidate_role_evaluations": PAPER_REPORTED_CANDIDATE_ROLE_EVALUATIONS,
            "total_candidates": len(full_errors),
            "total_evaluations": len(full_errors),
            "seeds": seeds,
            "roles": [role.value for role in roles],
            "candidates_per_role": candidates_per_role,
            "execution_time_seconds": round(elapsed_time, 2),
        },
        "ablation_summary": ablation_summary,
        "statistical_tests": statistical_tests,
        "per_role_summary": per_role_summary,
    }


def format_role_breakdown_markdown(
    per_role_summary: Dict[str, Dict[str, float]],
) -> str:
    """Format Full CCI supplementary-ablation performance by canonical role."""
    lines = [
        "# Canonical Engineering Role Breakdown (Supplementary Implementation Ablation)",
        "",
        "These are repository implementation diagnostics, not the submitted paper's headline benchmark.",
        "",
        "| Canonical Engineering Role | Sample Count ($N$) | RCI MAE ↓ | RCI RMSE ↓ | Spearman's $\\rho$ ↑ |",
        "|:---------------------------|:------------------:|:---------:|:----------:|:-------------------:|",
    ]
    for role_name, metrics in per_role_summary.items():
        role_display = role_name.replace("_", " ").title()
        lines.append(
            f"| **{role_display}** | {metrics['sample_count']:,} | "
            f"{metrics['rci_mae']:.3f} | {metrics['rci_rmse']:.3f} | "
            f"{metrics['spearman_rho']:.3f} |"
        )
    return "\n".join(lines)


def save_publication_artifacts(results: Dict[str, Any], output_dir: Path) -> None:
    """Write supplementary-ablation artifacts with explicit provenance labels."""
    output_dir.mkdir(parents=True, exist_ok=True)

    ablation_summary = results["ablation_summary"]
    statistical_tests = results["statistical_tests"]
    per_role_summary = results["per_role_summary"]
    sample_count = results["metadata"]["total_evaluations"]

    markdown_table = format_markdown_ablation_table(
        ablation_summary,
        statistical_tests,
    )
    markdown_path = output_dir / "table_ablation_study.md"
    markdown_path.write_text(
        "# Repository Supplementary Implementation Ablation Study\n\n"
        f"Candidate-role samples: $N = {sample_count:,}$.\n\n"
        "This is not an exact regeneration of the paper benchmark. The submitted paper "
        "reports 28,800 candidate-role evaluations under a broader controlled generator and "
        "separate stress/negative-control experiments. See `research/paper_benchmark_manifest.json`.\n\n"
        f"{markdown_table}\n\n"
        "*Paired Wilcoxon tests compare each repository ablation against the Full CCI implementation baseline.*\n",
        encoding="utf-8",
    )

    latex_path = output_dir / "table_ablation_study.tex"
    latex_path.write_text(
        format_latex_ablation_table(ablation_summary, statistical_tests) + "\n",
        encoding="utf-8",
    )

    role_path = output_dir / "role_breakdown.md"
    role_path.write_text(
        format_role_breakdown_markdown(per_role_summary) + "\n",
        encoding="utf-8",
    )

    json_path = output_dir / "ablation_results.json"
    json_path.write_text(json.dumps(results, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="CCI supplementary implementation ablation harness"
    )
    parser.add_argument(
        "--seeds",
        type=int,
        nargs="+",
        default=list(range(1, 17)),
        help="Deterministic seeds for the supplementary harness (default: 1..16)",
    )
    parser.add_argument(
        "--candidates-per-role",
        type=int,
        default=50,
        help="Role-specific samples per seed (default: 50; 4,800 samples across six roles)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=str(REPO_ROOT / "research" / "results"),
        help="Output directory for supplementary ablation artifacts",
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Run a rapid 2-seed x 10-samples-per-role verification pass",
    )
    args = parser.parse_args()

    seeds = [42, 100] if args.quick else args.seeds
    candidates_per_role = 10 if args.quick else args.candidates_per_role

    results = run_full_simulation_study(
        seeds=seeds,
        candidates_per_role=candidates_per_role,
    )
    save_publication_artifacts(results, Path(args.output_dir))

    summary_table = format_markdown_ablation_table(
        results["ablation_summary"],
        results["statistical_tests"],
    )
    try:
        print(summary_table)
    except UnicodeEncodeError:
        safe_table = (
            summary_table.replace("↓", "v")
            .replace("↑", "^")
            .replace("$\\rho$", "rho")
            .replace("$\\tau$", "tau")
        )
        print(safe_table.encode("ascii", errors="replace").decode("ascii"))
    print("=" * 80)


if __name__ == "__main__":
    main()
