import { defineConfig } from '@playwright/test';

function readPort(name: string, fallback: number): number {
  const value = Number(process.env[name] ?? fallback);
  if (!Number.isInteger(value) || value < 1 || value > 65535) {
    throw new Error(name + ' must be an integer port between 1 and 65535');
  }
  return value;
}

const apiPort = readPort('PLAYWRIGHT_API_PORT', 8017);
const webPort = readPort('PLAYWRIGHT_WEB_PORT', 3108);
const apiUrl = 'http://127.0.0.1:' + apiPort;
const webUrl = 'http://127.0.0.1:' + webPort;

export default defineConfig({
  testDir: './tests',
  fullyParallel: false,
  workers: 1,
  use: { baseURL: webUrl, trace: 'retain-on-failure' },
  webServer: [
    {
      command: 'python -m uvicorn cci.main:app --app-dir ../../services/backend/src --host 127.0.0.1 --port ' + apiPort,
      url: apiUrl + '/health',
      reuseExistingServer: false,
      timeout: 60000,
    },
    {
      command: 'pnpm exec next start --hostname 127.0.0.1 --port ' + webPort,
      url: webUrl,
      env: { CCI_API_URL: apiUrl },
      reuseExistingServer: false,
      timeout: 60000,
    },
  ],
});