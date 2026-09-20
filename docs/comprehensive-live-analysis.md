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
independently substantiated. Repository-level commit attribution retains its existing limits.

Validation covers DOCX reading order/header links, section/name extraction, exact technology
matching, public-only DNS pinning and redirects, response caps, provider failures, full link
accounting, report rendering/export, and real public production upload/acquisition.
