#!/usr/bin/env python3
"""Source-aware CCI synthetic validity protocol v2.

This runs a NEW synthetic experiment; it does not reproduce the archived 2026-09
paper results. All target weights here come from the separately specified
ROLE_BASELINE_PRIORS, not from ROLE_CAPABILITY_PROFILES that generate candidates.
These are still designer-defined priors, NOT external expert ground truth.
The evidence graph, live ingestion, fairness, and employment decisions are NOT
tested by this experiment.
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import sys
import scipy
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from scipy import stats

ROOT = Path(__file__).resolve().parent.parent
BACKEND_SRC = ROOT / "services" / "backend" / "src"
for search_root in (str(ROOT), str(BACKEND_SRC)):
    if search_root not in sys.path:
        sys.path.insert(0, search_root)
from cci.domain.enums import CanonicalRole, CapabilityKey, SourceFamily
from cci.research.ablation import AblationMode, evaluate_candidate_ablation
from cci.research.simulation import generate_synthetic_cohort
from cci.scoring.weights import ROLE_BASELINE_PRIORS


def independent_role_prior(role: CanonicalRole) -> dict[CapabilityKey, float]:
    """Normalize fixed scoring priors that the simulator does not read."""
    raw = ROLE_BASELINE_PRIORS[role]
    values = {cap: float(raw.get(cap, 0.0)) for cap in CapabilityKey}
    denom = sum(values.values())
    assert denom > 0.0
    return {k: v / denom for k, v in values.items()}


def simple_baseline(candidate, weights, kind: str):
    """Non-model baseline: equal evidence weight or within-capability median."""
    grouped = defaultdict(list)
    for observation in candidate.observations:
        grouped[observation.capability_key].append(observation.observed_score)
    qhat = {}
    for cap, values in grouped.items():
        qhat[cap] = float(np.median(values) if kind == "MEDIAN" else np.mean(values))
    if not qhat:
        return None, None, qhat
    denom = sum(weights[k] for k in qhat)
    if denom <= 0.0:
        return None, None, qhat
    pred = sum(weights[k] * qhat[k] for k in qhat) / denom
    target = sum(weights[k] * candidate.ground_truth_capabilities[k] for k in qhat) / denom
    return float(pred), float(target), qhat


def seed_bootstrap(sample_by_seed, seed_values, n_resamples=2000):
    """Percentile bootstrap over seed blocks, NOT 4,800 individual observations."""
    means = np.array([np.mean(sample_by_seed[s]) for s in seed_values], dtype=float)
    rng = np.random.default_rng(20261107)
    draws = rng.integers(0, len(means), size=(n_resamples, len(means)))
    boot = means[draws].mean(axis=1)
    return [float(np.quantile(boot, 0.025)), float(np.quantile(boot, 0.975))]


def run_validation(seeds, candidates_per_role=50, bootstrap_resamples=2000, record_sink=None):
    modes = ["FULL_CCI", "EQUAL_EVIDENCE", "MEDIAN_EVIDENCE",
             "NO_RECENCY_DECAY", "NO_OWNERSHIP_DISCOUNT",
             "UNCALIBRATED_SOURCES", "UNIFORM_WEIGHTS"]
    collected = {m: {"est": [], "true": [], "cap_err": [], "seed_err": defaultdict(list)}
                 for m in modes}
    sources = Counter()
    invalid_non_github_forks = 0
    count = 0
    for seed in seeds:
        for role in CanonicalRole:
            w = independent_role_prior(role)
            equal_w = {cap: 1.0 / len(CapabilityKey) for cap in CapabilityKey}
            for candidate_index, cand in enumerate(generate_synthetic_cohort(role=role, count=candidates_per_role, seed=seed)):
                count += 1
                for ob in cand.observations:
                    sources[ob.source_family.value] += 1
                    if ob.source_family is not SourceFamily.GITHUB and ob.ownership_score < 0.5:
                        invalid_non_github_forks += 1
                assert invalid_non_github_forks == 0, "source/ownership integrity violated"
                for mode in modes:
                    if mode == "EQUAL_EVIDENCE":
                        est, tru, qhat = simple_baseline(cand, w, "MEAN")
                    elif mode == "MEDIAN_EVIDENCE":
                        est, tru, qhat = simple_baseline(cand, w, "MEDIAN")
                    else:
                        setting = (AblationMode.UNIFORM_WEIGHTS if mode == "UNIFORM_WEIGHTS"
                                   else AblationMode(mode))
                        evaluated = equal_w if mode == "UNIFORM_WEIGHTS" else w
                        est, tru, qhat = evaluate_candidate_ablation(
                            cand, setting, role_weights=evaluated, true_weights=w
                        )
                    if est is None or tru is None:
                        continue
                    row = collected[mode]
                    row["est"].append(float(est))
                    row["true"].append(float(tru))
                    row["seed_err"][seed].append(abs(est - tru))
                    cap_abs_errors = [abs(qhat[k] - cand.ground_truth_capabilities[k]) for k in qhat]
                    row["cap_err"].extend(cap_abs_errors)
                    if record_sink is not None:
                        # Each row is synthetic and contains no personal data or generated UUID.
                        record_sink({
                            "seed": int(seed), "role": role.value,
                            "candidate_index": int(candidate_index), "mode": mode,
                            "estimated_rci": float(est), "target_rci": float(tru),
                            "rci_absolute_error": float(abs(est - tru)),
                            "capability_mae": float(np.mean(cap_abs_errors)) if cap_abs_errors else None,
                            "observed_capabilities": len(qhat),
                            "evidence_observations": len(cand.observations),
                        })

    summary = {}
    for mode, row in collected.items():
        e = np.array(row["est"])
        t = np.array(row["true"])
        rank = stats.spearmanr(e, t).statistic if len(e) > 2 else float("nan")
        summary[mode] = {
            "sample_count": int(len(e)),
            "rci_mae": round(float(np.mean(abs(e - t))), 5),
            "rci_rmse": round(float(np.sqrt(np.mean((e - t) ** 2))), 5),
            "capability_mae": round(float(np.mean(row["cap_err"])), 5),
            "spearman_rho": round(float(rank), 5),
            "rci_mae_95ci_seed_bootstrap": [
                round(x, 5) for x in seed_bootstrap(row["seed_err"], seeds, bootstrap_resamples)
            ],
        }
    # Paired seed-block intervals against BOTH simple baselines.
    # This post-run extension is labelled an additional contrast in the report:
    # the median baseline was observed to be stronger in the initial V2 run.
    for baseline_name in ("EQUAL_EVIDENCE", "MEDIAN_EVIDENCE"):
        baseline = collected[baseline_name]["seed_err"]
        full = collected["FULL_CCI"]["seed_err"]
        paired_delta = {
            s: [float(np.mean(baseline[s]) - np.mean(full[s]))] for s in seeds
        }
        summary[f"FULL_MINUS_{baseline_name}_BASELINE"] = {
            "metric": f"MAE({baseline_name}) - MAE(FULL_CCI), positive favors FULL",
            "analysis_type": "preregistered" if baseline_name == "EQUAL_EVIDENCE" else "post_hoc_follow_up",
            "seed_block_95ci": [
                round(x, 5) for x in seed_bootstrap(paired_delta, seeds, bootstrap_resamples)
            ],
            "mean_seed_difference": round(
                float(np.mean([paired_delta[s][0] for s in seeds])), 5
            ),
        }
    return {
        "protocol": "source-aware-v2",
        "runtime": {"python": platform.python_version(), "numpy": np.__version__,
                    "scipy": scipy.__version__, "github_sha": os.getenv("GITHUB_SHA"),
                    "github_ref": os.getenv("GITHUB_REF")},
        "record_schema": "one synthetic candidate-role instance per scoring mode; candidate_index is local to seed and role",
        "status": "synthetic experiment only; not independent human validation",
        "archived_v1_metrics_comparable": False,
        "target_weights": "designer-defined ROLE_BASELINE_PRIORS; independent of generator means",
        "known_limitations": [
            "ground truth remains generated from a role-profile simulator",
            "role target weights are designer-defined, not expert-validated",
            "no graph-on/graph-off causal experiment",
            "no real candidate assessment or demographic fairness measurement",
            "bootstrap seed blocks are only 16 when using default seeds",
        ],
        "seeds": seeds,
        "roles": [x.value for x in CanonicalRole],
        "candidates_per_role_per_seed": candidates_per_role,
        "simulated_instances": count,
        "source_counts": dict(sources),
        "invalid_non_github_fork_observations": invalid_non_github_forks,
        "results": summary,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--quick", action="store_true")
    parser.add_argument("--output", type=Path,
                        default=Path("research/results_v2/validity_v2.json"))
    parser.add_argument("--records-output", type=Path,
                        default=Path("research/results_v2/validity_v2_cases.jsonl"),
                        help="Synthetic per-case predictions for independent review")
    args = parser.parse_args()
    args.records_output.parent.mkdir(parents=True, exist_ok=True)
    with args.records_output.open("w", encoding="utf-8") as records_file:
        def write_record(row):
            records_file.write(json.dumps(row, sort_keys=True) + "\n")

        results = run_validation(
            seeds=[1, 2] if args.quick else list(range(1, 17)),
            candidates_per_role=5 if args.quick else 50,
            bootstrap_resamples=500 if args.quick else 2000,
            record_sink=write_record,
        )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(results["results"], indent=2))


if __name__ == "__main__":
    main()
