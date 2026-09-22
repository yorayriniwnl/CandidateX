# CandidateX hardening baseline

**Audit date:** 2026-09-23
**Source:** Draft PR [#20](https://github.com/yorayriniwnl/CandidateX/pull/20), branch `codex/deep-evidence-foundation`
**Audited commit:** `57e9797dcfb7ad223aeec2de7226be0b9a3e684f`
**Base commit:** `baa559f130fcb1bc5706ce55765bd7cb6cffa0ba`
**Working branch:** `codex/backend-hardening`

This baseline was captured before Fix 1. No scoring behavior was changed.

## Environment

- Python 3.12.10 was available. Python 3.11 was not installed locally, so the CI Python 3.11 matrix was not reproduced.
- Node.js v24.19.0 and pnpm 11.19.0 were used. CI specifies Node 22 and pnpm 11.15.1.
- 209 backend tests and 8 browser tests across 2 files were collected.

## Verification results

| Check | Result |
| --- | --- |
| Full backend suite (`python -m pytest tests -q`) | Passed, 209 collected, 0 failures |
| Browser suite (`pnpm --filter web test`) | Passed, 8/8 |
| Next.js route type generation | Passed |
| Frontend TypeScript check (`pnpm --filter web lint`) | Passed |
| Frontend production build | Passed |
| SSRF and repository workspace security tests | Passed, 10/10 |
| Scoring and paper theorem audit | Passed |
| Research quick simulation | Passed, 120 simulated candidates per mode |
| Database seeding smoke test | Passed, 2 sample dossiers created in a temporary database |
| Static untrusted-code checks | Passed: no analyzer `exec`/`eval` calls and no candidate-sourced `subprocess.run` pattern |

The backend suite emitted two dependency deprecation warnings: Starlette's `TestClient` integration with `httpx`, and AnyIO's `BlockingPortal` alias. The seeder also emitted a PyMuPDF `fitz` API deprecation warning.

## Deployment state

- Production `https://candidatex-smoky.vercel.app` resolved to `/analyze` and the live analysis page was reachable during the audit.
- PR #20 reports an active, Ready Vercel preview at commit `57e9797`: [preview](https://candidatex-eekvulvlt-yorayriniwnl-1218s-projects.vercel.app). The listed deployment event is from 2026-09-22 19:25 UTC.
- The GitHub checks page reported checks re-running, so there was no settled overall CI result to record at audit time.

## Findings carried into the sequential audit

- PR #20 documents synchronous request and acquisition budgets that constrain deeper analysis. These are later backend architecture fixes in the supplied sequence.
- The seed-data smoke test emitted personal-looking names and email domains. This is tracked for the supplied synthetic-data cleanup fix.
- No scoring behavior was changed while establishing this baseline.

Machine-readable results: [candidatex-hardening-baseline.json](candidatex-hardening-baseline.json).
