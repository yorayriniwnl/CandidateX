import { defineConfig } from '@playwright/test';
import fs from 'node:fs';
import path from 'node:path';

const repoRoot = path.resolve(process.cwd(), '..', '..');
const projectPython = process.platform === 'win32'
  ? path.join(repoRoot, 'services', 'backend', '.venv', 'Scripts', 'python.exe')
  : path.join(repoRoot, 'services', 'backend', '.venv', 'bin', 'python');
const configuredPython = process.env.CCI_PYTHON;
const python = configuredPython || (fs.existsSync(projectPython) ? projectPython : (process.platform === 'win32' ? 'python' : 'python3'));

if (path.isAbsolute(python) && fs.existsSync(python)) {
  process.env.CCI_PYTHON = python;
  process.env.PATH = `${path.dirname(python)}${path.delimiter}${process.env.PATH || ''}`;
}

const shellArgument = (value: string) => /[\s"]/.test(value) ? `"${value.replaceAll('"', '\\"')}"` : value;

export default defineConfig({
  testDir: './tests',
  fullyParallel: false,
  workers: 1,
  use: { baseURL: 'http://127.0.0.1:3108', trace: 'retain-on-failure' },
  webServer: [
    { command: `${shellArgument(python)} -m uvicorn cci.main:app --app-dir ../../services/backend/src --host 127.0.0.1 --port 8017`, url: 'http://127.0.0.1:8017/health', reuseExistingServer: false, timeout: 60000 },
    { command: 'pnpm exec next start --hostname 127.0.0.1 --port 3108', url: 'http://127.0.0.1:3108', env: { CCI_API_URL: 'http://127.0.0.1:8017' }, reuseExistingServer: false, timeout: 60000 },
  ],
});
