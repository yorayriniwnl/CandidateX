/** Same-origin bridge. Destinations are fixed; candidate URLs are never fetched. */
import { resolveCciBackendUrl } from '../../../lib/server/cci-backend';

export async function POST(request: Request) {
  let body;
  try { body = await request.json(); }
  catch { return Response.json({ detail: 'Invalid JSON request.' }, { status: 400 }); }
  if (!body || !['run', 'rescore'].includes(body.operation)) {
    return Response.json({ detail: 'Unknown demonstration operation.' }, { status: 400 });
  }
  const base = resolveCciBackendUrl();
  if (!base) {
    return Response.json(
      { detail: 'Synthetic demo backend is not configured.' },
      { status: 503, headers: { 'Cache-Control': 'no-store' } },
    );
  }
  try {
    const response = await fetch(`${base}/api/v1/synthetic-demo/${body.operation}`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body.payload), cache: 'no-store', signal: AbortSignal.timeout(30000),
    });
    return new Response(await response.text(), {
      status: response.status, headers: { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' },
    });
  } catch {
    return Response.json({ detail: 'Backend unavailable. Start the CCI backend and try again. No sample result substituted.' }, { status: 503 });
  }
}
