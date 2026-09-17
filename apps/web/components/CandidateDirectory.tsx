'use client';

import React, { useEffect, useMemo, useState } from 'react';
import {
  AlertTriangle,
  Award,
  Download,
  GitCompare,
  LayoutGrid,
  List,
  Plus,
  Search,
  Users,
} from 'lucide-react';
import { CandidateSummary, fetchCandidatesList } from '../lib/api';
import { GlassCard } from './ui/GlassCard';
import { GlowBadge } from './ui/GlowBadge';
import { RadialGauge } from './ui/RadialGauge';
import { AnimatedCounter } from './ui/AnimatedCounter';

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
  onSelectCandidate: (candidateId: string, name: string) => void | Promise<void>;
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
  const [isLoading, setIsLoading] = useState(false);
  const [directoryError, setDirectoryError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedRole, setSelectedRole] = useState<string>('all');
  const [selectedStatus, setSelectedStatus] = useState<string>('all');
  const [sortBy, setSortBy] = useState<'rci_desc' | 'rci_asc' | 'coverage_desc' | 'name_asc' | 'conflict_first'>('rci_desc');
  const [selectedForComparison, setSelectedForComparison] = useState<string[]>(initialSelectedForComparison || []);
  const [loadingCandidateId, setLoadingCandidateId] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<'grid' | 'table'>('grid');

  useEffect(() => {
    if (initialSelectedForComparison) {
      setSelectedForComparison(initialSelectedForComparison);
    }
  }, [initialSelectedForComparison]);

  useEffect(() => {
    if (isBackendOnline !== true) {
      setCandidates([]);
      setDirectoryError(
        isBackendOnline === false
          ? 'Backend unavailable. CandidateX is not showing browser-generated candidate scores as a substitute.'
          : null,
      );
      return;
    }

    let cancelled = false;
    setIsLoading(true);
    setDirectoryError(null);

    fetchCandidatesList()
      .then((data) => {
        if (cancelled) return;
        setCandidates(Array.isArray(data) ? data : []);
      })
      .catch((error) => {
        if (cancelled) return;
        const message = error instanceof Error ? error.message : 'Unknown candidate-directory failure';
        setCandidates([]);
        setDirectoryError(`Could not load live candidate evaluations. ${message}`);
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [isBackendOnline]);

  const toggleSelectForComparison = (id: string) => {
    setSelectedForComparison((prev) => {
      if (prev.includes(id)) return prev.filter((item) => item !== id);
      if (prev.length >= 3) return [...prev.slice(1), id];
      return [...prev, id];
    });
  };

  const filteredCandidates = useMemo(() => {
    return [...candidates]
      .filter((candidate) => {
        const query = searchQuery.toLowerCase();
        const matchesSearch =
          candidate.display_name.toLowerCase().includes(query) ||
          Boolean(candidate.primary_email?.toLowerCase().includes(query));
        const matchesRole = selectedRole === 'all' || candidate.role === selectedRole;

        let matchesStatus = true;
        if (selectedStatus === 'conflict') matchesStatus = candidate.has_meaningful_conflict;
        if (selectedStatus === 'sparse') matchesStatus = candidate.coverage !== undefined && candidate.coverage < 0.10;
        if (selectedStatus === 'robust') {
          matchesStatus = !candidate.has_meaningful_conflict && candidate.coverage !== undefined && candidate.coverage >= 0.10;
        }

        return matchesSearch && matchesRole && matchesStatus;
      })
      .sort((a, b) => {
        if (sortBy === 'rci_desc') return (b.rci ?? -1) - (a.rci ?? -1);
        if (sortBy === 'rci_asc') return (a.rci ?? Number.POSITIVE_INFINITY) - (b.rci ?? Number.POSITIVE_INFINITY);
        if (sortBy === 'coverage_desc') return (b.coverage ?? -1) - (a.coverage ?? -1);
        if (sortBy === 'name_asc') return a.display_name.localeCompare(b.display_name);
        if (sortBy === 'conflict_first') return Number(b.has_meaningful_conflict) - Number(a.has_meaningful_conflict);
        return 0;
      });
  }, [candidates, searchQuery, selectedRole, selectedStatus, sortBy]);

  const cohortMetrics = useMemo(() => {
    const validRcis = filteredCandidates.map((candidate) => candidate.rci).filter((value): value is number => value !== null && value !== undefined);
    const validCoverage = filteredCandidates.map((candidate) => candidate.coverage).filter((value): value is number => value !== null && value !== undefined);
    return {
      total: filteredCandidates.length,
      meanRci: validRcis.length ? validRcis.reduce((sum, value) => sum + value, 0) / validRcis.length : null,
      meanCoverage: validCoverage.length ? validCoverage.reduce((sum, value) => sum + value, 0) / validCoverage.length : null,
      conflictCount: filteredCandidates.filter((candidate) => candidate.has_meaningful_conflict).length,
    };
  }, [filteredCandidates]);

  const handleExportCohortMarkdown = () => {
    if (!filteredCandidates.length) return;
    const lines = [
      '# CandidateX — Live Candidate Evaluation Export',
      '',
      `Generated: ${new Date().toISOString()}`,
      'Source: CandidateX backend candidate directory',
      '',
      '| Candidate | Role | RCI | Evidence Coverage | Contradiction |',
      '|:---|:---|:---:|:---:|:---:|',
    ];

    filteredCandidates.forEach((candidate) => {
      const rci = candidate.rci == null ? 'UNKNOWN' : `${candidate.rci.toFixed(1)} / 100`;
      const coverage = candidate.coverage == null ? 'UNKNOWN' : `${(candidate.coverage * 100).toFixed(1)}%`;
      lines.push(`| ${candidate.display_name} | ${candidate.role || 'Unspecified'} | ${rci} | ${coverage} | ${candidate.has_meaningful_conflict ? 'Flagged' : 'None flagged'} |`);
    });

    lines.push('', '*Decision support only. Missing evidence remains UNKNOWN; this export is not an autonomous hiring decision.*');
    const blob = new Blob([lines.join('\n')], { type: 'text/markdown;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `candidatex_live_export_${new Date().toISOString().slice(0, 10)}.md`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
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
      <GlassCard variant="strong" glow="indigo" className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center gap-3.5">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-brand-500 to-violet-600 flex items-center justify-center text-white shadow-lg shadow-brand-500/25">
            <Users className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-white tracking-tight">Candidate Directory</h2>
            <p className="text-xs text-slate-400">Live evaluations returned by the connected CandidateX backend. Browser fallback scores are disabled.</p>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            disabled={!filteredCandidates.length}
            onClick={handleExportCohortMarkdown}
            className="px-3 py-1.5 glass hover:bg-white/[0.08] disabled:opacity-40 disabled:cursor-not-allowed text-slate-300 rounded-xl text-xs font-medium transition-all flex items-center gap-1.5"
          >
            <Download className="w-3.5 h-3.5 text-brand-400" />
            <span>Export live data</span>
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

      {directoryError && (
        <GlassCard variant="subtle" className="p-3.5 border-amber-500/20">
          <div className="flex items-start gap-2.5 text-xs text-amber-200">
            <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
            <div>
              <div className="font-semibold text-amber-300">No live cohort data</div>
              <div className="mt-1 text-amber-100/70">{directoryError}</div>
            </div>
          </div>
        </GlassCard>
      )}

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <GlassCard variant="subtle" className="p-3.5">
          <span className="text-[10px] text-slate-500 uppercase font-mono block">Live profiles</span>
          <span className="text-xl font-bold text-white font-mono"><AnimatedCounter value={cohortMetrics.total} /></span>
        </GlassCard>
        <GlassCard variant="subtle" glow="indigo" className="p-3.5">
          <span className="text-[10px] text-slate-500 uppercase font-mono block">Mean RCI</span>
          <span className="text-xl font-bold text-brand-400 font-mono">
            {cohortMetrics.meanRci == null ? '—' : <><AnimatedCounter value={cohortMetrics.meanRci} decimals={1} /><span className="text-xs text-slate-500"> / 100</span></>}
          </span>
        </GlassCard>
        <GlassCard variant="subtle" glow="emerald" className="p-3.5">
          <span className="text-[10px] text-slate-500 uppercase font-mono block">Mean coverage</span>
          <span className="text-xl font-bold text-emerald-400 font-mono">
            {cohortMetrics.meanCoverage == null ? '—' : <AnimatedCounter value={cohortMetrics.meanCoverage * 100} decimals={1} suffix="%" />}
          </span>
        </GlassCard>
        <GlassCard variant="subtle" className="p-3.5">
          <span className="text-[10px] text-slate-500 uppercase font-mono block">Contradiction flags</span>
          <span className={`text-xl font-bold font-mono ${cohortMetrics.conflictCount ? 'text-rose-400' : 'text-emerald-400'}`}>
            <AnimatedCounter value={cohortMetrics.conflictCount} />
          </span>
        </GlassCard>
      </div>

      <GlassCard variant="subtle" className="p-3.5">
        <div className="flex flex-col sm:flex-row gap-2.5">
          <div className="relative flex-1">
            <Search className="w-4 h-4 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Filter live candidates by name or email"
              value={searchQuery}
              onChange={(event) => setSearchQuery(event.target.value)}
              className="w-full bg-white/[0.03] border border-white/[0.06] rounded-xl pl-9 pr-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-brand-500/50 transition-colors"
            />
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            <select value={selectedRole} onChange={(event) => setSelectedRole(event.target.value)} className="bg-white/[0.03] border border-white/[0.06] rounded-xl px-3 py-2 text-xs text-slate-300 focus:outline-none">
              <option value="all" className="bg-slate-900">All Roles</option>
              <option value="backend" className="bg-slate-900">Backend</option>
              <option value="frontend" className="bg-slate-900">Frontend</option>
              <option value="ml_engineer" className="bg-slate-900">ML Engineer</option>
              <option value="devops_cloud" className="bg-slate-900">DevOps / SRE</option>
              <option value="fullstack" className="bg-slate-900">Fullstack</option>
            </select>
            <select value={selectedStatus} onChange={(event) => setSelectedStatus(event.target.value)} className="bg-white/[0.03] border border-white/[0.06] rounded-xl px-3 py-2 text-xs text-slate-300 focus:outline-none">
              <option value="all" className="bg-slate-900">All States</option>
              <option value="robust" className="bg-slate-900">Coverage ≥ 10%</option>
              <option value="sparse" className="bg-slate-900">Coverage &lt; 10%</option>
              <option value="conflict" className="bg-slate-900">Conflict Flagged</option>
            </select>
            <select value={sortBy} onChange={(event) => setSortBy(event.target.value as typeof sortBy)} className="bg-white/[0.03] border border-white/[0.06] rounded-xl px-3 py-2 text-xs text-slate-300 focus:outline-none">
              <option value="rci_desc" className="bg-slate-900">RCI high to low</option>
              <option value="rci_asc" className="bg-slate-900">RCI low to high</option>
              <option value="coverage_desc" className="bg-slate-900">Coverage high to low</option>
              <option value="name_asc" className="bg-slate-900">Name A–Z</option>
              <option value="conflict_first" className="bg-slate-900">Conflicts first</option>
            </select>
            <div className="flex items-center glass rounded-xl p-0.5">
              <button type="button" onClick={() => setViewMode('grid')} className={`p-1.5 rounded-lg ${viewMode === 'grid' ? 'bg-brand-500/20 text-white' : 'text-slate-500'}`} title="Grid view"><LayoutGrid className="w-3.5 h-3.5" /></button>
              <button type="button" onClick={() => setViewMode('table')} className={`p-1.5 rounded-lg ${viewMode === 'table' ? 'bg-brand-500/20 text-white' : 'text-slate-500'}`} title="Table view"><List className="w-3.5 h-3.5" /></button>
            </div>
          </div>
        </div>
      </GlassCard>

      {isLoading && (
        <GlassCard className="text-center py-12">
          <p className="text-sm text-slate-300">Loading live candidate evaluations…</p>
        </GlassCard>
      )}

      {!isLoading && viewMode === 'grid' && filteredCandidates.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredCandidates.map((candidate, index) => {
            const roleInfo = ROLE_META[candidate.role || 'backend'] || { label: candidate.role || 'Unknown', variant: 'neutral' as const };
            const isInspecting = loadingCandidateId === candidate.id;
            const isSelected = selectedForComparison.includes(candidate.id);
            const scoreKnown = candidate.rci !== null && candidate.rci !== undefined;
            const coverageKnown = candidate.coverage !== null && candidate.coverage !== undefined;

            return (
              <GlassCard key={candidate.id} variant="default" glow={isSelected ? 'indigo' : 'none'} hoverLift className={isSelected ? 'border-brand-500/50 ring-1 ring-brand-500/30' : ''}>
                <div className="flex items-start justify-between gap-3 mb-4">
                  <div className="flex items-center gap-3 min-w-0">
                    <div className={`w-10 h-10 rounded-xl bg-gradient-to-br ${AVATAR_GRADIENTS[index % AVATAR_GRADIENTS.length]} flex items-center justify-center text-white font-bold text-sm shrink-0`}>
                      {candidate.display_name.charAt(0)}
                    </div>
                    <div className="min-w-0">
                      <h3 className="text-sm font-semibold text-white truncate">{candidate.display_name}</h3>
                      <p className="text-[11px] text-slate-500 truncate">{candidate.primary_email || 'No email declared'}</p>
                    </div>
                  </div>
                  <GlowBadge variant={roleInfo.variant} size="sm">{roleInfo.label}</GlowBadge>
                </div>

                <div className="p-3 glass-subtle rounded-xl flex items-center justify-between gap-3">
                  <div className="flex items-center gap-3">
                    {scoreKnown ? (
                      <RadialGauge value={candidate.rci! / 100} size={52} strokeWidth={5} showPercentage />
                    ) : (
                      <div className="w-[52px] h-[52px] rounded-full border border-white/[0.08] flex items-center justify-center text-[9px] font-mono text-slate-500">UNKNOWN</div>
                    )}
                    <div>
                      <span className="text-[10px] text-slate-500 uppercase font-mono block">Role Capability Index</span>
                      <span className="text-xs font-semibold text-slate-300">{scoreKnown ? `${candidate.rci!.toFixed(1)} / 100` : 'UNKNOWN'}</span>
                    </div>
                  </div>
                  <div className="text-right">
                    <span className="text-[10px] text-slate-500 uppercase font-mono block">Coverage</span>
                    <span className="text-xs font-bold text-emerald-400 font-mono">{coverageKnown ? `${(candidate.coverage! * 100).toFixed(1)}%` : 'UNKNOWN'}</span>
                  </div>
                </div>

                {candidate.has_meaningful_conflict && (
                  <div className="mt-3 p-2 bg-red-500/[0.08] border border-red-500/20 rounded-lg flex items-center gap-2 text-[11px] text-red-300">
                    <AlertTriangle className="w-3.5 h-3.5 shrink-0 text-red-400" />
                    <span>Contradictory evidence flagged for interviewer review.</span>
                  </div>
                )}

                <div className="pt-4 mt-4 border-t border-white/[0.04] flex items-center justify-between gap-2">
                  <button type="button" onClick={() => toggleSelectForComparison(candidate.id)} className={`px-2.5 py-1 rounded-lg text-[11px] font-medium border flex items-center gap-1.5 ${isSelected ? 'bg-brand-600 border-brand-400 text-white' : 'glass border-white/[0.06] text-slate-400'}`}>
                    <GitCompare className="w-3 h-3" />{isSelected ? 'Selected' : 'Compare'}
                  </button>
                  <button type="button" disabled={isInspecting} onClick={() => handleInspect(candidate.id, candidate.display_name)} className="px-3 py-1.5 bg-gradient-to-r from-brand-600 to-violet-600 disabled:opacity-50 text-white rounded-lg text-xs font-semibold flex items-center gap-1.5">
                    <Award className="w-3.5 h-3.5" />{isInspecting ? 'Loading…' : 'View Dossier'}
                  </button>
                </div>
              </GlassCard>
            );
          })}
        </div>
      )}

      {!isLoading && viewMode === 'table' && filteredCandidates.length > 0 && (
        <GlassCard variant="subtle" noPadding className="overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead><tr className="border-b border-white/[0.06] text-slate-500 font-mono text-[10px] uppercase tracking-wider bg-white/[0.02]"><th className="py-3 px-4">Candidate</th><th className="py-3 px-4">Role</th><th className="py-3 px-4 text-center">RCI</th><th className="py-3 px-4 text-center">Coverage</th><th className="py-3 px-4 text-center">Conflict</th><th className="py-3 px-4 text-right">Action</th></tr></thead>
              <tbody className="divide-y divide-white/[0.04]">
                {filteredCandidates.map((candidate) => {
                  const roleInfo = ROLE_META[candidate.role || 'backend'] || { label: candidate.role || 'Unknown', variant: 'neutral' as const };
                  return (
                    <tr key={candidate.id} className="hover:bg-white/[0.03]">
                      <td className="py-3 px-4 font-semibold text-white">{candidate.display_name}</td>
                      <td className="py-3 px-4"><GlowBadge variant={roleInfo.variant} size="sm">{roleInfo.label}</GlowBadge></td>
                      <td className="py-3 px-4 text-center font-mono text-brand-400">{candidate.rci == null ? 'UNKNOWN' : candidate.rci.toFixed(1)}</td>
                      <td className="py-3 px-4 text-center font-mono text-emerald-400">{candidate.coverage == null ? 'UNKNOWN' : `${(candidate.coverage * 100).toFixed(1)}%`}</td>
                      <td className="py-3 px-4 text-center">{candidate.has_meaningful_conflict ? <GlowBadge variant="danger" size="sm">Flagged</GlowBadge> : <GlowBadge variant="neutral" size="sm">None flagged</GlowBadge>}</td>
                      <td className="py-3 px-4 text-right"><button type="button" onClick={() => handleInspect(candidate.id, candidate.display_name)} className="px-3 py-1 bg-brand-500/20 text-brand-300 border border-brand-500/30 rounded-lg text-xs font-semibold">Dossier</button></td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </GlassCard>
      )}

      {!isLoading && filteredCandidates.length === 0 && (
        <GlassCard className="text-center py-12">
          <Users className="w-8 h-8 text-slate-600 mx-auto mb-2" />
          <p className="text-sm text-slate-300 font-medium">
            {candidates.length === 0 ? 'No live candidate evaluations available' : 'No candidates match the selected filters'}
          </p>
          <p className="text-xs text-slate-500 mt-1">
            {candidates.length === 0 ? 'Connect the backend or run a new evaluation. CandidateX will not invent a fallback cohort.' : 'Try broadening the search or filters.'}
          </p>
        </GlassCard>
      )}

      {selectedForComparison.length > 0 && onCompareCandidates && (
        <div className="fixed bottom-6 inset-x-0 mx-auto max-w-xl px-4 z-40">
          <GlassCard variant="strong" glow="indigo" className="p-3.5 flex items-center justify-between gap-4 border-brand-500/30 shadow-2xl">
            <div className="text-xs text-slate-300"><strong className="text-white">Compare live dossiers</strong> · {selectedForComparison.length}/3 selected</div>
            <div className="flex items-center gap-2">
              <button type="button" onClick={() => setSelectedForComparison([])} className="px-2.5 py-1 text-xs text-slate-400">Clear</button>
              <button type="button" onClick={() => onCompareCandidates(selectedForComparison)} className="px-3.5 py-1.5 bg-gradient-to-r from-brand-600 to-violet-600 text-white rounded-xl text-xs font-bold flex items-center gap-1.5"><GitCompare className="w-3.5 h-3.5" />Compare</button>
            </div>
          </GlassCard>
        </div>
      )}
    </div>
  );
};
