import type { NextRequest } from 'next/server';

/**
 * Same-origin bridge with rate-limiting and payload validation.
 * Destinations are fixed; candidate URLs are never fetched.
 */

// Simple in-memory rate limiting map for DoS protection: IP -> [timestamps]
const RATE_LIMIT_WINDOW_MS = 60 * 1000; // 1 minute
const MAX_REQUESTS_PER_WINDOW = 30; // Max 30 demo evaluations per minute per IP
const requestHistory = new Map<string, number[]>();

function checkRateLimit(ip: string): boolean {
  const now = Date.now();
  const timestamps = requestHistory.get(ip) || [];
  const validTimestamps = timestamps.filter(t => now - t < RATE_LIMIT_WINDOW_MS);
  
  if (validTimestamps.length >= MAX_REQUESTS_PER_WINDOW) {
    requestHistory.set(ip, validTimestamps);
    return false;
  }
  
  validTimestamps.push(now);
  requestHistory.set(ip, validTimestamps);
  
  // Cleanup occasionally
  if (requestHistory.size > 1000) {
    for (const [key, times] of requestHistory.entries()) {
      if (times.every(t => now - t >= RATE_LIMIT_WINDOW_MS)) {
        requestHistory.delete(key);
      }
    }
  }
  
  return true;
}

export async function POST(request: NextRequest) {
  // 1. Enforce same-origin / Sec-Fetch-Site check if present
  const secFetchSite = request.headers.get('sec-fetch-site');
  if (secFetchSite && secFetchSite !== 'same-origin' && secFetchSite !== 'none') {
    return Response.json({ detail: 'Cross-origin requests are forbidden.' }, { status: 403 });
  }

  // 2. Rate Limiting per IP
  const clientIp = request.headers.get('x-forwarded-for')?.split(',')[0].trim() || '127.0.0.1';
  if (!checkRateLimit(clientIp)) {
    return Response.json(
      { detail: 'Rate limit exceeded. Too many demo requests from this client. Please wait a moment.' },
      { status: 429, headers: { 'Retry-After': '60' } }
    );
  }

  // 3. Size and JSON Validation
  let body;
  try {
    const text = await request.text();
    if (text.length > 64 * 1024) { // 64 KB limit for demo payload
      return Response.json({ detail: 'Request body exceeds 64KB limit.' }, { status: 413 });
    }
    body = JSON.parse(text);
  } catch {
    return Response.json({ detail: 'Invalid JSON request.' }, { status: 400 });
  }

  if (!body || !['run', 'rescore'].includes(body.operation)) {
    return Response.json({ detail: 'Unknown demonstration operation.' }, { status: 400 });
  }

  const base = (process.env.CCI_API_URL || 'http://127.0.0.1:8000').replace(/\/$/, '');
  try {
    const response = await fetch(`${base}/api/v1/research-demo/${body.operation}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body.payload),
      cache: 'no-store',
      signal: AbortSignal.timeout(30000),
    });
    return new Response(await response.text(), {
      status: response.status,
      headers: {
        'Content-Type': 'application/json',
        'Cache-Control': 'no-store',
        'X-RateLimit-Limit': String(MAX_REQUESTS_PER_WINDOW),
      },
    });
  } catch {
    return Response.json(
      { detail: 'Backend unavailable. Start the CCI backend and try again. No sample result substituted.' },
      { status: 503 }
    );
  }
}
