**Frontend audit evidence — 28 September 2026**

The findings are in [the audit report](../../docs/audits/2026-09-28-frontend-workflow-audit.md). These diagnostic tests demonstrate defects; their passing status is not an application acceptance result.

- `browser-results.json`: 12 recovered workflow scenarios, including controlled errors, downloads, mobile layout, keyboard behavior, and interview submission payloads.
- `auth-browser-results.json`: three focused scenarios covering the real local session endpoint, external login redirection, and recovery requests.
- `auth-results.json`: ten current-source route-handler probes with synthetic credentials and mocked OAuth transport. Includes valid-state, missing-code, and empty-session controls.
- `observations.json`: named observations extracted from both browser reports. Long duplicate dialog text and unrelated antivirus POST URLs are omitted here; raw browser output remains in the original reports.
- `source-manifest.json`: SHA-256 comparison of 113 application source/configuration files with the isolated preview source.
- `version-notes.json`: final comparison of concurrently changing files and finding qualifications.
- `original-audit.spec.cjs` / `original-audit.config.cjs`: exact copies of the recovered harness. Its fixture path and preview URL are retained for provenance. The original test path was in the isolated preview, where web dependencies resolve.
- `auth-probes.cjs`, `auth-browser.spec.cjs`, and `auth-browser.config.cjs`: focused probes added in this continuation.
- `browser-results/`: screenshots produced by the recovered scenarios.

The tested preview was `C:\Users\yoray\AppData\Local\Temp\candidatex-frontend-audit-20260928-105715\apps\web` with build ID `8Tf6W5i3lvlo7H7aIkTvF`. It used the workspace's installed dependencies and the existing `artifacts/result-redesign/live-result.json` fixture. Application writes were intercepted and OAuth responses mocked.

To repeat the source-only route probes from the repository root:

```powershell
node artifacts/frontend-audit-2026-09-28/auth-probes.cjs
```

To repeat the focused browser checks from `apps/web`, with the existing isolated build available and port 3178 free:

```powershell
$env:CANDIDATEX_AUDIT_PREVIEW_DIR = 'C:\Users\yoray\AppData\Local\Temp\candidatex-frontend-audit-20260928-105715\apps\web'
pnpm exec playwright test --config '../../artifacts/frontend-audit-2026-09-28/auth-browser.config.cjs'
Remove-Item Env:CANDIDATEX_AUDIT_PREVIEW_DIR
```

The recovered twelve-scenario harness can be rerun from the isolated preview's `apps/web` directory using `pnpm exec playwright test --config audit.config.cjs`. Reruns overwrite their configured result directories. A new source build should use a separate preview directory; these results should not be attributed to a later changed build without rerunning.

No application fixes, backend deletions, commits, pushes, or deployments were performed in this continuation. Temporary audit servers exited after the tests; the original development servers were preserved.
