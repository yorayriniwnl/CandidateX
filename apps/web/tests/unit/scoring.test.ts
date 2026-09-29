import { test, expect } from '@playwright/test';
import { needsClaimVerification } from '../../lib/result-claims';

test.describe('Result Claims Verification Logic', () => {
  test('supported and corroborated statuses do not need manual verification', () => {
    expect(needsClaimVerification('supported')).toBe(false);
    expect(needsClaimVerification('corroborated')).toBe(false);
    expect(needsClaimVerification('repository_support')).toBe(false);
  });

  test('unverified, contradicted, and unknown statuses require verification', () => {
    expect(needsClaimVerification('unverified')).toBe(true);
    expect(needsClaimVerification('contradicted')).toBe(true);
    expect(needsClaimVerification('inconclusive')).toBe(true);
    expect(needsClaimVerification('unknown')).toBe(true);
  });
});
