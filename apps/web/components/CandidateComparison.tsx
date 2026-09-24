'use client';

import React, { useState, useEffect } from 'react';
import {
  Users,
  Award,
  Gauge,
  AlertTriangle,
  CheckCircle2,
  HelpCircle,
  ArrowRight,
  Sparkles,
  Printer,
  ChevronDown,
  Download,
  Info,
  Shield,
} from 'lucide-react';
import { CanonicalRole, CapabilityKey, Dossier } from '../types/cci';
import { fetchCandidateDossier, fetchCandidatesList, CandidateSummary } from '../lib/api';
import { MOCK_DOSSIER } from '../data/mockDossier';
import { motion, AnimatePresence } from 'framer-motion';

import { GlassCard } from '@/components/ui/GlassCard';
import { GlowBadge } from '@/components/ui/GlowBadge';
import { GlassButton } from '@/components/ui/GlassButton';
import { ProgressBar } from '@/components/ui/ProgressBar';
import { RadialGauge } from '@/components/ui/RadialGauge';

interface ComparisonSubject {
  id: string;
  name: string;
  role: string;
  dossier: Dossier;
}

const PRESET_COHORTS = [
  { id: '11111111-1111-1111-1111-111111111111', name: 'Demo Candidate 01', role: 'backend' },
  { id: '77777777-7777-7777-7777-777777777777', name: 'Demo Candidate 06', role: 'backend' },
  { id: '22222222-2222-2222-2222-222222222222', name: 'Demo Candidate 02', role: 'frontend' },
  { id: '33333333-3333-3333-3333-333333333333', name: 'Demo Candidate 03', role: 'ml_engineer' },
  { id: '44444444-4444-4444-4444-444444444444', name: 'Demo Candidate 04', role: 'devops_cloud' },
  { id: '55555555-5555-5555-5555-555555555555', name: 'Demo Candidate 05', role: 'fullstack' },
];

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
  onSelectCandidateDossier?: (candidateId: string, name: string) => void;
  isBackendOnline?: boolean | null;
  selectedCandidateIds?: string[];
  onSelectedIdsChange?: (ids: string[]) => void;
}> = ({
  onSelectCandidateDossier,
  isBackendOnline,
  selectedCandidateIds,
  onSelectedIdsChange,
}) => {
  const [selectedIds, setSelectedIds] = useState<string[]>(
    selectedCandidateIds && selectedCandidateIds.length > 0
      ? selectedCandidateIds
      : ['11111111-1111-1111-1111-111111111111', '77777777-7777-7777-7777-777777777777']
  );
  const [subjects, setSubjects] = useState<ComparisonSubject[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [candidateOptions, setCandidateOptions] = useState<Array<{ id: string; name: string; role: string }>>(PRESET_COHORTS);

  useEffect(() => {
    if (selectedCandidateIds && selectedCandidateIds.length > 0) {
      setSelectedIds(selectedCandidateIds);
    }
  }, [selectedCandidateIds]);

  useEffect(() => {
    if (isBackendOnline) {
      fetchCandidatesList()
        .then((cands) => {
          if (cands.length > 0) {
            setCandidateOptions(
              cands.map((c) => ({
                id: c.id,
                name: c.display_name,
                role: c.role || 'backend',
              }))
            );
          }
        })
        .catch(() => {});
    }
  }, [isBackendOnline]);

  useEffect(() => {
    async function loadComparisonData() {
      setIsLoading(true);
      const loaded: ComparisonSubject[] = [];

      for (const id of selectedIds) {
        const option = candidateOptions.find((c) => c.id === id) || PRESET_COHORTS.find((c) => c.id === id);
        const name = option ? option.name : 'Candidate';
        const role = option ? option.role : 'backend';

        if (isBackendOnline) {
          try {
            const dossier = await fetchCandidateDossier(id);
            loaded.push({ id, name, role, dossier });
            continue;
          } catch (e) {}
        }
      }

      setSubjects(loaded);
      setIsLoading(false);
    }

    loadComparisonData();
  }, [selectedIds, candidateOptions, isBackendOnline]);

  const toggleCandidateSelection = (id: string) => {
    let nextIds: string[];
    if (selectedIds.includes(id)) {
      if (selectedIds.length <= 1) return;
      nextIds = selectedIds.filter((item) => item !== id);
    } else {
      if (selectedIds.length >= 3) {
        nextIds = [selectedIds[0], selectedIds[1], id];
      } else {
        nextIds = [...selectedIds, id];
      }
    }
    setSelectedIds(nextIds);
    if (onSelectedIdsChange) {
      onSelectedIdsChange(nextIds);
    }
  };

  const handlePrint = () => {
    window.print();
  };

  const handleDownloadMarkdown = () => {
    if (subjects.length === 0) return;
    let md = `# Candidate Comparative Evaluation Matrix\n\n`;
    md += `**Generated At:** ${new Date().toISOString()}\n`;
    md += `**Evaluation Mode:** Employer Decision Support (Invariants: No Execution, Missing Evidence is Unknown)\n\n`;

    md += `## 1. High-Level Summary\n\n`;
    md += `| Metric | ${subjects.map((s) => s.name).join(' | ')} |\n`;
    md += `| :--- | ${subjects.map(() => ':---:').join(' | ')} |\n`;
    md += `| **Role** | ${subjects.map((s) => s.role).join(' | ')} |\n`;
    md += `| **Role Capability Index (RCI)** | ${subjects
      .map((s) => (s.dossier.rci !== null ? `**${s.dossier.rci.toFixed(1)} / 100**` : 'UNKNOWN'))
      .join(' | ')} |\n`;
    md += `| **Evidence Coverage** | ${subjects
      .map((s) => `${(s.dossier.coverage * 100).toFixed(1)}%`)
      .join(' | ')} |\n`;
    md += `| **Evidence Sufficiency** | ${subjects
      .map((s) => (s.dossier.is_insufficient_evidence ? 'INSUFFICIENT' : 'SUFFICIENT'))
      .join(' | ')} |\n\n`;

    md += `## 2. 12 Core Capabilities Comparison\n\n`;
    md += `| Capability | ${subjects.map((s) => `${s.name} (Score / n_eff)`).join(' | ')} |\n`;
    md += `| :--- | ${subjects.map(() => ':---:').join(' | ')} |\n`;

    Object.entries(CAPABILITY_LABELS).forEach(([capKey, label]) => {
      const row = subjects.map((s) => {
        const est = s.dossier.capability_estimates[capKey as CapabilityKey];
        if (!est || !est.is_observed || est.estimate === null) return 'UNKNOWN';
        return `${est.estimate.toFixed(1)} (n=${est.effective_evidence_count.toFixed(1)})`;
      });
      md += `| **${label}** | ${row.join(' | ')} |\n`;
    });

    const blob = new Blob([md], { type: 'text/markdown;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `candidate_comparison_matrix.md`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  const containerVariants = {
    hidden: { opacity: 0 },
    show: {
      opacity: 1,
      transition: {
        staggerChildren: 0.1
      }
    }
  };

  const itemVariants = {
    hidden: { opacity: 0, scale: 0.95, y: 10 },
    show: { opacity: 1, scale: 1, y: 0 }
  };

  const meanRCI = subjects.length > 0 
    ? subjects.reduce((acc, sub) => acc + (sub.dossier.rci || 0), 0) / subjects.filter(s => s.dossier.rci !== null).length
    : 0;

  return (
    <div className="space-y-6">
      <GlassCard glow="indigo" className="p-6 space-y-4">
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 border-b border-slate-800 pb-4">
          <div>
            <div className="flex items-center gap-2">
              <Users className="w-5 h-5 text-indigo-400" />
              <h1 className="text-xl font-bold text-white tracking-tight">
                Candidate Comparative Capability Matrix
              </h1>
              <GlowBadge variant="brand" size="sm">Side-by-Side Evaluation</GlowBadge>
            </div>
            <p className="text-xs text-slate-400 mt-1">
              Objective decision support: Compare empirical capability estimates, evidence coverage, and contradiction diagnostics side-by-side.
            </p>
          </div>

          <div className="flex items-center gap-2.5">
            <GlassButton
              variant="primary"
              size="sm"
              icon={<Download className="w-3.5 h-3.5" />}
              iconPosition="left"
              onClick={handleDownloadMarkdown}
            >
              Download Matrix (.md)
            </GlassButton>
            <GlassButton
              variant="secondary"
              size="sm"
              icon={<Printer className="w-3.5 h-3.5 text-indigo-400" />}
              iconPosition="left"
              onClick={handlePrint}
            >
              Print Comparison
            </GlassButton>
          </div>
        </div>

        <div>
          <div className="text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2 flex items-center gap-1.5">
            <span>Select Candidates to Compare (Max 3):</span>
            <span className="text-slate-500 font-normal">({selectedIds.length}/3 selected)</span>
          </div>
          <div className="flex flex-wrap gap-2">
            {candidateOptions.map((cand) => {
              const isSelected = selectedIds.includes(cand.id);
              return (
                <GlassCard
                  key={cand.id}
                  variant="subtle"
                  glow={isSelected ? 'indigo' : 'none'}
                  className={`px-3 py-1.5 cursor-pointer flex items-center gap-1.5 border transition-all ${
                    isSelected ? 'ring-1 ring-indigo-500/50' : ''
                  }`}
                  onClick={() => toggleCandidateSelection(cand.id)}
                >
                  <span
                    className={`w-2 h-2 rounded-full ${isSelected ? 'bg-indigo-400' : 'bg-slate-600'}`}
                  />
                  <span className={`text-xs font-medium ${isSelected ? 'text-indigo-200' : 'text-slate-400'}`}>
                    {cand.name}
                  </span>
                  <span className="text-[10px] text-slate-400 font-mono">({cand.role})</span>
                </GlassCard>
              );
            })}
          </div>
        </div>
      </GlassCard>

      <GlassCard variant="subtle" className="p-3.5 bg-indigo-950/30 flex items-center gap-3 text-xs text-indigo-200">
        <Shield className="w-4 h-4 text-indigo-400 shrink-0" />
        <div>
          <span className="font-semibold">Platform Invariant: Employer Decision Support Only.</span> CCI presents empirical capability signals side-by-side to assist technical interviewers. Unobserved capabilities evaluate to <code>UNKNOWN</code> and never penalize with an arbitrary 0.0.
        </div>
      </GlassCard>

      {isLoading ? (
        <GlassCard className="p-12 text-center text-slate-400 text-sm animate-pulse">
          Loading comparative candidate dossiers...
        </GlassCard>
      ) : (
        <AnimatePresence>
          <motion.div variants={containerVariants} initial="hidden" animate="show" className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {subjects.map((sub) => {
              const coveragePct = Math.round(sub.dossier.coverage * 100);
              const isLowCov = sub.dossier.coverage < 0.30 || sub.dossier.is_insufficient_evidence;
              const hasConflict = Object.values(sub.dossier.capability_conflicts).some(
                (c) => c.has_meaningful_conflict
              );

              const rciScore = sub.dossier.rci;
              const rciDelta = rciScore !== null && subjects.length > 1 && !isNaN(meanRCI)
                ? rciScore - meanRCI
                : null;

              return (
                <motion.div key={sub.id} variants={itemVariants}>
                  <GlassCard className="p-5 space-y-4 h-full flex flex-col justify-between">
                    <div>
                      <div className="flex items-start justify-between gap-2 border-b border-slate-800 pb-3 mb-3">
                        <div>
                          <h3 className="font-bold text-white text-base tracking-tight">{sub.name}</h3>
                          <span className="text-xs text-slate-400 font-mono uppercase">
                            {sub.role.replace('_', ' ')}
                          </span>
                        </div>
                        <GlowBadge variant={hasConflict ? 'danger' : isLowCov ? 'warning' : 'success'} size="sm">
                          {hasConflict ? 'Conflict Flag' : isLowCov ? 'Sparse Evidence' : 'Robust Evidence'}
                        </GlowBadge>
                      </div>

                      <div className="grid grid-cols-2 gap-3 mb-3">
                        <GlassCard variant="subtle" className="p-3 text-center flex flex-col items-center justify-center relative">
                           <span className="text-[11px] uppercase tracking-wider text-slate-400 font-medium block mb-1">
                            RCI Score
                          </span>
                          {rciScore !== null ? (
                            <>
                              <RadialGauge 
                                value={rciScore / 100} 
                                size={70} 
                                color={rciScore > 80 ? '#10b981' : '#6366f1'} 
                                showPercentage 
                                animated
                              />
                              {rciDelta !== null && rciDelta !== 0 && (
                                <div className={`text-[10px] mt-1 font-mono font-semibold ${rciDelta > 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                                  {rciDelta > 0 ? '+' : '−'}{Math.abs(rciDelta).toFixed(1)} vs mean
                                </div>
                              )}
                            </>
                          ) : (
                            <GlowBadge variant="neutral">UNKNOWN</GlowBadge>
                          )}
                        </GlassCard>

                        <GlassCard variant="subtle" className="p-3 text-center flex flex-col items-center justify-center">
                          <span className="text-[11px] uppercase tracking-wider text-slate-400 font-medium block mb-1">
                            Coverage
                          </span>
                          <ProgressBar 
                            value={sub.dossier.coverage} 
                            color={isLowCov ? 'amber' : 'emerald'}
                            size="md"
                            showValue
                            animated
                          />
                        </GlassCard>
                      </div>

                      <GlassCard variant="subtle" className="p-2.5 text-xs text-slate-400 space-y-1">
                        <div className="flex justify-between">
                          <span>Observed Capabilities:</span>
                          <span className="font-mono text-slate-200">
                            {
                              Object.values(sub.dossier.capability_estimates).filter((e) => e.is_observed)
                                .length
                            }{' '}
                            / 12
                          </span>
                        </div>
                        <div className="flex justify-between">
                          <span>Interview Probes:</span>
                          <span className="font-mono text-slate-200">
                            {sub.dossier.interview_probes.length} prioritized
                          </span>
                        </div>
                      </GlassCard>
                    </div>

                    <GlassButton
                      variant="secondary"
                      size="md"
                      fullWidth
                      className="mt-3"
                      icon={<ArrowRight className="w-3.5 h-3.5" />}
                      iconPosition="right"
                      onClick={() => onSelectCandidateDossier && onSelectCandidateDossier(sub.id, sub.name)}
                    >
                      View Technical Dossier
                    </GlassButton>
                  </GlassCard>
                </motion.div>
              );
            })}
          </motion.div>

          <GlassCard noPadding className="overflow-hidden mt-6">
            <div className="p-4 border-b border-slate-800 bg-slate-900/80 flex items-center justify-between">
              <div>
                <h3 className="font-bold text-white text-base">
                  12 Core Capabilities Comparative Matrix
                </h3>
                <p className="text-xs text-slate-400">
                  Side-by-side point estimates \(q_k\) and empirical evidence confidence intervals.
                </p>
              </div>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse text-xs">
                <thead>
                  <tr className="border-b border-slate-800 bg-slate-950 text-slate-400 uppercase tracking-wider font-semibold">
                    <th className="p-3.5 pl-5">Capability Dimension</th>
                    {subjects.map((sub) => (
                      <th key={sub.id} className="p-3.5 text-center">
                        <div className="text-slate-200 font-bold text-sm">{sub.name}</div>
                        <div className="text-[10px] text-slate-500 font-mono lowercase">
                          {sub.role}
                        </div>
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60 text-slate-300 font-sans">
                  {(Object.keys(CAPABILITY_LABELS) as CapabilityKey[]).map((capKey) => {
                    const label = CAPABILITY_LABELS[capKey];

                    let maxVal = -1;
                    subjects.forEach((s) => {
                      const est = s.dossier.capability_estimates[capKey];
                      if (est?.is_observed && est.estimate !== null && est.estimate > maxVal) {
                        maxVal = est.estimate;
                      }
                    });

                    return (
                      <tr key={capKey} className="hover:bg-slate-800/40 transition-colors">
                        <td className="p-3.5 pl-5 font-medium text-slate-200">
                          {label}
                        </td>
                        {subjects.map((sub) => {
                          const est = sub.dossier.capability_estimates[capKey];
                          const isHighest =
                            est?.is_observed &&
                            est.estimate !== null &&
                            est.estimate === maxVal &&
                            subjects.length > 1;

                          return (
                            <td key={sub.id} className="p-3.5 text-center">
                              {est?.is_observed && est.estimate !== null ? (
                                <div className="inline-flex flex-col items-center gap-1">
                                  {isHighest ? (
                                    <GlowBadge variant="success" size="sm">
                                      {est.estimate.toFixed(1)} / 100
                                    </GlowBadge>
                                  ) : (
                                    <span
                                      className={`px-2 py-0.5 rounded font-mono font-bold text-xs ${
                                        est.estimate >= 80
                                          ? 'bg-indigo-500/15 text-indigo-300'
                                          : 'bg-slate-800 text-slate-300'
                                      }`}
                                    >
                                      {est.estimate.toFixed(1)} / 100
                                    </span>
                                  )}
                                  <span className="text-[10px] text-slate-500 font-mono">
                                    {est.effective_evidence_count.toFixed(1)} n_eff
                                  </span>
                                </div>
                              ) : (
                                <GlowBadge variant="neutral" size="sm">UNKNOWN</GlowBadge>
                              )}
                            </td>
                          );
                        })}
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </GlassCard>

          <GlassCard className="p-5 space-y-4 mt-6">
            <div className="border-b border-slate-800 pb-3">
              <h3 className="font-bold text-white text-base">
                Contradiction Diagnostics Comparison (\(D_k \in [-1, 1]\))
              </h3>
              <p className="text-xs text-slate-400">
                Identifies divergence between declared resume claims and deterministic repository artifacts.
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {subjects.map((sub) => {
                const conflicts = Object.values(sub.dossier.capability_conflicts);
                const flagged = conflicts.filter((c) => c.has_meaningful_conflict);

                return (
                  <GlassCard
                    key={sub.id}
                    variant="subtle"
                    className="p-4 space-y-3"
                  >
                    <div className="flex items-center justify-between border-b border-slate-800 pb-2">
                      <span className="font-bold text-sm text-slate-200">{sub.name}</span>
                      <GlowBadge variant={flagged.length > 0 ? 'danger' : 'success'} size="sm">
                        {flagged.length > 0 ? `${flagged.length} Conflict(s)` : 'All Consistent'}
                      </GlowBadge>
                    </div>

                    {flagged.length > 0 ? (
                      <div className="space-y-2">
                        {flagged.map((f) => (
                          <div
                            key={f.capability_key}
                            className="p-2.5 bg-rose-500/10 border border-rose-500/20 rounded-lg text-xs"
                          >
                            <div className="font-semibold text-rose-300">
                              {CAPABILITY_LABELS[f.capability_key] || f.capability_key}
                            </div>
                            <div className="text-[11px] text-rose-400/90 font-mono mt-0.5">
                              Diagnostic D_k: {f.contradiction_diagnostic.toFixed(2)} (Contradiction)
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p className="text-xs text-slate-500 italic py-2">
                        No meaningful discrepancies between claims and codebase artifacts detected.
                      </p>
                    )}
                  </GlassCard>
                );
              })}
            </div>
          </GlassCard>

          <GlassCard className="p-5 space-y-4 mt-6">
            <div className="border-b border-slate-800 pb-3">
              <h3 className="font-bold text-white text-base">
                Tailored Technical Interview Questions
              </h3>
              <p className="text-xs text-slate-400">
                Top-priority inquiries generated to resolve candidate-specific uncertainty gaps during live panel rounds.
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {subjects.map((sub) => {
                const topProbes = sub.dossier.interview_probes.slice(0, 2);

                return (
                  <GlassCard
                    key={sub.id}
                    variant="subtle"
                    className="p-4 space-y-3"
                  >
                    <div className="font-bold text-sm text-slate-200 border-b border-slate-800 pb-2">
                      Questions for {sub.name}
                    </div>

                    {topProbes.map((probe, idx) => {
                      const matchedQ = sub.dossier.interview_questions.find(
                        (q) => q.target_capability === probe.capability_key
                      );

                      return (
                        <div
                          key={probe.capability_key}
                          className="p-3 bg-slate-900 border-l-2 border-indigo-500 rounded-r-lg space-y-1.5"
                        >
                          <div className="text-xs font-semibold text-indigo-300">
                            Probe #{idx + 1}: {CAPABILITY_LABELS[probe.capability_key] || probe.capability_key}
                          </div>
                          <div className="text-xs text-slate-200">
                            {matchedQ?.question_text ||
                              `Discuss production challenges and architectural boundaries in ${probe.capability_key}.`}
                          </div>
                          {matchedQ?.verification_guidance && (
                            <div className="text-[11px] text-indigo-400/90 bg-indigo-950/40 p-1.5 rounded">
                              <span className="font-semibold">Listen for:</span>{' '}
                              {matchedQ.verification_guidance}
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </GlassCard>
                );
              })}
            </div>
          </GlassCard>
        </AnimatePresence>
      )}
    </div>
  );
};
