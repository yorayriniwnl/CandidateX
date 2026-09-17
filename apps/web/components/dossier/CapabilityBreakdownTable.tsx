'use client';

import React, { useState } from 'react';
import { Layers, Eye, Calculator, ArrowRight, CheckCircle2, HelpCircle } from 'lucide-react';
import { CapabilityEstimate, CapabilityKey } from '../../types/cci';
import { GlassCard } from '../ui/GlassCard';
import { GlowBadge } from '../ui/GlowBadge';

const ALL_CAPABILITIES: { key: CapabilityKey; label: string; description: string }[] = [
  { key: 'backend_engineering', label: 'Backend Engineering', description: 'APIs, business logic, asynchronous services' },
  { key: 'frontend_engineering', label: 'Frontend Engineering', description: 'User interfaces, responsive layouts, client state' },
  { key: 'database_engineering', label: 'Database Engineering', description: 'Relational schemas, queries, migrations, indexing' },
  { key: 'devops_cloud', label: 'DevOps & Cloud', description: 'Docker, CI/CD, deployment orchestration, Terraform' },
  { key: 'machine_learning', label: 'Machine Learning', description: 'Model architectures, training, evaluation pipelines' },
  { key: 'data_engineering', label: 'Data Engineering', description: 'ETL flows, distributed processing, event streaming' },
  { key: 'algorithms_problem_solving', label: 'Algorithms & Problem Solving', description: 'Data structures, computational complexity, efficiency' },
  { key: 'testing_quality', label: 'Testing & Quality', description: 'Unit testing, mocking, property testing, coverage' },
  { key: 'security', label: 'Security & Privacy', description: 'Defensive headers, auth, SSRF prevention, data safety' },
  { key: 'software_architecture', label: 'Software Architecture', description: 'Layer boundaries, ADRs, modular separation, design patterns' },
  { key: 'collaboration', label: 'Collaboration', description: 'Code reviews, contribution velocity, PR participation' },
  { key: 'documentation_communication', label: 'Documentation & Communication', description: 'READMEs, architectural diagrams, API specifications' },
];

export const CapabilityBreakdownTable: React.FC<{
  estimates: Record<CapabilityKey, CapabilityEstimate>;
  weights?: Record<CapabilityKey, number>;
  onSelectCapability?: (key: CapabilityKey) => void;
  selectedCapability?: CapabilityKey | null;
}> = ({ estimates, weights, onSelectCapability, selectedCapability }) => {
  const [viewMode, setViewMode] = useState<'recruiter' | 'math'>('recruiter');

  return (
    <GlassCard variant="strong" glow="indigo" className="space-y-4">
      {/* Header with Mode Toggle */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 border-b border-white/[0.06] pb-4">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-brand-500/15 flex items-center justify-center text-brand-400">
            <Layers className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-base font-bold text-white tracking-tight">12 Core Technical Capabilities</h2>
            <p className="text-xs text-slate-400">
              {viewMode === 'recruiter'
                ? 'Intuitive capability scores and interview verification status'
                : 'Formal point estimates q_k with 95% bootstrap confidence intervals'}
            </p>
          </div>
        </div>

        {/* View Toggle */}
        <div className="flex items-center glass rounded-xl p-1 text-xs">
          <button
            type="button"
            onClick={() => setViewMode('recruiter')}
            className={`px-3 py-1.5 rounded-lg font-medium transition-all flex items-center gap-1.5 ${
              viewMode === 'recruiter'
                ? 'bg-brand-500/20 text-white shadow-glow-sm'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Eye className="w-3.5 h-3.5" />
            <span>Recruiter View</span>
          </button>
          <button
            type="button"
            onClick={() => setViewMode('math')}
            className={`px-3 py-1.5 rounded-lg font-medium transition-all flex items-center gap-1.5 ${
              viewMode === 'math'
                ? 'bg-brand-500/20 text-white shadow-glow-sm'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Calculator className="w-3.5 h-3.5" />
            <span>Audit / Math View</span>
          </button>
        </div>
      </div>

      {/* Recruiter View */}
      {viewMode === 'recruiter' ? (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-white/[0.06] text-slate-500 font-mono text-[10px] uppercase tracking-wider">
                <th className="pb-3 pl-2">Capability Dimension</th>
                <th className="pb-3 w-48">Demonstrated Readiness</th>
                <th className="pb-3 text-center">Status</th>
                <th className="pb-3 text-center">Role Weight</th>
                <th className="pb-3 text-right pr-2">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/[0.04]">
              {ALL_CAPABILITIES.map((cap) => {
                const est = estimates[cap.key];
                const isObserved = est && est.is_observed && est.estimate !== null;
                const isSelected = selectedCapability === cap.key;
                const score = est?.estimate ?? null;
                const weightVal = weights ? weights[cap.key] : 1.0 / 12.0;
                const barColor = score !== null && score >= 80
                  ? 'from-emerald-500 to-emerald-400'
                  : score !== null && score >= 65
                  ? 'from-brand-500 to-brand-400'
                  : 'from-amber-500 to-amber-400';

                return (
                  <tr
                    key={cap.key}
                    onClick={() => onSelectCapability && onSelectCapability(cap.key)}
                    className={`cursor-pointer transition-colors ${
                      isSelected
                        ? 'bg-brand-500/[0.12] border-l-2 border-brand-400'
                        : 'hover:bg-white/[0.03]'
                    }`}
                  >
                    <td className="py-3.5 pl-2">
                      <div className="font-semibold text-slate-200">{cap.label}</div>
                      <div className="text-[11px] text-slate-500 truncate max-w-xs">{cap.description}</div>
                    </td>

                    <td className="py-3.5">
                      {isObserved && score !== null ? (
                        <div className="space-y-1">
                          <div className="flex items-center justify-between text-xs font-mono">
                            <span className="font-bold text-white">{score.toFixed(1)}</span>
                            <span className="text-slate-500 text-[10px]">/ 100</span>
                          </div>
                          <div className="w-full bg-white/[0.06] h-2 rounded-full overflow-hidden">
                            <div
                              className={`h-full rounded-full bg-gradient-to-r ${barColor} transition-all duration-1000`}
                              style={{ width: `${Math.min(100, Math.max(0, score))}%` }}
                            />
                          </div>
                        </div>
                      ) : (
                        <div className="space-y-1">
                          <div className="flex items-center justify-between text-xs font-mono text-slate-500">
                            <span>UNKNOWN</span>
                            <span className="text-[10px] text-amber-400/70">No Repos</span>
                          </div>
                          <div className="w-full bg-white/[0.04] h-2 rounded-full overflow-hidden">
                            <div className="h-full bg-white/[0.08] w-1/4" />
                          </div>
                        </div>
                      )}
                    </td>

                    <td className="py-3.5 text-center">
                      {isObserved ? (
                        <GlowBadge variant="success" size="sm">
                          <CheckCircle2 className="w-3 h-3 inline mr-1" />
                          Demonstrated ({est.effective_evidence_count.toFixed(1)} proofs)
                        </GlowBadge>
                      ) : (
                        <GlowBadge variant="warning" size="sm">
                          <HelpCircle className="w-3 h-3 inline mr-1" />
                          Probe in Interview
                        </GlowBadge>
                      )}
                    </td>

                    <td className="py-3.5 text-center font-mono text-slate-300">
                      <span className={`px-2 py-0.5 rounded text-[11px] ${
                        weightVal >= 0.15 ? 'bg-brand-500/20 text-brand-300 font-semibold' : 'text-slate-500'
                      }`}>
                        {(weightVal * 100).toFixed(0)}%
                      </span>
                    </td>

                    <td className="py-3.5 text-right pr-2">
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          if (onSelectCapability) onSelectCapability(cap.key);
                        }}
                        className="text-xs text-brand-400 hover:text-brand-300 inline-flex items-center gap-1 font-medium transition-colors"
                      >
                        <span>Inspect</span>
                        <ArrowRight className="w-3 h-3" />
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      ) : (
        /* Math View */
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-white/[0.06] text-slate-500 font-mono text-[10px] uppercase tracking-wider">
                <th className="pb-3 pl-2">Capability</th>
                <th className="pb-3 text-center">Score (q_k)</th>
                <th className="pb-3 text-center">95% Bootstrap CI</th>
                <th className="pb-3 text-center">Eff. Count (n_eff)</th>
                <th className="pb-3 text-center">Dispersion (s_k)</th>
                <th className="pb-3 text-center">Coverage (Cov_k)</th>
                <th className="pb-3 text-center">Weight (w_k)</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/[0.04]">
              {ALL_CAPABILITIES.map((cap) => {
                const est = estimates[cap.key];
                const isObserved = est && est.is_observed && est.estimate !== null;
                const isSelected = selectedCapability === cap.key;
                const weightVal = weights ? weights[cap.key] : 1.0 / 12.0;

                return (
                  <tr
                    key={cap.key}
                    onClick={() => onSelectCapability && onSelectCapability(cap.key)}
                    className={`cursor-pointer transition-colors ${
                      isSelected
                        ? 'bg-brand-500/[0.12] border-l-2 border-brand-400'
                        : 'hover:bg-white/[0.03]'
                    }`}
                  >
                    <td className="py-3 pl-2">
                      <div className="font-medium text-slate-200">{cap.label}</div>
                      <div className="text-[11px] text-slate-500 truncate max-w-xs">{cap.description}</div>
                    </td>

                    <td className="py-3 text-center font-mono">
                      {isObserved ? (
                        <span className="text-sm font-bold text-white">
                          {est.estimate?.toFixed(1)}
                        </span>
                      ) : (
                        <GlowBadge variant="neutral" size="sm">UNKNOWN</GlowBadge>
                      )}
                    </td>

                    <td className="py-3 text-center font-mono text-slate-400">
                      {isObserved && est.ci_lower !== null && est.ci_upper !== null ? (
                        <span>[{est.ci_lower.toFixed(1)}, {est.ci_upper.toFixed(1)}]</span>
                      ) : (
                        <span className="text-slate-600">-</span>
                      )}
                    </td>

                    <td className="py-3 text-center font-mono text-slate-400">
                      {isObserved ? est.effective_evidence_count.toFixed(1) : '0.0'}
                    </td>

                    <td className="py-3 text-center font-mono text-slate-400">
                      {isObserved ? est.dispersion.toFixed(1) : '-'}
                    </td>

                    <td className="py-3 text-center font-mono">
                      {isObserved ? (
                        <div className="flex items-center justify-center gap-1.5">
                          <span className="text-slate-300">{(est.coverage_k * 100).toFixed(0)}%</span>
                          <div className="w-12 bg-white/[0.06] h-1.5 rounded-full overflow-hidden">
                            <div
                              className="bg-brand-400 h-full rounded-full"
                              style={{ width: `${Math.min(100, est.coverage_k * 100)}%` }}
                            />
                          </div>
                        </div>
                      ) : (
                        <span className="text-slate-600">0%</span>
                      )}
                    </td>

                    <td className="py-3 text-center font-mono text-slate-400">
                      {(weightVal * 100).toFixed(1)}%
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Footer Invariant Note */}
      <div className="pt-3 text-[11px] text-slate-500 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 border-t border-white/[0.06]">
        <span className="flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full bg-emerald-400 inline-block shadow-glow-sm" />
          <span><strong>Missing &ne; Zero</strong>: Skills without public GitHub artifacts are marked UNKNOWN, never penalized to zero.</span>
        </span>
        <span className="text-slate-600 font-mono text-[10px]">
          Theorem 3 (Convexity) &bull; Theorem 4 (Kish Effective Depth)
        </span>
      </div>
    </GlassCard>
  );
};
