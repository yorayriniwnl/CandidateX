# Live resume analysis (local development only)

Live resume and public profile analysis (`/analyze`) is strictly a local-development workflow. The public hosted deployment serves only the bounded synthetic demonstration at `/research-demo`. In production builds, real-data inputs and live analysis routes are blocked, and entry routes redirect to `/research-demo`.

## Data flow and implementation (local only)

1. The same-origin Next.js `/api/live/intake` route forwards a bounded binary upload to FastAPI when running in development. Digital PDF text, embedded annotations, DOCX hyperlinks, and visible URLs are extracted with the existing parsers. No OCR, search, or invented links.
2. Intake returns a document SHA-256, extracted manifest, and text preview. The browser holds this only in memory. The user can correct the source selection and supply the candidate-declared GitHub username; neither constitutes verified identity.
3. `/api/live/analyze` forwards the reviewed manifest, selected role/JD, explicit GitHub URLs and other selected public links. Profiles include public account metadata and up to 200 public repository inventory entries. Explicit repository links take priority for detailed scans.
4. The acquisition service fetches GitHub metadata, up to 30 recent commits, and a commit-pinned archive from fixed GitHub hosts. It does not follow redirects or execute candidate code. Only public repositories are accepted, even if a server token can access private ones.
5. Selected files pass through the existing code, database, testing, infrastructure, and documentation analyzers. Observations preserve commit SHA, artifact hash, file/line, extracted trace, analyzer version, and all confidence factors. All analyzer observations are retained with stable IDs; correlated observations receive family weights before scoring. For up to 24 high-signal paths, path history supplies artifact recency and attribution. Repository last activity is recorded separately and never stands in for artifact age. Missing or deferred path history yields `artifact_recency_unknown`.
6. Supplied public HTML/text pages and small digital PDFs are inspected through DNS-pinned transport. Every redirect is validated; proxies, credentials, private networks and script execution are excluded. Public claims do not increase capability scores.
7. The response includes structured resume sections, skill-to-artifact matches, credential text matches, project/education/experience review, repository engineering summaries, source receipts, ownership assumptions, dossier, complete graph and scoring configuration. No public candidate lookup endpoint or cross-user dossier store is used. Download JSON to retain the snapshot.

## Limits and honest interpretation

- Upload: 3 MB, up to 30 PDF pages, bounded DOCX expansion. Image-only resumes must be converted to text-based documents first.
- Acquisition: up to 6 repositories, 100 selected text files/repository, 128 KB/file, 8 MB compressed and 24 MB expanded archive, 45-second network budget. Oversized archives fall back to up to 12 Git blobs selected across categories, checked against their Git object hashes. Generated/vendor/build directories and symlinks are omitted. Receipts report omissions; a bounded scan is not a whole-repository audit.
- Other public links: up to 24 per run, 512 KB each, three redirects, six concurrent requests within a separate 20-second budget. Digital PDFs are limited to five pages. Every supplied URL remains visible, including those omitted by selection or budget. The page does not recursively crawl discovered links.
- Ownership: the fraction of recent commits attributed by GitHub to the declared account, capped at 0.9 (0.5 for forks). No declared/matching author means zero attribution, unknown capability, and preserved uncredited observations. This does not prove line-level ownership.
- Reliability uses existing source-family priors, without simulated true/false positives. Static verification/depth factors are explicit conservative prototype settings. They are not empirically calibrated probabilities.
- Resume claims do not create technical scores. Missing, unavailable, rate-limited, or uncredited evidence stays unknown. The result supports interviews and does not make hiring decisions.
- LinkedIn, coding profiles, credentials, portfolios and deployed websites expose public text only when accessible. Login gates and script-only pages can remain unresolved. Credential topic/name matches are review leads, not issuer authentication, proof of completion or skill mastery. No login bypass or broad identity search occurs.
- The document and result are request-scoped, with no server-side retention or account history. Refresh clears the browser view. Exports contain personal information; the user controls where to save them.

## Run locally

To run the local live analysis application:

```powershell
python -m pip install -e "services/backend[dev]"
python -m uvicorn cci.live_app:app --app-dir services/backend/src --port 8000
# In another terminal:
pnpm --filter web dev
```

The full local backend (`cci.main:app`) also includes the live endpoints as well as the `/api/v1/synthetic-demo` endpoints for local tests and development. The dedicated local live app (`cci.live_app:app`) excludes candidate directory and lookup APIs. Neither entrypoint is mounted for the production deployment.

## Production hosting boundary

The public deployment is strictly a synthetic demonstration:

- **Backend Vercel entrypoint:** `services/backend/app.py` serves the production FastAPI application (`cci.synthetic_demo_app:app`), exposing only `/health` and the stateless synthetic demo endpoints at `/api/v1/synthetic-demo/run` and `/api/v1/synthetic-demo/rescore`. It does not mount live intake, live profile analysis, database, or candidate-persistence routes.
- **Strict synthetic API contracts:** The public demo API accepts only allowlisted simulation parameters: `scenario`, `role`, `excluded_sources`, `ownership_multiplier`, and `reliability_false_positives` (and valid `weights` on rescore). Extra fields—including candidate UUIDs, resume text, profile URLs, job descriptions, or user-written override notes—are rejected with HTTP 422. A fixed synthetic candidate identity (`d3333333-3333-4333-8333-333333333333`) and constant demonstration justification are applied server-side.
- **Frontend production boundary:** In production builds, `/`, `/analyze`, `/hr`, and `/workspace` redirect to `/research-demo`. Requests to `/api/live/*` return HTTP 404 before reading the request body or contacting any upstream service.
- **Fail-closed backend bridge:** The Next.js demo bridge (`/api/demo`) requires a configured `CCI_API_URL` environment variable pointing to the deployed synthetic backend. If `CCI_API_URL` is omitted in production, it fails closed with HTTP 503 and never falls back to `127.0.0.1`.
- **Non-hiring prototype notice:** The hosted demo is an interactive research prototype designed to inspect evidence propagation and uncertainty handling under synthetic scenarios. It is not a validated hiring predictor, fairness-certified assessment, or multi-tenant SaaS.

Deploy `services/backend` as a Vercel FastAPI project using its `app.py`, `.python-version`, and `vercel.json`. Set the frontend project's server-only `CCI_API_URL` environment variable to the deployed backend's URL, then deploy the frontend.

## Verification

- **Backend tests:** `pytest -v` exercises synthetic-demo isolation, strict input validation, stateless rescoring, empty-scenario unknown preservation, and local live-analysis analyzers.
- **Production web tests:** `pnpm --filter web run test:production` runs Playwright against the built Next.js production server and the Vercel FastAPI entrypoint (`app:app`), verifying route redirects, blocked live endpoints, and end-to-end synthetic run/rescore flows.
- **Local web tests:** `pnpm --filter web test` verifies local development behavior against `next dev` and `cci.main:app`.
