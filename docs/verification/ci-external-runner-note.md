# GitHub Actions runner failure signature

Observed on 17 September 2026 for CandidateX PR #4 and the preceding main-branch run:

- every job concluded before executing any workflow step,
- `steps` was an empty array,
- `runner_id` was `0`,
- `runner_name` was empty,
- backend, frontend, and security jobs all failed within a few seconds of creation.

This signature means the workflow was parsed and jobs were created, but GitHub never assigned a runner. It is therefore not evidence that pytest, pnpm, the security audit, or the research sanity check executed and failed.

The repository should not add bypasses or fake-success workflow steps to hide this state. Resolve the GitHub Actions account / runner availability condition, then rerun the unchanged verification workflow and require real step output before calling CI green.
