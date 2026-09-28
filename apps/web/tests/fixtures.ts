import { test as base, expect } from '@playwright/test';

// Workflow tests start with a local demo session. login.spec.ts separately covers
// unauthenticated redirects and the complete sign-in interaction.
export const test = base.extend({
  page: async ({ page, context, baseURL }, use) => {
    await context.addCookies([{ name: 'cx_auth', value: 'studio-review%40example.invalid', url: baseURL! }]);
    await use(page);
  },
});
export { expect };
export type { Page } from '@playwright/test';
