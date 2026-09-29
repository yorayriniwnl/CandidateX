import type { NextRequest } from 'next/server';
import { verifySession } from '../../../../lib/session';

export const maxDuration = 14400; // 4 hours — give the backend full leverage of time.

export async function POST(request: NextRequest, context: { params: Promise<{ operation: string }> }) {
  const sessionCookie = request.cookies.get('cx_session')?.value;
  if (!sessionCookie || !verifySession(sessionCookie)) {
    return Response.json({ detail: 'Unauthorized.' }, { status: 401 });
  }

  const { operation } = await context.params;
  if (!['intake', 'analyze', 'parse-jd', 'fetch-link'].includes(operation)) return Response.json({ detail: 'Unknown operation.' }, { status: 404 });
  const base = process.env.CCI_API_URL || (process.env.VERCEL ? '' : 'http://127.0.0.1:8000');
  if (!base) return Response.json({ detail: 'Live analysis backend is not configured.' }, { status: 503 });
  const isFileUpload = operation === 'intake' || operation === 'parse-jd';
  const limit = isFileUpload ? 3 * 1024 * 1024 : 1024 * 1024;
  const contentLength = Number(request.headers.get('content-length') || 0);
  if (contentLength > limit) {
    return Response.json({ detail: 'Request exceeds the upload limit.' }, { status: 413 });
  }

  try {
    const body = await request.arrayBuffer();
    if (body.byteLength > limit) {
      return Response.json({ detail: 'Request exceeds the upload limit.' }, { status: 413 });
    }
    const upstream = await fetch(`${base.replace(/\/$/, '')}/api/v1/live/${operation}`, {
      method: 'POST', body,
      headers: { 'Content-Type': isFileUpload ? 'application/octet-stream' : 'application/json',
        'X-Filename': request.headers.get('X-Filename') || (operation === 'parse-jd' ? 'job_description.pdf' : 'resume.pdf') },
      cache: 'no-store', // No AbortSignal timeout — let the backend take as long as it needs.
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
