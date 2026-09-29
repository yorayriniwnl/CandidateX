import { test as base, expect } from '@playwright/test';
import { signSession } from '../lib/session';

// Workflow tests start with a local demo session. login.spec.ts separately covers
// unauthenticated redirects and the complete sign-in interaction.
export const test = base.extend({
  page: async ({ page, context, baseURL }, use) => {
    const sessionToken = signSession({
      email: 'studio-review@example.invalid',
      name: 'Studio Reviewer',
      role: 'evaluator',
      provider: 'credentials',
      loginTime: Date.now(),
    });
    await context.addCookies([
      {
        name: 'cx_session',
        value: sessionToken,
        url: baseURL!,
        httpOnly: true,
        sameSite: 'Lax',
      },
    ]);
    await use(page);
  },
});
export { expect };
export type { Page } from '@playwright/test';
