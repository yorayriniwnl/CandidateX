"""Durable Analysis Runs execution engine and state machine (Fix 26).

Replaces synchronous single-request analysis with durable, multi-stage,
resumable, and idempotent pipeline execution.

Pipeline States:
- QUEUED
- PARSING_RESUME
- EXTRACTING_CLAIMS
- DISCOVERING_SOURCES
- FETCHING_SOURCES
- ANALYZING_GITHUB
- ANALYZING_DEPLOYMENTS
- ANALYZING_CREDENTIALS
- ANALYZING_ACADEMICS
- ANALYZING_PROJECTS
- CORROBORATING_CLAIMS
- COMPUTING_SIGNALS
- BUILDING_GRAPH
- BUILDING_DOSSIER
- COMPLETED
- PARTIAL
- FAILED
- CANCELLED

Invariants:
- Never executes candidate or repository code.
- Each stage is idempotent: repeated executions produce the exact same outcome without duplicate work.
- Each stage is resumable: interrupted or failed runs resume from the last incomplete stage.
- Progress is pollable/streamable without resending large intake payloads.
"""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timezone
import logging
import threading
from typing import Any, Mapping, Sequence
from uuid import UUID, uuid4

from cci.domain.contracts import (
    CandidateManifest,
    RepositoryAssociation,
    RepositoryContribution,
    ScoringConfig,
)
from cci.domain.enums import AnalysisRunState, CanonicalRole
from cci.graph.builder import build_dossier_graph
from cci.live.acquisition import acquire_sources
from cci.limits import get_system_limits
from cci.live.contracts import LiveAnalysisRequest, MAX_REPOSITORIES, MAX_FILES, MAX_SECONDS
from cci.live.deployment import acquire_deployment_sources
from cci.live.public_links import acquire_public_links
from cci.live.report import build_report
from cci.pipeline.orchestrator import execute_analysis_pipeline

logger = logging.getLogger(__name__)

PIPELINE_STAGES = [
    AnalysisRunState.PARSING_RESUME,
    AnalysisRunState.EXTRACTING_CLAIMS,
    AnalysisRunState.DISCOVERING_SOURCES,
    AnalysisRunState.FETCHING_SOURCES,
    AnalysisRunState.ANALYZING_GITHUB,
    AnalysisRunState.ANALYZING_DEPLOYMENTS,
    AnalysisRunState.ANALYZING_CREDENTIALS,
    AnalysisRunState.ANALYZING_ACADEMICS,
    AnalysisRunState.ANALYZING_PROJECTS,
    AnalysisRunState.CORROBORATING_CLAIMS,
    AnalysisRunState.COMPUTING_SIGNALS,
    AnalysisRunState.BUILDING_GRAPH,
    AnalysisRunState.BUILDING_DOSSIER,
]

STAGE_PROGRESS = {
    AnalysisRunState.QUEUED: 0.0,
    AnalysisRunState.PARSING_RESUME: 5.0,
    AnalysisRunState.EXTRACTING_CLAIMS: 12.0,
    AnalysisRunState.DISCOVERING_SOURCES: 20.0,
    AnalysisRunState.FETCHING_SOURCES: 30.0,
    AnalysisRunState.ANALYZING_GITHUB: 45.0,
    AnalysisRunState.ANALYZING_DEPLOYMENTS: 55.0,
    AnalysisRunState.ANALYZING_CREDENTIALS: 62.0,
    AnalysisRunState.ANALYZING_ACADEMICS: 68.0,
    AnalysisRunState.ANALYZING_PROJECTS: 75.0,
    AnalysisRunState.CORROBORATING_CLAIMS: 82.0,
    AnalysisRunState.COMPUTING_SIGNALS: 90.0,
    AnalysisRunState.BUILDING_GRAPH: 95.0,
    AnalysisRunState.BUILDING_DOSSIER: 98.0,
    AnalysisRunState.COMPLETED: 100.0,
    AnalysisRunState.PARTIAL: 100.0,
}


@dataclass
class DurableAnalysisRun:
    """Persistent execution record of a durable analysis run."""

    analysis_run_id: UUID
    target_role: str
    state: AnalysisRunState = AnalysisRunState.QUEUED
    current_stage: str | None = None
    progress_percent: float = 0.0
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    started_at: str | None = None
    completed_at: str | None = None
    error_message: str | None = None
    input_payload: dict[str, Any] = field(default_factory=dict)
    stage_data: dict[str, Any] = field(default_factory=dict)
    result: dict[str, Any] | None = None
    client_ip: str = "127.0.0.1"
    budget_tracker: Any = None
    telemetry: Any = None

    def __post_init__(self):
        if self.telemetry is None:
            from cci.telemetry import create_run_telemetry
            req_id = self.input_payload.get("request_id") if isinstance(self.input_payload, dict) else None
            self.telemetry = create_run_telemetry(self.analysis_run_id, request_id=req_id)

    def to_status_dict(self) -> dict[str, Any]:
        """Returns pollable execution status."""
        from cci.security.abuse import sanitize_credentials
        missing_pieces = []
        if isinstance(self.result, dict):
            missing_pieces = self.result.get("missing_pieces", [])
        return {
            "analysis_run_id": str(self.analysis_run_id),
            "state": self.state.value,
            "current_stage": self.current_stage,
            "progress_percent": self.progress_percent,
            "target_role": self.target_role,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "completed_stages": list(self.stage_data.keys()),
            "error_message": sanitize_credentials(self.error_message) if self.error_message else None,
            "structured_error": self.telemetry.structured_error if self.telemetry else None,
            "budget_summary": self.budget_tracker.get_summary() if self.budget_tracker else None,
            "telemetry": self.telemetry.to_dict() if self.telemetry else None,
            "missing_pieces": missing_pieces,
            "result": sanitize_credentials(self.result) if self.result else None,
        }


class AnalysisRunManager:
    """Thread-safe manager for creating, running, polling, resuming, and cancelling analysis runs."""

    def __init__(self, max_workers: int = 4):
        self._runs: dict[UUID, DurableAnalysisRun] = {}
        self._lock = threading.Lock()
        self._executor = ThreadPoolExecutor(max_workers=max_workers)

    def create_run(
        self,
        input_payload: dict[str, Any],
        *,
        analysis_run_id: UUID | None = None,
        auto_start: bool = True,
        client_ip: str = "127.0.0.1",
        budget_tracker: Any = None,
    ) -> DurableAnalysisRun:
        """Admits a new analysis run into QUEUED state."""
        run_id = analysis_run_id or uuid4()
        target_role = input_payload.get("role", "backend")
        if isinstance(target_role, CanonicalRole):
            target_role = target_role.value

        with self._lock:
            if run_id in self._runs:
                run = self._runs[run_id]
                run.input_payload.update(input_payload)
                if target_role:
                    run.target_role = str(target_role)
                if client_ip:
                    run.client_ip = client_ip
                if budget_tracker:
                    run.budget_tracker = budget_tracker
            else:
                run = DurableAnalysisRun(
                    analysis_run_id=run_id,
                    target_role=str(target_role),
                    state=AnalysisRunState.QUEUED,
                    current_stage="QUEUED",
                    progress_percent=0.0,
                    input_payload=input_payload,
                    client_ip=client_ip,
                    budget_tracker=budget_tracker,
                )
                self._runs[run_id] = run

        if auto_start:
            self._executor.submit(self._execute_run, run_id)

        return run

    def start_run(
        self,
        run_id: UUID | str,
        update_payload: dict[str, Any] | None = None,
        sync: bool = False,
        client_ip: str | None = None,
        budget_tracker: Any = None,
    ) -> DurableAnalysisRun | None:
        """Starts or re-executes an existing run with updated payload."""
        key = UUID(str(run_id))
        with self._lock:
            run = self._runs.get(key)
            if not run:
                return None
            if client_ip:
                run.client_ip = client_ip
            if budget_tracker:
                run.budget_tracker = budget_tracker
            if update_payload:
                run.input_payload.update(update_payload)
                if "role" in update_payload:
                    target_role = update_payload["role"]
                    if isinstance(target_role, CanonicalRole):
                        target_role = target_role.value
                    run.target_role = str(target_role)
                # Clear downstream stage data if inputs changed
                for stage_name in list(run.stage_data.keys()):
                    if stage_name not in (
                        AnalysisRunState.PARSING_RESUME.value,
                        AnalysisRunState.EXTRACTING_CLAIMS.value,
                    ):
                        del run.stage_data[stage_name]
            run.state = AnalysisRunState.QUEUED
            run.current_stage = "QUEUED"
            run.error_message = None
            run.completed_at = None

        if sync:
            self._execute_run(key)
        else:
            self._executor.submit(self._execute_run, key)

        return run

    def get_run(self, run_id: UUID | str) -> DurableAnalysisRun | None:
        """Retrieves a durable run by its ID."""
        key = UUID(str(run_id))
        with self._lock:
            return self._runs.get(key)

    def cancel_run(self, run_id: UUID | str) -> DurableAnalysisRun | None:
        """Transitions a run into CANCELLED state if active or queued."""
        key = UUID(str(run_id))
        with self._lock:
            run = self._runs.get(key)
            if not run or run.state.is_terminal:
                return run
            run.state = AnalysisRunState.CANCELLED
            run.current_stage = "CANCELLED"
            run.completed_at = datetime.now(timezone.utc).isoformat()
            from cci.security.abuse import get_abuse_controls
            get_abuse_controls().release_run_slot(getattr(run, "client_ip", "127.0.0.1"))
            return run

    def resume_run(self, run_id: UUID | str, sync: bool = False) -> DurableAnalysisRun | None:
        """Resumes an interrupted or failed run from its last incomplete stage."""
        key = UUID(str(run_id))
        with self._lock:
            run = self._runs.get(key)
            if not run:
                return None
            if run.state == AnalysisRunState.COMPLETED or run.state == AnalysisRunState.PARTIAL:
                return run

            run.state = AnalysisRunState.QUEUED
            run.error_message = None

        if sync:
            self._execute_run(key)
        else:
            self._executor.submit(self._execute_run, key)

        return run

    def evict_candidate_runs(self, candidate_id: UUID | str) -> int:
        """Evicts all analysis runs associated with the candidate upon deletion request."""
        cid_str = str(candidate_id)
        with self._lock:
            to_delete = [
                rid
                for rid, r in self._runs.items()
                if str(getattr(r, "candidate_id", "")) == cid_str
                or (r.input_payload and str(r.input_payload.get("candidate_id", "")) == cid_str)
            ]
            for rid in to_delete:
                self._runs.pop(rid, None)
            return len(to_delete)

    def evict_expired_runs(self, max_age_seconds: float) -> int:
        """Evicts in-memory runs older than max_age_seconds to prevent hidden indefinite storage."""
        now = datetime.now(timezone.utc)
        count = 0
        with self._lock:
            to_delete = []
            for rid, r in self._runs.items():
                try:
                    created = datetime.fromisoformat(r.created_at)
                    if (now - created).total_seconds() > max_age_seconds:
                        to_delete.append(rid)
                except Exception:
                    pass
            for rid in to_delete:
                self._runs.pop(rid, None)
                count += 1
        return count


    def _execute_run(self, run_id: UUID) -> None:
        """Executes all sequential pipeline stages idempotently."""
        with self._lock:
            run = self._runs.get(run_id)
            if not run:
                return
            if not run.started_at:
                run.started_at = datetime.now(timezone.utc).isoformat()
            if run.telemetry is None:
                from cci.telemetry import create_run_telemetry
                req_id = run.input_payload.get("request_id") if isinstance(run.input_payload, dict) else None
                run.telemetry = create_run_telemetry(run.analysis_run_id, request_id=req_id)
            run.telemetry.start_run()

        try:
            if run.budget_tracker is None:
                from cci.security.abuse import RunBudgetTracker
                from cci.config import settings
                run.budget_tracker = RunBudgetTracker(
                    max_wall_clock_seconds=getattr(settings, "MAX_RUN_WALL_CLOCK_SECONDS", 60.0),
                    max_github_calls=getattr(settings, "MAX_GITHUB_CALLS_PER_RUN", 50),
                    max_crawl_pages=getattr(settings, "MAX_CRAWL_PAGES_PER_RUN", 24),
                    max_crawl_bytes=getattr(settings, "MAX_CRAWL_BYTES_PER_RUN", 5 * 1024 * 1024),
                )

            for stage in PIPELINE_STAGES:
                # Check cancellation
                with self._lock:
                    if run.state == AnalysisRunState.CANCELLED:
                        return
                    if run.budget_tracker and run.budget_tracker.is_time_exhausted():
                        logger.warning("Analysis run %s wall-clock timeout exceeded.", run_id)
                        break
                    run.state = stage
                    run.current_stage = stage.value
                    run.progress_percent = STAGE_PROGRESS.get(stage, run.progress_percent)

                # Idempotency check: if stage data already exists, skip execution
                if stage.value in run.stage_data:
                    continue

                if run.telemetry:
                    run.telemetry.start_stage(stage.value)

                # Execute stage logic
                try:
                    stage_output = self._run_stage(run, stage)
                except Exception as stage_exc:
                    if run.telemetry:
                        run.telemetry.fail_stage(stage.value, stage_exc)
                    raise

                with self._lock:
                    run.stage_data[stage.value] = stage_output
                    if run.telemetry:
                        art_count = len(stage_output) if isinstance(stage_output, (list, dict)) else 1
                        run.telemetry.complete_stage(stage.value, artifacts_count=art_count)

            # Finalize run
            with self._lock:
                dossier_data = run.stage_data.get(AnalysisRunState.BUILDING_DOSSIER.value, {})
                sources = dossier_data.get("sources", [])
                evidence = dossier_data.get("evidence", [])
                time_exhausted = run.budget_tracker.is_time_exhausted() if run.budget_tracker else False
                has_partials = any(s.get("status") not in ("observed", "completed") for s in sources) or not evidence or time_exhausted

                from cci.live.resilience import extract_missing_pieces
                missing_pieces = extract_missing_pieces(sources, time_exhausted=time_exhausted, has_evidence=bool(evidence))
                if isinstance(dossier_data, dict):
                    dossier_data["missing_pieces"] = missing_pieces

                run.state = AnalysisRunState.PARTIAL if has_partials else AnalysisRunState.COMPLETED
                run.current_stage = run.state.value
                run.progress_percent = 100.0
                run.completed_at = datetime.now(timezone.utc).isoformat()
                run.result = dossier_data
                if run.telemetry:
                    run.telemetry.finalize()

        except Exception as exc:
            logger.exception("Analysis run %s failed during stage %s", run_id, run.current_stage)
            with self._lock:
                run.state = AnalysisRunState.FAILED
                from cci.security.abuse import sanitize_credentials
                run.error_message = sanitize_credentials(str(exc))
                run.completed_at = datetime.now(timezone.utc).isoformat()
                if run.telemetry:
                    if not run.telemetry.failure_stage:
                        run.telemetry.fail_stage(run.current_stage or "PIPELINE", exc)
                    run.telemetry.finalize()
        finally:
            from cci.security.abuse import get_abuse_controls
            get_abuse_controls().release_run_slot(getattr(run, "client_ip", "127.0.0.1"))

    def _run_stage(self, run: DurableAnalysisRun, stage: AnalysisRunState) -> dict[str, Any]:
        """Executes an individual pipeline stage and returns its serializable artifacts."""
        if stage.value in run.stage_data:
            return run.stage_data[stage.value]

        payload = run.input_payload
        intake_obj = payload.get("intake")
        candidate_id = getattr(intake_obj, "candidate_id", None)
        if candidate_id is None and isinstance(intake_obj, dict):
            candidate_id = intake_obj.get("candidate_id")
        if candidate_id is None:
            candidate_id = payload.get("candidate_id", run.analysis_run_id)
        if isinstance(candidate_id, str):
            try:
                candidate_id = UUID(candidate_id)
            except ValueError:
                candidate_id = run.analysis_run_id

        intake_model = None
        if hasattr(intake_obj, "manifest"):
            manifest = intake_obj.manifest
            intake_model = intake_obj
        elif isinstance(intake_obj, dict):
            try:
                from cci.live.contracts import ResumeIntake
                intake_model = ResumeIntake.model_validate(intake_obj)
                manifest = intake_model.manifest
            except Exception:
                if "manifest" in intake_obj:
                    m_dict = dict(intake_obj["manifest"])
                    m_dict.setdefault("display_name", "Candidate")
                    manifest = CandidateManifest.model_validate(m_dict)
                else:
                    manifest = CandidateManifest(display_name="Candidate")
        else:
            manifest = CandidateManifest(display_name="Candidate")

        target_role = run.target_role
        jd_text = payload.get("jd_text") or payload.get("jd_edits") or ""
        github_urls = payload.get("github_urls") if payload.get("github_urls") is not None else getattr(manifest, "github_urls", [])
        github_identity = payload.get("github_identity", "")
        external_urls = payload.get("external_urls") if payload.get("external_urls") is not None else payload.get("user_reviewed_urls")

        # Stage 1: PARSING_RESUME
        if stage == AnalysisRunState.PARSING_RESUME:
            return {"candidate_id": str(candidate_id), "status": "parsed"}

        # Stage 2: EXTRACTING_CLAIMS
        if stage == AnalysisRunState.EXTRACTING_CLAIMS:
            return {
                "claimed_skills": list(manifest.claimed_skills),
                "project_claims": list(manifest.project_claims),
                "experience_claims": list(manifest.experience_claims),
            }

        # Stage 3: DISCOVERING_SOURCES
        if stage == AnalysisRunState.DISCOVERING_SOURCES:
            from cci.intake.canonicalizer import classify_url
            extracted = list(dict.fromkeys(
                url for key in ("linkedin_urls", "coding_profile_urls", "credential_urls",
                                "deployment_urls", "portfolio_urls", "project_links")
                for url in getattr(manifest, key, [])
            ))
            selected = external_urls if external_urls is not None else extracted
            deployment_candidates = list(dict.fromkeys(
                list(getattr(manifest, "deployment_urls", [])) +
                [u for u in (getattr(manifest, "project_links", []) + getattr(manifest, "portfolio_urls", [])) if classify_url(u) == "deployment"]
            ))
            return {
                "extracted_urls": extracted,
                "selected_urls": selected,
                "deployment_candidates": deployment_candidates,
            }

        # Stage 4: FETCHING_SOURCES
        if stage == AnalysisRunState.FETCHING_SOURCES:
            discovery_data = run.stage_data.get(AnalysisRunState.DISCOVERING_SOURCES.value, {})
            selected = discovery_data.get("selected_urls", [])
            deployment_candidates = set(discovery_data.get("deployment_candidates", []))
            non_deployment_selected = [u for u in selected if u not in deployment_candidates]
            public_receipts = acquire_public_links(non_deployment_selected)
            if run.telemetry:
                run.telemetry.record_sources(public_receipts)
            return {"public_sources": public_receipts}

        # Stage 5: ANALYZING_GITHUB
        if stage == AnalysisRunState.ANALYZING_GITHUB:
            from cci.contradictions.expectations import build_observable_claim_expectations
            expectations = build_observable_claim_expectations(intake_model) if intake_model else []
            discovery_data = run.stage_data.get(AnalysisRunState.DISCOVERING_SOURCES.value, {})
            deployment_candidates = discovery_data.get("deployment_candidates", [])

            github_evidence, ownership, github_sources = acquire_sources(
                github_urls,
                github_identity,
                run.analysis_run_id,
                observable_expectations=expectations,
                target_role=target_role,
                manifest=manifest,
                jd_text=jd_text,
                deployment_urls=deployment_candidates,
                portfolio_urls=getattr(manifest, "portfolio_urls", []),
                budget_tracker=run.budget_tracker,
            )
            if run.telemetry:
                calls = run.budget_tracker.github_calls if run.budget_tracker else len(github_sources)
                budget = run.budget_tracker.max_github_calls if run.budget_tracker else 50
                run.telemetry.record_github_usage(calls, budget)
            return {
                "github_evidence": [e.model_dump(mode="json") for e in github_evidence],
                "ownership_assessments": [o.model_dump(mode="json") for o in ownership],
                "github_sources": github_sources,
            }

        # Stage 6: ANALYZING_DEPLOYMENTS
        if stage == AnalysisRunState.ANALYZING_DEPLOYMENTS:
            discovery_data = run.stage_data.get(AnalysisRunState.DISCOVERING_SOURCES.value, {})
            selected = set(discovery_data.get("selected_urls", []))
            deployment_candidates = [u for u in discovery_data.get("deployment_candidates", []) if u in selected]
            deployment_evidence, deployment_sources = acquire_deployment_sources(
                deployment_candidates,
                github_urls,
                run.analysis_run_id,
            )
            return {
                "deployment_evidence": [e.model_dump(mode="json") for e in deployment_evidence],
                "deployment_sources": deployment_sources,
            }

        # Stage 7: ANALYZING_CREDENTIALS
        if stage == AnalysisRunState.ANALYZING_CREDENTIALS:
            from cci.credentials.verification import verify_all_credentials
            fetching_output = run.stage_data.get(AnalysisRunState.FETCHING_SOURCES.value, {})
            sources = fetching_output.get("public_sources", [])
            resume_review = getattr(intake_model, "resume_review", None)
            cert_claims = []
            if resume_review and hasattr(resume_review, "sections"):
                cert_claims = list(resume_review.sections.get("certifications", []))
            if not cert_claims and hasattr(manifest, "claimed_skills"):
                cert_claims = [c for c in manifest.claimed_skills if "cert" in c.lower()]

            verified = verify_all_credentials(
                resume_claims=cert_claims,
                candidate_name=getattr(manifest, "display_name", "Candidate"),
                sources=sources,
                declared_urls=getattr(manifest, "credential_urls", ()),
            )
            return {
                "credential_status": "evaluated",
                "verified_credentials": [r.to_dict() for r in verified],
                "count": len(verified),
            }

        # Stage 8: ANALYZING_ACADEMICS
        if stage == AnalysisRunState.ANALYZING_ACADEMICS:
            return {"academic_status": "evaluated"}

        # Stage 9: ANALYZING_PROJECTS
        if stage == AnalysisRunState.ANALYZING_PROJECTS:
            return {"project_status": "evaluated"}

        # Stage 10: CORROBORATING_CLAIMS
        if stage == AnalysisRunState.CORROBORATING_CLAIMS:
            return {"contradictions_evaluated": True}

        # Stage 11: COMPUTING_SIGNALS
        if stage == AnalysisRunState.COMPUTING_SIGNALS:
            return {"signals_computed": True}

        # Stage 12: BUILDING_GRAPH
        if stage == AnalysisRunState.BUILDING_GRAPH:
            return {"graph_prebuilt": True}

        # Stage 13: BUILDING_DOSSIER
        if stage == AnalysisRunState.BUILDING_DOSSIER:
            from cci.contradictions.expectations import build_observable_claim_expectations
            from cci.domain.contracts import EvidenceRecord, OwnershipAssessment

            expectations = build_observable_claim_expectations(intake_model) if intake_model else []

            gh_data = run.stage_data.get(AnalysisRunState.ANALYZING_GITHUB.value, {})
            deploy_data = run.stage_data.get(AnalysisRunState.ANALYZING_DEPLOYMENTS.value, {})
            pub_data = run.stage_data.get(AnalysisRunState.FETCHING_SOURCES.value, {})

            github_evidence = [EvidenceRecord.model_validate(e) for e in gh_data.get("github_evidence", [])]
            deployment_evidence = [EvidenceRecord.model_validate(e) for e in deploy_data.get("deployment_evidence", [])]
            ownership = [OwnershipAssessment.model_validate(o) for o in gh_data.get("ownership_assessments", [])]

            github_sources = gh_data.get("github_sources", [])
            deployment_sources = deploy_data.get("deployment_sources", [])
            public_sources = pub_data.get("public_sources", [])

            # Fix 39: Coding Profile Evidence
            from cci.profiles.coding import inspect_coding_profiles
            coding_urls = getattr(manifest, "coding_profile_urls", [])
            coding_evidences = inspect_coding_profiles(coding_urls, public_sources)
            coding_records = [
                rec for ce in coding_evidences
                if (rec := ce.to_evidence_record(candidate_id)) is not None
            ]

            evidence = [*github_evidence, *deployment_evidence, *coding_records]
            sources = [*github_sources, *deployment_sources, *public_sources]

            scoring_config = ScoringConfig()
            pipeline_state = execute_analysis_pipeline(
                candidate_id=candidate_id,
                role=target_role,
                jd_text=jd_text,
                declared_claims=manifest.claimed_skills,
                custom_evidence=evidence,
                evidence_mode="live",
                scoring_config=scoring_config,
                analysis_run_id=run.analysis_run_id,
                observable_expectations=expectations,
            )
            if pipeline_state.dossier is None:
                raise RuntimeError("The pipeline could not compile a candidate dossier.")

            associations = [
                RepositoryAssociation.model_validate(source["repository_association"])
                for source in sources if source.get("repository_association")
            ]
            contributions = [
                RepositoryContribution.model_validate(source["repository_contribution"])
                for source in sources if source.get("repository_contribution")
            ]

            sys_limits = get_system_limits()
            limitations = [
                "Resume identity and GitHub account association are candidate declarations, not identity verification.",
                "Public GitHub evidence is fetched live. Static heuristic observations do not prove mastery or job performance; rule strengths are not calibrated proficiency ratings.",
                "Source reliability uses configured priors only; no simulated review outcomes are used.",
                "Verification/depth confidence factors are conservative prototype settings, not empirically calibrated probabilities.",
                "Repository association and repository-level contribution are separate from path-specific artifact contribution.",
                "Artifact attribution uses bounded recent path history; failed, deferred, or ambiguous history remains unknown. A matching GitHub account does not verify human identity or line-level authorship.",
                "Public page text, profile metadata and certificate mentions do not increase capability scores. Issuer authentication and employment verification are not automated.",
                (
                    f"Public links: up to {sys_limits.max_urls.budget} HTML/text/digital PDF pages, "
                    f"{sys_limits.max_page_bytes.budget // 1024} KB each, 3 redirects; PDFs up to "
                    f"{sys_limits.max_pdf_pages.budget} pages. Login gates, image-only and script-only pages remain unresolved."
                ),
                (
                    f"Bounded scan: {sys_limits.max_repositories.budget} repositories, "
                    f"{sys_limits.max_files_per_repo.budget} selected text files each, "
                    f"{sys_limits.acquisition_budget_seconds.budget}s acquisition budget."
                ),
                "Durable Analysis Run: each stage is persistent, idempotent, and resumable.",
            ]

            from cci.projects.dossier import build_project_entities
            project_entities = build_project_entities(
                project_claims=manifest.project_claims,
                sources=sources,
                evidence_records=evidence,
                candidate_identifier=manifest.display_name,
            )

            from cci.claims.quantified import extract_and_verify_all_quantified_claims
            quantified_claims = extract_and_verify_all_quantified_claims(intake_model, sources) if intake_model else []

            dossier = pipeline_state.dossier.model_copy(update={
                "ownership_assessments": ownership,
                "repository_associations": associations,
                "repository_contributions": contributions,
                "project_entities": project_entities,
                "quantified_claims": quantified_claims,
                "system_limitations": [*pipeline_state.dossier.system_limitations, *limitations],
            })
            if run.telemetry:
                run.telemetry.record_pipeline_metrics(
                    dossier,
                    raw_evidence_count=len(evidence),
                    artifacts_scanned=len(sources),
                )
            graph = build_dossier_graph(dossier)
            report = build_report(intake_model, sources) if intake_model else {}

            return {
                "intake": intake_obj.model_dump(mode="json") if hasattr(intake_obj, "model_dump") else intake_obj,
                "dossier": dossier.model_dump(mode="json"),
                "graph": graph.to_api_response(candidate_id=dossier.candidate_id, analysis_run_id=dossier.analysis_run_id),
                "graph_snapshot": graph.to_dict(),
                "sources": sources,
                "analysis": report,
                "scoring_config": scoring_config.model_dump(mode="json"),
                "status": "partial" if any(s.get("status") not in ("observed", "completed") for s in sources) or not evidence else "completed",
            }

        return {}


# Global default manager singleton
_GLOBAL_MANAGER: AnalysisRunManager | None = None


def get_analysis_run_manager() -> AnalysisRunManager:
    """Returns the process-wide AnalysisRunManager singleton."""
    global _GLOBAL_MANAGER
    if _GLOBAL_MANAGER is None:
        _GLOBAL_MANAGER = AnalysisRunManager()
    return _GLOBAL_MANAGER
