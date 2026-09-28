import { test } from '@playwright/test';
import { execFile } from 'node:child_process';
import path from 'node:path';
import { promisify } from 'node:util';

const run = promisify(execFile);
const webDirectory = path.resolve(__dirname, '..');

test('capture pages and workspace controls from 320px to desktop', async ({ baseURL }) => {
  await run(process.execPath, ['visual-frontend.cjs'], {
    cwd: webDirectory,
    env: { ...process.env, VISUAL_BASE_URL: baseURL },
    timeout: 120000,
  });
});

test('capture a replayed analysis and current research results', async ({ baseURL }) => {
  test.skip(!process.env.VISUAL_FIXTURE_DIR, 'Set VISUAL_FIXTURE_DIR to a local saved response and its synthetic resume.');
  await run(process.execPath, ['visual-frontend-flow.cjs'], {
    cwd: webDirectory,
    env: { ...process.env, VISUAL_BASE_URL: baseURL },
    timeout: 120000,
  });
});
