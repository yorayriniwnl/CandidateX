# Fix 5: Evidence Family Correlation Design

**Status:** Design approved in conversation; implementation plan in progress
**Scope:** CandidateX backend hardening, Fix 5 from the supplied sequential hardening brief

## Understanding and success criteria

The goal is to stop repeated or correlated analyzer observations from manufacturing evidence while retaining every observation and its provenance. The same underlying technical fact may be detected by different analyzers or expressed with different text. Such observations should share a deterministic identity and have diminishing influence on capability estimates, coverage, effective evidence counts, and uncertainty.

Success means:

- equivalent semantic facts receive the same stable family ID within the same source cluster;
- unrelated facts do not get grouped merely because their text matches;
- observation type remains visible so corroborating modalities can be distinguished;
- repeated detections stay available in the evidence trail, while their score contribution is bounded;
- persisted live evidence and synthetic research use the same family-weighting rule;
- old stored records remain readable and are not accidentally merged during migration.

## Current code context

`EvidenceInput` is the raw observation contract emitted by static analyzers. It currently carries source, artifact path, capability, support, polarity, and extractor metadata, but no correlation identity or observation type.

`EvidenceRecord` and the database `Evidence` row already have `cluster_id` and `artifact_id`. Live acquisition associates each analyzer observation with the indexed artifact and source repository, computes a fingerprint, and stores the raw support text in provenance. It currently deduplicates exact fingerprints and caps observations per artifact/capability, but does not model semantic correlation between different observations.

Capability scoring currently uses every positive-confidence record in the weighted estimate, effective count, dispersion, and coverage. Bootstrap confidence intervals resample source clusters. `EvidenceCapabilityLink.effective_weight` exists and is currently persisted as 1.0.

## Identity model

Add `evidence_family_id` and `observation_type` to `EvidenceInput` and `EvidenceRecord`. When live acquisition promotes an input to a record, it fills `cluster_id` from the normalized source identity and `artifact_id` from the indexed artifact foreign key. These existing fields retain their current database types and relationships.

Analyzer code will use one shared, versioned identity builder. Its canonical input is:

- normalized source-family and cluster scope;
- target capability;
- a semantic fact domain, such as `dependency`, `route`, or `database_schema`;
- a domain-normalized subject identifying the fact.

The builder returns `ef1:` followed by a SHA-256 digest of canonical serialization. It does not include the extractor version, observation type, source revision, raw support text, or support polarity. Excluding observation type allows different modalities for the same fact to share a family. Excluding polarity keeps contradictory observations linked to the same fact so both remain visible and can contribute with diminishing weight. Excluding revision keeps an unchanged fact's identity stable across analyses.

Examples:

- A manifest declaration and an import of the same normalized package in one repository use the same `dependency` subject and therefore share a family ID, while their observation types differ.
- A route observation uses a normalized method, route path, and source construct as its subject.
- Parser detections of the same construct call the same family builder with the same subject, even if their support text differs.
- An analyzer without a semantic subject uses a single-observation fallback family based on source cluster, artifact path, capability, observation type, and stable evidence fingerprint. It may collapse only exact repeated emissions from the same observation identity; it never infers cross-type semantic equivalence or uses raw-string similarity alone.

The family basis (domain, normalized subject, and identity schema version) will be retained in provenance for auditability. Observation types are stable, namespaced strings rather than a closed enum so analyzer families can evolve without a schema migration.

## Contribution rule

Add `evidence_family_decay` to `ScoringConfig`, defaulting to `0.5` and validated in `[0, 1)`. Bump the scoring configuration version to `5.0.0`.

For the records of one capability:

1. Group records by `evidence_family_id`.
2. Within each family, choose the strongest deterministic representative for each `(observation_type, support_polarity)` pair. Rank by confidence, then by fingerprint and evidence ID as deterministic tie-breakers. Other records remain in the evidence list and persistence layer but receive zero family contribution.
3. Rank the representatives in that family by confidence, with observation type, polarity, fingerprint, and evidence ID as deterministic tie-breakers.
4. Assign family multipliers `1, delta, delta^2, ...`, where `delta` is `evidence_family_decay`.

This keeps conflicting positive and negative observations represented, while repeated parser detections of the same type and polarity cannot add repeated weight. Distinct observation types can corroborate the fact, but each additional modality contributes less.

Multiply raw confidence by the family multiplier before calculating the capability point estimate, effective evidence count, dispersion, and cluster-aware coverage. Use the same adjusted confidence in bootstrap estimates, contradiction diagnostics, and claim-corroboration confidence sums. Keep all raw evidence IDs in conflict and claim provenance, including observations whose family multiplier is zero. Keep `raw_evidence_count` as the count of relevant raw observations before family weighting so provenance volume is not hidden.

Persist the per-record multiplier in `EvidenceCapabilityLink.effective_weight` so the evidence trail can show the contribution applied for that analysis. The weight is derived from the full evidence set and active scoring config; it is not a replacement for raw confidence.

## Persistence and compatibility

Add database columns for `evidence_family_id` and `observation_type`, and persist `evidence_family_decay` on `ScoringConfigEntity`. `cluster_id` and `artifact_id` already exist and retain their current database types and relationships.

The migration will backfill existing rows with a unique legacy family derived from each row's persisted evidence UUID and set the observation type to `legacy_unknown`. The legacy ID uses the `ef0:` prefix and a SHA-256 digest of that UUID. This preserves historical records without claiming semantic grouping that their stored provenance cannot establish. New live observations must use the shared family builder or the conservative fallback before persistence. Fresh databases and databases already at migration revision 0002 must both upgrade successfully; fresh schemas must not receive duplicate columns from the dynamic initial migration.

Evidence API responses and dossier graph nodes will expose family ID, observation type, cluster ID, and artifact ID. Provenance continues to include every stored observation and raw support snippet.

## Research and simulation

Synthetic scenarios and the ablation runner will assign deterministic family IDs and observation types. The research scoring path will use the same family multiplier helper as live scoring. Regenerate the committed benchmark artifacts under scoring config 5.0.0, and describe the result as a separate synthetic prototype experiment rather than empirical calibration.

## Acceptance tests

- Manifest declaration and import/use of one dependency share a family ID but retain distinct observation types.
- Repeated calls to the identity builder produce the same ID; changing semantic subject, capability, or source cluster changes it. Different text with the same semantic subject shares a family, while identical text with different subjects remains separate.
- Route observations for the same method/path/source construct correlate; different constructs remain separate.
- Duplicate detections with the same family, type, and polarity retain all rows but only the strongest has a nonzero family multiplier.
- Distinct observation types in one family receive the configured geometric weights.
- Contradictory positive and negative observations remain represented and contribute under the documented rule.
- Repeated correlated observations do not inflate capability estimates, coverage, effective evidence count, bootstrap intervals, contradiction diagnostics, or claim-corroboration confidence.
- Independent source clusters do not share a family ID by default. The separate Fix 4 content-hash deduplication continues to prevent byte-identical copied artifacts from being counted as independent coverage.
- Persistence, API serialization, legacy migration, synthetic scoring, and generated research artifacts agree on family IDs and contribution weights.

## Non-goals

- Fuzzy text matching, embeddings, or probabilistic semantic clustering.
- Deleting observations from the evidence trail.
- Claiming that synthetic results establish real-world hiring accuracy.
- Reworking artifact attribution or source-cluster coverage from Fixes 1-4.
