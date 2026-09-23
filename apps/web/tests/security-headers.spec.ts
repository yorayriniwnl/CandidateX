import { expect, test } from '@playwright/test';

test('sets browser security headers on product and legacy workspace pages', async ({ request }) => {
  for (const path of ['/analyze', '/hr', '/workspace']) {
    const response = await request.get(path);
    expect(response.status(), path).toBe(200);

    const headers = response.headers();
    expect(headers['x-content-type-options'], path).toBe('nosniff');
    expect(headers['x-frame-options'], path).toBe('DENY');
    expect(headers['referrer-policy'], path).toBe('strict-origin-when-cross-origin');
    expect(headers['permissions-policy'], path).toBe(
      'camera=(), microphone=(), geolocation=(), browsing-topics=()',
    );
  }
});
