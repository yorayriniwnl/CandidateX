'use client';

import React from 'react';
import { getStoredUser, type AuthUser } from './auth';

export type UserRole = 'admin' | 'evaluator' | 'interviewer' | 'candidate' | 'viewer';

export type Permission =
  | 'candidate:read'
  | 'candidate:write'
  | 'candidate:create'
  | 'candidate:edit'
  | 'candidate:delete'
  | 'evaluation:run'
  | 'dossier:evaluate'
  | 'dossier:override'
  | 'override:apply'
  | 'dossier:export'
  | 'audit:view'
  | 'team:manage'
  | 'settings:manage'
  | 'billing:manage';

export const ROLE_PERMISSIONS: Record<UserRole, Permission[]> = {
  admin: [
    'candidate:read',
    'candidate:write',
    'candidate:create',
    'candidate:edit',
    'candidate:delete',
    'evaluation:run',
    'dossier:evaluate',
    'dossier:override',
    'override:apply',
    'dossier:export',
    'audit:view',
    'team:manage',
    'settings:manage',
    'billing:manage',
  ],
  evaluator: [
    'candidate:read',
    'candidate:write',
    'candidate:create',
    'candidate:edit',
    'evaluation:run',
    'dossier:evaluate',
    'dossier:override',
    'override:apply',
    'dossier:export',
    'audit:view',
    'team:manage',
  ],
  interviewer: [
    'candidate:read',
    'dossier:export',
    'audit:view',
  ],
  candidate: [
    'candidate:read',
    'dossier:export',
  ],
  viewer: [
    'candidate:read',
  ],
};

export function getRolePermissions(role: UserRole | string | undefined): Permission[] {
  if (!role) return [];
  const normalizedRole = (role.toLowerCase() as UserRole);
  return ROLE_PERMISSIONS[normalizedRole] || [];
}

export function hasPermission(userRole: UserRole | string | undefined, permission: Permission): boolean {
  if (!userRole) return false;
  const permissions = getRolePermissions(userRole);
  return permissions.includes(permission);
}

export function usePermissions() {
  const user = getStoredUser();
  const role: UserRole = (user?.role as UserRole) || 'evaluator';

  return {
    role,
    can: (permission: Permission) => hasPermission(role, permission),
    permissions: getRolePermissions(role),
  };
}

export function RoleGate({
  permission,
  children,
  fallback = null,
}: {
  permission: Permission;
  children: React.ReactNode;
  fallback?: React.ReactNode;
}) {
  const { can } = usePermissions();
  if (!can(permission)) {
    return <>{fallback}</>;
  }
  return <>{children}</>;
}
