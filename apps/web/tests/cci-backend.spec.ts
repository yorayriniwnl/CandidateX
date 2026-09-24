import { expect, test } from '@playwright/test';
import { POST as postDemo } from '../app/api/demo/route';
import { POST as postLive } from '../app/api/live/[operation]/route';
import { isSyntheticOnlyDeployment, resolveCciBackendUrl } from '../lib/server/cci-backend';

const ENV_KEYS = ['NODE_ENV', 'VERCEL', 'CCI_API_URL'] as const;

async function withProductionEnvironment(
  backendUrl: string | undefined,
  action: () => Promise<void>,
) {
  const originalValues = Object.fromEntries(ENV_KEYS.map((key) => [key, process.env[key]]));
  const originalFetch = globalThis.fetch;
  Reflect.set(process.env, 'NODE_ENV', 'production');
  Reflect.set(process.env, 'VERCEL', '1');
  if (backendUrl === undefined) Reflect.deleteProperty(process.env, 'CCI_API_URL');
  else Reflect.set(process.env, 'CCI_API_URL', backendUrl);

  try {
    await action();
  } finally {
    for (const key of ENV_KEYS) {
      const value = originalValues[key];
      if (value === undefined) Reflect.deleteProperty(process.env, key);
      else Reflect.set(process.env, key, value);
    }
    globalThis.fetch = originalFetch;
  }
}

test('detects production and Vercel deployments as synthetic-only', () => {
  expect(isSyntheticOnlyDeployment({ NODE_ENV: 'production' })).toBe(true);
  expect(isSyntheticOnlyDeployment({ NODE_ENV: 'development', VERCEL: '1' })).toBe(true);
  expect(isSyntheticOnlyDeployment({ NODE_ENV: 'development', VERCEL: '' })).toBe(false);
});

test('does not invent a localhost backend for production or Vercel', () => {
  expect(resolveCciBackendUrl({ NODE_ENV: 'production' })).toBeNull();
  expect(resolveCciBackendUrl({ NODE_ENV: 'development', VERCEL: '1' })).toBeNull();
});

test('keeps the loopback fallback for local development only', () => {
  expect(resolveCciBackendUrl({ NODE_ENV: 'development' })).toBe('http://127.0.0.1:8000');
  expect(resolveCciBackendUrl({ NODE_ENV: 'production', CCI_API_URL: 'https://api.example.test/' }))
    .toBe('https://api.example.test');
});

test('production demo bridge does not fetch when its backend is unconfigured', async () => {
  await withProductionEnvironment(undefined, async () => {
    let fetchCalled = false;
    globalThis.fetch = async () => {
      fetchCalled = true;
      return Response.json({ ok: true });
    };

    const response = await postDemo(new Request('http://localhost/api/demo', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ operation: 'run', payload: { scenario: 'consistent' } }),
    }));

    expect(response.status).toBe(503);
    expect(fetchCalled).toBe(false);
  });
});

test('production live bridge rejects before reading or forwarding the request body', async () => {
  await withProductionEnvironment('https://api.example.test', async () => {
    let fetchCalled = false;
    let bodyRead = false;
    globalThis.fetch = async () => {
      fetchCalled = true;
      return Response.json({ detail: 'Upstream reached' }, { status: 404 });
    };

    const request = new Request('http://localhost/api/live/analyze', {
      method: 'POST',
      body: '{"resume_text":"must not be read"}',
    });
    const body = request.body;
    Object.defineProperty(request, 'body', {
      get() {
        bodyRead = true;
        return body;
      },
    });
    const response = await postLive(
      request as Parameters<typeof postLive>[0],
      { params: Promise.resolve({ operation: 'analyze' }) },
    );

    expect(response.status).toBe(404);
    expect(response.headers.get('Cache-Control')).toBe('no-store');
    expect(bodyRead).toBe(false);
    expect(fetchCalled).toBe(false);
  });
});
