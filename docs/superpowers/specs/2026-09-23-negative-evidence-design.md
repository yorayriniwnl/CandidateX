# CandidateX Fix 12: Qualified Negative Evidence

**Status:** Conversational design approved on 2026-09-23; spec pending user review.

## Purpose

Build a production path for contradiction candidates that can be audited from a specific claim, an immutable observation, and the scan scope that produced it. Missing artifacts, incomplete scans, failed fetches, and ambiguous comparisons remain unknown. The system must not infer that absence is contradiction unless the claim defines an observable expectation and the relevant source was completely inspected.

This design covers Fix 12 only. The separate canonical claim entity planned for Fix 13 remains out of scope; Fix 12 uses a stable reference to the existing claim text so the later claim-model work can replace that bridge.

## Current behavior and constraints

- `EvidenceInput` and `EvidenceRecord` have `is_positive_support`, but no typed expected/actual observations or scan-completeness context. Production analyzers currently emit only positive support.
- `compute_contradiction_diagnostic` and claim corroboration count any record with `is_positive_support=False` as negative evidence.
- The documented capability estimate `q_k` aggregates evidence across both support polarities. Evidence-family decay separates representatives by support polarity. Fix 12 preserves those equations for qualified records.
- Live repository analysis has the pinned workspace, artifact index, and archive/tree inventory during acquisition. Claim corroboration runs later, after the workspace is closed.
- Repository selection is bounded by file, byte, and time limits. The existing receipt reports only an aggregate omitted-file count, and the acquisition path excludes the `coverage` directory. That receipt cannot justify a closed-world absence claim.
- Evidence persistence already stores provenance as JSON. The negative-evidence context can be added there without a relational schema migration.

## Architecture

Add a dedicated contradiction-candidate module under `cci/contradictions`. It owns strict parsing of supported observable claim expectations and source-specific evaluators. The evaluators run while the pinned repository snapshot is available, using the existing live acquisition boundary. They return no candidate when an expectation cannot be parsed, source facts are missing, or the comparison is not like-for-like.

Introduce a transient `ObservableClaimExpectation` for Fix 12, not a replacement canonical claim entity. It contains the original claim text, stable reference, candidate type, target capability, normalized comparison fields when applicable, and an optional explicit repository scope. `live.service.analyze_resume` builds these expectations before acquisition and passes the same values to repository evaluators and pipeline claim corroboration. Map coverage claims to `TESTING_QUALITY`; map framework claims only through the existing controlled technology-to-capability ontology; map deployment claims to `DEVOPS_CLOUD`; and map performance claims only when an explicit technology/workload context resolves through that ontology. Unmapped claims do not create capability-level negative records. Claim parsing is deterministic and versioned: no LLM, fuzzy paraphrase, or inferred scope fallback is used. The supported claim grammars are specified under Candidate rules below.

Derive `claim_reference` deterministically from a versioned prefix plus the Unicode NFKC-normalized, trimmed, whitespace-collapsed, case-folded claim text, target capability, candidate type, and canonical repository scope when one is required, encoded as UTF-8 and SHA-256 hashed. Repository scope is the normalized owner/name identity, without branch or commit; the commit SHA remains in evidence provenance. The same helper is used by acquisition and claim corroboration. Corroboration accepts a negative record only for that exact reference. Capability-level contradiction diagnostics continue to use qualified negative records by capability.

The acquisition flow is:

1. Parse only deterministic, supported expectations from declared claim text; retain the original text, target-capability mapping, explicit repository scope, and stable reference.
2. Fetch and pin the repository snapshot; enumerate selected and omitted artifacts by category and reason.
3. Run positive analyzers and contradiction-candidate evaluators over the same snapshot.
4. Convert every emitted observation into the existing immutable `EvidenceRecord`, retaining source URL, commit SHA, artifact hash/path, rule ID/version, and existing evidence confidence.
5. Persist contradiction details in provenance JSON and expose them in the evidence record response.
6. Use qualified negatives in contradiction diagnostics and exact-claim corroboration. Preserve the documented `q_k` and uncertainty formulas for qualified observations of either polarity.

## Negative-evidence contract

Add a typed `NegativeEvidenceDetails` model with these required fields:

- `claim_reference`: stable hash of the versioned normalized claim text, target capability, candidate type, and canonical repository scope when required.
- `candidate_type`: one of the versioned candidate rule types below.
- `expected_observation`: the explicit, claim-derived condition being checked.
- `actual_observation`: the report-stated measurement or completely scanned result, with its source and limits.
- `scan_scope`: the precise artifact or repository category scope used for the comparison.
- `required_scan_completeness` and `observed_scan_completeness`: fractions in `[0, 1]`.
- `explanation`: concise reason the actual observation contradicts the expected observation, including relevant measured values and scan limitations.

The final `EvidenceRecord.confidence` remains the required confidence field. It is computed through the existing evidence-confidence factors and describes the evidence record under the current model; it is not a calibrated probability that the artifact is truthful or that a claim is false. `technical_signal_strength` remains the separate, rule-defined heuristic observation value; it must not be copied from a claim threshold or described as proficiency. New candidate rules receive stable rule IDs and catalog entries with documented strengths and limits. Version `1.0.0` assigns fixed signal strengths that do not vary with the claimed threshold or size of mismatch:

| Rule ID | Strength | Reason and limit |
|---|---:|---|
| `candidatex.contradiction.coverage_below_claim` | `70.0` | A pinned parsed report states a comparable value below the explicit expectation; the report's measurement is not independently reproduced. |
| `candidatex.contradiction.framework_usage_absent` | `55.0` | A complete static scan found no recognized usage in the defined source and manifest scope; unscanned or out-of-scope use is not ruled out. |
| `candidatex.contradiction.deployment_project_mismatch` | `85.0` | An authoritative verifier reports a project identity different from the explicit expected identity; this rule is dormant until such a verifier is available. |
| `candidatex.contradiction.performance_claim_mismatch` | `70.0` | A pinned parsed benchmark report states a comparable value violating the claim; the measurement is not independently reproduced. |

These values are uncalibrated policy heuristics. Changing a rule's strength or detection behavior requires a signal-rule version update and catalog review.

`EvidenceInput` rejects a new negative observation without `NegativeEvidenceDetails`. `EvidenceRecord` remains able to load historical negative records that predate this contract. A serialized `negative_evidence_qualification` value is `qualified` when details are present and `legacy_unqualified` when a historical negative has no details. Legacy records remain visible for provenance and contribute zero to capability aggregation, family weights, contradiction diagnostics, bootstrap uncertainty, and claim statuses; they do not receive a contradiction graph edge. Qualified negative records retain the existing polarity-aware scoring behavior.

Store the typed details in a dedicated serialized evidence field and mirror them in the existing provenance JSON for database round-trips. Existing rows without details load as `legacy_unqualified`; no database migration is required. Positive record serialization and fingerprints remain unchanged except where the existing fingerprint contract includes new candidate details for negative records. Synthetic research scenarios and tests that create negative records must supply explicit synthetic expectation/observation details and must label their evidence as synthetic.

## Scan-completeness contract

Inventory truncation, an unavailable archive/tree listing, or a Git tree response marked truncated sets completeness below `1.0` for all repository absence scans. Counts are recorded before applying the selected-file cap. A file with an eligible extension that cannot be decoded or parsed is skipped, not inspected. A scope with zero eligible files produces no absence candidate. The category receipt keeps eligible, inspected, and skipped counts plus every applicable skip reason; completeness is `inspected / eligible` and is `0.0` for an empty scope.

For report discovery, inspect every path in the fixed allowlists: Cobertura XML at `coverage.xml`, `cobertura.xml`, or `coverage/cobertura.xml`; LCOV at `lcov.info` or `coverage/lcov.info`; and benchmark JSON at `benchmarks/*.json` or `benchmark/*.json` (one directory level only). An omitted, unreadable, or malformed allowlisted report makes that report category incomplete, even if another report parsed successfully. More than one valid report for the claim's metric is ambiguous even when values agree. XML parsing disables external entities; JSON parsing rejects duplicate keys and non-finite numbers. All parsers enforce the existing artifact byte limit and acquisition deadline.

Replace the aggregate-only completeness signal with category-specific counts for eligible, inspected, and skipped artifacts, plus skipped reasons such as file cap, byte cap, timeout, parse failure, unsafe/symlink input, and unsupported format. Compute completeness against the complete archive or commit-tree inventory before selection truncation. Version the eligibility and exclusion rules as `candidatex.negative-scan-scope/1.0.0`: framework scans include all regular files with a registered source extension for the mapped language and all recognized dependency-manifest names; test source files are included. Exclude only path components already designated as generated or vendored by acquisition (`node_modules`, `vendor`, `dist`, `build`, `.git`, `.next`, `coverage`, `__pycache__`, `.venv`, and `venv`). A file matching an eligible extension or manifest name but skipped for any reason remains in the denominator and suppresses absence candidates. Unsupported extensions are outside this versioned scope and must not be counted as inspected. Empty eligible scope yields no candidate.

For artifact-backed numeric comparisons, the required and observed completeness for the exact artifact must both be `1.0`: the report was read, parsed, and tied to the pinned revision. This verifies the tracked report content and its provenance, not the truth of the report's measurement. For framework-usage absence, the claim must be explicitly scoped to the selected repository and completeness must be `1.0` across every eligible first-party source and dependency-manifest artifact for that framework's registered language and file types. Any skipped eligible artifact or unrecognized usage-rule scope makes the result unknown. A total file count or the absence of emitted positive analyzer findings is never a substitute for this completeness vector.

## Candidate rules

All candidate rules preserve every observed record and use `is_positive_support=False` only for a qualified contradiction candidate. Rule IDs use version `1.0.0` initially and are added to the backend signal-rule catalog.

Coverage, framework-use, and performance expectations are repository-backed: each must resolve to exactly one selected repository from the same project claim before its artifacts are inspected. The evaluator never searches every selected repository and attributes a matching report to a claim by proximity. Missing or ambiguous repository scope leaves the claim unverified.

### Test coverage claims

The parser accepts only an explicit percentage with `at least`, `no less than`, `>=`, or `>` and the word `coverage`, `test coverage`, `line coverage`, or `branch coverage`. `>= X` is violated only below `X`; `> X` is violated at or below `X`. Percent is the only supported claim unit. Cobertura rates are fractions converted to percent; LCOV counts require a positive denominator and `0 <= hit <= total`. A report with both valid line and branch metrics is ambiguous for a generic coverage claim.

The v1 claim grammar accepts a percentage and explicit lower-bound comparator (`at least`, `no less than`, `>=`, or `>`), followed by `coverage` or `test coverage`, with optional `line` or `branch` qualifier. A missing comparator, unsupported unit, or multiple possible thresholds is unparsed and remains unverified. Supported reports are Cobertura XML (`line-rate` and `branch-rate`) and LCOV (`LH`/`LF` for lines; `BRH`/`BRF` for branches). Counts require a positive total and `0 <= hit <= total`; Cobertura rates must be finite and in `[0,1]`. Compare only matching metrics. A generic coverage claim may use a report only when it exposes exactly one valid metric. A metric-specific claim requires that metric. Emit a candidate only when the value stated by the parsed report violates the comparator and the exact report was parsed completely. A report meeting the threshold is not negative evidence. No report, malformed output, ambiguous multiple reports, conflicting values, or an incomplete artifact read yields no candidate and leaves the claim unverified. CI configuration by itself cannot contradict a coverage claim.

### Framework-use claims

The repository scope must resolve from the same project claim to a unique selected repository using the canonical owner/name identity. Framework usage rules are explicit, versioned token-to-language/extension and token-to-manifest mappings; a dependency name alone is not treated as source usage. The scope includes all registered first-party source files, including tests, and supported manifests. Any cap, timeout, unsupported parser for an eligible file, unsafe path, or incomplete inventory leaves the candidate unknown.

Dependency declarations remain weak positive observations and never establish mastery. The v1 claim grammar requires an explicit usage phrase (`use`, `using`, `used`, or `built with`), one exact registered framework token, and a unique repository scope from the same project claim (the selected repository URL or its owner/name slug must resolve to exactly one selected repository). Do not infer the repository from a nearby resume link or from the only available repository. Emit an absence-based candidate only when the framework token is recognized by a versioned usage rule and every eligible first-party source and manifest file in that repository was inspected. The actual observation reports the registered language/extensions, manifest names, excluded directory rules, and eligible/inspected/skipped counts. Generic claims of framework mastery, claims not tied to a uniquely selected repository, unsupported framework tokens, or any incomplete or empty scan remain unknown.

### Deployment claims

The expected project identity uses the same normalized exact identifier format as the authoritative provider's actual identity. `scan_scope` records the selected deployment URL and verifier identity; required and observed completeness are both `1.0` only when the provider returns a successful structured identity observation. Failed, denied, missing, stale, or unverified provider results produce no negative record.

The v1 claim grammar requires an explicit project identity in a deployment claim and a uniquely associated selected deployment URL. An unreachable or access-restricted URL produces an `INACCESSIBLE`/unverified source status, never negative evidence. A deployment mismatch candidate requires both that explicit expected identity and an authoritative verified observation of the deployed project identity. Generic HTTP reachability, page title/text, and a single failed request cannot establish a mismatch. The current generic public-link inspector does not provide authoritative project identity, so it cannot emit deployment negatives; the evaluator accepts only a separately verified structured identity observation and stays dormant until a provider supplies it.

### Performance claims

The supported claim form is `<metric-id> <comparator> <number> <unit> technology=<registered-token>` with optional `statistic=<token>`, `workload=<token>`, and `environment=<token>` fields; for example, `latency <= 100 ms technology=FastAPI statistic=p95 workload=checkout environment=prod`. Metric IDs and context tokens use NFKC, trimming, whitespace collapse, and case-folding before exact comparison; the metric ID grammar is `[a-z][a-z0-9_.-]*`. Report observations require all six fields (`metric`, `value`, `unit`, `statistic`, `workload`, `environment`). If statistic/workload/environment is absent from the claim, the metric must have exactly one observation in the parsed report. Time conversion is limited to `ms` and `s` for the same metric; all other units must match exactly. The required technology field must resolve through the existing capability ontology or the expectation is not emitted.

Recognize only an explicit numeric claim with one comparator (`at least`, `no less than`, `>=`, `>`, `at most`, `no more than`, `<=`, `<`, `under`, or `below`), metric, threshold, and unit. Parse only JSON reports matching `{ "schema_version": "1.0.0", "observations": [...] }`; each observation must contain non-empty `metric`, finite non-negative numeric `value`, `unit`, `statistic`, `workload`, and `environment`. A claim's metric is the exact normalized metric identifier, not a guessed synonym. Only time units `ms` and `s` are converted, within the same time metric; all other units must match exactly. A claim that omits statistic, workload, or environment can match only one benchmark observation for that metric; a claim that names any of those fields must match it exactly after trimming whitespace. Multiple possible observations, missing context, conflicting values, or a unit mismatch yields no candidate. Comparator violations use ordinary numeric ordering (for example, `>= X` is violated only below `X`; `<= X` only above `X`). Emit a candidate only when the value stated by the parsed report violates the claim comparator. Missing or malformed benchmark data remains unverified. No benchmark artifact is not contradiction.

## Compatibility and downstream behavior

- Positive evidence behavior, the documented `q_k` formula, and `D_k = (P_k - N_k)/(P_k + N_k + epsilon)` remain unchanged for qualified evidence. The family multiplier continues to separate qualified records by support polarity; `q_k` consumes the resulting confidence-weighted signal strengths for both polarities, and `D_k` separately computes positive and negative support.
- `compute_record_family_weights` assigns no contribution to `legacy_unqualified` negatives; qualified positive and negative records remain separate family representatives.
- `compute_contradiction_diagnostic` and `corroborate_candidate_claims` ignore unqualified negatives. Claim corroboration matches qualified negatives by stable `claim_reference`, not merely by capability or a coincidental keyword.
- The dossier graph must not render an unqualified historical negative as a contradiction edge. Evidence API/export output retains its qualification and details.
- An empty evidence match must not claim that the entire repository or deployment was scanned. Its explanation states only that no qualifying evidence was observed in the available scope.
- No frontend changes, new relational columns, or candidate-code execution are introduced.

## Failure and security behavior

Candidate repository code, tests, and benchmarks are never executed. Parsers operate on bounded, commit-pinned artifact bytes under the existing file and time limits. `actual_observation` states what the tracked report says or what a complete static scan found; it does not claim independent reproduction of test coverage or runtime performance. Unsafe paths, archive truncation, unreadable content, unsupported formats, missing units, mismatched metrics, conflicting reports, and deadline failures produce no negative candidate. The acquisition receipt records why completeness fell below the required value.

## Acceptance evidence

Fix 12 is accepted only when tests and review establish all of the following:

1. Every newly emitted negative `EvidenceInput` has all required typed contradiction details; the resulting `EvidenceRecord` retains immutable source provenance and the existing confidence value.
2. Coverage and benchmark mismatches produce qualified negative evidence only when a pinned parsed report states a value that violates an explicit, comparable numeric expectation and controlled capability mapping; matching values, absent reports, malformed data, ambiguous metrics, or conflicting reports do not.
3. Framework-use absence produces a candidate only for a repository-scoped claim with complete eligible-source and manifest scans; file, byte, category, and time omissions suppress the candidate.
4. Unreachable deployments never produce negative evidence; a mismatch is possible only from a verified expected/actual project-identity pair.
5. Qualified negatives affect contradiction totals, claim status, graph provenance, and the existing capability estimator according to the documented polarity-aware evidence contract. Legacy unqualified negatives affect none of those calculations.
6. Evidence persistence/API round-trips preserve contradiction details and qualification without a schema migration.
7. Tests cover record validation, confidence/provenance, exact claim matching, family decay by polarity, archive and git-blob completeness, and all unknown/inaccessible cases.
8. The existing backend test suite, static checks, adversarial review, and independent acceptance review pass without frontend or database-schema changes.
