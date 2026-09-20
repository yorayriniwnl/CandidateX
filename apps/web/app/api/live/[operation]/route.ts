import type { NextRequest } from 'next/server';

export const maxDuration = 60;

export async function POST(request: NextRequest, context: { params: Promise<{ operation: string }> }) {
  const { operation } = await context.params;
  if (!['intake', 'analyze'].includes(operation)) return Response.json({ detail: 'Unknown operation.' }, { status: 404 });
  const base = process.env.CCI_API_URL || (process.env.VERCEL ? '' : 'http://127.0.0.1:8000');
  if (!base) return Response.json({ detail: 'Live analysis backend is not configured.' }, { status: 503 });
  const limit = operation === 'intake' ? 3 * 1024 * 1024 : 128 * 1024;
  const reader = request.body?.getReader();
  if (!reader) return Response.json({ detail: 'Request body is required.' }, { status: 400 });
  const chunks: Uint8Array[] = [];
  let size = 0;
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      size += value.length;
      if (size > limit) {
        await reader.cancel();
        return Response.json({ detail: 'Request exceeds the upload limit.' }, { status: 413 });
      }
      chunks.push(value);
    }
    const body = new Uint8Array(size);
    let offset = 0;
    for (const chunk of chunks) { body.set(chunk, offset); offset += chunk.length; }
    const upstream = await fetch(`${base.replace(/\/$/, '')}/api/v1/live/${operation}`, {
      method: 'POST', body,
      headers: { 'Content-Type': operation === 'intake' ? 'application/octet-stream' : 'application/json',
        'X-Filename': request.headers.get('X-Filename') || 'resume.pdf' },
      cache: 'no-store', signal: AbortSignal.timeout(55000),
    });
    if (!upstream.headers.get('content-type')?.includes('application/json')) {
      return Response.json({ detail: 'The live backend returned an unexpected response. Please retry.' }, { status: 502 });
    }
    return new Response(await upstream.text(), { status: upstream.status,
      headers: { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' } });
  } catch {
    return Response.json({ detail: 'Live analysis could not reach the backend or timed out. Please retry. No result was substituted.' }, { status: 503 });
  }
}
