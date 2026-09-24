"""Stateless live resume workflow. No publicly retrievable candidate records are created."""
import json
from urllib.parse import unquote
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import ValidationError
from starlette.concurrency import run_in_threadpool

from cci.config import settings
from cci.domain.enums import AnalysisRunState
from cci.live.contracts import (
    MAX_UPLOAD,
    MAX_ANALYSIS_REQUEST_BYTES,
    LiveAnalysisRequest,
    ResumeIntake,
)
from cci.live.intake import parse_resume
from cci.live.service import analyze_resume
from cci.security.abuse import (
    ConcurrencyLimitExceeded,
    InvalidTokenError,
    RateLimitExceeded,
    get_abuse_controls,
)

router = APIRouter(prefix='/api/v1/live', tags=['Live Resume Analysis'])


def extract_client_info(request: Request) -> tuple[str, str | None]:
    """Extracts client IP and optional analysis token from headers."""
    client_ip = request.client.host if request.client else "127.0.0.1"
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        client_ip = forwarded.split(",")[0].strip()

    token = request.headers.get("X-Analysis-Token")
    if not token:
        auth = request.headers.get("Authorization", "")
        if auth.lower().startswith("bearer "):
            token = auth[7:].strip()
    return client_ip, token or None


async def limited_body(request, limit):
    chunks, size = [], 0
    async for chunk in request.stream():
        size += len(chunk)
        if size > limit:
            raise HTTPException(413, 'Request is too large.')
        chunks.append(chunk)
    return b''.join(chunks)


@router.post('/tokens')
async def create_analysis_token(request: Request, response: Response):
    """Issues a cryptographically signed HMAC-SHA256 analysis token (Fix 28)."""
    response.headers['Cache-Control'] = 'no-store'
    client_ip, _ = extract_client_info(request)
    body = await limited_body(request, 16 * 1024)
    data = json.loads(body) if body else {}
    tier = data.get("tier", "default")
    subject = data.get("subject", client_ip)
    expires_in = min(86400, max(60, int(data.get("expires_in_seconds", 3600))))

    token_str = get_abuse_controls().token_manager.issue_token(
        subject=subject,
        expires_in_seconds=expires_in,
        tier=tier,
    )
    return {
        "analysis_token": token_str,
        "token_type": "Bearer",
        "expires_in_seconds": expires_in,
        "tier": tier,
    }


@router.post('/intake')
async def intake(request: Request, response: Response):
    response.headers['Cache-Control'] = 'no-store'
    client_ip, token = extract_client_info(request)

    # Abuse Controls: Token check and sliding-window rate limit
    try:
        get_abuse_controls().verify_request_access(
            client_ip=client_ip,
            token=token,
            bucket="intake",
            limit=settings.RATE_LIMIT_INTAKE_PER_MINUTE,
        )
    except RateLimitExceeded as exc:
        retry_str = str(int(exc.retry_after))
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded for resume intake. Retry after {retry_str} seconds.",
            headers={"Retry-After": retry_str},
        ) from exc
    except InvalidTokenError as exc:
        raise HTTPException(401, str(exc)) from exc

    filename = unquote(request.headers.get('X-Filename', 'resume.pdf'))
    if not filename.lower().endswith(('.pdf', '.docx')):
        raise HTTPException(415, 'Upload a digital PDF or DOCX resume.')
    body = await limited_body(request, MAX_UPLOAD)
    try:
        intake_res = await run_in_threadpool(parse_resume, body, filename)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(422, 'The document could not be read. Upload a valid, unlocked PDF or DOCX.') from exc

    # Persist safe normalized analysis data into durable analysis run
    from cci.live.runner import get_analysis_run_manager
    manager = get_analysis_run_manager()
    run = manager.create_run(
        input_payload={
            "intake": intake_res.model_dump(),
            "candidate_id": str(intake_res.candidate_id),
            "manifest": intake_res.manifest.model_dump(),
        },
        analysis_run_id=intake_res.analysis_run_id,
        auto_start=False,
        client_ip=client_ip,
    )
    # Pre-cache parsed resume stage and extracted claims stage
    run.stage_data[AnalysisRunState.PARSING_RESUME.value] = {
        "candidate_id": str(intake_res.candidate_id),
        "document_sha256": intake_res.document_sha256,
        "status": "parsed",
    }
    run.stage_data[AnalysisRunState.EXTRACTING_CLAIMS.value] = {
        "claimed_skills": list(intake_res.manifest.claimed_skills),
        "project_claims": [
            c.model_dump() if hasattr(c, "model_dump") else c
            for c in intake_res.manifest.project_claims
        ],
        "experience_claims": [
            e.model_dump() if hasattr(e, "model_dump") else e
            for e in intake_res.manifest.experience_claims
        ],
    }

    return intake_res


@router.post('/analyze')
async def analyze(request: Request, response: Response):
    response.headers['Cache-Control'] = 'no-store'
    client_ip, token = extract_client_info(request)

    # Abuse Controls: Token check and sliding-window rate limit
    try:
        get_abuse_controls().verify_request_access(
            client_ip=client_ip,
            token=token,
            bucket="analyze",
            limit=settings.RATE_LIMIT_RUNS_PER_MINUTE,
        )
    except RateLimitExceeded as exc:
        retry_str = str(int(exc.retry_after))
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded for analysis. Retry after {retry_str} seconds.",
            headers={"Retry-After": retry_str},
        ) from exc
    except InvalidTokenError as exc:
        raise HTTPException(401, str(exc)) from exc

    # Abuse Controls: Concurrency cap
    try:
        get_abuse_controls().acquire_run_slot(client_ip)
    except ConcurrencyLimitExceeded as exc:
        raise HTTPException(
            status_code=429,
            detail=str(exc),
            headers={"Retry-After": "5"},
        ) from exc

    try:
        body = await limited_body(request, MAX_ANALYSIS_REQUEST_BYTES)
        try:
            data = json.loads(body)
        except Exception as exc:
            raise HTTPException(422, 'Malformed JSON payload.') from exc

        run_id_str = data.get("analysis_run_id")
        if run_id_str and "intake" not in data:
            try:
                run_uuid = UUID(str(run_id_str))
            except ValueError:
                raise HTTPException(422, 'Invalid analysis_run_id UUID format.')
            from cci.live.runner import get_analysis_run_manager
            manager = get_analysis_run_manager()
            stored_run = manager.get_run(run_uuid)
            if not stored_run:
                raise HTTPException(404, f'Analysis run {run_id_str} not found.')
            stored_intake = stored_run.input_payload.get("intake")
            if not stored_intake:
                raise HTTPException(422, f'Analysis run {run_id_str} has no intake data.')
            data["intake"] = stored_intake

        if "user_reviewed_urls" in data and "external_urls" not in data:
            data["external_urls"] = data["user_reviewed_urls"]
        if "jd_edits" in data and "jd_text" not in data:
            data["jd_text"] = data["jd_edits"]

        try:
            payload = LiveAnalysisRequest.model_validate(data)
        except (ValidationError, ValueError) as exc:
            raise HTTPException(422, 'Invalid analysis input. Check the GitHub URLs, identity, and resume fields.') from exc
        try:
            return await run_in_threadpool(analyze_resume, payload)
        except RuntimeError as exc:
            raise HTTPException(500, 'The analysis failed. No sample result was substituted.') from exc
    finally:
        get_abuse_controls().release_run_slot(client_ip)


@router.post('/runs', status_code=202)
async def create_analysis_run(request: Request, response: Response):
    """Creates or starts a durable, asynchronous AnalysisRun (Fix 26, 27, 28)."""
    response.headers['Cache-Control'] = 'no-store'
    client_ip, token = extract_client_info(request)

    # Abuse Controls: Token check and rate limit
    try:
        get_abuse_controls().verify_request_access(
            client_ip=client_ip,
            token=token,
            bucket="runs",
            limit=settings.RATE_LIMIT_RUNS_PER_MINUTE,
        )
    except RateLimitExceeded as exc:
        retry_str = str(int(exc.retry_after))
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded for analysis runs. Retry after {retry_str} seconds.",
            headers={"Retry-After": retry_str},
        ) from exc
    except InvalidTokenError as exc:
        raise HTTPException(401, str(exc)) from exc

    # Abuse Controls: Concurrency cap & budget tracker
    try:
        budget_tracker = get_abuse_controls().acquire_run_slot(client_ip)
    except ConcurrencyLimitExceeded as exc:
        raise HTTPException(
            status_code=429,
            detail=str(exc),
            headers={"Retry-After": "5"},
        ) from exc

    try:
        body = await limited_body(request, MAX_ANALYSIS_REQUEST_BYTES)
        try:
            data = json.loads(body)
        except Exception as exc:
            raise HTTPException(422, 'Malformed JSON payload.') from exc

        from cci.live.runner import get_analysis_run_manager
        manager = get_analysis_run_manager()

        run_id_str = data.get("analysis_run_id")
        if run_id_str:
            try:
                run_uuid = UUID(str(run_id_str))
            except ValueError:
                raise HTTPException(422, 'Invalid analysis_run_id UUID format.')

            run = manager.get_run(run_uuid)
            if not run:
                if "intake" not in data:
                    raise HTTPException(404, f'Analysis run {run_id_str} not found.')
                run = manager.create_run(
                    data,
                    analysis_run_id=run_uuid,
                    auto_start=True,
                    client_ip=client_ip,
                    budget_tracker=budget_tracker,
                )
            else:
                run = manager.start_run(
                    run_uuid,
                    update_payload=data,
                    client_ip=client_ip,
                    budget_tracker=budget_tracker,
                )
        else:
            if "intake" not in data:
                raise HTTPException(422, 'Either analysis_run_id or intake must be provided.')
            run = manager.create_run(
                data,
                auto_start=True,
                client_ip=client_ip,
                budget_tracker=budget_tracker,
            )

        return {
            "analysis_run_id": str(run.analysis_run_id),
            "state": "QUEUED",
            "current_stage": "QUEUED",
            "progress_percent": run.progress_percent,
            "poll_url": f"/api/v1/live/runs/{run.analysis_run_id}",
        }
    except Exception:
        # If run creation failed before background executor took over, release slot
        get_abuse_controls().release_run_slot(client_ip)
        raise


@router.get('/runs/{run_id}')
async def get_analysis_run_status(run_id: str, request: Request, response: Response):
    """Polls progress, stage status, and final dossier artifacts of an AnalysisRun."""
    response.headers['Cache-Control'] = 'no-store'
    client_ip, _ = extract_client_info(request)

    # Abuse Controls: Polling rate limit
    try:
        get_abuse_controls().verify_request_access(
            client_ip=client_ip,
            bucket="poll",
            limit=120,
        )
    except RateLimitExceeded as exc:
        retry_str = str(int(exc.retry_after))
        raise HTTPException(
            status_code=429,
            detail=f"Polling rate limit exceeded. Retry after {retry_str} seconds.",
            headers={"Retry-After": retry_str},
        ) from exc

    from cci.live.runner import get_analysis_run_manager
    manager = get_analysis_run_manager()
    run = manager.get_run(run_id)
    if not run:
        raise HTTPException(404, f'Analysis run {run_id} not found.')
    return run.to_status_dict()


@router.post('/runs/{run_id}/resume')
async def resume_analysis_run(run_id: str, response: Response):
    """Resumes an interrupted or failed AnalysisRun from its last incomplete stage."""
    response.headers['Cache-Control'] = 'no-store'
    from cci.live.runner import get_analysis_run_manager
    manager = get_analysis_run_manager()
    run = manager.resume_run(run_id)
    if not run:
        raise HTTPException(404, f'Analysis run {run_id} not found.')
    return run.to_status_dict()


@router.post('/runs/{run_id}/cancel')
async def cancel_analysis_run(run_id: str, response: Response):
    """Cancels an active or queued AnalysisRun."""
    response.headers['Cache-Control'] = 'no-store'
    from cci.live.runner import get_analysis_run_manager
    manager = get_analysis_run_manager()
    run = manager.cancel_run(run_id)
    if not run:
        raise HTTPException(404, f'Analysis run {run_id} not found.')
    return run.to_status_dict()


@router.get('/runs/{run_id}/telemetry')
async def get_analysis_run_telemetry(run_id: str, response: Response):
    """Returns execution telemetry, timing metrics, and structured observability for an AnalysisRun."""
    response.headers['Cache-Control'] = 'no-store'
    from cci.live.runner import get_analysis_run_manager
    manager = get_analysis_run_manager()
    run = manager.get_run(run_id)
    if not run:
        raise HTTPException(404, f'Analysis run {run_id} not found.')
    if not run.telemetry:
        raise HTTPException(404, f'Telemetry not recorded for run {run_id}.')
    return run.telemetry.to_dict()

