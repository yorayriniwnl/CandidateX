#!/usr/bin/env python3
"""Candidate Capability Intelligence (CCI) - Paper Experiment Reproduction Engine.

FORMAL CONFERENCE PAPER REPRODUCIBILITY:
Executes the comprehensive Monte Carlo candidate cohort simulation and ablation study
across 16 deterministic pseudo-random seeds x 300 candidates across the 6 canonical
engineering roles (N = 4,800 total candidates).

EVALUATION MODES:
1. FULL_CCI: Attribution-gated confidence c_{e,k} = o * (a * t * v * x * r)^{1/5},
   source-cluster coverage with unique artifacts and geometric within-cluster decay,
   recency decay exp(-lambda_k * delta_t), calibrated reliability, and role weights.
2. NO_RECENCY_DECAY: lambda_k = 0 -> t_{e,k} = 1.0 (ignores staleness & skill progression).
3. NO_OWNERSHIP_DISCOUNT: o_e = 1.0 (ignores forks and multi-author team code).
4. UNIFORM_WEIGHTS: w_k = 1/12 (ignores job-specific role capability requirements).
5. UNCALIBRATED_SOURCES: r_s = 1.0 (treats unverified resume claims identically to git commits).

STATISTICAL VERIFICATION:
- Paired Wilcoxon signed-rank tests comparing Full CCI error distributions against each ablation.
- Non-parametric Cliff's delta effect size estimation.
- Generates publication-ready Markdown, LaTeX, and JSON artifacts.
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from scipy import stats

# Ensure backend package is importable regardless of working directory
REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_SRC = REPO_ROOT / "services" / "backend" / "src"
if str(BACKEND_SRC) not in sys.path:
    sys.path.insert(0, str(BACKEND_SRC))

from cci.domain.contracts import ScoringConfig
from cci.domain.enums import CanonicalRole, CapabilityKey
from cci.research.ablation import (
    AblationMode,
    evaluate_candidate_ablation,
    run_ablation_evaluation,
)
from cci.research.simulation import (
    ROLE_CAPABILITY_PROFILES,
    SimulatedCandidate,
    generate_synthetic_cohort,
)
from cci.research.statistics import (
    calculate_cliffs_delta,
    compute_wilcoxon_comparison,
    format_latex_ablation_table,
    format_markdown_ablation_table,
    pair_candidate_errors,
)
from cci.scoring.weights import compute_softmax_weights


def get_role_weights(role: CanonicalRole) -> Dict[CapabilityKey, float]:
    """Computes target role softmax weights for a canonical engineering role."""
    raw_importances = {k: 1.0 for k in CapabilityKey}
    prof = ROLE_CAPABILITY_PROFILES.get(role, {})
    for k, (mean_val, _) in prof.items():
        raw_importances[k] = mean_val / 50.0
    return compute_softmax_weights(raw_importances, temperature=1.0)


def run_full_simulation_study(
    seeds: List[int],
    candidates_per_role: int = 50,
    roles: Optional[List[CanonicalRole]] = None,
) -> Dict[str, Any]:
    """Runs the complete paper simulation across all seeds, roles, and ablation modes."""
    if roles is None:
        roles = list(CanonicalRole)

    total_candidates_planned = len(seeds) * len(roles) * candidates_per_role
    print(f"================================================================================")
    print(f"CCI PAPER REPRODUCIBILITY ENGINE: MONTE CARLO EXPERIMENT SUITE")
    print(f"Seeds: {len(seeds)} (values: {seeds[0]}..{seeds[-1]}) | Roles: {len(roles)} | Per-Role: {candidates_per_role}")
    print(f"Total Cohort Size: N = {total_candidates_planned:,} simulated candidates")
    print(f"================================================================================")

    # Precompute role weights
    role_weights_map = {r: get_role_weights(r) for r in roles}
    uniform_weights = {k: 1.0 / 12.0 for k in CapabilityKey}

    # Tracking metrics per ablation mode across the entire cohort
    mode_estimates: Dict[AblationMode, List[float]] = {m: [] for m in AblationMode}
    mode_true_rcis: Dict[AblationMode, List[float]] = {m: [] for m in AblationMode}
    mode_errors: Dict[AblationMode, List[float]] = {m: [] for m in AblationMode}
    mode_errors_by_candidate: Dict[AblationMode, Dict[Any, float]] = {
        m: {} for m in AblationMode
    }
    mode_cap_errors: Dict[AblationMode, List[float]] = {m: [] for m in AblationMode}

    # Per-role tracking for Full CCI
    role_metrics: Dict[str, Dict[str, List[float]]] = {
        r.value: {"errors": [], "est": [], "true": []} for r in roles
    }

    t0 = time.time()
    candidates_processed = 0

    for seed_idx, seed in enumerate(seeds, 1):
        for role in roles:
            cohort = generate_synthetic_cohort(role=role, count=candidates_per_role, seed=seed)
            target_weights = role_weights_map[role]

            for cand in cohort:
                candidates_processed += 1

                for mode in AblationMode:
                    eval_w = uniform_weights if mode == AblationMode.UNIFORM_WEIGHTS else target_weights
                    rci_est, rci_true, q_hats = evaluate_candidate_ablation(
                        candidate=cand,
                        mode=mode,
                        role_weights=eval_w,
                        true_weights=target_weights,
                    )

                    if rci_est is not None:
                        err = abs(rci_est - rci_true)
                        mode_estimates[mode].append(rci_est)
                        mode_true_rcis[mode].append(rci_true)
                        mode_errors[mode].append(err)
                        mode_errors_by_candidate[mode][cand.candidate_id] = err

                        # Track capability-level errors
                        for cap_key, q_val in q_hats.items():
                            true_q = cand.ground_truth_capabilities[cap_key]
                            mode_cap_errors[mode].append(abs(q_val - true_q))

                        # Role-specific tracking for baseline
                        if mode == AblationMode.FULL_CCI:
                            role_metrics[role.value]["errors"].append(err)
                            role_metrics[role.value]["est"].append(rci_est)
                            role_metrics[role.value]["true"].append(rci_true)

    elapsed_time = time.time() - t0
    print(f"Simulation completed in {elapsed_time:.2f} seconds ({candidates_processed:,} evaluations per mode).")
    print(f"================================================================================")

    # Compute aggregate metrics per mode
    ablation_summary: Dict[str, Dict[str, float]] = {}
    for mode in AblationMode:
        est = mode_estimates[mode]
        tru = mode_true_rcis[mode]
        errs = mode_errors[mode]
        cap_errs = mode_cap_errors[mode]

        mae = float(np.mean(errs)) if errs else 0.0
        rmse = float(np.sqrt(np.mean([(e - t) ** 2 for e, t in zip(est, tru)]))) if errs else 0.0
        spearman_rho, _ = stats.spearmanr(est, tru) if len(est) > 1 else (0.0, 0.0)
        kendall_tau, _ = stats.kendalltau(est, tru) if len(est) > 1 else (0.0, 0.0)
        cap_mae = float(np.mean(cap_errs)) if cap_errs else 0.0

        ablation_summary[mode.value] = {
            "rci_mae": round(mae, 4),
            "rci_rmse": round(rmse, 4),
            "spearman_rho": round(float(spearman_rho), 4),
            "kendall_tau": round(float(kendall_tau), 4),
            "capability_mae": round(cap_mae, 4),
            "sample_count": len(errs),
        }

    # Statistical tests: Wilcoxon signed-rank & Cliff's delta vs Full CCI
    statistical_tests: Dict[str, Dict[str, Any]] = {}
    full_error_map = mode_errors_by_candidate[AblationMode.FULL_CCI]

    for mode in AblationMode:
        if mode == AblationMode.FULL_CCI:
            continue
        ablated_error_map = mode_errors_by_candidate[mode]
        paired_full, paired_ablated = pair_candidate_errors(
            full_error_map, ablated_error_map
        )
        comp = compute_wilcoxon_comparison(paired_full, paired_ablated)
        comp["paired_sample_count"] = len(paired_full)
        comp["full_eligible_candidate_count"] = len(full_error_map)
        comp["ablation_eligible_candidate_count"] = len(ablated_error_map)
        statistical_tests[mode.value] = comp

    # Per-role summary for Full CCI
    per_role_summary: Dict[str, Dict[str, float]] = {}
    for r_name, data in role_metrics.items():
        r_errs = data["errors"]
        r_est = data["est"]
        r_true = data["true"]
        r_mae = float(np.mean(r_errs)) if r_errs else 0.0
        r_rmse = float(np.sqrt(np.mean([(e - t) ** 2 for e, t in zip(r_est, r_true)]))) if r_errs else 0.0
        rho, _ = stats.spearmanr(r_est, r_true) if len(r_est) > 1 else (0.0, 0.0)
        per_role_summary[r_name] = {
            "rci_mae": round(r_mae, 4),
            "rci_rmse": round(r_rmse, 4),
            "spearman_rho": round(float(rho), 4),
            "sample_count": len(r_errs),
        }

    return {
        "metadata": {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
            "scoring_config_version": ScoringConfig().version,
            "confidence_formula": "o * (a * t * v * x * r)^(1/5)",
            "minimum_capability_coverage": ScoringConfig().low_coverage_threshold,
            "cluster_artifact_decay": ScoringConfig().cluster_artifact_decay,
            "total_candidates": candidates_processed,
            "seeds": seeds,
            "roles": [r.value for r in roles],
            "candidates_per_role": candidates_per_role,
            "execution_time_seconds": round(elapsed_time, 2),
        },
        "ablation_summary": ablation_summary,
        "statistical_tests": statistical_tests,
        "per_role_summary": per_role_summary,
    }


def format_role_breakdown_markdown(per_role_summary: Dict[str, Dict[str, float]]) -> str:
    """Formats a Markdown table detailing Full CCI performance per canonical role."""
    lines = [
        "# Canonical Engineering Role Breakdown (Full CCI)",
        "",
        "Evaluation of Full CCI model accuracy across all six canonical engineering profiles.",
        f"Scoring config {ScoringConfig().version}; candidate estimates require attribution-gated coverage >= "
        f"{ScoringConfig().low_coverage_threshold:.2f}; artifact decay {ScoringConfig().cluster_artifact_decay:.1f}; "
        "lower coverage is UNKNOWN.",
        "",
        "| Canonical Engineering Role | Sample Count ($N$) | RCI MAE ↓ | RCI RMSE ↓ | Spearman's $\\rho$ ↑ |",
        "|:---------------------------|:------------------:|:---------:|:----------:|:-------------------:|",
    ]
    for role_name, metrics in per_role_summary.items():
        role_display = role_name.replace("_", " ").title()
        lines.append(
            f"| **{role_display}** | {metrics['sample_count']:,} | "
            f"{metrics['rci_mae']:.3f} | {metrics['rci_rmse']:.3f} | {metrics['spearman_rho']:.3f} |"
        )
    return "\n".join(lines)


def save_publication_artifacts(results: Dict[str, Any], output_dir: Path) -> None:
    """Generates and writes Markdown, LaTeX, and JSON publication tables."""
    output_dir.mkdir(parents=True, exist_ok=True)

    ablation_summary = results["ablation_summary"]
    statistical_tests = results["statistical_tests"]
    per_role_summary = results["per_role_summary"]

    # 1. table_ablation_study.md
    md_table = format_markdown_ablation_table(ablation_summary, statistical_tests)
    md_path = output_dir / "table_ablation_study.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("# Paper Reproducibility: Table 1 - Model Architecture Ablation Study\n\n")
        f.write(f"Total simulated candidates: $N = {results['metadata']['total_candidates']:,}$ across 6 canonical engineering roles.\n\n")
        f.write(md_table)
        f.write("\n\n*Note: Statistical significance tests ($p < 0.001$, marked ***) conducted via paired Wilcoxon signed-rank test against the Full CCI baseline.*\n")
    print(f"[+] Saved Markdown Table: {md_path}")

    # 2. table_ablation_study.tex
    latex_table = format_latex_ablation_table(ablation_summary, statistical_tests)
    tex_path = output_dir / "table_ablation_study.tex"
    with open(tex_path, "w", encoding="utf-8") as f:
        f.write(latex_table)
        f.write("\n")
    print(f"[+] Saved LaTeX Table:    {tex_path}")

    # 3. role_breakdown.md
    role_md = format_role_breakdown_markdown(per_role_summary)
    role_path = output_dir / "role_breakdown.md"
    with open(role_path, "w", encoding="utf-8") as f:
        f.write(role_md)
        f.write("\n")
    print(f"[+] Saved Role Breakdown: {role_path}")

    # 4. ablation_results.json
    json_path = output_dir / "ablation_results.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"[+] Saved JSON Results:   {json_path}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Candidate Capability Intelligence (CCI) Paper Reproducibility Engine"
    )
    parser.add_argument(
        "--seeds",
        type=int,
        nargs="+",
        default=list(range(1, 17)),
        help="Deterministic pseudo-random seeds (default: 1..16)",
    )
    parser.add_argument(
        "--candidates-per-role",
        type=int,
        default=50,
        help="Candidates per role per seed (default: 50, yielding 300 per seed)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=str(REPO_ROOT / "research" / "results"),
        help="Directory where output markdown, LaTeX, and JSON tables are written",
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Run a rapid evaluation (2 seeds, 10 candidates per role) for verification",
    )

    args = parser.parse_args()

    if args.quick:
        seeds = [42, 100]
        cand_per_role = 10
    else:
        seeds = args.seeds
        cand_per_role = args.candidates_per_role

    out_dir = Path(args.output_dir)
    results = run_full_simulation_study(
        seeds=seeds,
        candidates_per_role=cand_per_role,
    )

    save_publication_artifacts(results, out_dir)

    summary_table = format_markdown_ablation_table(results["ablation_summary"], results["statistical_tests"])
    try:
        print(summary_table)
    except UnicodeEncodeError:
        safe_table = summary_table.replace("↓", "v").replace("↑", "^").replace("$\\rho$", "rho").replace("$\\tau$", "tau")
        print(safe_table.encode("ascii", errors="replace").decode("ascii", errors="replace"))
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
