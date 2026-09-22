# Evidence Strength and Backend Resilience Design

## Status

Design approved in conversation on 2026-09-22. The implementation must remain
additive, deterministic, and conservative: it may make uncertainty more
visible, but it must not manufacture a probability of candidate ability.

## Goal

Strengthen CandidateX's backend and live analysis workflow so that a numerical
RCI cannot be mistaken for strong evidence when the result is based on thin,
correlated, unattributed, contradictory, or incomplete observations. At the
same time, make the live API more predictable under maximum-size inputs and
unexpected internal failures.

## User outcome

After an analysis, an interviewer should be able to answer:

1. Is there usable empirical evidence at all?
2. How broad is the evidence across the target role?
3. Is it supported by independent project/source clusters or only one sample?
4. Are confidence intervals estimable, and how wide are they?
5. Which missing, failed, unresolved, or contradictory inputs limit the result?
6. Can the backend failure or partial-result state be traced without exposing
   internal stack traces or silently substituting a sample result?

The result remains human decision support. The system must not present an
evidence band as a hiring recommendation, a validated probability, or proof of
identity, authorship, skill mastery, employment, or credential authenticity.

## Existing context and identified gaps

The current system already preserves unknown capability, separates RCI from
coverage, shrinks small ownership samples, discounts correlated live signals,
and returns cluster-bootstrap intervals when at least two clusters exist. The
remaining gaps are:

- A high RCI is still a standalone numeric value. The dossier has no additive
  summary that makes a single-cluster or low-coverage result visibly limited.
- The frontend labels any positive estimate as “Evidence found” even when its
  interval is unavailable or its role coverage is low.
- Live analysis accepts up to 100 external URLs but the route body limit is
  smaller than the declared worst-case JSON payload.
- The live route normalizes known runtime failures but does not consistently
  convert unexpected exceptions into a safe, request-traceable response.
- Pipeline status responses can expose the internal traceback retained by the
  execution state.
- Source receipt health and analysis evidence strength are not presented as a
  single, typed explanation.

## Non-goals

- Replacing the existing RCI, Evidence Coverage, six-factor evidence
  confidence, ownership, or cluster-bootstrap mathematics.
- Adding an LLM, a learned calibration model, or external hiring-outcome
  labels.
- Treating public page text, resume declarations, or credential matches as
  technical capability evidence.
- Expanding identity discovery, repository scope, network destinations, or
  candidate-code execution.
- Adding persistence, authentication, or a new public candidate lookup API.

## Design

### 1. Additive analysis-confidence contract

Add `AnalysisConfidenceSummary` to the shared domain contracts and add an
`analysis_confidence` field to `Dossier` with a default empty/insufficient
value so existing dossier payloads remain valid. The summary is an evidence
quality statement, not a probability.

The contract will contain:

- `evidence_strength`: `insufficient`, `limited`, `moderate`, or
  `well_supported`;
- `explanation`: a short deterministic explanation of the selected band;
- `uncertainty_flags`: stable machine-readable reasons;
- `role_coverage`: the existing role-weighted coverage value;
- `observed_capabilities`: count of observed capabilities;
- `independent_clusters`: count of usable evidence clusters;
- `capabilities_with_intervals`: count of observed capabilities with both
  interval bounds;
- `interval_coverage`: role-weighted fraction of observed capability weight
  with estimable intervals;
- `maximum_interval_width`: widest available interval, or `None`;
- `meaningful_conflicts`: count of capabilities with meaningful positive and
  negative support;
- `mandatory_unknown` and `mandatory_unresolved` counts from role fit;
- `source_failures` and `source_unscanned` counts, defaulting to zero for
  non-live pipeline runs;
- `unusable_evidence_records`: records retained for provenance but excluded
  from capability scoring because their composite confidence is zero.

The summary is built by a new uncertainty-summary helper over the existing
capability estimates, evidence records, role weights, conflicts, and role-fit
summary. It must be recomputed during functional rescoring because role
weights and role-weighted interval coverage can change.

An unusable record is material when it targets a capability with positive role
weight and either (a) that capability has no usable positive-confidence
records, or (b) unusable records are at least as numerous as its usable
records. Unusable records from unrelated, zero-weight capabilities remain
visible in provenance but do not lower the overall band.

### 2. Conservative band rules

The presentation gates are versioned constants in the uncertainty-summary
module, not statistical claims:

- `insufficient` when there is no observed capability or role coverage is
  below the existing low-coverage threshold of `0.35`;
- `limited` when coverage is below `0.60`, fewer than two independent usable
  clusters exist, role-weighted interval coverage is incomplete, a mandatory
  requirement is unknown or unresolved, a source failed or was not scanned,
  or unusable/unattributed records are material to the result;
- `moderate` when the limited gates are cleared but coverage is below `0.80`,
  fewer than three clusters exist, intervals are wide, or meaningful evidence
  conflict remains;
- `well_supported` only when coverage is at least `0.80`, at least three
  independent clusters exist, at least `0.80` of observed role weight has an
  interval, the widest available interval is no wider than `25` points, and
  there are no mandatory gaps, meaningful conflicts, source failures, or
  material unusable records.

The band must never be elevated by RCI alone. An observed estimate with no
interval remains usable for inspection but carries an
`interval_unavailable` flag. A single repository can therefore produce an
RCI while remaining `limited`.

The summary will use stable flags such as:

`no_empirical_evidence`, `low_role_coverage`, `single_cluster`,
`interval_unavailable`, `wide_intervals`, `mandatory_unknown`,
`mandatory_unresolved`, `source_failures`, `source_unscanned`,
`meaningful_conflict`, and `unusable_evidence`.

The explanation and UI copy must state that “well supported” means supported
by the supplied artifacts under bounded static inspection; it is not proof of
ability or a hiring recommendation.

### 3. Live source-health summary

Add a deterministic `source_health` object to the live `analysis` report. It
will count supplied, observed, failed, not-selected, and not-scanned receipts,
and include stable flags for failed, blocked, or omitted acquisition.

For the summary, a receipt is failed when its status is neither `observed`,
`not_selected`, nor `not_scanned`; it is unscanned when its status is
`not_selected` or `not_scanned`. The exact status and URL remain available in
the receipt list.

The live service will recompute `dossier.analysis_confidence` after acquisition
using these counts, then rebuild the graph from the updated dossier. This keeps
the core pipeline independent of live transport details while ensuring a
partial source run cannot appear fully supported merely because another source
returned evidence.

Existing per-source receipts remain authoritative for exact URLs, statuses,
limits, redirects, and omission details. `source_health` is a summary only.

### 4. Backend request and failure hardening

For `/api/v1/live/analyze`:

- Define an explicit bounded body constant large enough for the declared
  maximum `github_urls`, `external_urls`, JD text, intake preview, and JSON
  overhead, while retaining a finite limit.
- Reject an over-limit `Content-Length` before reading the stream and retain
  streaming enforcement for clients without a reliable header.
- Generate a request ID for each intake/analyze request and return it in an
  `X-Request-ID` response header. Log unexpected exceptions with that ID but
  return a generic error message without internal details.
- Keep validation errors at 422, size errors at 413, unsupported documents at
  415, and analysis failures at 500. No failed request may return a previous,
  synthetic, or partial dossier as a successful result.

For pipeline status responses, retain diagnostic tracebacks only in internal
execution state and expose a safe failure message plus the failed stage. A
successful response must continue to expose the existing status, RCI, and
coverage fields unchanged.

No backend hardening change may loosen URL validation, SSRF checks, archive
containment, repository bounds, or candidate-code execution prohibitions.

### 5. Frontend disclosure

Extend the TypeScript dossier/result contracts with the additive summary and
source-health fields. On the live result page:

- place an “Evidence strength” panel before the capability table;
- show the evidence band, one-line explanation, and uncertainty flags in
  plain language;
- label a capability with an unavailable interval or low coverage as
  “Limited evidence”/“Needs verification” rather than only “Evidence found”;
- preserve the expandable interval, observation-count, provenance, and role-fit
  details;
- show source-health counts and a link/affordance to the existing source
  receipts when acquisition was partial;
- keep all copy explicit that the result supports interview questions and is not
  a hiring decision.

If an older response lacks `analysis_confidence`, the UI will fall back to the
existing coverage/interval presentation rather than fabricate a band. New
backend responses will always include the field.

## Data flow

```text
static observations + source receipts
        │
        ├── existing six-factor confidence / RCI / coverage / intervals
        │
        └── uncertainty summary
                │
                ├── dossier.analysis_confidence
                ├── live analysis.source_health
                └── frontend evidence-strength panel
```

Functional rescoring reuses the same evidence, recalculates role-weighted
metrics and the summary, and does not reacquire sources or rerun analyzers.

## Error handling and invariants

- Missing evidence remains `UNKNOWN`; it is never converted to a zero
  capability estimate or a negative claim.
- A numeric RCI may coexist with `insufficient` or `limited` evidence strength;
  the response must make that limitation visible.
- Confidence intervals are never synthesized when there are fewer than two
  independent clusters.
- Source failures, blocked URLs, omitted files, and uncredited evidence remain
  visible in receipts or uncertainty flags.
- Internal tracebacks are never returned in public API error fields.
- Failed live requests clear/replace no prior result on the client and never
  substitute synthetic data.
- Existing response fields and endpoint paths remain backward compatible; new
  fields are additive.

## Testing strategy

### Backend unit and contract tests

- No evidence yields `insufficient` plus `no_empirical_evidence`.
- One high-scoring cluster with no interval remains `limited` despite a high
  RCI.
- Two or more clusters with intervals improve summary metrics but do not reach
  `well_supported` until all gates pass.
- Low coverage, wide intervals, meaningful conflict, mandatory gaps, source
  failures, and unusable records each produce the expected flags and cap the
  band.
- Summary values remain bounded and deterministic for repeated inputs.
- Capability estimates and dossier serialization retain old fields and accept
  old manually constructed dossiers through defaults.

### Pipeline and live integration tests

- Functional rescore recomputes the summary while retaining evidence and does
  not trigger acquisition.
- Live responses include `dossier.analysis_confidence`,
  `analysis.analysis_confidence`, and `analysis.source_health`.
- A one-commit/single-repository result is explicitly limited.
- A provider failure or blocked source remains visible and adds source-health
  uncertainty without manufacturing RCI.
- Maximum declared URL payloads fit within the bounded request body, while an
  over-limit stream returns 413.
- Unexpected analysis exceptions return a generic 500 with `X-Request-ID` and
  no traceback; successful and validation responses retain their current
  status behavior.
- Pipeline failure responses do not expose `state.error` tracebacks.

### Frontend acceptance tests

- A mocked thin result shows the evidence-strength panel, limited band, and
  uncertainty flag.
- A result with a source failure shows partial source health.
- Existing upload, unknown-result, role-fit, source-receipt, export, failure
  clearing, and mobile overflow tests continue to pass.

## Verification gate

Before declaring the work complete:

1. Run the focused backend confidence and live API tests.
2. Run the complete backend test suite.
3. Run the web TypeScript check and focused Playwright live-analysis tests.
4. Run the complete web test suite and production build.
5. Inspect the final diff for accidental changes to acquisition bounds,
   identity discovery, persistence, or candidate-code execution behavior.

The final report must distinguish green local verification from any
environment-dependent gate that could not run.
