"""Stateless live resume workflow. No publicly retrievable candidate records are created."""
import json
from urllib.parse import unquote

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import ValidationError
from starlette.concurrency import run_in_threadpool

from cci.live.contracts import MAX_UPLOAD, LiveAnalysisRequest
from cci.live.intake import parse_resume
from cci.live.service import analyze_resume

router = APIRouter(prefix='/api/v1/live', tags=['Live Resume Analysis'])


async def limited_body(request, limit):
    chunks, size = [], 0
    async for chunk in request.stream():
        size += len(chunk)
        if size > limit:
            raise HTTPException(413, 'Request is too large.')
        chunks.append(chunk)
    return b''.join(chunks)


@router.post('/intake')
async def intake(request: Request, response: Response):
    response.headers['Cache-Control'] = 'no-store'
    filename = unquote(request.headers.get('X-Filename', 'resume.pdf'))
    if not filename.lower().endswith(('.pdf', '.docx')):
        raise HTTPException(415, 'Upload a digital PDF or DOCX resume.')
    body = await limited_body(request, MAX_UPLOAD)
    try:
        return await run_in_threadpool(parse_resume, body, filename)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(422, 'The document could not be read. Upload a valid, unlocked PDF or DOCX.') from exc


@router.post('/analyze')
async def analyze(request: Request, response: Response):
    response.headers['Cache-Control'] = 'no-store'
    body = await limited_body(request, 128 * 1024)
    try:
        payload = LiveAnalysisRequest.model_validate_json(body)
    except (ValidationError, ValueError) as exc:
        raise HTTPException(422, 'Invalid analysis input. Check the GitHub URLs, identity, and resume fields.') from exc
    try:
        return await run_in_threadpool(analyze_resume, payload)
    except RuntimeError as exc:
        raise HTTPException(500, 'The analysis failed. No sample result was substituted.') from exc
