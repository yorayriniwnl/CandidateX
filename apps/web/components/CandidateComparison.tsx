'use client';

import React, { useEffect, useMemo, useState } from 'react';
import {
  AlertTriangle,
  Download,
  Printer,
  Shield,
  Users,
} from 'lucide-react';
import { CapabilityKey, Dossier } from '../types/cci';
import { fetchCandidateDossier, fetchCandidatesList } from '../lib/api';
import { GlassCard } from './ui/GlassCard';
import { GlowBadge } from './ui/GlowBadge';

interface ComparisonSubject {
  id: string;
  name: string;
  role: string;
  dossier: Dossier;
}

const CAPABILITY_LABELS: Record<CapabilityKey, string> = {
  backend_engineering: 'Backend Engineering',
  database_engineering: 'Database Engineering',
  software_architecture: 'Software Architecture',
  testing_quality: 'Testing & Quality Assurance',
  devops_cloud: 'DevOps & Cloud Infrastructure',
  security: 'Security Posture & Controls',
  algorithms_problem_solving: 'Algorithms & Problem Solving',
  collaboration: 'Collaboration & Git Workflow',
  documentation_communication: 'Documentation & Communication',
  data_engineering: 'Data Engineering & Pipelines',
  frontend_engineering: 'Frontend Engineering',
  machine_learning: 'Machine Learning Systems',
};

export const CandidateComparison: React.FC<{
  onSelectCandidateDossier?: (candidateId: string, name: string) => void | Promise<void>;
  isBackendOnline?: boolean | null;
  selectedCandidateIds?: string[];
  onSelectedIdsChange?: (ids: string[]) => void;
}> = ({
  onSelectCandidateDossier,
  isBackendOnline,
  selectedCandidateIds,
  onSelectedIdsChange,
}) => {
  const [selectedIds, setSelectedIds] = useState<string[]>(selectedCandidateIds || []);
  const [subjects, setSubjects] = useState<ComparisonSubject[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [comparisonError, setComparisonError] = useState<string | null>(null);
  const [candidateOptions, setCandidateOptions] = useState<Array<{ id: string; name: string; role: string }>>([]);

  useEffect(() => {
    setSelectedIds(selectedCandidateIds || []);
  }, [selectedCandidateIds]);

  useEffect(() => {
    if (isBackendOnline !== true) {
      setCandidateOptions([]);
      setSubjects([]);
      if (isBackendOnline === false) {
        setComparisonError('Backend unavailable. Candidate comparison is disabled rather than populated with synthetic scores.');
      }
      return;
    }

    let cancelled = false;
    setComparisonError(null);
    fetchCandidatesList()
      .then((candidates) => {
        if (cancelled) return;
        setCandidateOptions(
          candidates.map((candidate) => ({
            id: candidate.id,
            name: candidate.display_name,
            role: candidate.role || 'unspecified',
          })),
        );
      })
      .catch((error) => {
        if (cancelled) return;
        const message = error instanceof Error ? error.message : 'Unknown candidate-list failure';
        setCandidateOptions([]);
        setComparisonError(`Could not load live candidate options. ${message}`);
      });

    return () => {
      cancelled = true;
    };
  }, [isBackendOnline]);

  useEffect(() => {
    let cancelled = false;

    async function loadComparisonData() {
      if (isBackendOnline !== true || selectedIds.length === 0) {
        setSubjects([]);
        return;
      }

      setIsLoading(true);
      setComparisonError(null);
      try {
        const loaded = await Promise.all(
          selectedIds.map(async (id) => {
            const option = candidateOptions.find((candidate) => candidate.id === id);
            if (!option) {
              throw new Error(`Candidate ${id} is not present in the live candidate directory.`);
            }
            const dossier = await fetchCandidateDossier(id);
            return { id, name: option.name, role: option.role, dossier } satisfies ComparisonSubject;
          }),
        );
        if (!cancelled) setSubjects(loaded);
      } catch (error) {
        if (!cancelled) {
          const message = error instanceof Error ? error.message : 'Unknown comparison failure';
          setSubjects([]);
          setComparisonError(`Live comparison could not be loaded. No mock dossiers were substituted. ${message}`);
        }
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }

    loadComparisonData();
    return () => {
      cancelled = true;
    };
  }, [selectedIds, candidateOptions, isBackendOnline]);

  const toggleCandidateSelection = (id: string) => {
    const nextIds = selectedIds.includes(id)
      ? selectedIds.filter((item) => item !== id)
      : selectedIds.length >= 3
      ? [...selectedIds.slice(1), id]
      : [...selectedIds, id];

    setSelectedIds(nextIds);
    onSelectedIdsChange?.(nextIds);
  };

  const handleDownloadMarkdown = () => {
    if (!subjects.length) return;
    const lines = [
      '# CandidateX Live Comparison',
      '',
      `Generated: ${new Date().toISOString()}`,
      '**Mode:** Human decision support. Missing evidence remains UNKNOWN.',
      '',
      `| Metric | ${subjects.map((subject) => subject.name).join(' | ')} |`,
      `| :--- | ${subjects.map(() => ':---:').join(' | ')} |`,
      `| Role | ${subjects.map((subject) => subject.role).join(' | ')} |`,
      `| RCI | ${subjects.map((subject) => subject.dossier.rci == null ? 'UNKNOWN' : `${subject.dossier.rci.toFixed(1)} / 100`).join(' | ')} |`,
      `| Coverage | ${subjects.map((subject) => `${(subject.dossier.coverage * 100).toFixed(1)}%`).join(' | ')} |`,
      '',
      `| Capability | ${subjects.map((subject) => subject.name).join(' | ')} |`,
      `| :--- | ${subjects.map(() => ':---:').join(' | ')} |`,
    ];

    Object.entries(CAPABILITY_LABELS).forEach(([key, label]) => {
      const values = subjects.map((subject) => {
        const estimate = subject.dossier.capability_estimates[key as CapabilityKey];
        return !estimate || !estimate.is_observed || estimate.estimate == null
          ? 'UNKNOWN'
          : `${estimate.estimate.toFixed(1)} (n_eff=${estimate.effective_evidence_count.toFixed(1)})`;
      });
      lines.push(`| ${label} | ${values.join(' | ')} |`);
    });

    const blob = new Blob([lines.join('\n')], { type: 'text/markdown;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'candidatex_live_comparison.md';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  const comparisonCapabilities = useMemo(() => Object.entries(CAPABILITY_LABELS), []);

  return (
    <div className="space-y-6">
      <GlassCard variant="strong" glow="indigo" className="space-y-4">
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 border-b border-white/[0.06] pb-4">
          <div>
            <div className="flex items-center gap-2">
              <Users className="w-5 h-5 text-indigo-400" />
              <h1 className="text-xl font-bold text-white tracking-tight">Candidate Comparison</h1>
              <GlowBadge variant="brand" size="sm">Live dossiers only</GlowBadge>
            </div>
            <p className="text-xs text-slate-400 mt-1">Side-by-side capability estimates, coverage, and contradiction signals returned by the backend.</p>
          </div>

          <div className="flex items-center gap-2.5">
            <button type="button" disabled={!subjects.length} onClick={handleDownloadMarkdown} className="px-3 py-1.5 bg-indigo-600 disabled:opacity-40 disabled:cursor-not-allowed text-white rounded-lg text-xs font-semibold flex items-center gap-1.5">
              <Download className="w-3.5 h-3.5" /> Export
            </button>
            <button type="button" disabled={!subjects.length} onClick={() => window.print()} className="px-3 py-1.5 bg-slate-800 disabled:opacity-40 text-slate-200 border border-slate-700 rounded-lg text-xs font-medium flex items-center gap-1.5">
              <Printer className="w-3.5 h-3.5" /> Print
            </button>
          </div>
        </div>

        <div>
          <div className="text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">Select live candidates (max 3)</div>
          <div className="flex flex-wrap gap-2">
            {candidateOptions.map((candidate) => {
              const selected = selectedIds.includes(candidate.id);
              return (
                <button key={candidate.id} type="button" onClick={() => toggleCandidateSelection(candidate.id)} className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all border ${selected ? 'bg-indigo-600/30 border-indigo-500 text-indigo-200' : 'bg-slate-950 border-slate-800 text-slate-400 hover:text-slate-200'}`}>
                  {candidate.name} <span className="text-[10px] opacity-70">({candidate.role})</span>
                </button>
              );
            })}
          </div>
          {candidateOptions.length === 0 && isBackendOnline === true && (
            <p className="text-xs text-slate-500 mt-2">No live candidates are available to compare yet.</p>
          )}
        </div>
      </GlassCard>

      <div className="p-3.5 bg-indigo-950/30 border border-indigo-800/40 rounded-xl flex items-center gap-3 text-xs text-indigo-200">
        <Shield className="w-4 h-4 text-indigo-400 shrink-0" />
        <div><span className="font-semibold">Decision support only.</span> Comparison displays observed evidence and UNKNOWN states. It does not auto-select or reject a candidate.</div>
      </div>

      {comparisonError && (
        <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/25 text-xs text-amber-200 flex items-start gap-2">
          <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0" />
          <span>{comparisonError}</span>
        </div>
      )}

      {isLoading && (
        <GlassCard className="p-12 text-center text-slate-400 text-sm">Loading live comparison dossiers…</GlassCard>
      )}

      {!isLoading && !comparisonError && subjects.length === 0 && (
        <GlassCard className="p-12 text-center">
          <Users className="w-8 h-8 text-slate-600 mx-auto mb-2" />
          <p className="text-sm text-slate-300 font-medium">No live comparison loaded</p>
          <p className="text-xs text-slate-500 mt-1">Select evaluated candidates from the backend directory. CandidateX does not fabricate comparison rows.</p>
        </GlassCard>
      )}

      {!isLoading && subjects.length > 0 && (
        <>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {subjects.map((subject) => {
              const hasConflict = Object.values(subject.dossier.capability_conflicts).some((conflict) => conflict.has_meaningful_conflict);
              const lowCoverage = subject.dossier.coverage < 0.30 || subject.dossier.is_insufficient_evidence;
              return (
                <GlassCard key={subject.id} variant="default" className="space-y-4">
                  <div className="flex items-start justify-between gap-2 border-b border-white/[0.06] pb-3">
                    <div>
                      <h3 className="font-bold text-white text-base">{subject.name}</h3>
                      <span className="text-xs text-slate-400 font-mono uppercase">{subject.role.replace('_', ' ')}</span>
                    </div>
                    <GlowBadge variant={hasConflict ? 'danger' : lowCoverage ? 'warning' : 'success'} size="sm">
                      {hasConflict ? 'Conflict' : lowCoverage ? 'Sparse evidence' : 'Observed'}
                    </GlowBadge>
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <div className="p-3 bg-slate-950 border border-slate-800 rounded-lg">
                      <span className="text-[10px] uppercase tracking-wider text-slate-500 block">RCI</span>
                      <div className="text-2xl font-black text-indigo-400">{subject.dossier.rci == null ? 'UNKNOWN' : subject.dossier.rci.toFixed(1)}</div>
                    </div>
                    <div className="p-3 bg-slate-950 border border-slate-800 rounded-lg">
                      <span className="text-[10px] uppercase tracking-wider text-slate-500 block">Coverage</span>
                      <div className={`text-2xl font-black ${lowCoverage ? 'text-amber-400' : 'text-emerald-400'}`}>{(subject.dossier.coverage * 100).toFixed(1)}%</div>
                    </div>
                  </div>
                  {onSelectCandidateDossier && (
                    <button type="button" onClick={() => onSelectCandidateDossier(subject.id, subject.name)} className="w-full px-3 py-2 rounded-lg bg-indigo-500/15 border border-indigo-500/30 text-indigo-200 text-xs font-semibold hover:bg-indigo-500/20">Open dossier</button>
                  )}
                </GlassCard>
              );
            })}
          </div>

          <GlassCard variant="subtle" noPadding className="overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-white/[0.06] text-slate-500 font-mono text-[10px] uppercase tracking-wider">
                    <th className="py-3 px-4">Capability</th>
                    {subjects.map((subject) => <th key={subject.id} className="py-3 px-4 text-center">{subject.name}</th>)}
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/[0.04]">
                  {comparisonCapabilities.map(([key, label]) => (
                    <tr key={key} className="hover:bg-white/[0.02]">
                      <td className="py-3 px-4 text-slate-300 font-medium">{label}</td>
                      {subjects.map((subject) => {
                        const estimate = subject.dossier.capability_estimates[key as CapabilityKey];
                        const value = !estimate || !estimate.is_observed || estimate.estimate == null ? null : estimate.estimate;
                        return <td key={subject.id} className="py-3 px-4 text-center font-mono text-slate-300">{value == null ? 'UNKNOWN' : value.toFixed(1)}</td>;
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </GlassCard>
        </>
      )}
    </div>
  );
};
