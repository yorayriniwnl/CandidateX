const path = require('node:path');
const { defineConfig } = require('../../apps/web/node_modules/@playwright/test');
const webDir = path.resolve(__dirname, '../../apps/web');
module.exports = defineConfig({
  testDir: __dirname, testMatch: 'auth-browser.spec.cjs', workers: 1, timeout: 30000,
  expect: { timeout: 10000 }, outputDir: path.join(__dirname, 'auth-browser-results'),
  reporter: [['line'], ['json', { outputFile: path.join(__dirname, 'auth-browser-results.json') }]],
  use: { baseURL: 'http://127.0.0.1:3178', channel: 'chromium', reducedMotion: 'reduce' },
  webServer: {
    command: 'pnpm exec next start --hostname 127.0.0.1 --port 3178',
    cwd: process.env.CANDIDATEX_AUDIT_PREVIEW_DIR || webDir,
    url: 'http://127.0.0.1:3178', reuseExistingServer: false, timeout: 60000,
    env: { CCI_API_URL: 'http://127.0.0.1:65530' },
  },
});
