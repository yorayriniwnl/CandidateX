// Read-only probes: application route handlers, real NextRequest/NextResponse,
// synthetic OAuth credentials, and a fetch stub that cannot contact a provider.
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { createRequire } = require('node:module');
const assert = require('node:assert/strict');
const repo = path.resolve(__dirname, '../..');
const webRequire = createRequire(path.join(repo, 'apps/web/package.json'));
const ts = webRequire('typescript');
const { NextRequest } = webRequire('next/server');
const base = 'http://127.0.0.1:3178';
const results = [];

function loadRoute(relativePath, fetchStub) {
  const filename = path.join(repo, 'apps/web', relativePath);
  const output = ts.transpileModule(fs.readFileSync(filename, 'utf8'), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
    fileName: filename,
  }).outputText;
  const mod = { exports: {} };
  vm.runInNewContext(output, {
    module: mod, exports: mod.exports, require: webRequire,
    Buffer, URL, URLSearchParams, console,
    process: { env: {
      NEXTAUTH_URL: base,
      GITHUB_CLIENT_ID: 'audit-only-client', GITHUB_CLIENT_SECRET: 'audit-only-secret',
    } },
    fetch: fetchStub || (() => { throw new Error('Unexpected fetch'); }),
  }, { filename });
  return mod.exports;
}

async function callbackProbe(name, state, cookie) {
  const calls = [];
  const route = loadRoute('app/api/auth/callback/[provider]/route.ts', async url => {
    calls.push(String(url));
    if (url === 'https://github.com/login/oauth/access_token') {
      return Response.json({ access_token: 'audit-only-token' });
    }
    if (url === 'https://api.github.com/user') {
      return Response.json({ email: 'audit@example.invalid', name: 'Audit User', login: 'audit' });
    }
    throw new Error(`Unmocked URL: ${url}`);
  });
  const url = new URL('/api/auth/callback/github', base);
  if (name !== 'control_missing_code') url.searchParams.set('code', 'audit-only-code');
  if (state !== undefined) url.searchParams.set('state', state);
  const response = await route.GET(new NextRequest(url, {
    headers: cookie === undefined ? {} : { cookie: `cx_oauth_state=${encodeURIComponent(cookie)}` },
  }), { params: Promise.resolve({ provider: 'github' }) });
  const item = {
    probe: name, status: response.status, location: response.headers.get('location'),
    issuedSession: Boolean(response.cookies.get('cx_session')), mockedProviderCalls: calls.length,
  };
  results.push(item);
  return item;
}

async function main() {
  const internalState = Buffer.from(JSON.stringify({ token: 'audit', redirect: '/workspace' })).toString('base64url');
  const externalState = Buffer.from(JSON.stringify({ token: 'audit', redirect: '//audit-redirect.invalid/landing' })).toString('base64url');
  assert.equal((await callbackProbe('control_missing_code')).issuedSession, false);
  assert.equal((await callbackProbe('control_valid_state', internalState, internalState)).issuedSession, true);
  for (const [name, state, cookie] of [
    ['oauth_missing_state'],
    ['oauth_missing_state_cookie', internalState],
    ['oauth_mismatched_state', internalState, 'different-state'],
    ['oauth_malformed_matching_state', 'not-json', 'not-json'],
  ]) assert.equal((await callbackProbe(name, state, cookie)).issuedSession, true);
  const external = await callbackProbe('oauth_external_redirect', externalState, externalState);
  assert.equal(external.location, 'http://audit-redirect.invalid/landing');

  const sessionRoute = loadRoute('app/api/auth/session/route.ts');
  for (const [name, cookie] of [
    ['control_no_session', undefined],
    ['forged_auth_cookie', 'cx_auth=audit%40example.invalid'],
    ['forged_session_cookie', `cx_session=${encodeURIComponent(JSON.stringify({ email: 'audit@example.invalid', role: 'evaluator', loginTime: 1 }))}`],
  ]) {
    const response = await sessionRoute.GET(new NextRequest(`${base}/api/auth/session`, {
      headers: cookie ? { cookie } : {},
    }));
    const body = await response.json();
    if (cookie) assert.equal(body.user.email, 'audit@example.invalid');
    else assert.equal(body.user, null);
    results.push({ probe: name, status: response.status, body });
  }
  fs.writeFileSync(path.join(__dirname, 'auth-results.json'), JSON.stringify({
    testedAt: new Date().toISOString(), mode: 'Current source; mocked OAuth transport; no external requests', results,
  }, null, 2));
  results.forEach(result => console.log('AUDIT ' + JSON.stringify(result)));
}
main().catch(error => { console.error(error); process.exitCode = 1; });
