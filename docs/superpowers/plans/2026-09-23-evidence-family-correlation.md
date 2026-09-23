# Evidence Family Correlation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prevent correlated CandidateX observations from manufacturing evidence while preserving each observation and its provenance.

**Architecture:** A shared domain identity builder will create deterministic, source-scoped semantic family IDs; analyzer-specific observation types will let related modalities share a family. One scoring helper will assign deterministic family multipliers, and live scoring, confidence intervals, contradiction diagnostics, claim corroboration, persistence, and synthetic research will use that same result.

**Tech Stack:** Python 3.12, Pydantic, SQLAlchemy, Alembic, FastAPI, NumPy/SciPy, pytest.

**Spec:** [2026-09-23-evidence-family-correlation-design.md](../specs/2026-09-23-evidence-family-correlation-design.md)

## Global Constraints

- This is a backend-scoped fix: change backend code, research artifacts, and backend-facing documentation; do not edit React components.
- The builder returns `ef1:` followed by a SHA-256 digest of canonical serialization.
- `evidence_family_decay` defaults to `0.5` and is validated in `[0, 1)`; scoring configuration version is `5.0.0`.
- Preserve every raw observation and its provenance; observations with zero family contribution remain visible.
- Do not use fuzzy text matching, embeddings, or raw-string similarity to infer semantic equivalence.
- Keep `cluster_id` and `artifact_id` as the existing source-cluster identity and indexed-artifact foreign key.
- Backfill historical rows with `ef0:` plus a SHA-256 digest of the persisted evidence UUID and `observation_type = legacy_unknown`.

## Review Focus

- **Same fact, different wording or modality:** a manifest declaration and package import share an ID but keep distinct observation types; test in Task 2.
- **Same text, different facts:** identical support text with different semantic subjects yields different IDs; test in Task 1.
- **Repeated analyzer emissions:** same family/type/polarity rows all persist with unique record IDs, but only the strongest contributes; test in Task 5.
- **Contradictory observations:** positive and negative records in one family remain present and both enter diagnostics with the specified diminishing weights; test in Task 4.
- **Legacy and incomplete identity:** revision-0002 database rows backfill to independent `ef0:` IDs, while records without explicit family identity use the documented single-observation fallback; test in Tasks 1 and 5.

## File Map

- `services/backend/src/cci/domain/evidence_families.py`: shared source-cluster normalization, semantic family IDs, and conservative single-observation fallback identity.
- `services/backend/src/cci/domain/contracts.py`: family identity, observation type, and scoring-config contract fields.
- `services/backend/src/cci/analyzers/code/dependencies.py`, `services/backend/src/cci/analyzers/code/python_analyzer.py`, and `services/backend/src/cci/analyzers/code/multi_language.py`: emit dependency and route family metadata.
- `services/backend/src/cci/scoring/evidence_families.py`: deterministic family representative selection and multiplier calculation.
- `services/backend/src/cci/live/acquisition.py`: attach family metadata and retain every analyzer observation with stable distinct record IDs.
- `services/backend/src/cci/db/models/evidence.py`, `services/backend/src/cci/db/models/scoring.py`, and `services/backend/alembic/versions/0003_evidence_family_correlation.py`: persist identity, observation type, and decay configuration.
- `services/backend/src/cci/api/contracts/evidence.py`, `services/backend/src/cci/graph/builder.py`, and `services/backend/src/cci/api/contracts/graph.py`: expose family, observation, cluster, and artifact metadata through the backend response contracts.
- `services/backend/src/cci/research/` and `research/run_paper_experiments.py`: synthetic family identities and the same contribution rule in published prototype artifacts.

---

### Task 1: Canonical Family Identity and Evidence Contracts

**Files:**
- Create: `services/backend/src/cci/domain/evidence_families.py`
- Modify: `services/backend/src/cci/domain/contracts.py`
- Modify: `services/backend/src/cci/scoring/capability.py`
- Test: `services/backend/tests/unit/scoring/test_evidence_family_identity.py`
- Test: `services/backend/tests/unit/test_contracts.py`

**Interfaces:**
- `normalize_source_cluster(source_family: SourceFamily, identity: str) -> str` returns the same canonical cluster key currently used by coverage.
- `normalize_family_subject(fact_domain: str, subject: str) -> str` applies domain-specific normalization; dependency package names are case-insensitive and route path case is preserved.
- `EvidenceFamilyIdentity` contains `evidence_family_id: str` and `basis: dict[str, str]`.
- `build_evidence_family_identity(*, source_family: SourceFamily, cluster_id: str, capability: CapabilityKey, fact_domain: str, subject: str) -> EvidenceFamilyIdentity` builds explicit semantic identity.
- `build_fallback_evidence_family_identity(*, source_family: SourceFamily, cluster_id: str, artifact_path: str | None, capability: CapabilityKey, observation_type: str, fingerprint: str) -> EvidenceFamilyIdentity` scopes unknown analyzer output to one stable observation identity.
- `EvidenceInput` and `EvidenceRecord` gain `evidence_family_id: str | None`, `observation_type: str` defaulting to `legacy_unknown` and limited to 100 characters, plus `evidence_family_basis: dict[str, str]` kept in provenance.

- [ ] **Step 1: Write failing identity tests**

```python
def test_family_id_is_stable_and_semantic_not_text_based():
    first = build_evidence_family_identity(source_family=SourceFamily.GITHUB, cluster_id="https://github.com/acme/api", capability=CapabilityKey.BACKEND_ENGINEERING, fact_domain="dependency", subject="FastAPI")
    same_fact = build_evidence_family_identity(source_family=SourceFamily.GITHUB, cluster_id="https://github.com/acme/api/", capability=CapabilityKey.BACKEND_ENGINEERING, fact_domain="dependency", subject="fastapi")
    other_fact = build_evidence_family_identity(source_family=SourceFamily.GITHUB, cluster_id="https://github.com/acme/api", capability=CapabilityKey.BACKEND_ENGINEERING, fact_domain="dependency", subject="starlette")
    assert first.evidence_family_id == same_fact.evidence_family_id
    assert first.evidence_family_id != other_fact.evidence_family_id
    assert first.evidence_family_id.startswith("ef1:")
```

- [ ] **Step 2: Run the focused tests and confirm they fail**

Run from `services/backend`: `python -m pytest tests/unit/scoring/test_evidence_family_identity.py tests/unit/test_contracts.py -q`

Expected: FAIL because the identity module and contract fields do not exist.

- [ ] **Step 3: Implement the shared versioned identity builder**

```python
canonical = {
    "schema": "ef1",
    "source_family": source_family.value,
    "cluster": normalize_source_cluster(source_family, cluster_id),
    "capability": capability.value,
    "domain": fact_domain.strip().casefold(),
    "subject": normalize_family_subject(fact_domain, subject),
}
serialized = json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode("utf-8")
family_id = "ef1:" + hashlib.sha256(serialized).hexdigest()
```

Move the current source-family/cluster URL normalization used by Fix 4 into `normalize_source_cluster`; coverage passes `cluster_id or source_locator`, so coverage and semantic families use the same source boundary. Normalize package names case-insensitively, HTTP methods to uppercase, and route paths without lowercasing path segments. Build fallback identity from source cluster, artifact path, capability, observation type, and fingerprint; never use support text as a fallback key.

Add builder tests for same-text/different-subject separation, same-fact/different-wording equality, source-family and capability separation, stable fallback IDs, and distinct fallback IDs for different artifact paths or fingerprints.

- [ ] **Step 4: Add backward-compatible contract fields and run focused tests**

Run: `python -m pytest tests/unit/scoring/test_evidence_family_identity.py tests/unit/test_contracts.py -q`

Expected: PASS for deterministic IDs, normalization, distinct semantic subjects, source/capability separation, conservative fallback IDs, and defaults on existing EvidenceRecord constructors.

- [ ] **Step 5: Commit the identity contract**

```bash
git add services/backend/src/cci/domain/evidence_families.py services/backend/src/cci/domain/contracts.py services/backend/src/cci/scoring/capability.py services/backend/tests/unit/scoring/test_evidence_family_identity.py services/backend/tests/unit/test_contracts.py
git commit -m "feat(evidence): add deterministic family identities"
```

### Task 2: Emit Semantic Families from Dependency and Route Analyzers

**Files:**
- Modify: `services/backend/src/cci/analyzers/code/dependencies.py`
- Modify: `services/backend/src/cci/analyzers/code/python_analyzer.py`
- Modify: `services/backend/src/cci/analyzers/code/multi_language.py`
- Test: `services/backend/tests/golden/code_intel/test_code_analyzers.py`
- Test: `services/backend/tests/unit/analyzers/code/test_evidence_families.py`

**Interfaces:**
- Manifest and source-use observations call `build_evidence_family_identity` with `fact_domain="dependency"` and the same normalized package subject.
- Route observations use `fact_domain="route"` and a subject containing normalized method, path, and the handler/source construct.
- Observation types are stable namespaced values such as `dependency:manifest`, `dependency:python_import`, `route:python_decorator`, and `route:typescript_registration`.

- [ ] **Step 1: Write failing analyzer tests**

```python
manifest = dependencies_to_evidence(parse_requirements_txt("fastapi==0.115"), repo, path, revision)[0]
imported = analyze_python_source("import fastapi", "src/app.py", repo, revision)[0]
assert manifest.evidence_family_id == imported.evidence_family_id
assert manifest.observation_type != imported.observation_type
```

Add a route test asserting that Python and TypeScript observations for the same normalized method/path/source construct produce the same family ID, and that different route paths remain separate.

- [ ] **Step 2: Run analyzer tests and confirm they fail**

Run from `services/backend`: `python -m pytest tests/unit/analyzers/code/test_evidence_families.py tests/golden/code_intel/test_code_analyzers.py -q`

Expected: FAIL because package imports and semantic family metadata are not currently emitted.

- [ ] **Step 3: Emit explicit semantic keys at the analyzer boundary**

Add Python AST `Import` and `ImportFrom` observations for dependencies already recognized by `DEPENDENCY_CAPABILITY_MAP`. Reuse the manifest package normalizer and conservative support score of `55.0`. Attach explicit family ID, basis, and observation type to dependency and route EvidenceInput records. Keep unknown analyzers on the single-observation fallback; do not derive semantic families by comparing support text.

```python
identity = build_evidence_family_identity(
    source_family=SourceFamily.GITHUB,
    cluster_id="https://github.com/acme/api",
    capability=CapabilityKey.BACKEND_ENGINEERING,
    fact_domain="route",
    subject="GET|/health|health_handler",
)
route_observation = EvidenceInput(
    source_family=SourceFamily.GITHUB,
    source_locator="https://github.com/acme/api",
    immutable_revision="a" * 40,
    artifact_path="src/app.py",
    target_capability=CapabilityKey.BACKEND_ENGINEERING,
    observed_score=80.0,
    raw_support_text="@app.get('/health')",
    extractor_version="python_ast_v1",
    evidence_family_id=identity.evidence_family_id,
    observation_type="route:python_decorator",
    evidence_family_basis=identity.basis,
)
```

- [ ] **Step 4: Run analyzer tests and confirm they pass**

Run: `python -m pytest tests/unit/analyzers/code/test_evidence_families.py tests/golden/code_intel/test_code_analyzers.py -q`

Expected: PASS for manifest/import correlation, route correlation, different-subject separation, and unchanged analyzer provenance.

- [ ] **Step 5: Commit semantic analyzer IDs**

```bash
git add services/backend/src/cci/analyzers/code/dependencies.py services/backend/src/cci/analyzers/code/python_analyzer.py services/backend/src/cci/analyzers/code/multi_language.py services/backend/tests/golden/code_intel/test_code_analyzers.py services/backend/tests/unit/analyzers/code/test_evidence_families.py
git commit -m "feat(analyzers): identify correlated dependency and route facts"
```

### Task 3: Family Multiplier and Scoring Configuration

**Files:**
- Create: `services/backend/src/cci/scoring/evidence_families.py`
- Modify: `services/backend/src/cci/domain/contracts.py`
- Modify: `services/backend/src/cci/api/contracts/analyses.py`
- Test: `services/backend/tests/unit/scoring/test_evidence_family_weights.py`
- Test: `services/backend/tests/unit/test_contracts.py`

**Interfaces:**
- `EvidenceFamilyWeightInput` is an immutable value with `evidence_id: UUID`, `evidence_family_id: str`, `observation_type: str`, `is_positive_support: bool`, `confidence: float`, and `fingerprint: str`.
- `family_weight_input_from_record(record: EvidenceRecord) -> EvidenceFamilyWeightInput` resolves the explicit family ID or the conservative single-observation fallback; fallback uses `record.cluster_id or record.source_locator`, `provenance["artifact_path"]`, capability, observation type, and fingerprint.
- `compute_evidence_family_weights(items: Sequence[EvidenceFamilyWeightInput], decay: float) -> dict[UUID, float]` returns a multiplier for every retained evidence ID.
- Group by family; choose the strongest item per `(observation_type, is_positive_support)`; rank representatives by confidence, observation type, polarity, fingerprint, and evidence ID; assign `decay ** rank`.

- [ ] **Step 1: Write failing multiplier tests**

```python
weights = compute_evidence_family_weights([manifest, duplicate_manifest, import_use], decay=0.5)
assert weights[manifest.evidence_id] == 1.0
assert weights[duplicate_manifest.evidence_id] == 0.0
assert weights[import_use.evidence_id] == 0.5
```

Also test deterministic ties, positive/negative representatives, decay `0.0`, and that the same fingerprint in separate explicit semantic families is not merged.

Define a test-local `_weight_input(name, observation_type, polarity, confidence)` factory returning the exact input contract with one fixed family ID, deterministic UUIDv5 evidence IDs, and deterministic fingerprints. Construct `manifest`, `duplicate_manifest`, and `import_use` with `dependency:manifest` and `dependency:python_import` observation types.

- [ ] **Step 2: Run the weight tests and confirm they fail**

Run from `services/backend`: `python -m pytest tests/unit/scoring/test_evidence_family_weights.py -q`

Expected: FAIL because the family-weighting helper does not exist.

- [ ] **Step 3: Implement family representative weighting and config**

Add `evidence_family_decay: float = Field(default=0.5, ge=0.0, lt=1.0)` to ScoringConfig, bump the default scoring version, Dossier version metadata, and request version to `5.0.0`, and implement the weight map with deterministic sorting. Keep zero-weight records in the returned map.

```python
from collections import defaultdict
from collections.abc import Sequence
from uuid import UUID


def compute_evidence_family_weights(
    items: Sequence[EvidenceFamilyWeightInput],
    decay: float,
) -> dict[UUID, float]:
    if not 0.0 <= decay < 1.0:
        raise ValueError("decay must be in [0, 1)")

    grouped: dict[str, list[EvidenceFamilyWeightInput]] = defaultdict(list)
    weights = {item.evidence_id: 0.0 for item in items}
    for item in items:
        grouped[item.evidence_family_id].append(item)

    for family_items in grouped.values():
        strongest: dict[tuple[str, bool], EvidenceFamilyWeightInput] = {}
        for item in family_items:
            key = (item.observation_type, item.is_positive_support)
            current = strongest.get(key)
            item_rank = (item.confidence, item.fingerprint, str(item.evidence_id))
            current_rank = (
                (current.confidence, current.fingerprint, str(current.evidence_id))
                if current is not None
                else None
            )
            if current_rank is None or item_rank > current_rank:
                strongest[key] = item

        representatives = sorted(
            strongest.values(),
            key=lambda item: (
                -item.confidence,
                item.observation_type,
                item.is_positive_support,
                item.fingerprint,
                str(item.evidence_id),
            ),
        )
        for rank, item in enumerate(representatives):
            weights[item.evidence_id] = decay**rank

    return weights
```

The helper accepts only normalized `EvidenceFamilyWeightInput` values. Live scoring converts each record with `family_weight_input_from_record`; synthetic research constructs the same type using deterministic simulated observation IDs.

- [ ] **Step 4: Run weight and config tests**

Run: `python -m pytest tests/unit/scoring/test_evidence_family_weights.py tests/unit/test_contracts.py -q`

Expected: PASS, including rejection of decay `1.0` and exact multiplier values.

- [ ] **Step 5: Commit family weighting primitive**

```bash
git add services/backend/src/cci/scoring/evidence_families.py services/backend/src/cci/domain/contracts.py services/backend/src/cci/api/contracts/analyses.py services/backend/tests/unit/scoring/test_evidence_family_weights.py services/backend/tests/unit/test_contracts.py
git commit -m "feat(scoring): add diminishing family weights"
```

### Task 4: Apply Family Weights to Scoring and Evidence Aggregates

**Files:**
- Modify: `services/backend/src/cci/scoring/capability.py`
- Modify: `services/backend/src/cci/uncertainty/bootstrap.py`
- Modify: `services/backend/src/cci/contradictions/diagnostic.py`
- Modify: `services/backend/src/cci/claims/corroborator.py`
- Modify: `services/backend/src/cci/pipeline/orchestrator.py`
- Test: `services/backend/tests/unit/scoring/test_math_core.py`
- Test: `services/backend/tests/unit/scoring/test_cluster_aware_coverage.py`
- Test: `services/backend/tests/unit/claims/test_corroborator.py`

**Interfaces:**
- All aggregate functions consume the same `compute_evidence_family_weights` map derived from the active ScoringConfig.
- Capability confidence is `record.confidence * family_multiplier`; raw count remains the number of relevant records before family weighting.

- [ ] **Step 1: Add failing regressions for correlated score, coverage, CI, contradiction, and claim confidence**

Assert that repeating one same-type family observation does not change the estimate, coverage, effective count, bootstrap interval, contradiction sums, or claim status; assert that a second distinct observation type contributes at the configured decay.

```python
base = compute_capability_score([manifest], CAPABILITY, cfg)
repeated = compute_capability_score([manifest, duplicate_manifest], CAPABILITY, cfg)
assert repeated.estimate == base.estimate
assert repeated.coverage_k == base.coverage_k
assert repeated.effective_evidence_count == base.effective_evidence_count
```

Extend the existing `_record` and `_create_mock_evidence` test factories with family ID and observation type arguments. Also assert raw evidence count grows for the repeated observation while provenance still includes both IDs; seed bootstrap sampling so equal weighted inputs produce repeatable intervals.

- [ ] **Step 2: Run affected tests and confirm the regressions fail**

Run from `services/backend`: `python -m pytest tests/unit/scoring/test_math_core.py tests/unit/scoring/test_cluster_aware_coverage.py tests/unit/claims/test_corroborator.py -q`

Expected: FAIL because these paths still sum raw confidence.

- [ ] **Step 3: Use weighted confidence consistently**

```python
weight_inputs = [family_weight_input_from_record(record) for record in relevant]
family_weights = compute_evidence_family_weights(
    weight_inputs,
    cfg.evidence_family_decay,
)
effective_confidences = [
    record.confidence * family_weights[record.evidence_id] for record in relevant
]
```

Use these values for point estimates, Kish effective count, dispersion, coverage item quality, bootstrap base/sample estimates, contradiction sums, and claim confidence. Pass adjusted confidence into coverage item construction instead of letting `evidence_coverage_item` read raw confidence. Keep every EvidenceRecord ID in conflict and claim provenance, including zero-weight records; `raw_evidence_count` remains the number of relevant observations before weighting.

- [ ] **Step 4: Run focused score and aggregate tests**

Run: `python -m pytest tests/unit/scoring/test_math_core.py tests/unit/scoring/test_cluster_aware_coverage.py tests/unit/claims/test_corroborator.py -q`

Expected: PASS for correlated repeats, distinct modalities, contradictory polarity, unchanged provenance IDs, and confidence intervals.

- [ ] **Step 5: Commit aggregate integration**

```bash
git add services/backend/src/cci/scoring/capability.py services/backend/src/cci/uncertainty/bootstrap.py services/backend/src/cci/contradictions/diagnostic.py services/backend/src/cci/claims/corroborator.py services/backend/src/cci/pipeline/orchestrator.py services/backend/tests/unit/scoring/test_math_core.py services/backend/tests/unit/scoring/test_cluster_aware_coverage.py services/backend/tests/unit/claims/test_corroborator.py
git commit -m "fix(scoring): discount correlated evidence across aggregates"
```

### Task 5: Preserve Live Observations and Persist Family Metadata

**Files:**
- Modify: `services/backend/src/cci/live/acquisition.py`
- Modify: `services/backend/src/cci/db/models/evidence.py`
- Modify: `services/backend/src/cci/db/models/scoring.py`
- Modify: `services/backend/src/cci/db/repository.py`
- Create: `services/backend/alembic/versions/0003_evidence_family_correlation.py`
- Modify: `services/backend/src/cci/api/contracts/evidence.py`
- Modify: `services/backend/src/cci/api/contracts/graph.py`
- Modify: `services/backend/src/cci/graph/builder.py`
- Modify: `services/backend/src/cci/pipeline/orchestrator.py`
- Test: `services/backend/tests/integration/test_db_migration.py`
- Test: `services/backend/tests/integration/test_db_seeding.py`
- Test: `services/backend/tests/unit/test_live_evidence_families.py`
- Test: `services/backend/tests/unit/dossier/test_dossier_builder.py`
- Test: `services/backend/tests/unit/graph/test_ceg.py`
- Test: `services/backend/tests/unit/test_contracts.py`

**Interfaces:**
- Live conversion fills `cluster_id` from normalized repository identity and `artifact_id` from the indexed artifact.
- Every `EvidenceInput` becomes a persisted `EvidenceRecord`; duplicate content fingerprints may match, but deterministic occurrence IDs keep database primary keys unique.
- `evidence_ids_for_fingerprints(analysis_run_id: UUID, fingerprints: Sequence[str]) -> list[UUID]` returns one deterministic UUID per ordered fingerprint occurrence; run ID is part of the UUIDv5 name so separate analyses cannot collide.
- `save_evidence_records(session: Session, analysis_run_id: UUID, evidence_records: list[EvidenceRecord], scoring_config: ScoringConfig) -> list[models.Evidence]` stores each family multiplier in `EvidenceCapabilityLink.effective_weight`.

- [ ] **Step 1: Write failing live-retention and migration tests**

Feed 200 inputs with repeated fingerprints through `evidence_ids_for_fingerprints` for one run and assert all IDs are unique and stable across repeated calls; assert another run gets disjoint IDs. Add a live conversion test asserting every input remains in the EvidenceRecord list with its raw support text and stable fingerprint. Create a revision-0002 database with duplicate legacy fingerprints and assert migration assigns different `ef0:` IDs by evidence UUID. Also assert EvidenceDetailResponse serialization and CEG evidence nodes expose family ID, observation type, cluster ID, and artifact ID.

- [ ] **Step 2: Run focused tests and confirm they fail**

Run from `services/backend`: `python -m pytest tests/unit/test_live_evidence_families.py tests/unit/dossier/test_dossier_builder.py tests/unit/graph/test_ceg.py tests/unit/test_contracts.py tests/integration/test_db_migration.py tests/integration/test_db_seeding.py -q`

Expected: FAIL because live acquisition currently drops repeats and the schema lacks family fields.

- [ ] **Step 3: Retain observations and persist their contribution metadata**

Remove exact-fingerprint, per-artifact/capability suppression, and the 180-observation truncation from live evidence conversion while retaining existing archive, file-count, expanded-size, and time budgets. Keep the content fingerprint stable and derive each evidence UUID as UUIDv5 over the analysis-run ID, fingerprint, and that fingerprint's deterministic occurrence ordinal. Persist family ID and observation type in columns, family basis in provenance, and the multiplier in the evidence-capability link. Pass the active ScoringConfig from the pipeline into repository persistence so stored multipliers match the analysis.

```python
from collections.abc import Sequence
from uuid import NAMESPACE_URL, UUID, uuid5


def evidence_ids_for_fingerprints(
    analysis_run_id: UUID,
    fingerprints: Sequence[str],
) -> list[UUID]:
    counts: dict[str, int] = {}
    evidence_ids: list[UUID] = []
    for fingerprint in fingerprints:
        occurrence = counts.get(fingerprint, 0)
        counts[fingerprint] = occurrence + 1
        evidence_ids.append(
            uuid5(NAMESPACE_URL, f"{analysis_run_id}:{fingerprint}:{occurrence}")
        )
    return evidence_ids
```

- [ ] **Step 4: Add a migration compatible with fresh schemas and revision-0002 databases**

Add `String(68)` `evidence_family_id` and `String(100)` `observation_type` to Evidence, and non-null Float `evidence_family_decay` with server default `0.5` to ScoringConfigEntity. For an old schema, add evidence columns nullable, backfill each row with `ef0:` plus SHA-256 of its persisted UUID and `legacy_unknown`, then enforce non-null (use Alembic batch alteration on SQLite). Fresh revision 0001 creates tables from current metadata, so inspect column existence and skip already-present columns. Add `save_scoring_config(session: Session, config: ScoringConfig) -> models.ScoringConfigEntity` to persist the active version and all current config fields, including family decay. Pass the active ScoringConfig through `save_dossier` to `save_evidence_records`, and calculate link multipliers from the complete per-capability evidence set before inserting rows.

```python
legacy_id = "ef0:" + hashlib.sha256(str(evidence_id).encode()).hexdigest()
```

- [ ] **Step 5: Run persistence and migration tests**

Run: `python -m pytest tests/unit/test_live_evidence_families.py tests/unit/dossier/test_dossier_builder.py tests/unit/graph/test_ceg.py tests/unit/test_contracts.py tests/integration/test_db_migration.py tests/integration/test_db_seeding.py -q`

Expected: PASS for 200 preserved observations, run-scoped unique record IDs, family-weight storage, scoring-config round trip, legacy backfill, fresh-schema upgrade without duplicate-column errors, and revision-0002 upgrade.

- [ ] **Step 6: Commit live and persistence changes**

```bash
git add services/backend/src/cci/live/acquisition.py services/backend/src/cci/db/models/evidence.py services/backend/src/cci/db/models/scoring.py services/backend/src/cci/db/repository.py services/backend/src/cci/pipeline/orchestrator.py services/backend/alembic/versions/0003_evidence_family_correlation.py services/backend/src/cci/api/contracts/evidence.py services/backend/src/cci/api/contracts/graph.py services/backend/src/cci/graph/builder.py services/backend/tests/integration/test_db_migration.py services/backend/tests/integration/test_db_seeding.py services/backend/tests/unit/test_live_evidence_families.py services/backend/tests/unit/dossier/test_dossier_builder.py services/backend/tests/unit/graph/test_ceg.py services/backend/tests/unit/test_contracts.py
git commit -m "feat(evidence): persist family identities and all observations"
```

### Task 6: Reuse Family Weighting in Synthetic Research and Backend Interfaces

**Files:**
- Modify: `services/backend/src/cci/research/scenarios.py`
- Modify: `services/backend/src/cci/research/simulation.py`
- Modify: `services/backend/src/cci/research/ablation.py`
- Modify: `services/backend/src/cci/research/statistics.py`
- Modify: `research/run_paper_experiments.py`
- Modify: `services/backend/src/cci/api/routers/research.py`
- Modify: `services/backend/src/cci/api/routers/research_demo.py`
- Modify: `README.md`, `services/backend/README.md`, `docs/contracts/interfaces.md`, `docs/research-demonstration.md`
- Test: `services/backend/tests/unit/research/test_ablation.py`
- Test: `services/backend/tests/unit/research/test_simulation.py`
- Test: `services/backend/tests/unit/research/test_run_paper_experiments.py`
- Test: `services/backend/tests/unit/api/test_research_api.py`

**Interfaces:**
- Simulated observations carry deterministic evidence IDs, family IDs, observation types, fingerprints, and semantic subjects.
- The ablation scorer uses the same weight helper and ScoringConfig as the live scorer.

- [ ] **Step 1: Write failing research consistency tests**

Create two simulated observations for one family/type and a third for a second type. Assert repeated runs assign the same IDs and ablation capability weights match live family multipliers.

- [ ] **Step 2: Run research tests and confirm they fail**

Run from `services/backend`: `python -m pytest tests/unit/research/test_ablation.py tests/unit/research/test_simulation.py tests/unit/research/test_run_paper_experiments.py tests/unit/api/test_research_api.py -q`

Expected: FAIL because synthetic observations and runner outputs do not yet carry scoring config 5.0.0 family data.

- [ ] **Step 3: Use the common family identity and weight helpers in research**

Give synthetic observations deterministic UUIDv5 evidence IDs based on scenario seed, candidate ordinal, and observation ordinal. Derive source clusters and artifact IDs from stable scenario and artifact ordinals, not random candidate UUIDs; keep fingerprints, semantic subjects, family IDs, and observation types deterministic as well. For each ablation mode, compute its mode-specific confidence, convert observations to `EvidenceFamilyWeightInput`, and route both capability and coverage calculations through the shared weight helper and `evidence_family_decay` setting.

```python
identity = build_evidence_family_identity(
    source_family=obs.source_family,
    cluster_id=obs.cluster_id,
    capability=obs.capability_key,
    fact_domain="simulation",
    subject=obs.semantic_subject,
)
item = EvidenceFamilyWeightInput(
    evidence_id=obs.evidence_id,
    evidence_family_id=identity.evidence_family_id,
    observation_type=obs.observation_type,
    is_positive_support=True,
    confidence=_compute_ablation_confidence(obs, mode),
    fingerprint=obs.fingerprint,
)
weights = compute_evidence_family_weights([item], config.evidence_family_decay)
```

- [ ] **Step 4: Regenerate artifacts and update interfaces**

Run from the repository root: `python research/run_paper_experiments.py`. Update the JSON, Markdown, and LaTeX artifacts from this run; update backend API notes and docs to report config `5.0.0`, family decay, paired sample sizes, and the new measured values. Do not label synthetic results empirical calibration.

```json
{
  "scoring_config_version": "5.0.0",
  "evidence_family_decay": 0.5
}
```

- [ ] **Step 5: Run research and backend API checks**

Run from `services/backend`: `python -m pytest tests/unit/research/test_ablation.py tests/unit/research/test_simulation.py tests/unit/research/test_run_paper_experiments.py tests/unit/api/test_research_api.py -q`

Expected: PASS; API metadata and generated backend artifacts agree.

- [ ] **Step 6: Commit research and documentation updates**

```bash
git add services/backend/src/cci/research services/backend/src/cci/api/routers/research.py services/backend/src/cci/api/routers/research_demo.py research/run_paper_experiments.py research/results README.md services/backend/README.md docs/contracts/interfaces.md docs/research-demonstration.md services/backend/tests/unit/research services/backend/tests/unit/api/test_research_api.py
git commit -m "research: align ablations with evidence families"
```

### Task 7: Full Acceptance Gate

**Files:**
- Test: `services/backend/tests/`
- Review: all Task 1-6 diffs and the supplied Fix 5 acceptance list.

- [ ] **Step 1: Run the complete backend suite**

Run from `services/backend` with `PYTHONPATH` set to the worktree `services/backend/src`: `python -m pytest tests -q`

Expected: PASS.

- [ ] **Step 2: Recheck migration paths and research artifacts**

Upgrade an empty temporary SQLite database and an existing revision-0002 database to head; inspect the family, observation-type, and decay columns. Confirm the research JSON has scoring version `5.0.0`, the configured decay, and paired sample counts matching the generated tables.

- [ ] **Step 3: Audit the final diff and commit any acceptance-only corrections**

Run `git diff --check`, search backend code, API schemas, generated research artifacts, and docs for stale scoring version `4.0.0`, and verify each supplied Fix 5 example against its acceptance test. Expected: no stale v4 backend scoring defaults, no untested example, and no unverified gate. If the audit finds a defect, return to its owning task, add a failing regression, fix it, rerun that task's gate, and update the task commit before finishing.

## Plan Self-Review

- **Spec coverage:** identity schema and semantic examples are covered by Tasks 1-2; deterministic family weights and config by Task 3; estimates, uncertainty, contradictions, and claims by Task 4; observation retention, API exposure, persistence, and migration by Task 5; synthetic scoring and published prototype artifacts by Task 6; complete acceptance evidence by Task 7.
- **Placeholder scan:** all tasks name concrete paths, commands, expected outcomes, and commit messages; no deferred implementation placeholders remain.
- **Type consistency:** `EvidenceFamilyIdentity`, `EvidenceFamilyWeightInput`, and `compute_evidence_family_weights` are defined before downstream tasks consume them; the weight map is keyed by evidence UUID throughout, including synthetic runs.
- **Review focus:** every listed edge class has an explicit test in its owning task.
