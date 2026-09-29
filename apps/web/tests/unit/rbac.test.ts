import { test, expect } from '@playwright/test';
import { hasPermission, getRolePermissions } from '../../lib/rbac';

test.describe('Role-Based Access Control (RBAC)', () => {
  test('admin role has full privileges including billing and candidate deletion', () => {
    expect(hasPermission('admin', 'candidate:read')).toBe(true);
    expect(hasPermission('admin', 'candidate:write')).toBe(true);
    expect(hasPermission('admin', 'candidate:delete')).toBe(true);
    expect(hasPermission('admin', 'dossier:override')).toBe(true);
    expect(hasPermission('admin', 'billing:manage')).toBe(true);
  });

  test('evaluator role cannot manage billing or delete candidates', () => {
    expect(hasPermission('evaluator', 'candidate:read')).toBe(true);
    expect(hasPermission('evaluator', 'dossier:evaluate')).toBe(true);
    expect(hasPermission('evaluator', 'dossier:override')).toBe(true);
    expect(hasPermission('evaluator', 'candidate:delete')).toBe(false);
    expect(hasPermission('evaluator', 'billing:manage')).toBe(false);
  });

  test('candidate role has strictly limited view permissions', () => {
    expect(hasPermission('candidate', 'candidate:read')).toBe(true);
    expect(hasPermission('candidate', 'dossier:export')).toBe(true);
    expect(hasPermission('candidate', 'candidate:write')).toBe(false);
    expect(hasPermission('candidate', 'dossier:evaluate')).toBe(false);
    expect(hasPermission('candidate', 'dossier:override')).toBe(false);
  });

  test('unauthenticated or unknown role has zero permissions', () => {
    expect(hasPermission(undefined, 'candidate:read')).toBe(false);
    expect(hasPermission('', 'candidate:read')).toBe(false);
    expect(hasPermission('anonymous', 'candidate:read')).toBe(false);
  });
});
