# CCI Source-Aware Validity Protocol v2 (pre-registered engineering plan)

**Status:** Implementation proposed for review. The 2026-09-17 archived 4,800-case
results were produced by v1 and cannot be transferred to this revised generator.

## Purpose

Test whether CCI's six-factor confidence fusion improves synthetic capability
and role-index estimation over simpler, preregistered alternatives. This is NOT
a validation of real candidate competence, recruitment decisions, causal graph
benefits, source-crawling reliability, or demographic fairness.

## Changes from v1

1. Fork/shared-repository contamination is emitted only for GitHub observations.
2. Role-specific random streams are derived from both the seed and the role index.
3. The validation target uses independently specified, fixed
   `ROLE_BASELINE_PRIORS` instead of profile means used by the generator. These
   are still designer-authored priors, **not** independent job-expert labels.
4. Equal-evidence and median-evidence estimators serve as non-CCI baselines.
5. Error uncertainty is calculated with 16 seed blocks, not with 4,800 presumed
   independent candidate-level rows.
6. Results are written to a new `research/results_v2/` directory. Never overwrite
   or relabel the v1 `research/results/` artifacts.

## Hypotheses and interpretation

- H1 (synthetic capability): Full CCI has lower capability MAE than equal
  evidence and median-evidence baselines. The hypothesis is supported only if
  the observed effect is positive and uncertainty is sufficiently narrow.
- H2 (synthetic role index): Full CCI has lower RCI MAE than the equal-evidence
  baseline under a *fixed*, disclosed set of role priors. Primary effect is
  MAE(equal evidence) minus MAE(full). A seed-bootstrap 95% interval entirely
  greater than zero supports H2 under these assumptions; intervals crossing
  zero indicate inconclusive evidence. No multiple-test inference is claimed.
- H3 (ablation): Removing a factor can improve one metric while worsening
  another. Report every negative and null result, including source weighting.
- H4 (graph contribution): NOT TESTED. The graph is constructed downstream of
  scoring in the inspected pipeline. Only a newly implemented graph-derived
  scoring feature compared against an otherwise matched graph-off model could
  establish an accuracy contribution.

## Dataset and analysis scope

Default: 16 seeds × 6 roles × 50 synthetic candidate-role instances = 4,800.
The generator contains 12 latent capabilities and source-family-conditioned noisy
observations; it is not an independent human assessment set.
Primary measurements: RCI MAE, capability MAE, RCI RMSE.
Secondary descriptive measurement: Spearman rho. The seed-block bootstrap
estimates variability under generator seed changes only.
Correlated evidence, model misspecification, synthetic role stereotypes,
and self-reported evidence biases remain threats to validity.

## Execute after installing the repository's dependencies

```bash
python -m pytest services/backend/tests/unit/research/test_synthetic_generator_integrity.py services/backend/tests/unit/research/test_validity_v2.py
python research/run_validity_v2.py --quick --output research/results_v2/quick.json
python research/run_validity_v2.py --output research/results_v2/validity_v2.json
python research/run_paper_experiments.py --output-dir research/results_v2/original_ablation_rerun
```

The V2 runner now also exports synthetic per-case JSONL records with seed, role, mode,
local candidate index, predicted and latent target indices, and absolute errors.
The CI artifact bundles both aggregate and case-level files; no real applicant data
are included. Record runtime NumPy/SciPy/Python versions and GitHub runner SHA.

Validate all output counts, no invalid non-GitHub fork patterns, no NaN/Inf values,
and convergence of metrics across the two scripts. Pin and report Python/NumPy/SciPy
versions and the exact Git commit SHA in the eventual manuscript supplement.
Don't copy the output into the manuscript until source review and rerun checks pass.

## Publication gates remaining

1. Independently evaluated job-role weights and blind technical assessments.
2. An external or de-identified candidate dataset with permission and consent.
3. Graph *reporting* usefulness assessed separately from predictive accuracy.
4. Dataset leakage audits, dependence-aware sensitivity studies, robustness
   analyses for missing or adversarial evidence, and explicit fairness evaluation.
5. Author-approved affiliations, corresponding author, contributions, funding,
   competing interests, ethics, and AI-tool disclosures.

**Do not claim journal-level validation, statistical superiority, or real-world
hiring effectiveness solely from this synthetic protocol.**
