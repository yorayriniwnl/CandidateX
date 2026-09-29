import { test, expect } from '@playwright/test';
import { signSession, verifySession } from '../../lib/session-core';

test.describe('Cryptographic Session Security', () => {
  test('signs and verifies a valid evaluator session payload', () => {
    const payload = {
      email: 'evaluator@candidatex.dev',
      name: 'Lead Evaluator',
      role: 'evaluator',
      provider: 'credentials',
      loginTime: Date.now(),
    };

    const token = signSession(payload);
    expect(token.includes('.')).toBe(true);

    const verified = verifySession(token);
    expect(verified).not.toBeNull();
    expect(verified?.email).toBe(payload.email);
    expect(verified?.role).toBe(payload.role);
  });

  test('rejects tampered session payloads', () => {
    const payload = {
      email: 'candidate@candidatex.dev',
      role: 'candidate',
      loginTime: Date.now(),
    };

    const token = signSession(payload);
    const [data, sig] = token.split('.');
    const forgedSig = sig.slice(0, -3) + 'xyz';
    const tamperedToken = `${data}.${forgedSig}`;

    const verified = verifySession(tamperedToken);
    expect(verified).toBeNull();
  });

  test('rejects expired sessions', () => {
    const expiredPayload = {
      email: 'expired@candidatex.dev',
      role: 'evaluator',
      loginTime: Date.now() - 100000,
      exp: Date.now() - 1000,
    };

    const token = signSession(expiredPayload);
    const verified = verifySession(token);
    expect(verified).toBeNull();
  });
});
