# Comprehensive live candidate analysis

The candidate uploads a real resume and reviews the extracted identity, skills, projects,
education, experience, certifications, achievements, and links before starting acquisition.
The report must explain each finding using supplied document text or retrieved public sources.

Implementation extends the existing request-scoped live pipeline. GitHub acquisition retains
the profile, a bounded public repository inventory (including forks and archived repositories),
and detailed commit-pinned inspections of up to six repositories (100 selected files each).
Archives exceeding the size budget fall back to up to 12 Git blobs, selected across file
categories and checked against Git object hashes. Explicit repository links
take precedence. Inventory metadata and popularity never become capability evidence.

Other supplied public links are retrieved through DNS-pinned HTTP with public-address checks
at every redirect, no credentials/proxies, strict response/time limits, and no script execution.
Up to 24 links are fetched concurrently within a separate 20-second budget, capped at 512 KB
per page. Digital PDFs up to five pages are supported; scanned images are not OCRed. Every supplied link appears
in the report, including omitted, blocked, unavailable, or unsupported content. There is no
recursive crawl and links discovered on fetched pages are not automatically requested.

The report includes structured resume claims, profile/inventory information, per-repository
languages, dependency declarations, file categories, documentation and engineering signals,
claim-to-source skill matches, public page titles/excerpts, and credential review findings.
Names and titles on a credential page can match a resume; that is not issuer authentication,
proof of completion, or skill mastery. Experience and education remain declarations unless
independently substantiated. Repository-level commit attribution is sample-size-aware: small
recent-commit samples are shrunk before entering evidence confidence, and fork attribution
remains capped. Correlated observations from one repository are assigned evidence tiers and
diminishing returns, with the evidence kind and correlation rank retained in provenance.

When a job description is supplied, the dossier also includes requirement-level role fit.
Each requirement is `observed` for an exact technology-backed match, `related` for mapped
capability evidence without an exact technology match, `unknown` when no supporting evidence
was observed, or `unresolved` when the controlled ontology cannot map it. Mandatory gaps are
shown as interview priorities, not as an autonomous hiring recommendation.

## Evidence strength is explicit uncertainty

Every completed live dossier now carries an `analysis_confidence` summary. It is a deterministic evidence-quality band, not a probability or hiring recommendation. It does not establish identity, authorship, mastery, employment, credential authenticity, or job-performance accuracy, and it never changes the underlying RCI or six-factor evidence calculation.

The band gates are deliberately conservative: `insufficient` means no positive-confidence empirical evidence or role coverage below `0.35`; `limited` applies below `0.60` coverage or when a single cluster, missing interval, mandatory gap, source failure/unscanned source, or material unusable evidence limits the read; `moderate` applies below `0.80` coverage, below `3` independent clusters, below `0.80` interval coverage, an interval wider than `25`, or a meaningful conflict; `well_supported` requires all of the corresponding thresholds (`0.80` coverage, `3` clusters, `0.80` interval coverage, and maximum interval width `25`). These are presentation gates, not real-world validation or calibrated probabilities.

The `source_health` receipt summary retains partial-scan uncertainty with counts for supplied, observed, failed, not selected, not scanned, and security-blocked sources. Any status other than `observed`, `not_selected`, or `not_scanned` is failed; a `security_blocked` receipt is also counted as blocked. The summary is available at the response top level and under `analysis`, and its failure/unscanned counts are reflected in the dossier flags.

The UI keeps the numeric observed score visible for auditability but labels a capability `Limited evidence` when coverage is below `0.35` or its interval is unavailable. If an older response lacks the additive fields, the client falls back to `Insufficient evidence` rather than inventing a stronger band.

Validation covers DOCX reading order/header links, section/name extraction, exact technology
matching, public-only DNS pinning and redirects, response caps, provider failures, full link
accounting, report rendering/export, and real public production upload/acquisition.
