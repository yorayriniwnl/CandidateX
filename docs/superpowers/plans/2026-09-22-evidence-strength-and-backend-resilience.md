# Evidence Strength and Backend Resilience Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add conservative, explicit evidence-strength reporting and harden the live/pipeline APIs so thin evidence and backend failures cannot appear more trustworthy than they are.

**Architecture:** Keep the existing RCI, coverage, six-factor confidence, ownership, and cluster-bootstrap calculations. Add a pure uncertainty-summary module that derives a non-probabilistic evidence-strength band from those outputs, attach it additively to dossiers, and let the live service overlay source-health counts. Harden request limits and error boundaries at the FastAPI edge, then disclose the new summary in the existing live-analysis UI.

**Tech Stack:** Python 3.11+, FastAPI, Pydantic v2, pytest, SQLAlchemy-compatible domain contracts, Next.js 16, React 19, TypeScript, Playwright, pnpm.

**Spec:** `docs/superpowers/specs/2026-09-22-evidence-strength-and-backend-resilience-design.md`

## Global Constraints

- The result remains human decision support and must not present an evidence band as a hiring recommendation, validated probability, or proof of identity, authorship, skill mastery, employment, or credential authenticity.
- Existing RCI, Evidence Coverage, six-factor evidence confidence, ownership, and cluster-bootstrap mathematics remain unchanged.
- Missing evidence remains `UNKNOWN`; no numeric RCI may elevate evidence strength by itself.
- Confidence intervals remain unavailable when fewer than two independent clusters exist.
- Existing endpoint paths and response fields remain backward compatible; new fields are additive.
- No LLM, learned calibration model, external hiring-outcome labels, persistence, authentication, broader identity discovery, or candidate-code execution may be added.
- Live acquisition bounds, URL validation, SSRF checks, archive containment, and source receipts remain intact.
- Presentation gates use `0.35` low coverage, `0.60` limited-to-moderate coverage, `0.80` moderate-to-well-supported coverage, `3` clusters for `well_supported`, `0.80` interval coverage, and `25` maximum interval width; these are deterministic presentation gates, not probabilities.

## Review Focus

- One high RCI from one repository must remain `limited` because its interval is unavailable; owned by Task 1 and Task 2 tests.
- A partial live run with one successful source and one failed or unscanned source must expose source-health uncertainty; owned by Task 3 integration tests.
- A maximum-size declared URL payload must be accepted within the finite bound, while a streamed body over the bound must return 413; owned by Task 4 API tests.
- Unexpected live exceptions and pipeline failures must return safe, traceable messages without stack traces; owned by Task 4 API tests.
- An older response without the new summary must render the existing audit view without fabricating a band; owned by Task 5 browser tests.

### Task 1: Build the deterministic analysis-confidence summary

**Files:**
- Create: `services/backend/src/cci/uncertainty/summary.py`
- Modify: `services/backend/src/cci/domain/contracts.py: capability estimate and dossier contract section`
- Create: `services/backend/tests/unit/uncertainty/test_analysis_confidence.py`
- Modify: `services/backend/tests/unit/test_contracts.py`

**Interfaces:**
- Consumes: existing `CapabilityEstimate`, `EvidenceRecord`, `CapabilityConflict`, `RoleFitSummary`, `ScoringConfig`, `CapabilityKey`, and role-weight mappings.
- Produces: frozen `AnalysisConfidenceSummary` and `build_analysis_confidence(...)`.

The public helper signature is:

~~~python
def build_analysis_confidence(
    *,
    capabilities: Mapping[CapabilityKey, CapabilityEstimate],
    evidence_records: Sequence[EvidenceRecord],
    role_weights: Mapping[CapabilityKey, float],
    conflicts: Mapping[CapabilityKey, CapabilityConflict],
    role_fit: RoleFitSummary,
    config: ScoringConfig | None = None,
    source_failures: int = 0,
    source_unscanned: int = 0,
) -> AnalysisConfidenceSummary:
    """Derive bounded evidence-strength metadata; never return a probability."""
~~~

`AnalysisConfidenceSummary` must expose these exact fields:

~~~python
class AnalysisConfidenceSummary(BaseModel):
    model_config = ConfigDict(frozen=True)

    evidence_strength: Literal["insufficient", "limited", "moderate", "well_supported"] = "insufficient"
    explanation: str = "No empirical evidence was observed."
    uncertainty_flags: list[str] = Field(default_factory=lambda: ["no_empirical_evidence"])
    role_coverage: float = Field(default=0.0, ge=0.0, le=1.0)
    observed_capabilities: int = Field(default=0, ge=0)
    independent_clusters: int = Field(default=0, ge=0)
    capabilities_with_intervals: int = Field(default=0, ge=0)
    interval_coverage: float = Field(default=0.0, ge=0.0, le=1.0)
    maximum_interval_width: float | None = Field(default=None, ge=0.0, le=100.0)
    meaningful_conflicts: int = Field(default=0, ge=0)
    mandatory_unknown: int = Field(default=0, ge=0)
    mandatory_unresolved: int = Field(default=0, ge=0)
    source_failures: int = Field(default=0, ge=0)
    source_unscanned: int = Field(default=0, ge=0)
    unusable_evidence_records: int = Field(default=0, ge=0)
~~~

An unusable record is material when it targets a positive-role-weight capability and either that capability has no usable positive-confidence record or its unusable-record count is at least its usable-record count. Count usable clusters from records with `confidence > 0` using `cluster_id` or `source_locator`; count interval coverage only over observed capabilities and normalize by their observed role weight.

- [ ] **Step 1: Write failing summary tests**

Add real `EvidenceRecord` fixtures using `EvidenceConfidenceFactors` rather than mocks. Cover the core contract before production code exists:

~~~python
def test_one_high_score_cluster_cannot_be_well_supported():
    capabilities, evidence, conflicts, role_fit, weights = one_cluster_fixture(score=96.0)

    result = build_analysis_confidence(
        capabilities=capabilities,
        evidence_records=evidence,
        role_weights=weights,
        conflicts=conflicts,
        role_fit=role_fit,
    )

    assert result.evidence_strength == "limited"
    assert "single_cluster" in result.uncertainty_flags
    assert "interval_unavailable" in result.uncertainty_flags


def test_no_evidence_is_explicitly_insufficient():
    result = build_analysis_confidence(
        capabilities=empty_capabilities(),
        evidence_records=[],
        role_weights=uniform_weights(),
        conflicts=empty_conflicts(),
        role_fit=RoleFitSummary(),
    )

    assert result.evidence_strength == "insufficient"
    assert result.uncertainty_flags == ["no_empirical_evidence", "low_role_coverage"]
    assert result.role_coverage == 0.0
~~~

Also assert that two independent clusters with intervals improve `independent_clusters`, `capabilities_with_intervals`, and `interval_coverage`, while a meaningful conflict or mandatory gap prevents `well_supported`.

- [ ] **Step 2: Run the focused tests and verify the expected RED failure**

Run:

~~~powershell
& services/backend/.venv/Scripts/python.exe -m pytest services/backend/tests/unit/uncertainty/test_analysis_confidence.py -q
~~~

Expected: collection fails because `AnalysisConfidenceSummary` and `build_analysis_confidence` do not exist yet. If fixture construction fails first, correct the test fixture until the failure is specifically the missing production interface.

- [ ] **Step 3: Add the contract and minimal pure summary implementation**

Add the model to `domain/contracts.py`. Implement `summary.py` with constants:

~~~python
LIMITED_COVERAGE = 0.60
WELL_SUPPORTED_COVERAGE = 0.80
WELL_SUPPORTED_INTERVAL_COVERAGE = 0.80
WELL_SUPPORTED_MAX_INTERVAL_WIDTH = 25.0
WELL_SUPPORTED_MIN_CLUSTERS = 3
~~~

Build flags in stable order, apply the band precedence `insufficient` → `limited` → `moderate` → `well_supported`, clamp counts to non-negative integers, and generate an explanation from the first applicable flags. Do not add a numeric confidence score.

- [ ] **Step 4: Run focused tests and contract regression tests**

Run:

~~~powershell
& services/backend/.venv/Scripts/python.exe -m pytest services/backend/tests/unit/uncertainty/test_analysis_confidence.py services/backend/tests/unit/test_contracts.py -q
~~~

Expected: PASS, with bounded summary fields and deterministic repeated output.

- [ ] **Step 5: Commit the isolated summary unit**

~~~powershell
git add services/backend/src/cci/domain/contracts.py services/backend/src/cci/uncertainty/summary.py services/backend/tests/unit/uncertainty/test_analysis_confidence.py services/backend/tests/unit/test_contracts.py
git commit -m "feat: add conservative analysis confidence summary"
~~~

### Task 2: Integrate confidence into dossiers and functional rescoring

**Files:**
- Modify: `services/backend/src/cci/domain/contracts.py: Dossier`
- Modify: `services/backend/src/cci/dossier/builder.py: build_candidate_dossier`
- Modify: `services/backend/src/cci/pipeline/orchestrator.py: execute_analysis_pipeline and rescore_dossier`
- Modify: `services/backend/tests/test_pipeline_orchestration.py`
- Modify: `services/backend/tests/test_research_demonstration.py`
- Modify: `services/backend/tests/unit/dossier/test_dossier_builder.py`

**Interfaces:**
- Consumes: `AnalysisConfidenceSummary` and `build_analysis_confidence(...)` from Task 1.
- Produces: `Dossier.analysis_confidence`, populated by every new pipeline run and recomputed by `rescore_dossier`.

- [ ] **Step 1: Write failing integration tests**

Extend the synthetic pipeline test with a single-cluster high-score case:

~~~python
def test_pipeline_exposes_limited_confidence_for_thin_evidence():
    state = execute_analysis_pipeline(
        candidate_id=uuid4(),
        role=CanonicalRole.BACKEND,
        custom_evidence=one_cluster_high_score_evidence(),
        evidence_mode="synthetic",
    )

    assert state.dossier is not None
    assert state.dossier.rci is not None
    assert state.dossier.analysis_confidence.evidence_strength == "limited"
    assert "single_cluster" in state.dossier.analysis_confidence.uncertainty_flags
~~~

Add a rescore assertion that `analysis_confidence.role_coverage` changes when role weights change, while the original dossier's summary, evidence records, and dossier ID remain unchanged.

- [ ] **Step 2: Run the focused integration tests and verify RED**

Run:

~~~powershell
& services/backend/.venv/Scripts/python.exe -m pytest services/backend/tests/test_pipeline_orchestration.py -k "thin_evidence or functional_rescore" -q
~~~

Expected: the existing pipeline may produce a dossier, but `analysis_confidence` is missing or not recomputed, so the new assertions fail for the expected reason.

- [ ] **Step 3: Wire summary creation into the orchestrator and dossier builder**

Add an optional `analysis_confidence: AnalysisConfidenceSummary | None = None` parameter to `build_candidate_dossier`, pass it into `Dossier`, and compute it immediately after `role_fit` and capability conflicts are available:

~~~python
analysis_confidence = build_analysis_confidence(
    capabilities=capability_estimates,
    evidence_records=raw_evidence,
    role_weights=role_weights,
    conflicts=capability_conflicts,
    role_fit=role_fit,
)
~~~

In `rescore_dossier`, rebuild the summary after the new role weights and coverage are calculated. Keep evidence, acquisition, analyzers, and the original dossier immutable.

- [ ] **Step 4: Run focused pipeline, dossier, and research tests**

Run:

~~~powershell
& services/backend/.venv/Scripts/python.exe -m pytest services/backend/tests/test_pipeline_orchestration.py services/backend/tests/test_research_demonstration.py services/backend/tests/unit/dossier/test_dossier_builder.py -q
~~~

Expected: PASS, including legacy dossier fixtures that rely on the additive default.

- [ ] **Step 5: Commit dossier integration**

~~~powershell
git add services/backend/src/cci/domain/contracts.py services/backend/src/cci/dossier/builder.py services/backend/src/cci/pipeline/orchestrator.py services/backend/tests/test_pipeline_orchestration.py services/backend/tests/test_research_demonstration.py services/backend/tests/unit/dossier/test_dossier_builder.py
git commit -m "feat: attach evidence strength to analysis dossiers"
~~~

### Task 3: Add live source health and recompute live confidence

**Files:**
- Modify: `services/backend/src/cci/live/report.py`
- Modify: `services/backend/src/cci/live/service.py`
- Modify: `services/backend/tests/test_comprehensive_live.py`
- Modify: `services/backend/tests/test_live_analysis.py`
- Modify: `services/backend/tests/test_live_boundaries.py`

**Interfaces:**
- Consumes: live source receipt dictionaries and Task 2 dossier summaries.
- Produces: `build_source_health(sources) -> dict[str, object]`, `analysis.source_health`, and `analysis.analysis_confidence` with live source failure/unscanned counts applied.

Define `build_source_health` with this exact output shape:

~~~python
{
    "supplied_sources": int,
    "observed_sources": int,
    "failed_sources": int,
    "not_selected_sources": int,
    "not_scanned_sources": int,
    "blocked_sources": int,
    "is_partial": bool,
    "flags": list[str],
}
~~~

Treat a receipt as failed when its status is not `observed`, `not_selected`, or `not_scanned`; treat `not_selected` and `not_scanned` as unscanned; treat `security_blocked` as blocked as well as failed. Preserve every original receipt.

- [ ] **Step 1: Write failing live integration tests**

Add assertions to the existing service tests:

~~~python
def test_live_result_exposes_source_health_and_confidence(monkeypatch):
    monkeypatch.setattr(service, "acquire_sources", lambda urls, identity: ([], [], [
        {"url": "https://github.com/example/api", "status": "observed"},
        {"url": "https://example.invalid", "status": "timeout"},
    ]))
    monkeypatch.setattr(service, "acquire_public_links", lambda urls: [])

    result = service.analyze_resume(LiveAnalysisRequest(intake=intake()))

    assert result["analysis"]["source_health"]["failed_sources"] == 1
    assert result["analysis"]["source_health"]["is_partial"] is True
    assert result["analysis"]["analysis_confidence"]["source_failures"] == 1
    assert "source_failures" in result["dossier"].analysis_confidence.uncertainty_flags
~~~

Also assert a one-commit repository returns `limited` confidence, and a provider failure with no evidence keeps `rci` as `None` while exposing the failure receipt.

- [ ] **Step 2: Run the focused live tests and verify RED**

Run:

~~~powershell
& services/backend/.venv/Scripts/python.exe -m pytest services/backend/tests/test_comprehensive_live.py services/backend/tests/test_live_analysis.py -k "source_health or confidence or one_commit" -q
~~~

Expected: `source_health` and the live confidence fields are missing or still show zero source failures.

- [ ] **Step 3: Implement source-health aggregation and live summary overlay**

Add `build_source_health` to `live/report.py` and include it in the dictionary returned by `build_report`. In `live/service.py`, build the report after source acquisition, then call `build_analysis_confidence` again with the dossier's existing evidence/estimates/weights/conflicts/role fit and the source-health failure/unscanned counts. Update the dossier immutably and rebuild the graph after the update:

~~~python
source_health = analysis["source_health"]
live_confidence = build_analysis_confidence(
    capabilities=dossier.capability_estimates,
    evidence_records=dossier.evidence_records,
    role_weights=dossier.role_weights,
    conflicts=dossier.capability_conflicts,
    role_fit=dossier.role_fit,
    source_failures=source_health["failed_sources"],
    source_unscanned=source_health["not_scanned_sources"] + source_health["not_selected_sources"],
)
dossier = dossier.model_copy(update={"analysis_confidence": live_confidence})
~~~

Copy the same JSON summary into `analysis["analysis_confidence"]`. Do not let public page text, credentials, or source-health counts create positive capability evidence.

- [ ] **Step 4: Run live acquisition, boundary, and comprehensive tests**

Run:

~~~powershell
& services/backend/.venv/Scripts/python.exe -m pytest services/backend/tests/test_comprehensive_live.py services/backend/tests/test_live_analysis.py services/backend/tests/test_live_boundaries.py -q
~~~

Expected: PASS with source receipts, graph output, role fit, unknown evidence, ownership behavior, and security boundaries unchanged.

- [ ] **Step 5: Commit live confidence integration**

~~~powershell
git add services/backend/src/cci/live/report.py services/backend/src/cci/live/service.py services/backend/tests/test_comprehensive_live.py services/backend/tests/test_live_analysis.py services/backend/tests/test_live_boundaries.py
git commit -m "feat: expose live source health and confidence limits"
~~~

### Task 4: Harden live and pipeline API boundaries

**Files:**
- Modify: `services/backend/src/cci/live/contracts.py`
- Modify: `services/backend/src/cci/api/routers/live.py`
- Modify: `services/backend/src/cci/api/routers/pipeline_router.py`
- Create: `services/backend/tests/unit/api/test_live_api_resilience.py`
- Modify: `services/backend/tests/unit/api/test_pipeline_orchestration.py`

**Interfaces:**
- Consumes: existing `LiveAnalysisRequest`, `limited_body`, `PipelineExecutionState`, and FastAPI route contracts.
- Produces: `MAX_ANALYZE_BODY = 512 * 1024`, `X-Request-ID` on live responses, safe 500 errors, and sanitized pipeline failure responses.

- [ ] **Step 1: Write failing API resilience tests**

Add a route-level test with a client that does not re-raise server exceptions:

~~~python
def test_unexpected_live_error_is_safe_and_traceable(monkeypatch):
    monkeypatch.setattr(live_router, "analyze_resume", lambda payload: (_ for _ in ()).throw(RuntimeError("secret traceback")))
    response = TestClient(app, raise_server_exceptions=False).post(
        "/api/v1/live/analyze", json=valid_analyze_payload()
    )

    assert response.status_code == 500
    assert response.headers["x-request-id"]
    assert "secret traceback" not in response.text
    assert "Traceback" not in response.text
~~~

Add a maximum-payload test using 100 strings of length 2048 in `external_urls`, with acquisition monkeypatched to return bounded receipts, and assert the request does not fail at the body gate. Add an over-limit streaming request and assert 413. Add a pipeline failure-state test that feeds `error="Traceback (most recent call last): secret"` and asserts the response contains a generic message, not the traceback.

- [ ] **Step 2: Run the resilience tests and verify RED**

Run:

~~~powershell
& services/backend/.venv/Scripts/python.exe -m pytest services/backend/tests/unit/api/test_live_api_resilience.py services/backend/tests/unit/api/test_pipeline_orchestration.py -q
~~~

Expected: the current analyze route leaks an uncaught exception to the test client or rejects the valid maximum payload, and pipeline status exposes the raw error.

- [ ] **Step 3: Implement bounded body checks and safe request IDs**

In `live/contracts.py`, define:

~~~python
MAX_ANALYZE_BODY = 512 * 1024
~~~

Update `limited_body` to inspect a numeric `Content-Length` when present, raise 413 before reading when it exceeds the limit, and retain the streaming byte counter. In both live routes, create a UUID request ID, set `response.headers["X-Request-ID"]`, and use `logger.exception` with that ID for unexpected exceptions. Return the existing generic messages with no internal details; keep 422/413/415/500 status semantics.

- [ ] **Step 4: Sanitize pipeline status errors**

Centralize conversion from `PipelineExecutionState` to `PipelineStatusResponse` or add a private helper in `pipeline_router.py`. Return `error=None` for non-failed runs and `error="The analysis pipeline failed before producing a dossier."` for failed runs. Preserve `current_stage`, stage details, status, RCI, and coverage; never serialize `state.error`.

- [ ] **Step 5: Run API, security, and live regression tests**

Run:

~~~powershell
& services/backend/.venv/Scripts/python.exe -m pytest services/backend/tests/unit/api/test_live_api_resilience.py services/backend/tests/unit/api/test_pipeline_orchestration.py services/backend/tests/test_live_analysis.py services/backend/tests/test_live_boundaries.py -q
~~~

Expected: PASS with no changes to SSRF, archive, private-repository, or source-failure behavior.

- [ ] **Step 6: Commit API hardening**

~~~powershell
git add services/backend/src/cci/live/contracts.py services/backend/src/cci/api/routers/live.py services/backend/src/cci/api/routers/pipeline_router.py services/backend/tests/unit/api/test_live_api_resilience.py services/backend/tests/unit/api/test_pipeline_orchestration.py
git commit -m "fix: harden live analysis API failure boundaries"
~~~

### Task 5: Expose evidence strength in the live-analysis UI

**Files:**
- Modify: `apps/web/types/cci.ts`
- Modify: `apps/web/lib/live-analysis.ts`
- Modify: `apps/web/app/analyze/page.tsx`
- Modify: `apps/web/app/analyze/shared.module.css`
- Modify: `apps/web/tests/live-analysis-ui.spec.ts`
- Modify: `apps/web/tests/live-analysis.spec.ts`

**Interfaces:**
- Consumes: backend `dossier.analysis_confidence`, `analysis.analysis_confidence`, and `analysis.source_health` from Tasks 2–4.
- Produces: typed frontend fields, an accessible evidence-strength panel, conservative per-capability status copy, and backward-compatible fallback behavior.

Add these TypeScript types:

~~~ts
export type EvidenceStrength = 'insufficient' | 'limited' | 'moderate' | 'well_supported';

export interface AnalysisConfidenceSummary {
  evidence_strength: EvidenceStrength;
  explanation: string;
  uncertainty_flags: string[];
  role_coverage: number;
  observed_capabilities: number;
  independent_clusters: number;
  capabilities_with_intervals: number;
  interval_coverage: number;
  maximum_interval_width: number | null;
  meaningful_conflicts: number;
  mandatory_unknown: number;
  mandatory_unresolved: number;
  source_failures: number;
  source_unscanned: number;
  unusable_evidence_records: number;
}

export interface SourceHealth {
  supplied_sources: number;
  observed_sources: number;
  failed_sources: number;
  not_selected_sources: number;
  not_scanned_sources: number;
  blocked_sources: number;
  is_partial: boolean;
  flags: string[];
}
~~~

- [ ] **Step 1: Write failing browser assertions**

Extend the mocked analyze response with a limited summary:

~~~ts
analysis_confidence: {
  evidence_strength: 'limited',
  explanation: 'One project cluster; interval unavailable.',
  uncertainty_flags: ['single_cluster', 'interval_unavailable'],
  role_coverage: 0.22,
  observed_capabilities: 1,
  independent_clusters: 1,
  capabilities_with_intervals: 0,
  interval_coverage: 0,
  maximum_interval_width: null,
  meaningful_conflicts: 0,
  mandatory_unknown: 0,
  mandatory_unresolved: 0,
  source_failures: 1,
  source_unscanned: 0,
  unusable_evidence_records: 0,
},
source_health: {
  supplied_sources: 2, observed_sources: 1, failed_sources: 1,
  not_selected_sources: 0, not_scanned_sources: 0, blocked_sources: 0,
  is_partial: true, flags: ['source_failures'],
},
~~~

Assert that the result shows `Evidence strength`, `Limited`, `single cluster`, and the partial-source message. Add a compatibility test whose mocked result omits both new fields and assert the existing audit table still renders without an invented band.

- [ ] **Step 2: Run focused browser tests and verify RED**

Run:

~~~powershell
pnpm --dir apps/web exec playwright test tests/live-analysis-ui.spec.ts --project=chromium
~~~

Expected: the new evidence-strength assertions fail because the panel and types do not exist.

- [ ] **Step 3: Add typed fields and the evidence-strength panel**

Add optional `analysis_confidence` to `Dossier`, add `analysis_confidence` and `source_health` to `ComprehensiveAnalysis`, and render a focused panel before `CapabilitySnapshotTable`. Map flags to readable labels without hiding the raw deterministic flag text. Use `styles.warning`/existing panel tokens unless a dedicated class is required for layout.

The panel must state:

~~~text
Evidence strength: Limited
This is evidence strength from the supplied artifacts, not a probability or hiring recommendation.
~~~

In `CapabilitySnapshotTable`, mark an observed capability as limited when `coverage_k < 0.35` or `ci_lower == null`; keep the numeric estimate visible but change the status text to `Limited evidence` and the next action to `Prepare verification`.

- [ ] **Step 4: Run focused UI and live workflow tests**

Run:

~~~powershell
pnpm --dir apps/web exec playwright test tests/live-analysis-ui.spec.ts tests/live-analysis.spec.ts --project=chromium
~~~

Expected: PASS for the evidence panel, source-health disclosure, older-response fallback, upload, export, source receipts, failure clearing, and mobile layout.

- [ ] **Step 5: Run TypeScript validation**

Run:

~~~powershell
pnpm --dir apps/web exec tsc --noEmit --incremental false
~~~

Expected: exit 0 with no new type errors.

- [ ] **Step 6: Commit frontend disclosure**

~~~powershell
git add apps/web/types/cci.ts apps/web/lib/live-analysis.ts apps/web/app/analyze/page.tsx apps/web/app/analyze/shared.module.css apps/web/tests/live-analysis-ui.spec.ts apps/web/tests/live-analysis.spec.ts
git commit -m "feat: disclose evidence strength in live analysis"
~~~

### Task 6: Align documentation and run the full verification gate

**Files:**
- Modify: `docs/live-resume-analysis.md`
- Modify: `docs/comprehensive-live-analysis.md`
- Modify: `README.md` only if the verification section needs the new confidence terminology
- No new production interfaces

**Interfaces:**
- Consumes: completed backend and frontend behavior from Tasks 1–5.
- Produces: documentation that describes evidence bands as deterministic evidence quality, not probabilities, and a verification record covering the full stack.

- [ ] **Step 1: Write documentation regression checks**

Before editing, search for the existing confidence/coverage explanations:

~~~powershell
rg -n "confidence|coverage|interval|unknown|verification" docs/live-resume-analysis.md docs/comprehensive-live-analysis.md README.md
~~~

Use the result to update the live workflow documentation with the exact bands, gates, uncertainty flags, source-health meaning, and the explicit “not a probability or hiring recommendation” limitation. Do not claim real-world validation.

- [ ] **Step 2: Run the complete backend suite**

~~~powershell
& services/backend/.venv/Scripts/python.exe -m pytest services/backend/tests -q
~~~

Expected: all backend tests pass. Any failure must be fixed or reported by test name before completion.

- [ ] **Step 3: Run the complete frontend verification**

~~~powershell
pnpm --dir apps/web exec tsc --noEmit --incremental false
pnpm --dir apps/web build
pnpm --dir apps/web exec playwright test --project=chromium
~~~

Expected: all commands exit 0. Preserve Playwright artifacts under `apps/web/test-results`.

- [ ] **Step 4: Inspect the final diff and working tree**

~~~powershell
git diff --check
git status --short
git diff HEAD~5..HEAD --stat
~~~

Confirm the diff contains no changes that broaden source acquisition, identity discovery, persistence, or candidate-code execution. Confirm the final tree has no accidental generated reports or test artifacts staged.

- [ ] **Step 5: Commit documentation and final verification alignment**

~~~powershell
git add docs/live-resume-analysis.md docs/comprehensive-live-analysis.md README.md
git commit -m "docs: explain evidence strength and uncertainty limits"
~~~

## Final handoff

After Task 6, report:

- the evidence-strength contract and conservative gates;
- backend request/error protections and request-ID behavior;
- live source-health and UI disclosure behavior;
- exact backend, TypeScript, build, and Playwright commands run with results;
- any environment-dependent verification that could not run;
- the commits created for each task.



