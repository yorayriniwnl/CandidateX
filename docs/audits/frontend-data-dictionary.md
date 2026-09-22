# CandidateX Frontend Data Dictionary

**Audited against:** current backend contracts and the request-scoped live response on 2026-09-23.
**Scope rule:** “Available” means a field is defined in the current backend response or model. It does not mean that the public Vercel live-analysis app persists or serves it later.

## Current live intake

| Field | Meaning | Type / unit | Nullable | Source | User-facing name | Screen |
| --- | --- | --- | --- | --- | --- | --- |
| candidate_id | Request-scoped candidate identifier generated during resume intake. | UUID | No | ResumeIntake | Review ID; not a durable candidate record | Intake and export |
| manifest.display_name | Name extracted from the supplied resume. | String | No | CandidateManifest | Candidate | Intake, report header |
| manifest.email | Email extracted from the supplied resume. | String | Yes | CandidateManifest | Email | Intake; PII, show only where needed |
| manifest.claimed_skills | Resume-declared skills. | String[] | No; may be empty | CandidateManifest | Claimed skills | Intake and claims/skills review; declaration only |
| manifest.github_urls | GitHub profiles/repositories supplied or extracted from the resume. | HTTPS URL[] | No; may be empty | CandidateManifest | GitHub sources | Source selection |
| manifest.linkedin_urls | Supplied LinkedIn URLs. | URL[] | No; may be empty | CandidateManifest | LinkedIn sources | Source selection |
| manifest.coding_profile_urls | Supplied coding-profile URLs. | URL[] | No; may be empty | CandidateManifest | Coding-profile sources | Source selection |
| manifest.credential_urls | Supplied credential URLs. | URL[] | No; may be empty | CandidateManifest | Credential sources | Source selection |
| manifest.deployment_urls | Supplied deployment URLs. | URL[] | No; may be empty | CandidateManifest | Deployment sources | Source selection |
| manifest.portfolio_urls | Supplied portfolio URLs. | URL[] | No; may be empty | CandidateManifest | Portfolio sources | Source selection |
| manifest.project_links | Supplied project links. | URL[] | No; may be empty | CandidateManifest | Project links | Source selection |
| manifest.project_claims | Structured resume project claims, usually title, description, and technologies. | Object[] | No; may be empty | CandidateManifest | Claimed projects | Intake and project review |
| filename | Uploaded document name. | String | No | ResumeIntake | Resume file | Intake details |
| document_sha256 | Hash of the uploaded document. | 64-character SHA-256 | No | ResumeIntake | Document hash | Audit detail/export |
| text_preview | Bounded extracted-text preview. | String, max 12,000 characters | No; may be empty | ResumeIntake | Extracted text | Collapsed “Inspect extraction” detail |
| warnings | Resume parser warnings. | String[] | No; may be empty | ResumeIntake | Extraction notes | Intake |
| storage | Retention mode for this endpoint. Currently request_only. | String enum-like value | No | ResumeIntake and live response | Processing and storage | Privacy note |
| resume_review.sections | Resume claims grouped by section (education, experience, credentials, achievements, etc.). | Map<string, string[]> | No; keys may be absent | ResumeReview | Resume claims | Claim, education, experience, and credential views |
| resume_review.learning_skills | Skills explicitly described as currently being learned. | String[] | No; may be empty | ResumeReview | Currently learning | Skills view |
| resume_review.observations | Deterministic extraction observations. | String[] | No; may be empty | ResumeReview | Extraction observations | Intake/audit |
| resume_review.extraction_method | Name of extraction approach. | String | No | ResumeReview | Extraction method | Audit detail |

The backend CandidateManifest also has experience_claims, manifest_version, and created_at. The current ResumeIntake TypeScript shape does not declare all of these fields. Do not rely on them in the UI until frontend and backend contracts are aligned.

## Analysis request context

| Field | Meaning | Type / unit | Nullable | Source | User-facing name | Screen |
| --- | --- | --- | --- | --- | --- | --- |
| role | One of the six canonical engineering roles: backend, frontend, fullstack, ml_engineer, devops_cloud, data_engineer. | Enum string | No; defaults to backend | LiveAnalysisRequest | Target role | Intake and report header |
| jd_text | User-provided job-description text used to derive normalized requirements and role weights. | String, max 20,000 characters | No; may be empty | LiveAnalysisRequest | Job description | Intake and expected-requirements view |
| github_urls | Selected GitHub profiles or repositories. | Validated HTTPS URL[]; max 20 | No; may be empty | LiveAnalysisRequest | Selected GitHub sources | Source selection |
| external_urls | Selected public links outside the GitHub-specific field. | URL[]; max 100 | Yes; omitted means use extracted links | LiveAnalysisRequest | Selected public sources | Source selection |
| github_identity | Candidate-declared GitHub username used for recent-commit attribution. | String, max 39 characters | No; empty means no declared identity | LiveAnalysisRequest | Candidate-declared GitHub username | Source selection and attribution notes |

The live workflow has no persisted analysis profile setting or durable run-creation field. The current page sends role/JD/source values directly in the analyze request.

## Role expectations and fit

| Field | Meaning | Type / unit | Nullable | Source | User-facing name | Screen |
| --- | --- | --- | --- | --- | --- | --- |
| role_requirements[].requirement_id | Stable identifier for one normalized requirement. | UUID | No | NormalizedRequirement | Requirement ID | Audit detail |
| role_requirements[].source_text | Original text excerpt from the job description. | String | No | NormalizedRequirement | Expected | Expected vs Observed table |
| role_requirements[].normalized_name | Normalized requirement label. | String | No | NormalizedRequirement | Requirement | Expected vs Observed table |
| role_requirements[].priority | mandatory, preferred, nice_to_have, or optional. | Enum string | No | NormalizedRequirement | Priority | Expected vs Observed table |
| role_requirements[].capability_mappings | Mapped capability dimensions; empty means mapping is unresolved. | CapabilityKey[] | No; may be empty | NormalizedRequirement | Capability mapping | Requirement details |
| role_requirements[].technology_mentions | Technologies explicitly mentioned in the job-description text. | String[] | No; may be empty | NormalizedRequirement | Technologies | Requirement details |
| role_requirements[].mention_frequency | Number of mentions in the job description. | Integer count | No | NormalizedRequirement | Mentions | Audit/detail only |
| role_requirements[].semantic_specificity | Parser specificity value in [0, 1]. | Decimal score | No | NormalizedRequirement | Not a proficiency target | Audit mode only |
| role_requirements[].mapping_confidence | Confidence in mapping the text to capabilities. | Decimal [0, 1] | No | NormalizedRequirement | Mapping confidence | Audit mode only |
| role_fit.requirement_matches[].status | Relationship between requirement and evidence: observed, related, unknown, unresolved. | Enum string | No | RequirementEvidenceMatch | Evidence state | Expected vs Observed table |
| role_fit.requirement_matches[].evidence_ids | Evidence records attached to the match. | UUID[] | No; may be empty | RequirementEvidenceMatch | Evidence links | Evidence drawer |
| role_fit.requirement_matches[].matching_technologies | Matched technology strings. | String[] | No; may be empty | RequirementEvidenceMatch | Observed technologies | Requirement details |
| role_fit.requirement_matches[].explanation | Deterministic explanation for the match. | String | No | RequirementEvidenceMatch | Evidence note | Requirement details |
| role_fit.mandatory_total / mandatory_observed / mandatory_related / mandatory_unknown / mandatory_unresolved | Counts of mandatory requirements by fit state. | Integer counts | No | RoleFitSummary | Mandatory requirements | KPI and filters |
| role_fit.preferred_total / preferred_observed / preferred_related / preferred_unknown / preferred_unresolved | Counts of preferred requirements by fit state. | Integer counts | No | RoleFitSummary | Preferred requirements | KPI and filters |
| role_fit.critical_gaps | Requirements flagged for follow-up. | String[] | No; may be empty | RoleFitSummary | Unresolved priorities | Summary / interview plan |

The live role-fit status values differ from the separate RequirementStatus enum (satisfied, partially_satisfied, contradicted, unknown). The current live match status is authoritative for this screen.

## Summary and capability metrics

| Field | Meaning | Type / unit | Nullable | Source | User-facing name | Screen |
| --- | --- | --- | --- | --- | --- | --- |
| dossier_id | Identifier for the returned dossier snapshot. | UUID | No | Dossier | Dossier ID | Audit/export |
| analysis_run_id | Identifier associated with this analysis response. | UUID | No | Dossier | Run ID | Report header/export; not a durable retrieval key in live_app |
| generated_at | Dossier generation time. | ISO datetime, UTC | No | Dossier | Generated | Report header |
| rci | Role Capability Index over observed capabilities only. | Score [0, 100] | Yes; null when no usable observed score exists | Dossier | Observed capability index | Summary with a plain-language boundary |
| coverage | Role-weighted evidence coverage. | Fraction [0, 1] | No | Dossier | Evidence coverage | KPI; display as percentage ×100 |
| is_insufficient_evidence | Whether evidence is below the scoring threshold for broad assessment. | Boolean | No | Dossier | Evidence sufficiency note | Summary |
| analysis_confidence.evidence_strength | Deterministic evidence-support band: insufficient, limited, moderate, well_supported. | Enum string | No, with a default in the contract | AnalysisConfidenceSummary | Evidence strength | Summary |
| analysis_confidence.explanation | Reason for the band. | String | No | AnalysisConfidenceSummary | Why this evidence level | Summary |
| analysis_confidence.uncertainty_flags | Stable reasons limiting interpretation. | String[] | No; may be empty | AnalysisConfidenceSummary | Evidence limitations | Summary/audit |
| analysis_confidence.role_coverage | Role-weighted coverage summary. | Fraction [0, 1] | No | AnalysisConfidenceSummary | Evidence coverage | Use once; reconcile with dossier.coverage before showing both |
| analysis_confidence.observed_capabilities | Count of observed capability estimates. | Integer count, up to 12 | No | AnalysisConfidenceSummary | Capabilities observed | KPI |
| analysis_confidence.independent_clusters | Count of usable evidence clusters. | Integer count | No | AnalysisConfidenceSummary | Independent evidence clusters | KPI |
| analysis_confidence.capabilities_with_intervals | Count of observed capabilities with both interval bounds. | Integer count | No | AnalysisConfidenceSummary | Capabilities with intervals | Audit detail |
| analysis_confidence.interval_coverage | Observed role weight with interval coverage. | Fraction [0, 1] | No | AnalysisConfidenceSummary | Interval coverage | Audit mode |
| analysis_confidence.maximum_interval_width | Widest available capability interval. | Score points [0, 100] | Yes | AnalysisConfidenceSummary | Widest interval | Audit mode |
| analysis_confidence.meaningful_conflicts | Count of capabilities with meaningful conflict. | Integer count | No | AnalysisConfidenceSummary | Open evidence conflicts | KPI |
| analysis_confidence.mandatory_unknown / mandatory_unresolved | Counts of mandatory role requirements with those states. | Integer counts | No | AnalysisConfidenceSummary | Mandatory gaps | KPI |
| analysis_confidence.source_failures / source_unscanned | Source receipt counts that failed or were not selected/scanned. | Integer counts | No | AnalysisConfidenceSummary | Source failures / unscanned | Source-health summary |
| analysis_confidence.unusable_evidence_records | Evidence records retained for provenance but excluded from scoring. | Integer count | No | AnalysisConfidenceSummary | Unusable observations | Audit mode |
| capability_estimates[key].estimate | Evidence-derived capability estimate. | Score [0, 100] | Yes; null is unknown | CapabilityEstimate | Observed score | Capability matrix |
| capability_estimates[key].is_observed | Whether an estimate is supported by usable evidence. | Boolean | No | CapabilityEstimate | Observed / Unknown | Capability matrix |
| capability_estimates[key].effective_evidence_count | Correlation-adjusted effective sample count. | Decimal count | No | CapabilityEstimate | Effective evidence count | Audit mode |
| capability_estimates[key].raw_evidence_count | Number of raw evidence records. | Integer count | No | CapabilityEstimate | Evidence records | Capability matrix |
| capability_estimates[key].cluster_count | Number of distinct evidence clusters for this capability. | Integer count | No in Python contract; optional in current TypeScript type | CapabilityEstimate | Independent clusters | Capability matrix |
| capability_estimates[key].standard_error / dispersion | Score-estimation diagnostics. | Score points / variance-like diagnostic | No | CapabilityEstimate | Standard error / dispersion | Audit mode |
| capability_estimates[key].ci_lower / ci_upper | Bootstrap 95% interval bounds when estimable. | Score [0, 100] | Yes; null means unavailable | CapabilityEstimate | 95% interval | Audit mode |
| capability_estimates[key].coverage_k | Evidence coverage for this capability. | Fraction [0, 1] | No | CapabilityEstimate | Capability coverage | Capability matrix; display percentage ×100 |
| capability_conflicts[key].positive_support_sum / negative_support_sum | Weighted positive and negative support totals. | Weighted sums | No | CapabilityConflict | Positive / negative evidence | Audit mode |
| capability_conflicts[key].contradiction_diagnostic | Signed conflict diagnostic D_k. | Decimal [-1, 1] | No | CapabilityConflict | Conflict diagnostic | Audit mode |
| capability_conflicts[key].has_meaningful_conflict | Whether conflict crosses the backend threshold. | Boolean | No | CapabilityConflict | Conflict state | Capability matrix |
| role_weights | Normalized importance assigned to each capability for this role. | Map<CapabilityKey, fraction>; totals sum to 1 | Optional on older TS payloads | Dossier | Role weight | Audit mode |

Null estimates and interval bounds must render as “Unknown” and “Unavailable,” never as zero. The current capability table prints “Unknown” but also draws an empty zero-width bar; that visual should be removed or explicitly styled as unavailable.

## Claims, skills, projects, experience, academics, and credentials

| Field | Meaning | Type / unit | Nullable | Source | User-facing name | Screen |
| --- | --- | --- | --- | --- | --- | --- |
| claims_corroboration[].claim_id / claim_text | Candidate claim and identifier. | UUID / String | No in current TS shape; validate runtime payload | Dossier claim corroboration | Claim | Claims vs Evidence matrix |
| claims_corroboration[].target_capability | Capability linked to the claim. | CapabilityKey | No in current TS shape | Dossier claim corroboration | Capability | Claims matrix |
| claims_corroboration[].status | corroborated, partial, unknown, or contradicted. | Enum string | No in current TS shape | ClaimStatus | Evidence state | Claims matrix |
| claims_corroboration[].confidence | Corroboration confidence, not candidate ability probability. | Decimal [0, 1] | No in current TS shape | ClaimCorroboration | Corroboration confidence | Audit/detail |
| claims_corroboration[].grounding_evidence_ids / citation_urls | Evidence and source references associated with the claim. | UUID[] / URL[] | No; may be empty | ClaimCorroboration | Supporting evidence / sources | Evidence drawer |
| analysis.skills[].skill / learning | Declared skill and learning flag. | String / Boolean | No | Live report | Claimed skill / Currently learning | Skills matrix |
| analysis.skills[].status | repository_support, repository_only, public_mention_only, or not_observed. | String status | No | Live report | Claim/evidence state | Skills matrix |
| analysis.skills[].evidence_count / evidence | Matching repository technology observations and detail. | Integer count / object[] | No; may be empty | Live report | Matches / Evidence | Skills matrix and drawer |
| analysis.coverage.supplied_sources / observed_sources | Counts over the live report's source receipts. | Integer counts | No | Live report | Source receipt counts | Source summary; use the same unit note as SourceHealth |
| analysis.coverage.skills_declared / skills_with_repository_matches | Number of declared skills and number with repository technology matches. | Integer counts | No | Live report | Skills with repository matches | Skills summary |
| analysis.coverage.credential_claims | Number of resume credential claims. | Integer count | No | Live report | Credential claims | Credential summary |
| analysis.method | Deterministic extraction/acquisition/matching method description. | String | No | Live report | Method | Methodology |
| analysis.projects[].title / description | Resume project claim. | String | No in current response | Live report | Claimed project | Project view |
| analysis.projects[].source_urls | Source URLs matched to the project text. | URL[] | No; may be empty | Live report | Linked sources | Project view |
| analysis.projects[].status | linked_sources or declaration_only. | String status | No | Live report | Project evidence state | Project view |
| analysis.experience[].claim, analysis.education[].claim, analysis.achievements[].claim | Resume-derived text. | String | No | Live report | Resume claim | Relevant section |
| experience/education/achievement status | Current live report labels these entries self_reported. | String status | No | Live report | Self-reported | Section-level note |
| analysis.credentials[].claim | Credential text from resume. | String | No | Live report | Claimed credential | Credential view |
| analysis.credentials[].status | Current values include unverified and possible_public_match. | String status | No | Live report | Credential evidence state | Credential view |
| matching_pages[].candidate_name_present / matched_terms | Text overlap details for a public page. | Boolean / String[] | No; may be empty | Live report | Name appears / Matched terms | Audit detail |
| quantified_claims_to_verify | Resume lines matching numeric-claim patterns. | String[] | No; may be empty | Live report | Quantified claims to verify | Claims section |
| next_steps | Deterministic follow-up suggestions. | String[] | No; may be empty | Live report | Interview checks | Interview plan |

The live model does not expose dedicated issuer-authenticated credential states, academic verification records, employment verification records, or an observed benchmark reproduction contract. Public text matching must not be promoted to verification.

## Sources, repositories, and evidence

| Field | Meaning | Type / unit | Nullable | Source | User-facing name | Screen |
| --- | --- | --- | --- | --- | --- | --- |
| sources[] / url | URL represented by one acquisition receipt. | URL | No | Live result | Source | Source explorer |
| kind | Classifier/acquisition kind (for example GitHub profile or credential). | String | Yes | SourceReceipt | Source type | Source explorer |
| status | Exact acquisition outcome. | String; endpoint vocabulary is broader than SourceState | No | SourceReceipt | Source state | Source explorer |
| detail | Human-readable acquisition result or limitation. | String | No | SourceReceipt | Result / limitation | Source explorer |
| fetched_at | Acquisition timestamp where provided. | ISO datetime | Yes | SourceReceipt | Fetched | Source explorer/audit |
| http_status | HTTP status for public web acquisition. | Integer | Yes | SourceReceipt | HTTP | Audit mode |
| final_url / redirects | Redirect destination and visited chain when present. | URL / URL[] | Yes | SourceReceipt | Redirects | Audit mode |
| content_sha256 | Retrieved page hash. | SHA-256 | Yes | SourceReceipt | Content hash | Audit mode |
| verification | Page-level verification label; currently not_verified for public-link reads. | String | Yes | SourceReceipt | Verification state | Audit mode |
| title / description / excerpt / acquisition_method | Retrieved public-page text metadata and acquisition strategy. | String | Yes | SourceReceipt | Page details / acquisition method | Source inspector |
| commit_sha | Repository revision used for inspection. | Git SHA | Yes | SourceReceipt | Commit | Repository/source inspector |
| files_inspected / files_omitted / evidence_count | Counts for a repository receipt. These are separate measures. | Integer counts | Yes | SourceReceipt | Files inspected / omitted / observations | Repository inspector |
| ownership_score | Heuristic repository attribution input. | Decimal [0, 1] | Yes | SourceReceipt | Attribution estimate | Attribution detail |
| inventory[] | Profile-expanded repository metadata, including language, stars, fork/archive flags, last push, and inspection status. | Object[] | Yes | SourceReceipt | Repository inventory | Repository explorer |
| repository_review.description / stars / forks / open_issues / is_fork / archived / license / topics / pushed_at | Repository metadata. Stars/forks are context only, not engineering evidence. | String / integer counts / Boolean / date / String[] | Some fields nullable | RepositoryReview | Repository context | Repository inspector |
| languages_by_inspected_file / file_categories | Counts in selected inspected files. | Map<string, integer count> | Yes | RepositoryReview | Languages / file categories | Repository inspector |
| dependencies / technologies / engineering_signals | Static observations from inspected repository files. | Object[] | Yes | RepositoryReview | Dependencies / technical signals | Repository inspector |
| readme_excerpt | Bounded README excerpt. | String | Yes | RepositoryReview | README excerpt | Repository inspector |
| repository_review.limitations | Per-repository scan limitations. | String[] | Yes | RepositoryReview | Inspection limits | Repository inspector |
| source_health.supplied_sources / observed_sources / failed_sources / not_selected_sources / not_scanned_sources / blocked_sources | Counts over returned receipt records. The supplied_sources name is not strictly user-entered-only: discovered receipts may also be included. | Integer counts | No when summary exists | SourceHealth | Sources by acquisition state | Source summary |
| source_health.is_partial / flags | Whether acquisition is incomplete and why. | Boolean / String[] | No when summary exists | SourceHealth | Partial source coverage | Summary/source explorer |
| evidence_records[].evidence_id / fingerprint | Evidence record identity and normalized fingerprint. | UUID / SHA-256 | No | EvidenceRecord | Evidence ID / fingerprint | Evidence drawer/audit |
| source_family / source_locator / immutable_revision | Evidence origin and immutable revision (for example repository URL and commit). | Enum / URL-or-path / revision string | No | EvidenceRecord | Source / location / revision | Evidence drawer |
| target_capability / support_score / is_positive_support | Mapped capability, support rating, and direction. | CapabilityKey / score [0, 100] / Boolean | No | EvidenceRecord | Capability / support / direction | Evidence drawer |
| confidence / confidence_factors | Composite evidence confidence and six factor values: artifact integrity, ownership, recency, verification, depth, source reliability. | Decimal [0, 1] per value | No | EvidenceRecord | Evidence confidence / factors | Audit mode |
| cluster_id | Correlation group identifier. | String | Yes | EvidenceRecord | Evidence cluster | Evidence drawer |
| provenance | File path, line/symbol, artifact data, snippet, and inspection metadata where available. | Object | No; keys may be absent | EvidenceRecord | Artifact provenance | Evidence drawer |
| extractor_version / created_at | Analyzer version and record timestamp. | String / ISO datetime | No | EvidenceRecord | Analyzer / observed | Audit mode |

Do not present a raw source receipt as a verified credential, a repository as proof of exact line authorship, or a profile popularity metric as skill evidence. The backend itself documents these boundaries.

## Interview, versions, graph, and exports

| Field | Meaning | Type / unit | Nullable | Source | User-facing name | Screen |
| --- | --- | --- | --- | --- | --- | --- |
| interview_probes[].rank / priority_score | Ordering and computed inquiry priority. | Integer / backend score | No | ProbePriority | Interview priority | Interview plan; explain as question order, not candidate ranking |
| interview_questions[].question_text / rationale / verification_guidance | Generated deterministic interview question and evidence/gap rationale. | String | No | InterviewQuestion | Interview question / why / what to check | Interview plan |
| grounding_evidence_ids / suggested_followups | Evidence links and follow-up prompts. | UUID[] / String[] | No; may be empty | InterviewQuestion | Related evidence / follow-ups | Evidence drawer |
| ownership_assessments[].ownership_score / attribution_confidence | Repository-level heuristic attribution signals. | Decimal [0, 1] | No | OwnershipAssessment | Attribution signal | Attribution detail |
| is_fork / is_vendor_or_generated / limitations | Repository caveats. | Boolean / Boolean / String[] | No | OwnershipAssessment | Attribution limitations | Repository inspector |
| versions | Version key/value data returned by the dossier. | Map<string, string> | No; may be empty | Dossier | Analysis versions | Audit mode |
| system_limitations | Method and scope limitations. | String[] | No | Dossier | Method limits | Methodology/audit |
| graph.nodes / graph.edges | Candidate, source, artifact, evidence, capability, requirement, run, and dossier-item connections. | Arrays of typed nodes/edges | No; may be empty | Candidate Evidence Graph response | Provenance graph | Optional evidence visualization |
| graph_snapshot | Serialized graph snapshot included in live response. | JSON object | No in current live service | Live response | Raw graph export | Audit/export |
| status | Live result status, currently completed or partial. | String | No | Live result | Analysis status | Report header |
| scoring_config | Scoring parameters returned by live analysis. | Structured object | No | Live response | Scoring configuration | Audit mode |

The public live workflow has no started_at, completed_at, stage list, actual per-stage progress, or server-measured elapsed duration in its result contract. The separate local pipeline API has stage/status responses, but it is synchronous and in-memory today. Do not show a durable progress timeline until that lifecycle is implemented.

The frontend JSON download contains the entire live response. The full local dossier API separately supports HTML, Markdown, and JSON export, but that route is not part of the public live_app deployment.

## Persisted-only schemas and SaaS fields

The SQLAlchemy schema includes Organization, User, Candidate, CandidateDocument, CandidateSource, Project, JobDescription, RoleRequirement, AnalysisRun, AnalysisStageRun, SourceSnapshot, Repository, RepositoryContributor, Artifact, Evidence, Claim, ownership/scoring/uncertainty/conflict/probe records, dossier snapshots/items, audit events, corrections, and deletion events.

These are not equivalent to fields currently available from the public live response. In particular:

- Organization and User schemas do not provide login, session state, membership administration, or authenticated tenant filtering in the frontend.
- AnalysisRun and AnalysisStageRun are schema entities, but the active live workflow is request-only and the pipeline service uses in-process state.
- Projects are represented in the current live report as resume-derived claims with matched source URLs, not as a persisted project dossier with deployment/test/security counts.
- No dedicated academic or credential ORM entities were found.
- Billing, plan, retention, and integration state are not current live-response fields.

## Metric use rules

| Candidate UI metric | Source and safe transformation | Current availability |
| --- | --- | --- |
| Evidence coverage | dossier.coverage × 100; whole percentage is appropriate. | Available per live result. |
| Role requirements with evidence | Count role_fit.requirement_matches in an explicitly chosen state. Keep unknown and unresolved separate. | Available when JD parsing produced matches. |
| Claims corroborated | Count claims_corroboration by backend ClaimStatus. Do not fold partial/unknown into corroborated. | Contract exists; response needs a fixture-backed integration check before display. |
| Capabilities observed | analysis_confidence.observed_capabilities or count observed estimates; choose one source and reconcile. | Available in current live response. |
| Independent evidence clusters | analysis_confidence.independent_clusters. | Available in current live response. |
| Sources observed / failures / unscanned | Use source_health counts and name their unit as receipt records. | Available in current live response. |
| Repositories analyzed | Count repository receipts after defining whether partial and failed repositories count as analyzed. | Derivable from receipts; no explicit total field. |
| Files inspected | Sum repository receipt files_inspected only after handling missing values and defining duplicate/retry semantics. Do not relabel as artifacts. | Per-repository fields only. |
| Artifacts inspected | No global field with this meaning in the current live response. | Unavailable as a top-level metric. |
| Analysis duration | No backend duration on the live result. Do not use a client stopwatch as if it were server analysis time. | Unavailable. |
| Credential verification | Use the exact public-match/unverified state and explain the text-match limitation. | Limited live fields; no issuer verification. |

No displayed number should be added to a dashboard until its response field, unit, null handling, transformation, and screen are recorded here and later carried to docs/audits/frontend-metric-lineage.md.
