'use client';

import React, { createContext, useContext, useState, useEffect } from 'react';

export interface Organization {
  id: string;
  name: string;
  slug: string;
  plan: 'starter' | 'growth' | 'enterprise';
  memberCount: number;
}

const DEFAULT_ORGANIZATIONS: Organization[] = [
  {
    id: 'org-default-01',
    name: 'CandidateX Core Studio',
    slug: 'cx-core',
    plan: 'enterprise',
    memberCount: 8,
  },
  {
    id: 'org-demo-02',
    name: 'Engineering Evaluation Labs',
    slug: 'eng-labs',
    plan: 'growth',
    memberCount: 24,
  },
];

interface TenantContextValue {
  currentOrg: Organization;
  organizations: Organization[];
  switchOrganization: (orgId: string) => void;
  tenantHeaders: Record<string, string>;
}

const TenantContext = createContext<TenantContextValue | undefined>(undefined);

export function TenantProvider({ children }: { children: React.ReactNode }) {
  const [currentOrg, setCurrentOrg] = useState<Organization>(DEFAULT_ORGANIZATIONS[0]);

  useEffect(() => {
    try {
      const stored = localStorage.getItem('cx_tenant_org_id');
      if (stored) {
        const found = DEFAULT_ORGANIZATIONS.find((o) => o.id === stored);
        if (found) setCurrentOrg(found);
      }
    } catch {}
  }, []);

  const switchOrganization = (orgId: string) => {
    const found = DEFAULT_ORGANIZATIONS.find((o) => o.id === orgId);
    if (found) {
      setCurrentOrg(found);
      try {
        localStorage.setItem('cx_tenant_org_id', orgId);
      } catch {}
    }
  };

  const tenantHeaders = {
    'X-Tenant-ID': currentOrg.id,
    'X-Tenant-Slug': currentOrg.slug,
  };

  return React.createElement(
    TenantContext.Provider,
    {
      value: {
        currentOrg,
        organizations: DEFAULT_ORGANIZATIONS,
        switchOrganization,
        tenantHeaders,
      },
    },
    children
  );
}

export function useTenant(): TenantContextValue {
  const context = useContext(TenantContext);
  if (!context) {
    // Fallback for standalone pages or SSR
    return {
      currentOrg: DEFAULT_ORGANIZATIONS[0],
      organizations: DEFAULT_ORGANIZATIONS,
      switchOrganization: () => {},
      tenantHeaders: {
        'X-Tenant-ID': DEFAULT_ORGANIZATIONS[0].id,
        'X-Tenant-Slug': DEFAULT_ORGANIZATIONS[0].slug,
      },
    };
  }
  return context;
}
