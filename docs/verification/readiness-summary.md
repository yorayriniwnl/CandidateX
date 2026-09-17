# CandidateX readiness summary — 17 September 2026

## Fixed in this branch

- Separates the submitted paper's **28,800 candidate-role controlled benchmark** from the repository's **4,800-sample supplementary implementation ablation**.
- Records paper headline metrics and experimental provenance in `research/paper_benchmark_manifest.json`.
- Aligns the displayed and calculated interview-probe priority equation with paper Eq. (11): `I_k = w_k [ alpha(1-Cov_k) + beta*CIwidth_k + gamma*Conf_k ]`.
- Removes the stale Mobile Engineering research role and uses the canonical Data Engineering role.
- Makes demo/fallback candidate provenance visible in the public UI.
- Relabels stored and regenerated ablation artifacts so they cannot be confused with the submitted paper benchmark.
- Adds paper-alignment regression tests and research API tests.
- Adds `/api/v1/research/paper-benchmark` and keeps `/api/v1/research/ablation-study` explicitly supplementary.
- Keeps the packaged FastAPI research router self-contained so the backend Docker image does not depend on repository-level `research/results` files.

## Verification evidence

- Vercel successfully built intermediate CandidateX branch heads containing the major UI and methodology changes. Recheck the final branch head immediately before integration.
- The companion portfolio repository built successfully on Vercel with corrected CandidateX benchmark/provenance copy.
- GitHub Actions currently cannot provide a valid backend/frontend test verdict: every observed job is terminated before a runner is assigned (`steps: []`, `runner_id: 0`, empty runner name). This is documented separately in `docs/verification/ci-external-runner-note.md`.

## Integration gate

Do not call CI green, and do not treat the GitHub Actions red badge as a test failure. Resolve the external runner/account condition, then rerun the unchanged workflow and require real step output before treating the full verification matrix as passed.
