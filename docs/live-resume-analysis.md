# Live analysis research demo

The live-analysis demonstration is `/analyze`: use synthetic PDF/DOCX documents to review extracted links and declared GitHub identity, fetch public repositories, and inspect/export an evidence-backed dossier. **Do not upload real candidate resumes.** The public flow has no user accounts, tenant isolation, or application-level rate limits, and its results are not validated for employment decisions. `/research-demo` is a separate synthetic teaching tool.

## Data flow and implementation

1. The same-origin Next.js `/api/live/intake` route forwards a bounded binary upload to FastAPI. Digital PDF text, embedded annotations, DOCX hyperlinks, and visible URLs are extracted with the existing parsers. No OCR, search, or invented links.
2. Intake returns a document SHA-256, extracted manifest, and text preview. The browser holds this only in memory. The user can correct the source selection and supply the candidate-declared GitHub username; neither constitutes verified identity.
3. `/api/live/analyze` forwards the reviewed manifest, selected role/JD, explicit GitHub URLs and other selected public links. Profiles include public account metadata and up to 200 public repository inventory entries. Explicit repository links take priority for detailed scans.
4. The acquisition service fetches GitHub metadata, up to 30 recent commits, and a commit-pinned archive from fixed GitHub hosts. It does not follow redirects or execute candidate code. Only public repositories are accepted, even if a server token can access private ones.
5. Selected files pass through the existing code, database, testing, infrastructure, and documentation analyzers. Observations preserve commit SHA, artifact hash, file/line, extracted trace, analyzer version, and all confidence factors. Evidence is deduplicated and bounded before invoking the paper's scoring pipeline.
6. Supplied public HTML/text pages and small digital PDFs are inspected through DNS-pinned transport. Every redirect is validated; proxies, credentials, private networks and script execution are excluded. Public claims do not increase capability scores.
7. The response includes structured resume sections, skill-to-artifact matches, credential text matches, project/education/experience review, repository engineering summaries, source receipts, ownership assumptions, dossier, complete graph and scoring configuration. No public candidate lookup endpoint or cross-user dossier store is used by the deployed live service. Download JSON to retain the snapshot.

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

```powershell
python -m pip install -e "services/backend[dev]"
python -m uvicorn cci.live_app:app --app-dir services/backend/src --port 8000
# In another terminal:
pnpm --filter web dev
```

The full legacy backend (`cci.main:app`) also includes the live endpoints for tests/local development. The dedicated deployed app (`cci.live_app:app`) excludes the legacy candidate directory and lookup APIs.

## Hosting

The hosting steps below deploy a public research demo for synthetic data only; they do not make this system ready for live hiring use. Deploy `services/backend` as a Vercel FastAPI project using its `app.py`, `.python-version`, and `vercel.json`. Set the existing frontend project's server-only `CCI_API_URL` to that backend's production URL, then deploy the frontend. The production bridge returns an explicit error if the backend URL is absent; it does not fall back to localhost on Vercel.

An optional server-side `GITHUB_TOKEN` increases GitHub API limits. No browser token or user's GitHub login is required for public acquisition. Without it, shared deployment IP limits can produce rate-limit receipts; those failures never substitute synthetic results.

## Verification

Backend tests exercise document extraction, actual static analyzers against HTTP fixtures, provider failures, profile bounds, zero ownership, redirects, archive traversal/symlinks/expansion limits, private repositories, and the absence of candidate lookup routes on the deployed app. Browser tests cover upload, review, unknown results, exports, and failures. A separate manual smoke test must fetch a real public GitHub repository through the deployed frontend before declaring the public flow operational.
