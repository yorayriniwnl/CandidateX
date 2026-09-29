export type UserRole = 'admin' | 'evaluator' | 'candidate' | 'viewer';

export type Permission =
  | 'candidate:read'
  | 'candidate:write'
  | 'candidate:delete'
  | 'dossier:evaluate'
  | 'dossier:override'
  | 'dossier:export'
  | 'team:manage'
  | 'billing:manage';

const ROLE_PERMISSIONS: Record<UserRole, Permission[]> = {
  admin: [
    'candidate:read',
    'candidate:write',
    'candidate:delete',
    'dossier:evaluate',
    'dossier:override',
    'dossier:export',
    'team:manage',
    'billing:manage',
  ],
  evaluator: [
    'candidate:read',
    'candidate:write',
    'dossier:evaluate',
    'dossier:override',
    'dossier:export',
    'team:manage',
  ],
  candidate: [
    'candidate:read',
    'dossier:export',
  ],
  viewer: [
    'candidate:read',
    'dossier:export',
  ],
};

export function hasPermission(role: string | undefined, permission: Permission): boolean {
  if (!role) return false;
  const normalizedRole = role.toLowerCase() as UserRole;
  const permissions = ROLE_PERMISSIONS[normalizedRole] || [];
  return permissions.includes(permission);
}

export function getRolePermissions(role: string | undefined): Permission[] {
  if (!role) return [];
  const normalizedRole = role.toLowerCase() as UserRole;
  return ROLE_PERMISSIONS[normalizedRole] || [];
}
