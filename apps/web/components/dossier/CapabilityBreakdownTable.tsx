'use client';

import React, { useState } from 'react';
import { HelpCircle, Layers, Sparkles, Eye, Calculator, ArrowRight, CheckCircle2, AlertCircle } from 'lucide-react';
import { CapabilityEstimate, CapabilityKey } from '../../types/cci';

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
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl space-y-4">
      {/* Header with View Mode Toggle */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 border-b border-slate-800 pb-4">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-indigo-500/10 rounded-lg text-indigo-400">
            <Layers className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-base font-semibold text-slate-100">12 Core Technical Capabilities</h2>
            <p className="text-xs text-slate-400">
              {viewMode === 'recruiter'
                ? 'Intuitive capability scores and interview verification status'
                : 'Formal point estimates q_k with 95% bootstrap confidence intervals'}
            </p>
          </div>
        </div>

        {/* View Toggle */}
        <div className="flex items-center bg-slate-950 p-1 border border-slate-800 rounded-lg text-xs">
          <button
            type="button"
            onClick={() => setViewMode('recruiter')}
            className={`px-3 py-1.5 rounded-md font-medium transition-colors flex items-center gap-1.5 ${
              viewMode === 'recruiter'
                ? 'bg-indigo-600 text-white shadow-sm'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Eye className="w-3.5 h-3.5" />
            <span>Recruiter View</span>
          </button>
          <button
            type="button"
            onClick={() => setViewMode('math')}
            className={`px-3 py-1.5 rounded-md font-medium transition-colors flex items-center gap-1.5 ${
              viewMode === 'math'
                ? 'bg-indigo-600 text-white shadow-sm'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Calculator className="w-3.5 h-3.5" />
            <span>Audit / Math View</span>
          </button>
        </div>
      </div>

      {/* Recruiter / Simple View */}
      {viewMode === 'recruiter' ? (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-slate-800 text-slate-400 font-mono text-[11px] uppercase tracking-wider">
                <th className="pb-3 pl-2">Capability Dimension</th>
                <th className="pb-3 w-48">Demonstrated Readiness</th>
                <th className="pb-3 text-center">Status</th>
                <th className="pb-3 text-center">Role Relevance</th>
                <th className="pb-3 text-right pr-2">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-sans">
              {ALL_CAPABILITIES.map((cap) => {
                const est = estimates[cap.key];
                const isObserved = est && est.is_observed && est.estimate !== null;
                const isSelected = selectedCapability === cap.key;
                const score = est?.estimate ?? null;
                const weightVal = weights ? weights[cap.key] : 1.0 / 12.0;

                return (
                  <tr
                    key={cap.key}
                    onClick={() => onSelectCapability && onSelectCapability(cap.key)}
                    className={`cursor-pointer transition-colors ${
                      isSelected
                        ? 'bg-indigo-500/15 border-l-2 border-indigo-500'
                        : 'hover:bg-slate-800/40'
                    }`}
                  >
                    {/* Capability Name & Description */}
                    <td className="py-3.5 pl-2">
                      <div className="font-semibold text-slate-200">{cap.label}</div>
                      <div className="text-[11px] text-slate-400 truncate max-w-xs">{cap.description}</div>
                    </td>

                    {/* Visual Score Bar */}
                    <td className="py-3.5">
                      {isObserved && score !== null ? (
                        <div className="space-y-1">
                          <div className="flex items-center justify-between text-xs font-mono">
                            <span className="font-bold text-slate-100">{score.toFixed(1)}</span>
                            <span className="text-slate-500 text-[10px]">/ 100</span>
                          </div>
                          <div className="w-full bg-slate-800 h-2 rounded-full overflow-hidden">
                            <div
                              className={`h-full rounded-full ${
                                score >= 80 ? 'bg-emerald-400' : score >= 70 ? 'bg-indigo-400' : 'bg-amber-400'
                              }`}
                              style={{ width: `${Math.min(100, Math.max(0, score))}%` }}
                            />
                          </div>
                        </div>
                      ) : (
                        <div className="space-y-1">
                          <div className="flex items-center justify-between text-xs font-mono text-slate-500">
                            <span>UNKNOWN</span>
                            <span className="text-[10px] text-amber-400/80">No Repos</span>
                          </div>
                          <div className="w-full bg-slate-800/60 h-2 rounded-full overflow-hidden">
                            <div className="h-full bg-slate-700 w-1/4 opacity-40" />
                          </div>
                        </div>
                      )}
                    </td>

                    {/* Status Badge */}
                    <td className="py-3.5 text-center">
                      {isObserved ? (
                        <span className="inline-flex items-center gap-1 px-2.5 py-1 bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 rounded-full text-[11px] font-medium">
                          <CheckCircle2 className="w-3 h-3" />
                          <span>Demonstrated ({est.effective_evidence_count.toFixed(1)} proofs)</span>
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 px-2.5 py-1 bg-amber-500/10 text-amber-300 border border-amber-500/20 rounded-full text-[11px] font-medium">
                          <HelpCircle className="w-3 h-3 text-amber-400" />
                          <span>Probe in Interview</span>
                        </span>
                      )}
                    </td>

                    {/* Role Relevance */}
                    <td className="py-3.5 text-center font-mono text-slate-300">
                      <span className={`px-2 py-0.5 rounded text-[11px] ${
                        weightVal >= 0.15 ? 'bg-indigo-500/20 text-indigo-300 font-semibold' : 'text-slate-400'
                      }`}>
                        {(weightVal * 100).toFixed(0)}%
                      </span>
                    </td>

                    {/* Inspect Link */}
                    <td className="py-3.5 text-right pr-2">
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          if (onSelectCapability) onSelectCapability(cap.key);
                        }}
                        className="text-xs text-indigo-400 hover:text-indigo-300 inline-flex items-center gap-1 font-medium"
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
        /* Math / Audit View */
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-slate-800 text-slate-400 font-mono text-[11px] uppercase tracking-wider">
                <th className="pb-3 pl-2">Capability</th>
                <th className="pb-3 text-center">Score (q_k)</th>
                <th className="pb-3 text-center">95% Bootstrap CI</th>
                <th className="pb-3 text-center">Eff. Count (n_eff)</th>
                <th className="pb-3 text-center">Dispersion (s_k)</th>
                <th className="pb-3 text-center">Coverage (Cov_k)</th>
                <th className="pb-3 text-center">Weight (w_k)</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-sans">
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
                        ? 'bg-indigo-500/15 border-l-2 border-indigo-500'
                        : 'hover:bg-slate-800/40'
                    }`}
                  >
                    <td className="py-3 pl-2">
                      <div className="font-medium text-slate-200">{cap.label}</div>
                      <div className="text-[11px] text-slate-500 truncate max-w-xs">{cap.description}</div>
                    </td>

                    {/* Point Estimate */}
                    <td className="py-3 text-center font-mono">
                      {isObserved ? (
                        <span className="text-sm font-bold text-slate-100">
                          {est.estimate?.toFixed(1)}
                        </span>
                      ) : (
                        <span className="px-2 py-0.5 bg-slate-800 text-slate-400 rounded text-[11px] font-medium border border-slate-700/60 inline-flex items-center gap-1">
                          UNKNOWN
                        </span>
                      )}
                    </td>

                    {/* 95% Bootstrap CI */}
                    <td className="py-3 text-center font-mono text-slate-300">
                      {isObserved && est.ci_lower !== null && est.ci_upper !== null ? (
                        <span>[{est.ci_lower.toFixed(1)}, {est.ci_upper.toFixed(1)}]</span>
                      ) : (
                        <span className="text-slate-600">-</span>
                      )}
                    </td>

                    {/* Effective Count */}
                    <td className="py-3 text-center font-mono text-slate-300">
                      {isObserved ? est.effective_evidence_count.toFixed(1) : '0.0'}
                    </td>

                    {/* Dispersion */}
                    <td className="py-3 text-center font-mono text-slate-300">
                      {isObserved ? est.dispersion.toFixed(1) : '-'}
                    </td>

                    {/* Coverage */}
                    <td className="py-3 text-center font-mono">
                      {isObserved ? (
                        <div className="flex items-center justify-center gap-1.5">
                          <span className="text-slate-300">{(est.coverage_k * 100).toFixed(0)}%</span>
                          <div className="w-12 bg-slate-800 h-1 rounded-full overflow-hidden">
                            <div
                              className="bg-indigo-400 h-full"
                              style={{ width: `${Math.min(100, est.coverage_k * 100)}%` }}
                            />
                          </div>
                        </div>
                      ) : (
                        <span className="text-slate-600">0%</span>
                      )}
                    </td>

                    {/* Role Weight */}
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
      <div className="pt-3 text-[11px] text-slate-400 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 border-t border-slate-800/80">
        <span className="flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full bg-emerald-400 inline-block" />
          <span><strong>Missing != Zero</strong>: Candidates without public GitHub artifacts for a skill are marked UNKNOWN, never failed.</span>
        </span>
        <span className="text-slate-500 font-mono text-[10px]">
          Theorem 3 (Convexity) • Theorem 4 (Kish Depth)
        </span>
      </div>
    </div>
  );
};
