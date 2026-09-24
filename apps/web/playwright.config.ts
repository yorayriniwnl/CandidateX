import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './tests',
  testIgnore: '**/production-demo.spec.ts',
  fullyParallel: false,
  workers: 1,
  use: { baseURL: 'http://127.0.0.1:3108', trace: 'retain-on-failure' },
  webServer: [
    { command: 'python -m uvicorn cci.main:app --app-dir ../../services/backend/src --host 127.0.0.1 --port 8017', url: 'http://127.0.0.1:8017/health', reuseExistingServer: false, timeout: 60000 },
    { command: 'pnpm exec next dev --hostname 127.0.0.1 --port 3108', url: 'http://127.0.0.1:3108', env: { CCI_API_URL: 'http://127.0.0.1:8017' }, reuseExistingServer: false, timeout: 60000 },
  ],
});
