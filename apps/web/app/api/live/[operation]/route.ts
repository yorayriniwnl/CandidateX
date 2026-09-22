import type { NextRequest } from 'next/server';

export const maxDuration = 60;

const REQUEST_ID_PATTERN = /^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$/;

function errorResponse(detail: string, status: number, requestId: string) {
  return Response.json({ detail }, {
    status,
    headers: { 'Cache-Control': 'no-store', 'X-Request-ID': requestId },
  });
}

export async function POST(request: NextRequest, context: { params: Promise<{ operation: string }> }) {
  const suppliedRequestId = request.headers.get('X-Request-ID') || '';
  const requestId = REQUEST_ID_PATTERN.test(suppliedRequestId) ? suppliedRequestId : crypto.randomUUID();
  const { operation } = await context.params;
  if (!['intake', 'analyze'].includes(operation)) return errorResponse('Unknown operation.', 404, requestId);
  const base = process.env.CCI_API_URL || (process.env.VERCEL ? '' : 'http://127.0.0.1:8000');
  if (!base) return errorResponse('Live analysis backend is not configured.', 503, requestId);
  const limit = operation === 'intake' ? 3 * 1024 * 1024 : 512 * 1024;
  const reader = request.body?.getReader();
  if (!reader) return errorResponse('Request body is required.', 400, requestId);
  const chunks: Uint8Array[] = [];
  let size = 0;
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      size += value.length;
      if (size > limit) {
        await reader.cancel();
        return errorResponse('Request exceeds the upload limit.', 413, requestId);
      }
      chunks.push(value);
    }
    const body = new Uint8Array(size);
    let offset = 0;
    for (const chunk of chunks) { body.set(chunk, offset); offset += chunk.length; }
    const upstream = await fetch(`${base.replace(/\/$/, '')}/api/v1/live/${operation}`, {
      method: 'POST', body,
      headers: { 'Content-Type': operation === 'intake' ? 'application/octet-stream' : 'application/json',
        'X-Filename': request.headers.get('X-Filename') || 'resume.pdf',
        'X-Request-ID': requestId },
      cache: 'no-store', signal: AbortSignal.timeout(55000),
    });
    if (!upstream.headers.get('content-type')?.includes('application/json')) {
      return errorResponse('The live backend returned an unexpected response. Please retry.', 502, requestId);
    }
    return new Response(await upstream.text(), { status: upstream.status,
      headers: { 'Content-Type': 'application/json', 'Cache-Control': 'no-store',
        'X-Request-ID': upstream.headers.get('X-Request-ID') || requestId } });
  } catch {
    return errorResponse('Live analysis could not reach the backend or timed out. Please retry. No result was substituted.', 503, requestId);
  }
}
