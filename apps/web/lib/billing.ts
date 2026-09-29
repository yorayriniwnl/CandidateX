'use client';

import { useTenant } from './tenant';

export interface PlanLimits {
  maxEvaluationsPerMonth: number;
  maxCandidates: number;
  canExportPdf: boolean;
  canUseCustomWeights: boolean;
  prioritySupport: boolean;
}

const LIMITS: Record<string, PlanLimits> = {
  starter: {
    maxEvaluationsPerMonth: 25,
    maxCandidates: 50,
    canExportPdf: false,
    canUseCustomWeights: false,
    prioritySupport: false,
  },
  growth: {
    maxEvaluationsPerMonth: 200,
    maxCandidates: 500,
    canExportPdf: true,
    canUseCustomWeights: true,
    prioritySupport: false,
  },
  enterprise: {
    maxEvaluationsPerMonth: 10000,
    maxCandidates: 50000,
    canExportPdf: true,
    canUseCustomWeights: true,
    prioritySupport: true,
  },
};

export function useSubscriptionTier() {
  const { currentOrg } = useTenant();
  const plan = currentOrg?.plan || 'enterprise';
  const limits = LIMITS[plan] || LIMITS.enterprise;

  return {
    plan,
    limits,
    isEnterprise: plan === 'enterprise',
    isGrowth: plan === 'growth',
    isStarter: plan === 'starter',
    upgradeUrl: '/billing/upgrade',
  };
}
