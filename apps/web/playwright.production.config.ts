import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './tests',
  testMatch: '**/production-demo.spec.ts',
  fullyParallel: false,
  workers: 1,
  use: { baseURL: 'http://127.0.0.1:3109', trace: 'retain-on-failure' },
  webServer: [
    {
      command: 'python -m uvicorn app:app --app-dir ../../services/backend --host 127.0.0.1 --port 8018',
      url: 'http://127.0.0.1:8018/health',
      reuseExistingServer: false,
      timeout: 60000,
    },
    {
      command: 'pnpm exec next start --hostname 127.0.0.1 --port 3109',
      url: 'http://127.0.0.1:3109/research-demo',
      env: { CCI_API_URL: 'http://127.0.0.1:8018' },
      reuseExistingServer: false,
      timeout: 60000,
    },
  ],
});
