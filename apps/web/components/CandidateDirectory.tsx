'use client';

import React, { useEffect, useState, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  AlertTriangle,
  ArrowRight,
  Award,
  CheckCircle2,
  Download,
  Filter,
  GitCompare,
  LayoutGrid,
  List,
  Plus,
  Printer,
  Search,
  Sparkles,
  Users,
} from 'lucide-react';
import { CandidateSummary, fetchCandidatesList } from '../lib/api';
import { GlassCard } from './ui/GlassCard';
import { GlowBadge } from './ui/GlowBadge';
import { RadialGauge } from './ui/RadialGauge';
import { AnimatedCounter } from './ui/AnimatedCounter';

const FALLBACK_CANDIDATES: CandidateSummary[] = [
  {
    id: '11111111-1111-1111-1111-111111111111',
    display_name: 'Jordan Example (SYNTHETIC DEMONSTRATION DATA)',
    primary_email: 'jordan@example.test',
    has_completed_dossier: true,
    rci: 90.0,
    coverage: 0.18,
    role: 'backend',
    has_meaningful_conflict: false,
    created_at: new Date().toISOString(),
  },
  {
    id: '22222222-2222-2222-2222-222222222222',
    display_name: 'Alex Rivera (SYNTHETIC DEMONSTRATION DATA)',
    primary_email: 'alex@example.test',
    has_completed_dossier: true,
    rci: 86.0,
    coverage: 0.182,
    role: 'frontend',
    has_meaningful_conflict: false,
    created_at: new Date().toISOString(),
  },
  {
    id: '33333333-3333-3333-3333-333333333333',
    display_name: 'Morgan Lee (SYNTHETIC DEMONSTRATION DATA)',
    primary_email: 'morgan@example.test',
    has_completed_dossier: true,
    rci: 88.0,
    coverage: 0.18,
    role: 'ml_engineer',
    has_meaningful_conflict: false,
    created_at: new Date().toISOString(),
  },
  {
    id: '44444444-4444-4444-4444-444444444444',
    display_name: 'Taylor Casey (SYNTHETIC DEMONSTRATION DATA)',
    primary_email: 'taylor@example.test',
    has_completed_dossier: true,
    rci: 89.0,
    coverage: 0.18,
    role: 'devops_cloud',
    has_meaningful_conflict: false,
    created_at: new Date().toISOString(),
  },
  {
    id: '55555555-5555-5555-5555-555555555555',
    display_name: 'Sam Vance (SYNTHETIC DEMONSTRATION DATA)',
    primary_email: 'sam@example.test',
    has_completed_dossier: true,
    rci: 89.0,
    coverage: 0.18,
    role: 'fullstack',
    has_meaningful_conflict: false,
    created_at: new Date().toISOString(),
  },
  {
    id: '77777777-7777-7777-7777-777777777777',
    display_name: 'Quinn Avery (SYNTHETIC DEMONSTRATION DATA)',
    primary_email: 'quinn@example.test',
    has_completed_dossier: true,
    rci: 69.9,
    coverage: 0.0,
    role: 'backend',
    has_meaningful_conflict: true,
    created_at: new Date().toISOString(),
  },
];

const ROLE_META: Record<string, { label: string; variant: 'brand' | 'success' | 'warning' | 'info' | 'neutral' }> = {
  backend: { label: 'Backend', variant: 'success' },
  frontend: { label: 'Frontend', variant: 'brand' },
  ml_engineer: { label: 'ML Engineer', variant: 'info' },
  devops_cloud: { label: 'DevOps / SRE', variant: 'info' },
  fullstack: { label: 'Fullstack', variant: 'brand' },
  data_engineer: { label: 'Data Engineer', variant: 'warning' },
};

const AVATAR_GRADIENTS = [
  'from-indigo-500 to-purple-600',
  'from-sky-500 to-blue-600',
  'from-emerald-500 to-teal-600',
  'from-violet-500 to-fuchsia-600',
  'from-amber-500 to-orange-600',
  'from-rose-500 to-pink-600',
];

export const CandidateDirectory: React.FC<{
  onSelectCandidate: (candidateId: string, name: string) => void;
  onNewCandidate: () => void;
  isBackendOnline: boolean | null;
  onCompareCandidates?: (candidateIds: string[]) => void;
  initialSelectedForComparison?: string[];
}> = ({
  onSelectCandidate,
  onNewCandidate,
  isBackendOnline,
  onCompareCandidates,
  initialSelectedForComparison,
}) => {
  const [candidates, setCandidates] = useState<CandidateSummary[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedRole, setSelectedRole] = useState<string>('all');
  const [selectedStatus, setSelectedStatus] = useState<string>('all');
  const [sortBy, setSortBy] = useState<
    'rci_desc' | 'rci_asc' | 'coverage_desc' | 'name_asc' | 'conflict_first'
  >('rci_desc');
  const [selectedForComparison, setSelectedForComparison] = useState<string[]>(
    initialSelectedForComparison || []
  );
  const [loadingCandidateId, setLoadingCandidateId] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<'grid' | 'table'>('grid');

  useEffect(() => {
    if (initialSelectedForComparison && initialSelectedForComparison.length > 0) {
      setSelectedForComparison(initialSelectedForComparison);
    }
  }, [initialSelectedForComparison]);

  useEffect(() => {
    if (isBackendOnline) {
      fetchCandidatesList()
        .then((data) => {
          setCandidates(data || []);
        })
        .catch(() => {
          setCandidates([]);
        });
    }
  }, [isBackendOnline]);

  const toggleSelectForComparison = (id: string) => {
    setSelectedForComparison((prev) => {
      if (prev.includes(id)) {
        return prev.filter((item) => item !== id);
      }
      if (prev.length >= 3) {
        return [...prev.slice(1), id];
      }
      return [...prev, id];
    });
  };

  const filteredCandidates = candidates
    .filter((c) => {
      const matchesSearch =
        c.display_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        (c.primary_email && c.primary_email.toLowerCase().includes(searchQuery.toLowerCase()));

      const matchesRole = selectedRole === 'all' || c.role === selectedRole;

      let matchesStatus = true;
      if (selectedStatus === 'conflict') {
        matchesStatus = c.has_meaningful_conflict;
      } else if (selectedStatus === 'sparse') {
        matchesStatus = c.coverage !== undefined && c.coverage < 0.10;
      } else if (selectedStatus === 'robust') {
        matchesStatus = !c.has_meaningful_conflict && (c.coverage === undefined || c.coverage >= 0.10);
      }

      return matchesSearch && matchesRole && matchesStatus;
    })
    .sort((a, b) => {
      if (sortBy === 'rci_desc') {
        return (b.rci ?? -1) - (a.rci ?? -1);
      }
      if (sortBy === 'rci_asc') {
        return (a.rci ?? 999) - (b.rci ?? 999);
      }
      if (sortBy === 'coverage_desc') {
        return (b.coverage ?? 0) - (a.coverage ?? 0);
      }
      if (sortBy === 'name_asc') {
        return a.display_name.localeCompare(b.display_name);
      }
      if (sortBy === 'conflict_first') {
        return (b.has_meaningful_conflict ? 1 : 0) - (a.has_meaningful_conflict ? 1 : 0);
      }
      return 0;
    });

  const cohortMetrics = useMemo(() => {
    const validRcis = filteredCandidates.map((c) => c.rci).filter((r): r is number => r !== null && r !== undefined);
    const validCovs = filteredCandidates.map((c) => c.coverage).filter((cv): cv is number => cv !== null && cv !== undefined);
    const meanRci = validRcis.length > 0 ? validRcis.reduce((a, b) => a + b, 0) / validRcis.length : 0;
    const meanCov = validCovs.length > 0 ? validCovs.reduce((a, b) => a + b, 0) / validCovs.length : 0;
    const conflictCount = filteredCandidates.filter((c) => c.has_meaningful_conflict).length;

    return {
      total: filteredCandidates.length,
      meanRci,
      meanCov,
      conflictCount,
    };
  }, [filteredCandidates]);

  const handleExportCohortMarkdown = () => {
    const lines = [
      '# Candidate Capability Intelligence (CCI) — Cohort Decision Support Summary',
      '',
      `Generated: ${new Date().toISOString()}`,
      `Total Evaluated Candidates: ${cohortMetrics.total}`,
      `Cohort Mean RCI: ${cohortMetrics.meanRci.toFixed(1)} / 100`,
      `Cohort Mean Evidence Coverage: ${(cohortMetrics.meanCov * 100).toFixed(1)}%`,
      `Candidates with Contradiction Alerts: ${cohortMetrics.conflictCount}`,
      '',
      '> **MANDATORY NOTICE:** CandidateX does not decide whether to hire a person. CandidateX never designates a "best candidate" or automated hiring recommendation. All metrics serve solely as human decision support.',
      '',
      '| Index | Candidate Name | Canonical Role | Role Capability Index (RCI) | Evidence Coverage | Contradiction Alert |',
      '|:---:|:---|:---|:---:|:---:|:---:|',
    ];

    filteredCandidates.forEach((c, idx) => {
      const itemIndex = idx + 1;
      const rciStr = c.rci !== null && c.rci !== undefined ? `${c.rci.toFixed(1)} / 100` : 'UNKNOWN';
      const covStr = c.coverage !== null && c.coverage !== undefined ? `${(c.coverage * 100).toFixed(1)}%` : '0.0%';
      const conflictStr = c.has_meaningful_conflict ? '⚠️ Discrepancy Detected' : 'Aligned';
      const roleStr = c.role || 'Unspecified';
      lines.push(`| ${itemIndex} | ${c.display_name} | ${roleStr} | ${rciStr} | ${covStr} | ${conflictStr} |`);
    });

    lines.push('');
    lines.push('---');
    lines.push('*Decision Support Only: CandidateX strictly assists human hiring committees and never makes autonomous hire/reject decisions.*');

    const blob = new Blob([lines.join('\n')], { type: 'text/markdown;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `cohort_decision_support_${new Date().toISOString().slice(0, 10)}.md`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const handleInspect = async (candidateId: string, name: string) => {
    setLoadingCandidateId(candidateId);
    try {
      await onSelectCandidate(candidateId, name);
    } finally {
      setLoadingCandidateId(null);
    }
  };

  return (
    <div className="space-y-5">
      {/* Header Bar */}
      <GlassCard variant="strong" glow="indigo" className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center gap-3.5">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-brand-500 to-violet-600 flex items-center justify-center text-white shadow-lg shadow-brand-500/25">
            <Users className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-white tracking-tight">Candidate Directory</h2>
            <p className="text-xs text-slate-400">
              Evaluated technical cohorts with evidence dossiers, RCI indicators, and contradiction diagnostics
            </p>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={handleExportCohortMarkdown}
            className="px-3 py-1.5 glass hover:bg-white/[0.08] text-slate-300 rounded-xl text-xs font-medium transition-all flex items-center gap-1.5"
            title="Download complete cohort decision support summary as Markdown"
          >
            <Download className="w-3.5 h-3.5 text-brand-400" />
            <span>Export (.md)</span>
          </button>
          <button
            type="button"
            onClick={() => window.print()}
            className="px-3 py-1.5 glass hover:bg-white/[0.08] text-slate-300 rounded-xl text-xs font-medium transition-all flex items-center gap-1.5"
            title="Print executive cohort decision support packet"
          >
            <Printer className="w-3.5 h-3.5 text-slate-400" />
            <span>Print</span>
          </button>
          <button
            type="button"
            onClick={onNewCandidate}
            className="px-4 py-1.5 bg-gradient-to-r from-brand-600 to-violet-600 hover:from-brand-500 hover:to-violet-500 text-white rounded-xl text-xs font-semibold shadow-lg shadow-brand-500/25 flex items-center gap-1.5 transition-all"
          >
            <Plus className="w-4 h-4" />
            <span>New Evaluation</span>
          </button>
        </div>
      </GlassCard>

      {/* Human Decision Support Invariant Banner */}
      <GlassCard variant="subtle" className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 text-xs p-3.5 border-brand-500/20 bg-brand-500/5">
        <div className="flex items-center gap-2.5">
          <span className="px-2 py-0.5 rounded text-[10px] font-mono font-semibold uppercase tracking-wider bg-brand-500/20 text-brand-300 border border-brand-500/30 shrink-0">
            Decision Support
          </span>
          <span className="text-slate-300">
            <strong className="text-white">CandidateX does not decide whether to hire a person.</strong> Evaluation metrics and evidence profiles provide factual corroboration for human hiring teams. Automated hiring recommendations and candidate rankings are not produced.
          </span>
        </div>
      </GlassCard>

      {/* Onboarding Helper Banner */}
      <GlassCard variant="subtle" className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 text-xs p-3.5">
        <div className="flex items-center gap-2.5">
          <Sparkles className="w-4 h-4 text-brand-400 shrink-0" />
          <div>
            <span className="font-semibold text-white">How to explore:</span>
            <span className="text-slate-400 ml-1.5">
              Click &ldquo;View Dossier&rdquo; on any candidate to inspect observed code capabilities, or select up to 3 candidates with &ldquo;Compare&rdquo; for side-by-side analysis.
            </span>
          </div>
        </div>
      </GlassCard>

      {/* Cohort Analytics Ribbon */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <GlassCard variant="subtle" className="p-3.5 flex items-center justify-between">
          <div>
            <span className="text-[10px] text-slate-500 uppercase font-mono block">Cohort Size</span>
            <span className="text-xl font-bold text-white font-mono">
              <AnimatedCounter value={cohortMetrics.total} /> <span className="text-xs font-normal text-slate-500">profiles</span>
            </span>
          </div>
          <div className="w-8 h-8 rounded-lg bg-brand-500/10 text-brand-400 flex items-center justify-center">
            <Users className="w-4 h-4" />
          </div>
        </GlassCard>

        <GlassCard variant="subtle" glow="indigo" className="p-3.5 flex items-center justify-between">
          <div>
            <span className="text-[10px] text-slate-500 uppercase font-mono block">Mean Readiness</span>
            <span className="text-xl font-bold text-brand-400 font-mono">
              <AnimatedCounter value={cohortMetrics.meanRci} decimals={1} />
              <span className="text-xs text-slate-500 font-normal"> / 100</span>
            </span>
          </div>
          <div className="w-8 h-8 rounded-lg bg-brand-500/10 text-brand-400 flex items-center justify-center">
            <Award className="w-4 h-4" />
          </div>
        </GlassCard>

        <GlassCard variant="subtle" glow="emerald" className="p-3.5 flex items-center justify-between">
          <div>
            <span className="text-[10px] text-slate-500 uppercase font-mono block">Mean Coverage</span>
            <span className="text-xl font-bold text-emerald-400 font-mono">
              <AnimatedCounter value={cohortMetrics.meanCov * 100} decimals={1} suffix="%" />
            </span>
          </div>
          <div className="w-8 h-8 rounded-lg bg-emerald-500/10 text-emerald-400 flex items-center justify-center">
            <CheckCircle2 className="w-4 h-4" />
          </div>
        </GlassCard>

        <GlassCard variant="subtle" glow={cohortMetrics.conflictCount > 0 ? 'none' : 'emerald'} className="p-3.5 flex items-center justify-between">
          <div>
            <span className="text-[10px] text-slate-500 uppercase font-mono block">Contradictions</span>
            <span className={`text-xl font-bold font-mono ${cohortMetrics.conflictCount > 0 ? 'text-rose-400' : 'text-emerald-400'}`}>
              <AnimatedCounter value={cohortMetrics.conflictCount} /> <span className="text-xs font-normal opacity-70">alerts</span>
            </span>
          </div>
          <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${cohortMetrics.conflictCount > 0 ? 'bg-rose-500/10 text-rose-400' : 'bg-emerald-500/10 text-emerald-400'}`}>
            <AlertTriangle className="w-4 h-4" />
          </div>
        </GlassCard>
      </div>

      {/* Search and Filters Bar */}
      <GlassCard variant="subtle" className="p-3.5 space-y-3">
        <div className="flex flex-col sm:flex-row gap-2.5">
          <div className="relative flex-1">
            <Search className="w-4 h-4 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Filter by name, email, role..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-white/[0.03] border border-white/[0.06] rounded-xl pl-9 pr-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-brand-500/50 transition-colors"
            />
          </div>

          <div className="flex items-center gap-2 flex-wrap">
            <select
              value={selectedRole}
              onChange={(e) => setSelectedRole(e.target.value)}
              className="bg-white/[0.03] border border-white/[0.06] rounded-xl px-3 py-2 text-xs text-slate-300 focus:outline-none focus:border-brand-500/50 transition-colors"
            >
              <option value="all" className="bg-slate-900">All Roles</option>
              <option value="backend" className="bg-slate-900">Backend</option>
              <option value="frontend" className="bg-slate-900">Frontend</option>
              <option value="ml_engineer" className="bg-slate-900">ML Engineer</option>
              <option value="devops_cloud" className="bg-slate-900">DevOps / SRE</option>
              <option value="fullstack" className="bg-slate-900">Fullstack</option>
            </select>

            <select
              value={selectedStatus}
              onChange={(e) => setSelectedStatus(e.target.value)}
              className="bg-white/[0.03] border border-white/[0.06] rounded-xl px-3 py-2 text-xs text-slate-300 focus:outline-none focus:border-brand-500/50 transition-colors"
            >
              <option value="all" className="bg-slate-900">All States</option>
              <option value="robust" className="bg-slate-900">Substantial Evidence</option>
              <option value="sparse" className="bg-slate-900">Sparse Warning</option>
              <option value="conflict" className="bg-slate-900">Discrepancy Flagged</option>
            </select>

            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as any)}
              className="bg-white/[0.03] border border-white/[0.06] rounded-xl px-3 py-2 text-xs text-slate-300 focus:outline-none focus:border-brand-500/50 transition-colors"
            >
              <option value="rci_desc" className="bg-slate-900">Sort: RCI (High &rarr; Low)</option>
              <option value="rci_asc" className="bg-slate-900">Sort: RCI (Low &rarr; High)</option>
              <option value="coverage_desc" className="bg-slate-900">Sort: Coverage (High &rarr; Low)</option>
              <option value="name_asc" className="bg-slate-900">Sort: Name (A &rarr; Z)</option>
              <option value="conflict_first" className="bg-slate-900">Sort: Discrepancies First</option>
            </select>

            <div className="flex items-center glass rounded-xl p-0.5 text-xs">
              <button
                type="button"
                onClick={() => setViewMode('grid')}
                className={`p-1.5 rounded-lg transition-colors cursor-pointer ${
                  viewMode === 'grid' ? 'bg-brand-500/20 text-white shadow-glow-sm' : 'text-slate-500 hover:text-slate-300'
                }`}
                title="Bento Grid View"
              >
                <LayoutGrid className="w-3.5 h-3.5" />
              </button>
              <button
                type="button"
                onClick={() => setViewMode('table')}
                className={`p-1.5 rounded-lg transition-colors cursor-pointer ${
                  viewMode === 'table' ? 'bg-brand-500/20 text-white shadow-glow-sm' : 'text-slate-500 hover:text-slate-300'
                }`}
                title="Table View"
              >
                <List className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        </div>
      </GlassCard>

      {/* Candidate Bento Grid */}
      {viewMode === 'grid' ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredCandidates.map((candidate, idx) => {
            const roleInfo = ROLE_META[candidate.role || 'backend'] || { label: candidate.role || 'Unknown', variant: 'neutral' as const };
            const isInspecting = loadingCandidateId === candidate.id;
            const isSelectedForCompare = selectedForComparison.includes(candidate.id);
            const avatarGrad = AVATAR_GRADIENTS[idx % AVATAR_GRADIENTS.length];
            const rci = candidate.rci ?? 0;

            return (
              <GlassCard
                key={candidate.id}
                variant="default"
                glow={isSelectedForCompare ? 'indigo' : 'none'}
                hoverLift={true}
                className={`flex flex-col justify-between transition-all duration-300 ${
                  isSelectedForCompare
                    ? 'border-brand-500/50 ring-1 ring-brand-500/30 bg-white/[0.05]'
                    : ''
                }`}
              >
                <div>
                  {/* Card Header */}
                  <div className="flex items-start justify-between gap-3 mb-3">
                    <div className="flex items-center gap-3 min-w-0">
                      <div className={`w-10 h-10 rounded-xl bg-gradient-to-br ${avatarGrad} flex items-center justify-center text-white font-bold text-sm shadow-md shrink-0`}>
                        {candidate.display_name.charAt(0)}
                      </div>
                      <div className="min-w-0">
                        <h3 className="text-sm font-semibold text-white truncate">{candidate.display_name}</h3>
                        <p className="text-[11px] text-slate-500 truncate">{candidate.primary_email || 'No email declared'}</p>
                      </div>
                    </div>

                    <GlowBadge variant={roleInfo.variant} size="sm">
                      {roleInfo.label}
                    </GlowBadge>
                  </div>

                  {/* Gauge & Metrics in Bento layout */}
                  <div className="my-3 p-3 glass-subtle rounded-xl flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <RadialGauge
                        value={rci / 100}
                        size={52}
                        strokeWidth={5}
                        showPercentage={true}
                      />
                      <div>
                        <span className="text-[10px] text-slate-500 uppercase font-mono block">Technical Readiness</span>
                        <span className="text-xs font-semibold text-slate-300">
                          {rci >= 88 ? 'Exceptional' : rci >= 75 ? 'Strong' : rci >= 60 ? 'Developing' : 'Sparse'}
                        </span>
                      </div>
                    </div>

                    <div className="text-right">
                      <span className="text-[10px] text-slate-500 uppercase font-mono block">Coverage</span>
                      <span className="text-xs font-bold text-emerald-400 font-mono">
                        {candidate.coverage !== null && candidate.coverage !== undefined
                          ? `${(candidate.coverage * 100).toFixed(0)}%`
                          : '0%'}
                      </span>
                    </div>
                  </div>

                  {/* Badges / Alerts */}
                  {candidate.has_meaningful_conflict && (
                    <div className="mb-2 p-2 bg-red-500/[0.08] border border-red-500/20 rounded-lg flex items-center gap-2 text-[11px] text-red-300">
                      <AlertTriangle className="w-3.5 h-3.5 shrink-0 text-red-400" />
                      <span><strong>Discrepancy:</strong> Resume claim conflicts with code</span>
                    </div>
                  )}

                  {!candidate.has_meaningful_conflict && candidate.coverage !== undefined && candidate.coverage < 0.10 && (
                    <div className="mb-2 p-2 bg-amber-500/[0.08] border border-amber-500/20 rounded-lg flex items-center gap-2 text-[11px] text-amber-300">
                      <Sparkles className="w-3.5 h-3.5 shrink-0 text-amber-400" />
                      <span><strong>Sparse Repos:</strong> Missing skills marked UNKNOWN</span>
                    </div>
                  )}
                </div>

                {/* Card Footer Actions */}
                <div className="pt-3 border-t border-white/[0.04] flex items-center justify-between gap-2">
                  <button
                    type="button"
                    onClick={() => toggleSelectForComparison(candidate.id)}
                    className={`px-2.5 py-1 rounded-lg text-[11px] font-medium border flex items-center gap-1.5 transition-all ${
                      isSelectedForCompare
                        ? 'bg-brand-600 border-brand-400 text-white shadow-glow-sm'
                        : 'glass border-white/[0.06] text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    <GitCompare className="w-3 h-3" />
                    <span>{isSelectedForCompare ? 'Selected' : 'Compare'}</span>
                  </button>

                  <button
                    type="button"
                    disabled={isInspecting}
                    onClick={() => handleInspect(candidate.id, candidate.display_name)}
                    className="px-3 py-1.5 bg-gradient-to-r from-brand-600 to-violet-600 hover:from-brand-500 hover:to-violet-500 disabled:opacity-50 text-white rounded-lg text-xs font-semibold shadow-md shadow-brand-500/20 flex items-center gap-1.5 transition-all"
                  >
                    <Award className="w-3.5 h-3.5" />
                    <span>{isInspecting ? 'Loading...' : 'View Dossier'}</span>
                  </button>
                </div>
              </GlassCard>
            );
          })}
        </div>
      ) : (
        /* Table View */
        <GlassCard variant="subtle" noPadding={true} className="overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-white/[0.06] text-slate-500 font-mono text-[10px] uppercase tracking-wider bg-white/[0.02]">
                  <th className="py-3 px-4 text-center">#</th>
                  <th className="py-3 px-4">Candidate &amp; Role</th>
                  <th className="py-3 px-4 text-center">RCI Score</th>
                  <th className="py-3 px-4 text-center">Coverage</th>
                  <th className="py-3 px-4 text-center">Status</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/[0.04]">
                {filteredCandidates.map((candidate, idx) => {
                  const roleInfo = ROLE_META[candidate.role || 'backend'] || { label: candidate.role || 'Unknown', variant: 'neutral' as const };
                  const isInspecting = loadingCandidateId === candidate.id;
                  const isSelectedForCompare = selectedForComparison.includes(candidate.id);

                  return (
                    <tr
                      key={candidate.id}
                      className={`hover:bg-white/[0.03] transition-colors ${
                        isSelectedForCompare ? 'bg-brand-500/[0.06]' : ''
                      }`}
                    >
                      <td className="py-3 px-4 text-center">
                        <span className="w-6 h-6 rounded-md inline-flex items-center justify-center font-mono text-xs text-slate-400 glass">
                          {idx + 1}
                        </span>
                      </td>

                      <td className="py-3 px-4">
                        <div className="flex items-center gap-2">
                          <button
                            type="button"
                            onClick={() => handleInspect(candidate.id, candidate.display_name)}
                            className="text-sm font-semibold text-white hover:text-brand-400 transition-colors text-left"
                          >
                            {candidate.display_name}
                          </button>
                          <GlowBadge variant={roleInfo.variant} size="sm">
                            {roleInfo.label}
                          </GlowBadge>
                        </div>
                        <p className="text-[11px] text-slate-500 font-mono mt-0.5">
                          {candidate.primary_email || candidate.id.slice(0, 8)}
                        </p>
                      </td>

                      <td className="py-3 px-4 text-center">
                        <span className="text-sm font-bold font-mono text-brand-400">
                          {candidate.rci !== null && candidate.rci !== undefined ? candidate.rci.toFixed(1) : 'UNKNOWN'}
                          <span className="text-[10px] text-slate-500 font-normal"> / 100</span>
                        </span>
                      </td>

                      <td className="py-3 px-4 text-center">
                        <span className="text-xs font-semibold font-mono text-emerald-400">
                          {candidate.coverage !== null && candidate.coverage !== undefined
                            ? `${(candidate.coverage * 100).toFixed(1)}%`
                            : '0.0%'}
                        </span>
                      </td>

                      <td className="py-3 px-4 text-center">
                        {candidate.has_meaningful_conflict ? (
                          <GlowBadge variant="danger" size="sm">Discrepancy Flagged</GlowBadge>
                        ) : (
                          <GlowBadge variant="success" size="sm">Aligned</GlowBadge>
                        )}
                      </td>

                      <td className="py-3 px-4 text-right">
                        <div className="flex items-center justify-end gap-2">
                          <button
                            type="button"
                            onClick={() => toggleSelectForComparison(candidate.id)}
                            className={`px-2.5 py-1 rounded-lg text-xs font-medium border transition-colors ${
                              isSelectedForCompare
                                ? 'bg-brand-600 text-white border-brand-500'
                                : 'glass border-white/[0.06] text-slate-400 hover:text-white'
                            }`}
                          >
                            <GitCompare className="w-3 h-3 inline mr-1" />
                            {isSelectedForCompare ? 'Selected' : 'Compare'}
                          </button>
                          <button
                            type="button"
                            disabled={isInspecting}
                            onClick={() => handleInspect(candidate.id, candidate.display_name)}
                            className="px-3 py-1 bg-brand-500/20 hover:bg-brand-500/30 text-brand-300 border border-brand-500/30 rounded-lg text-xs font-semibold transition-colors"
                          >
                            <Award className="w-3 h-3 inline mr-1" />
                            {isInspecting ? '...' : 'Dossier'}
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </GlassCard>
      )}

      {/* Empty State */}
      {filteredCandidates.length === 0 && (
        <GlassCard className="text-center py-12">
          <Users className="w-8 h-8 text-slate-600 mx-auto mb-2" />
          <p className="text-sm text-slate-300 font-medium">No candidates match the selected filters</p>
          <p className="text-xs text-slate-500 mt-1">Try broadening your search query or role filter.</p>
        </GlassCard>
      )}

      {/* Floating Comparison Bar */}
      {selectedForComparison.length > 0 && onCompareCandidates && (
        <div className="fixed bottom-6 inset-x-0 mx-auto max-w-xl px-4 z-40">
          <GlassCard variant="strong" glow="indigo" className="p-3.5 flex items-center justify-between gap-4 border-brand-500/30 shadow-2xl">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-xl bg-brand-600 text-white flex items-center justify-center shadow-glow-sm shrink-0">
                <GitCompare className="w-4 h-4" />
              </div>
              <div>
                <div className="text-xs font-bold text-white">
                  Compare Candidates ({selectedForComparison.length}/3)
                </div>
                <div className="text-[11px] text-slate-400 flex flex-wrap items-center gap-1.5 mt-0.5">
                  {selectedForComparison.map((id) => {
                    const cand = candidates.find((c) => c.id === id);
                    return (
                      <span key={id} className="px-1.5 py-0.5 glass rounded text-slate-300 text-[10px]">
                        {cand?.display_name || id.slice(0, 8)}
                      </span>
                    );
                  })}
                </div>
              </div>
            </div>

            <div className="flex items-center gap-2 shrink-0">
              <button
                type="button"
                onClick={() => setSelectedForComparison([])}
                className="px-2.5 py-1 text-xs text-slate-400 hover:text-white transition-colors"
              >
                Clear
              </button>
              <button
                type="button"
                onClick={() => onCompareCandidates(selectedForComparison)}
                className="px-3.5 py-1.5 bg-gradient-to-r from-brand-600 to-violet-600 hover:from-brand-500 hover:to-violet-500 text-white rounded-xl text-xs font-bold shadow-lg shadow-brand-500/30 flex items-center gap-1.5 transition-all"
              >
                <span>Compare</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </GlassCard>
        </div>
      )}
    </div>
  );
};
