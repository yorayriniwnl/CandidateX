# Evidence-Calibrated Live Analysis Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Improve the real resume-to-dossier workflow with exact technology matching, conservative evidence calibration, sample-size-aware ownership, and explicit role-requirement fit.

**Architecture:** Keep acquisition, deterministic normalization, scoring, and reporting as separate units. Resume/JD text is normalized by a shared token matcher; live repository observations are calibrated before entering the existing formal scorer; requirement fit is computed from the same immutable evidence records and added to the dossier without changing RCI mathematics.

**Tech Stack:** Python 3.11+, FastAPI, Pydantic v2, PyMuPDF, python-docx, pytest, existing Next.js 16/React 19 result page.

**Spec:** `docs/superpowers/specs/2026-09-21-evidence-calibrated-live-analysis-design.md`

## Global Constraints

- Candidate code is never executed, built, installed, or tested.
- Only resume-supplied or explicitly user-selected public sources are fetched.
- Missing, unavailable, uncredited, and unresolved evidence remains UNKNOWN.
- Existing RCI, coverage, provenance, and functional-rescore behavior remain backward compatible.
- No external LLM call is added.
- New result fields are additive and request-scoped.

## Review Focus

- A title such as `Senior Software Engineer` must not become the candidate name; test `test_candidate_name_rejects_job_title_header`.
- `Java` must not match `JavaScript`, while `C++` and `CI/CD` must match exactly; test `test_technology_matching_respects_token_boundaries`.
- One matching commit must not receive sustained-history ownership confidence; test `test_small_commit_samples_are_shrunk`.
- Repeated dependency/source signals from one repository must have diminishing confidence; test `test_live_evidence_calibration_discounts_correlated_signals`.
- A JD requirement must explain exact, related, unknown, and unresolved states; test `test_role_fit_reports_requirement_status_and_mandatory_gaps`.

---

### Task 1: Shared technology matching and resume normalization

**Files:**
- Create: `services/backend/src/cci/intake/technology.py`
- Modify: `services/backend/src/cci/intake/manifest.py`
- Modify: `services/backend/src/cci/live/report.py`
- Test: `services/backend/tests/unit/intake/test_technology_matching.py`
- Test: `services/backend/tests/test_comprehensive_live.py`

**Interfaces:**
- Produces `normalize_technology(value: str) -> str`, `technology_pattern(term: str) -> re.Pattern[str]`, and `contains_technology(text: str, term: str) -> bool`.
- Produces `extract_skills_from_section(skill_lines: list[str]) -> list[str]` behavior that preserves display spelling but removes equivalent duplicates.
- `live.report.normalize_skill` consumes `normalize_technology` so resume, JD, and public-page matching share boundaries.

- [x] **Step 1: Write the failing tests**

```python
def test_technology_matching_respects_token_boundaries():
    assert contains_technology("JavaScript and TypeScript", "JavaScript")
    assert not contains_technology("JavaScript", "Java")
    assert contains_technology("Built with C++ and CI/CD", "C++")
    assert contains_technology("Built with C++ and CI/CD", "CI/CD")


def test_candidate_name_rejects_job_title_header():
    assert extract_candidate_name("Senior Software Engineer\nSkills\nPython") == "Unknown Candidate"


def test_skill_extraction_deduplicates_aliases_without_losing_display_text():
    skills = extract_skills_from_section(["React.js, React, C++, CI/CD"])
    assert skills == ["React.js", "C++", "CI/CD"]
```

- [x] **Step 2: Run the focused tests and verify RED**

Run: `C:\Users\yoray\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m pytest services/backend/tests/unit/intake/test_technology_matching.py -q`

Expected: FAIL because the shared matcher module and title guard do not yet exist.

- [x] **Step 3: Implement the minimal shared matcher and intake changes**

Implement a normalized alias map and a lookaround-based pattern:

```python
def technology_pattern(term: str) -> re.Pattern[str]:
    escaped = re.escape(term.strip())
    return re.compile(rf"(?<![A-Za-z0-9_+#]){escaped}(?![A-Za-z0-9_+#])", re.IGNORECASE)
```

Use canonical aliases for comparison only (`react.js`/`reactjs` → `react`,
`scikit-learn`/`sklearn` → `scikitlearn`, `node.js`/`nodejs` → `nodejs`). Reject
name candidates containing obvious document labels or job-title tokens such as
`engineer`, `developer`, `resume`, `summary`, and `profile`. Preserve the
first display spelling for equivalent skills.

- [x] **Step 4: Run focused and existing intake/report tests**

Run: `C:\Users\yoray\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m pytest services/backend/tests/unit/intake/test_technology_matching.py services/backend/tests/unit/intake/test_canonicalizer.py services/backend/tests/unit/intake/test_cv_parser.py services/backend/tests/test_comprehensive_live.py -q`

Expected: PASS with all existing resume parsing and exact-match assertions retained.

### Task 2: Requirement-level role fit and JD boundary fixes

**Files:**
- Create: `services/backend/src/cci/scoring/role_fit.py`
- Modify: `services/backend/src/cci/domain/contracts.py`
- Modify: `services/backend/src/cci/jobs/parser.py`
- Modify: `services/backend/src/cci/pipeline/orchestrator.py`
- Modify: `services/backend/src/cci/dossier/builder.py`
- Test: `services/backend/tests/unit/scoring/test_role_fit.py`
- Test: `services/backend/tests/unit/jobs/test_jd_parser.py`

**Interfaces:**
- Produces `RequirementEvidenceMatch` and `RoleFitSummary` Pydantic models.
- Produces `build_role_fit(requirements: list[NormalizedRequirement], evidence_records: list[EvidenceRecord]) -> RoleFitSummary`.
- Adds `Dossier.role_fit` with a default empty summary so old dossier payloads remain valid.

- [x] **Step 1: Write the failing role-fit and JD tests**

```python
def test_role_fit_reports_requirement_status_and_mandatory_gaps():
    requirements = [
        requirement("Must have Python", [CapabilityKey.BACKEND_ENGINEERING], ["python"]),
        requirement("Must have PostgreSQL", [CapabilityKey.DATABASE_ENGINEERING], ["postgresql"]),
        requirement("Must have synergistic paradigms", [], []),
    ]
    evidence = [python_evidence_record()]

    result = build_role_fit(requirements, evidence)

    assert [match.status for match in result.requirement_matches] == ["observed", "unknown", "unresolved"]
    assert result.mandatory_observed == 1
    assert result.mandatory_unknown == 1
    assert result.mandatory_unresolved == 1
    assert "Must have PostgreSQL" in result.critical_gaps


def test_jd_parser_does_not_match_java_inside_javascript():
    requirements = extract_requirements_from_jd("Must have JavaScript and C++.")
    technologies = [technology for item in requirements for technology in item.technology_mentions]
    assert "javascript" in technologies
    assert "java" not in technologies
    assert "c++" in technologies
```

- [x] **Step 2: Run the focused tests and verify RED**

Run: `C:\Users\yoray\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m pytest services/backend/tests/unit/scoring/test_role_fit.py services/backend/tests/unit/jobs/test_jd_parser.py -q`

Expected: FAIL because `role_fit` models/builder and punctuation-safe JD matching do not yet exist.

- [x] **Step 3: Implement role-fit models, matcher, and orchestration wiring**

Use exact technology matching for `observed`, capability-only evidence for
`related`, no evidence for `unknown`, and empty capability mappings for
`unresolved`. Preserve evidence IDs and an explanation on every match. Build
the summary during the existing pipeline after capability estimates are
available, and pass it through `build_candidate_dossier`.

Replace every JD `\b` term check with the shared lookaround matcher so terms
containing `+`, `/`, or `.` work and `Java` cannot match `JavaScript`.

- [x] **Step 4: Run role-fit, JD, and pipeline tests**

Run: `C:\Users\yoray\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m pytest services/backend/tests/unit/scoring/test_role_fit.py services/backend/tests/unit/jobs/test_jd_parser.py services/backend/tests/test_pipeline_orchestration.py services/backend/tests/test_research_demonstration.py -q`

Expected: PASS, with all existing RCI/coverage/rescore tests unchanged.

### Task 3: Live evidence calibration and sample-aware ownership

**Files:**
- Create: `services/backend/src/cci/scoring/live_evidence.py`
- Modify: `services/backend/src/cci/live/acquisition.py`
- Test: `services/backend/tests/unit/scoring/test_live_evidence.py`
- Test: `services/backend/tests/test_live_analysis.py`
- Test: `services/backend/tests/test_live_boundaries.py`

**Interfaces:**
- Produces `classify_live_observation(observation: EvidenceInput, artifact_path: str | None) -> str`.
- Produces `live_confidence_profile(kind: str, correlation_rank: int) -> tuple[float, float]` returning verification and depth factors.
- Produces `estimate_declared_commit_ownership(candidate_commits: int, total_commits: int, identity_supplied: bool, is_fork: bool) -> tuple[float, float]` returning ownership score and sample confidence.

- [x] **Step 1: Write failing calibration and ownership tests**

```python
def test_small_commit_samples_are_shrunk():
    one_commit, one_sample_confidence = estimate_declared_commit_ownership(1, 1, True, False)
    sustained, sustained_sample_confidence = estimate_declared_commit_ownership(30, 30, True, False)
    assert 0 < one_commit < sustained
    assert one_sample_confidence < sustained_sample_confidence
    assert estimate_declared_commit_ownership(0, 30, True, False)[0] == 0
    assert estimate_declared_commit_ownership(30, 30, False, False)[0] == 0


def test_live_evidence_calibration_discounts_correlated_signals():
    first = live_confidence_profile("source_usage", 1)
    second = live_confidence_profile("source_usage", 2)
    dependency = live_confidence_profile("dependency_declaration", 1)
    assert second[1] < first[1]
    assert dependency[0] < first[0]
    assert dependency[1] < first[1]
```

- [x] **Step 2: Run the focused tests and verify RED**

Run: `C:\Users\yoray\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m pytest services/backend/tests/unit/scoring/test_live_evidence.py -q`

Expected: FAIL because the calibration helpers do not yet exist.

- [x] **Step 3: Implement conservative profiles and wire acquisition**

Classify from the observation text, target capability, file category, and
artifact path. Use lower factors for dependency declarations and documentation,
moderate factors for source/structure, and stronger factors for tests and
explicit infrastructure configurations. Apply a rank-based diminishing factor
within each repository/capability/kind group, and store `evidence_kind`,
`correlation_rank`, `sample_confidence`, and the ownership formula explanation
in provenance.

Replace the raw `authored / len(commits)` ownership assignment with a bounded
small-sample shrinkage factor. Preserve zero when the candidate identity is
missing or no sampled commit matches. Keep the existing fork caps and source
receipts.

- [x] **Step 4: Run live acquisition and security regression tests**

Run: `C:\Users\yoray\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m pytest services/backend/tests/unit/scoring/test_live_evidence.py services/backend/tests/test_live_analysis.py services/backend/tests/test_live_boundaries.py services/backend/tests/test_comprehensive_live.py -q`

Expected: PASS; matching identity still produces evidence, missing/unmatched identity still yields zero confidence and UNKNOWN RCI, and all provenance/security checks remain intact.

### Task 4: Integrate and expose role-fit explanations

**Files:**
- Modify: `services/backend/src/cci/live/service.py`
- Modify: `apps/web/lib/live-analysis.ts`
- Modify: `apps/web/app/analyze/page.tsx`
- Test: `services/backend/tests/test_comprehensive_live.py`
- Test: `apps/web/tests/live-analysis.spec.ts`

**Interfaces:**
- The live response includes `dossier.role_fit` and `analysis.role_fit` as additive JSON fields.
- The result page displays mandatory observed/unknown/unresolved counts and the first critical gaps.

- [x] **Step 1: Write failing integration assertions**

```python
def test_live_result_contains_role_fit_summary(monkeypatch):
    result = service.analyze_resume(request_with_python_jd_and_python_evidence(monkeypatch))
    assert result["dossier"].role_fit.mandatory_observed == 1
    assert result["analysis"]["role_fit"]["mandatory_observed"] == 1
```

- [x] **Step 2: Run the focused integration test and verify RED**

Run: `C:\Users\yoray\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m pytest services/backend/tests/test_comprehensive_live.py -k role_fit -q`

Expected: FAIL because the live response does not yet copy the additive role-fit summary into the report.

- [x] **Step 3: Implement the response and result-page presentation**

Copy `state.dossier.role_fit.model_dump(mode="json")` into the live report,
extend the TypeScript result contract, and render the summary beside the
existing RCI/coverage metrics. Keep unknown and unresolved gaps visibly
distinct from observed matches.

- [x] **Step 4: Run backend integration and web checks**

Run: `C:\Users\yoray\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m pytest services/backend/tests/test_comprehensive_live.py -q`

Run: `pnpm --dir apps/web exec tsc --noEmit`

Expected: PASS with existing upload/export/failure browser assertions still compatible with the additive UI.

### Task 5: Full verification and documentation alignment

**Files:**
- Modify: `docs/live-resume-analysis.md`
- Modify: `docs/comprehensive-live-analysis.md`
- Test: full backend suite and web typecheck/build

- [x] **Step 1: Update the live-workflow documentation**

Document evidence tiers, sample-size ownership shrinkage, correlated-signal
discounting, and the new role-fit statuses. State explicitly that role-fit
matches are decision-support explanations, not hiring recommendations.

- [x] **Step 2: Run the full backend suite**

Run: `C:\Users\yoray\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m pytest -q`

Expected: PASS with zero failures.

- [x] **Step 3: Run the web typecheck and production build**

Run: `pnpm --dir apps/web exec tsc --noEmit`

Run: `pnpm --dir apps/web build`

Expected: both commands exit 0 without type or build errors.
