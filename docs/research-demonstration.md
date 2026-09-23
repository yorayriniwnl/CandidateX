# CandidateX research demonstration

CandidateX demonstrates the mechanism in **Role-Aware Candidate Capability Intelligence for Pre-Interview Technical Assessment Using Multi-Source Evidence Fusion** at `/research-demo`. The main `/` route now opens the [real resume and live GitHub workflow](live-resume-analysis.md) at `/analyze`. `/workspace` retains the earlier prototype interface, and `/hr` retains the HR sample interface.

## What is implemented

The demonstration runs through the backend's actual confidence, capability, coverage, role-weight, uncertainty, contradiction, and interview-probe modules. It does not substitute precomputed dossiers in the browser.

| Paper concept | Executable demonstration |
| --- | --- |
| Source reliability, Eq. 1 | Beta priors with eight explicitly simulated true positives per source; adjustable simulated false positives |
| Confidence, Eq. 2 | Five-factor evidence-quality geometric mean multiplied by a direct path-attribution gate; inspectable, with no arbitrary attribution threshold |
| Capability, Eq. 3 | Confidence-weighted technical observations; candidate estimate is UNKNOWN until configured attribution-gated coverage reaches 0.35 |
| Effective count and conflict, Eq. 4 | Kish effective count and positive/negative support diagnostic |
| Role conditioning, Eq. 5 | Six canonical role priors plus parsed JD requirements; softmax normalization |
| Coverage and RCI, Eqs. 6-7 | Coverage uses source-family clusters, unique artifacts, and 0.5 geometric within-cluster decay; RCI includes only estimates meeting the configured 0.35 minimum |
| Interview priorities, Eq. 8 | Shared scorer: weight times the sum of coverage-gap, normalized interval-width and conflict terms |
| Provenance graph | All nine node types, source/artifact/revision/fingerprint links, confidence-bearing attribution, requirements and evidence-linked questions |
| Overrides | New dossier snapshots retaining evidence and an explicit justification/history; coverage, status, questions and graph update together |

### Implementation conventions

- Evidence support, capability estimates, and RCI are on a 0-100 scale. RCI therefore does not multiply these estimates by 100 again. Probe interval width is divided by 100.
- JD parsing uses the controlled synonym ontology. Unrecognized requirements remain unresolved and do not add capability weights. An embedding-based parser is not implemented in this demonstration.
- The prototype adds canonical-role priors to the JD importance function. Temperature, saturation, confidence weights, and threshold are exported with each run. These are prototype settings, not a reconstruction of the manuscript's unavailable calibration.
- Confidence intervals resample project clusters. Fewer than two independent clusters produces an unavailable interval. Missing cluster IDs conservatively group records by source locator. The probe scorer uses maximal normalized interval uncertainty when an interval cannot be estimated.
- Scenarios use three simulated project clusters. Artifact fingerprints hash normalized observation content, source locator, immutable content revision, and extractor version. A separate digest includes all observations and confidence factors, so changing ownership or reliability changes the exported digest.
- Authorship and review outcomes in these scenarios are simulated inputs, not independently verified facts about a person.

## Start locally

From the repository root, install dependencies once:

```powershell
python -m pip install -e "services/backend[dev]"
pnpm install --frozen-lockfile
```

In one terminal, start a single backend worker:

```powershell
python -m uvicorn cci.main:app --app-dir services/backend/src --host 127.0.0.1 --port 8000
```

In a second terminal:

```powershell
pnpm --filter web dev
```

Open `http://localhost:3000`. The new page uses a same-origin Next.js route to call the backend. `CCI_API_URL` is a **server-side runtime setting** (default `http://127.0.0.1:8000`). Set it in the frontend process if using another backend port. This avoids exposing a build-time localhost API URL to the demo browser.

The demonstration needs no database, Redis, external API credentials, candidate uploads, or network acquisition. Its run registry is process-local: use one backend worker and export JSON to retain a snapshot across restarts. Refreshing the page clears its current view; it never silently restores an unrelated dossier.

For a production-build local preview:

```powershell
pnpm --filter web build
pnpm --filter web start
```

## Five-minute presentation

1. **Consistent evidence / Backend:** run the default scenario. Show capability, coverage and the evidence inspector. Every displayed observation is explicitly synthetic.
2. **Same evidence / Frontend:** change only the role and rerun. Compare the previous snapshot and confirm the evidence digest is unchanged while weights and RCI change.
3. **JD conditioning:** enter `Must have React and TypeScript.` and rerun. Open parsed requirements and inspect the changed role weights. Unmapped wording is labeled unresolved.
4. **Missing evidence:** choose Sparse evidence. Backend/database/testing remain observed; other capabilities become unknown. Coverage falls and confidence intervals are unavailable because only one project is represented. No usable evidence gives unknown RCI and zero coverage.
5. **Ownership and conflict:** lower ownership or choose Ambiguous GitHub ownership. Inspect confidence changes. Choose Conflicting observations to see negative evidence, contradiction diagnostics and interview probes.
6. **Expert override:** give a justification and focus all weight on one capability. Evidence stays unchanged, but RCI, coverage, insufficient-evidence status, questions and the graph are regenerated together. The control is a teaching example; it is not a recommended hiring rubric.
7. **Export:** save the full JSON snapshot, including inputs, config, calibration assumptions, evidence, graph, questions and override history.
8. **Research boundary:** show the two experiment panels. State explicitly that neither synthetic experiment establishes real-world hiring accuracy.

Coverage saturates at the configured evidence threshold. Removing one source or slightly reducing confidence may leave saturated coverage unchanged; this is expected from Eq. 6, not a disconnected control.

## Benchmark boundaries

| Artifact | Meaning |
| --- | --- |
| Manuscript headline benchmark | 16 seeds x 300 candidates x 6 roles = 28,800 candidate-role pairs; reported rho 0.928 +/- 0.013. Each candidate is evaluated against all roles. |
| Public executable prototype | 16 seeds x 6 roles x 50 distinct candidates per role = 4,800 candidates per ablation mode; scoring config 4.0.0 uses cluster-aware coverage, 0.5 within-cluster artifact decay, and a 0.35 minimum capability coverage. |
| Interactive scenarios | Small, explicit teaching examples. They execute the core method and do not regenerate either benchmark. |

The manuscript's Section 2.6 states that original per-seed/per-role outputs and exact calibration values for the headline benchmark are unavailable. The public runner is a separate experiment. Do not label its outputs a reproduction of the headline benchmark. Per-role ablation values absent from the archived artifact are displayed as unavailable.

Run the separate experiment without replacing its committed artifacts:

```powershell
python research/run_paper_experiments.py --output-dir reports/research-demo-verification
```

## Verification

```powershell
python -m pytest services/backend/tests
pnpm --filter web exec tsc --noEmit --incremental false
pnpm --filter web build
pnpm --filter web exec playwright install chromium
pnpm --filter web test
```

The browser tests launch their own backend on 8017 and production frontend on 3108, then stop both. Those ports must be free. They exercise real browser-to-API calculations, role and JD changes, sparse/conflicting/empty evidence, zero ownership, provenance, overrides, export, failure handling, the default route, and mobile layout. The backend suite uses a disposable database instead of the user's local database.

## Scope limits

This completes a controlled research demonstration, not autonomous assessment of arbitrary real CVs or repositories. The library contains acquisition and static-analyzer modules, but the normal pipeline does not automatically call them. Without explicitly registered observations, it reports unknown rather than inventing capability or ownership. The earlier intake screens are prototype controls, not proof of document ingestion.

Live acquisition integration, embedding-assisted JD mapping, durable background execution, object-store snapshots, multi-tenant authorization, independently validated extraction/ownership, and real-world study validation remain separate work. Deployment inspector helpers also need further hardening before enabling untrusted remote acquisition. None of those integrations is represented as running on the synthetic demonstration page.

Overrides in the legacy workspace are session-scoped unless an organization requests database persistence. A requested persistent override returns failure if its transaction fails; it does not publish a new successful dossier in memory. The new demonstration exports its explicit snapshot history and does not claim database durability.
