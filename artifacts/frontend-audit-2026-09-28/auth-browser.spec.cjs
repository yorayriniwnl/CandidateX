const { test, expect } = require('../../apps/web/node_modules/@playwright/test');
function log(probe, data) { console.log('AUDIT ' + JSON.stringify({ probe, ...data })); }

test('session endpoint accepts unsigned cookies over HTTP', async ({ request }) => {
  const empty = await request.get('/api/auth/session');
  expect((await empty.json()).user).toBeNull();
  for (const [probe, cookie] of [
    ['http_forged_auth', 'cx_auth=audit%40example.invalid'],
    ['http_forged_session', `cx_session=${encodeURIComponent(JSON.stringify({ email: 'audit@example.invalid', role: 'evaluator', loginTime: 1 }))}`],
  ]) {
    const response = await request.get('/api/auth/session', { headers: { Cookie: cookie } });
    const body = await response.json();
    expect(body.user.email).toBe('audit@example.invalid');
    log(probe, { status: response.status(), body });
  }
});

test('login accepts an external redirect destination', async ({ page }) => {
  await page.route('**/api/**', route => route.fulfill({ status: 503, json: { detail: 'Audit interception' } }));
  await page.route('https://audit-redirect.invalid/**', route => route.fulfill({
    contentType: 'text/html', body: '<h1>Locally intercepted audit destination</h1>',
  }));
  await page.goto('/login?redirect=' + encodeURIComponent('https://audit-redirect.invalid/landing'));
  await page.getByRole('button', { name: 'Use authorized demo credentials', exact: true }).click();
  await page.getByRole('button', { name: 'Sign in to workspace', exact: true }).click();
  await expect(page).toHaveURL('https://audit-redirect.invalid/landing');
  log('login_external_redirect', { finalURL: page.url(), externalRequestIntercepted: true });
});

test('password recovery makes no application request', async ({ page }) => {
  const requests = [];
  await page.route('**/api/**', route => route.fulfill({ status: 503, json: { detail: 'Audit interception' } }));
  await page.goto('/login');
  await page.getByRole('button', { name: 'Forgot password?', exact: true }).click();
  await page.locator('#forgot-email').fill('audit@example.invalid');
  page.on('request', request => {
    const url = new URL(request.url());
    // Antivirus injects its own POSTs in this browser; distinguish app requests.
    if (url.hostname === '127.0.0.1' || url.hostname === 'localhost') {
      if (request.method() !== 'GET' || url.pathname.startsWith('/api/')) {
        requests.push({ method: request.method(), path: url.pathname });
      }
    }
  });
  await page.getByRole('button', { name: 'Send reset link', exact: true }).click();
  await expect(page.getByText(/we have dispatched a secure recovery token/)).toBeVisible();
  await page.keyboard.press('Escape');
  expect(requests).toEqual([]);
  log('password_recovery_app_requests', { requests, dialogRemainsAfterEscape: await page.getByRole('dialog').isVisible() });
});
