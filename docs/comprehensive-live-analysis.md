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

Validation covers DOCX reading order/header links, section/name extraction, exact technology
matching, public-only DNS pinning and redirects, response caps, provider failures, full link
accounting, report rendering/export, and real public production upload/acquisition.
