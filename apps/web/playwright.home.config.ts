import { defineConfig } from '@playwright/test';

// Homepage checks need no candidate data or backend service.
export default defineConfig({
  testDir: './tests',
  testMatch: /home.*\.spec\.ts/,
  workers: 1,
  timeout: 45000,
  expect: { timeout: 10000 },
  outputDir: '../../artifacts/home-redesign/test-results',
  use: {
    baseURL: 'http://127.0.0.1:3000',
    viewport: { width: 1440, height: 1000 },
    channel: 'chromium',
    trace: 'retain-on-failure',
  },
  webServer: {
    command: 'pnpm exec next dev --hostname 127.0.0.1 --port 3000',
    url: 'http://127.0.0.1:3000',
    reuseExistingServer: true,
    timeout: 60000,
  },
});
