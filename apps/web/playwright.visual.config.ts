import { defineConfig } from '@playwright/test';
import workflowConfig from './playwright.config';

// Keep capture servers alive for the scripts, then let Playwright stop them.
export default defineConfig({
  ...workflowConfig,
  testDir: './visual-tests',
  timeout: 150000,
  outputDir: '../../artifacts/frontend-redesign/test-results',
});
