'use client';

import React from 'react';
import {
  Award,
  AlertTriangle,
  CheckCircle2,
  HelpCircle,
  ArrowRight,
  Sparkles,
  ShieldCheck,
  TrendingUp,
  FileCode,
  Layers,
  MessageSquare,
} from 'lucide-react';
import { CapabilityKey, Dossier } from '../../types/cci';

interface Props {
  dossier: Dossier;
  candidateName: string;
  onNavigateToTab: (tab: 'capabilities' | 'probes' | 'claims' | 'graph') => void;
  onSelectCapability?: (key: CapabilityKey) => void;
}

const CAPABILITY_NAMES: Record<CapabilityKey, string> = {
  backend_engineering: 'Backend Engineering',
  frontend_engineering: 'Frontend Engineering',
  database_engineering: 'Database Engineering',
  devops_cloud: 'DevOps & Cloud Infrastructure',
  machine_learning: 'Machine Learning & AI',
  data_engineering: 'Data Engineering & Pipelines',
  algorithms_problem_solving: 'Algorithms & Problem Solving',
  testing_quality: 'Testing & Quality Assurance',
  security: 'Security & Defensive Architecture',
  software_architecture: 'Software Architecture & Design Patterns',
  collaboration: 'Code Collaboration & Review Velocity',
  documentation_communication: 'Technical Documentation & Specifications',
};

export const DossierOverviewTab: React.FC<Props> = ({
  dossier,
  candidateName,
  onNavigateToTab,
  onSelectCapability,
}) => {
  const rci = dossier.rci;
  const coveragePercent = Math.round(dossier.coverage * 100);

  // Group capabilities into observed (strengths) vs unobserved (unknowns)
  const observedCaps = Object.entries(dossier.capability_estimates)
    .filter(([_, est]) => est.is_observed && est.estimate !== null)
    .sort((a, b) => (b[1].estimate ?? 0) - (a[1].estimate ?? 0));

  const unobservedCaps = Object.entries(dossier.capability_estimates).filter(
    ([_, est]) => !est.is_observed || est.estimate === null
  );

  const topStrengths = observedCaps.slice(0, 3);
  const priorityGaps = unobservedCaps.slice(0, 3);

  // Check for contradiction alerts
  const conflictEntries = Object.entries(dossier.capability_conflicts).filter(
    ([_, c]) => c.has_meaningful_conflict
  );

  // Top probes
  const topProbes = (dossier.interview_probes || []).slice(0, 2);

  // Determine readiness tier
  let readinessTier = {
    label: 'Inconclusive / Sparse Evidence',
    color: 'text-amber-400 bg-amber-500/10 border-amber-500/30',
    desc: 'Public code artifacts are sparse. In-person technical interview inquiry is required.',
  };
  if (rci !== null) {
    if (rci >= 88) {
      readinessTier = {
        label: 'Exceptional Technical Competence',
        color: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/30',
        desc: 'Candidate demonstrates authoritative, complex production code across core role dimensions.',
      };
    } else if (rci >= 75) {
      readinessTier = {
        label: 'Strong Technical Readiness',
        color: 'text-indigo-400 bg-indigo-500/10 border-indigo-500/30',
        desc: 'Demonstrated solid software engineering fundamentals matching senior expectations.',
      };
    } else if (rci >= 60) {
      readinessTier = {
        label: 'Moderate / Developing Competence',
        color: 'text-sky-400 bg-sky-500/10 border-sky-500/30',
        desc: 'Demonstrated working knowledge with opportunities to probe architectural depth in interview.',
      };
    }
  }

  return (
    <div className="space-y-6">
      {/* Executive Summary Card */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl">
        <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-6 pb-6 border-b border-slate-800">
          <div className="space-y-2 max-w-xl">
            <div className="flex items-center gap-2">
              <span className="text-xs font-mono uppercase tracking-wider text-slate-400">Executive Technical Assessment</span>
              <span className={`px-2.5 py-0.5 rounded-full text-xs font-semibold border ${readinessTier.color}`}>
                {readinessTier.label}
              </span>
            </div>
            <h2 className="text-xl font-bold text-white tracking-tight">
              Evaluation for {candidateName}
            </h2>
            <p className="text-xs text-slate-300 leading-relaxed">
              {readinessTier.desc} Grounded in static AST analysis across public code repositories with zero runtime code execution.
            </p>
          </div>

          <div className="flex items-center gap-4 bg-slate-950 p-4 rounded-xl border border-slate-800 shrink-0">
            <div className="text-center px-3 border-r border-slate-800">
              <span className="text-[11px] text-slate-400 uppercase font-mono block">Technical Readiness</span>
              <span className="text-3xl font-black text-indigo-400 font-mono">
                {rci !== null ? rci.toFixed(1) : 'UNKNOWN'}
              </span>
              <span className="text-[11px] text-slate-500 block">out of 100</span>
            </div>

            <div className="text-center px-3">
              <span className="text-[11px] text-slate-400 uppercase font-mono block">Evidence Breadth</span>
              <span className="text-3xl font-black text-emerald-400 font-mono">
                {coveragePercent}%
              </span>
              <span className="text-[11px] text-slate-500 block">
                {observedCaps.length} of 12 observed
              </span>
            </div>
          </div>
        </div>

        {/* Discrepancy Alert Banner */}
        {conflictEntries.length > 0 ? (
          <div className="mt-4 p-3.5 bg-rose-500/10 border border-rose-500/30 rounded-xl flex items-start justify-between gap-3 text-xs">
            <div className="flex items-start gap-2.5">
              <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
              <div>
                <span className="font-bold text-rose-300">
                  Claim vs. Code Discrepancy Detected ({conflictEntries.length} alert):
                </span>
                <p className="text-rose-200/90 mt-0.5 leading-normal">
                  The candidate claims advanced expertise in{' '}
                  <span className="font-semibold text-white">
                    {conflictEntries.map(([k]) => CAPABILITY_NAMES[k as CapabilityKey] || k).join(', ')}
                  </span>
                  , but static repository analysis found low complexity or conflicting commit history ($D_k &lt; 0$).
                </p>
              </div>
            </div>
            <button
              type="button"
              onClick={() => onNavigateToTab('claims')}
              className="px-3 py-1 bg-rose-600/30 hover:bg-rose-600/50 text-rose-200 rounded-lg text-[11px] font-semibold transition-colors shrink-0 flex items-center gap-1 border border-rose-500/40"
            >
              <span>Inspect Proof</span>
              <ArrowRight className="w-3 h-3" />
            </button>
          </div>
        ) : (
          <div className="mt-4 p-3 bg-emerald-500/10 border border-emerald-500/20 rounded-xl flex items-center justify-between text-xs text-emerald-300">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
              <span><strong>All Self-Declared Claims Corroborated:</strong> No architectural discrepancies found between CV statements and repository ASTs.</span>
            </div>
            <button
              type="button"
              onClick={() => onNavigateToTab('claims')}
              className="text-xs text-emerald-400 hover:underline flex items-center gap-1 shrink-0"
            >
              <span>View Claims Matrix</span>
              <ArrowRight className="w-3 h-3" />
            </button>
          </div>
        )}
      </div>

      {/* Two Column Breakdown: Strengths vs Gaps */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Top Verified Strengths */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-xl space-y-3">
          <div className="flex items-center justify-between pb-3 border-b border-slate-800">
            <div className="flex items-center gap-2">
              <TrendingUp className="w-4 h-4 text-emerald-400" />
              <h3 className="font-bold text-slate-100 text-sm">Top Demonstrated Strengths</h3>
            </div>
            <button
              type="button"
              onClick={() => onNavigateToTab('capabilities')}
              className="text-xs text-indigo-400 hover:text-indigo-300 flex items-center gap-1"
            >
              <span>All 12 Capabilities</span>
              <ArrowRight className="w-3 h-3" />
            </button>
          </div>

          <div className="space-y-2.5">
            {topStrengths.length > 0 ? (
              topStrengths.map(([key, est]) => {
                const capKey = key as CapabilityKey;
                return (
                  <div
                    key={key}
                    onClick={() => {
                      if (onSelectCapability) onSelectCapability(capKey);
                      onNavigateToTab('capabilities');
                    }}
                    className="p-3 bg-slate-950 border border-slate-800/80 hover:border-indigo-500/40 rounded-lg flex items-center justify-between cursor-pointer transition-colors"
                  >
                    <div>
                      <div className="font-semibold text-slate-200 text-xs">{CAPABILITY_NAMES[capKey] || key}</div>
                      <div className="text-[11px] text-slate-500">
                        {est.effective_evidence_count.toFixed(1)} independent code proofs
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="text-sm font-bold text-emerald-400 font-mono">
                        {est.estimate?.toFixed(1)} / 100
                      </div>
                      <div className="text-[10px] text-slate-400">Demonstrated</div>
                    </div>
                  </div>
                );
              })
            ) : (
              <div className="p-4 text-center text-slate-500 text-xs">
                No verified public code evidence observed yet.
              </div>
            )}
          </div>
        </div>

        {/* Unobserved Areas / Interview Inquiries */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-xl space-y-3">
          <div className="flex items-center justify-between pb-3 border-b border-slate-800">
            <div className="flex items-center gap-2">
              <HelpCircle className="w-4 h-4 text-amber-400" />
              <h3 className="font-bold text-slate-100 text-sm">Key Unobserved Areas (Unknowns)</h3>
            </div>
            <button
              type="button"
              onClick={() => onNavigateToTab('probes')}
              className="text-xs text-amber-400 hover:text-amber-300 flex items-center gap-1"
            >
              <span>View Interview Guide</span>
              <ArrowRight className="w-3 h-3" />
            </button>
          </div>

          <div className="space-y-2.5">
            {priorityGaps.length > 0 ? (
              priorityGaps.map(([key]) => {
                const capKey = key as CapabilityKey;
                return (
                  <div
                    key={key}
                    onClick={() => {
                      if (onSelectCapability) onSelectCapability(capKey);
                      onNavigateToTab('probes');
                    }}
                    className="p-3 bg-slate-950 border border-slate-800/80 hover:border-amber-500/40 rounded-lg flex items-center justify-between cursor-pointer transition-colors"
                  >
                    <div>
                      <div className="font-semibold text-slate-200 text-xs">{CAPABILITY_NAMES[capKey] || key}</div>
                      <div className="text-[11px] text-slate-500">
                        No public repository artifacts found
                      </div>
                    </div>
                    <div className="text-right">
                      <span className="px-2 py-0.5 bg-slate-800 text-slate-400 border border-slate-700/60 rounded text-[11px] font-medium font-mono">
                        UNKNOWN
                      </span>
                      <div className="text-[10px] text-amber-400 mt-0.5">Probe in Interview</div>
                    </div>
                  </div>
                );
              })
            ) : (
              <div className="p-4 text-center text-slate-500 text-xs">
                All 12 role capabilities have direct verified evidence.
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Prioritized Interview Questions Preview */}
      {topProbes.length > 0 && (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-xl space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-slate-800">
            <div className="flex items-center gap-2">
              <MessageSquare className="w-4 h-4 text-indigo-400" />
              <h3 className="font-bold text-slate-100 text-sm">Recommended Interview Focus Questions</h3>
            </div>
            <button
              type="button"
              onClick={() => onNavigateToTab('probes')}
              className="text-xs text-indigo-400 hover:text-indigo-300 font-medium flex items-center gap-1"
            >
              <span>Open Full Interview Guide &amp; Scorecard</span>
              <ArrowRight className="w-3 h-3" />
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {topProbes.map((probe, idx) => {
              const capKey = probe.capability_key as CapabilityKey;
              // Find matching question
              const matchedQuestion = (dossier.interview_questions || []).find(
                (q) => q.target_capability === probe.capability_key
              );
              const questionText =
                matchedQuestion?.question_text ||
                `Explain your hands-on production experience with ${CAPABILITY_NAMES[capKey] || probe.capability_key}, detailing how you design and test these systems.`;
              const rationaleText =
                matchedQuestion?.rationale ||
                `Verify technical competence and resolve uncertainty in unobserved capability dimension ${CAPABILITY_NAMES[capKey] || probe.capability_key}.`;

              return (
                <div key={idx} className="p-4 bg-slate-950 border border-slate-800 rounded-xl space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-indigo-300">
                      {CAPABILITY_NAMES[capKey] || probe.capability_key}
                    </span>
                    <span className="text-[10px] font-mono px-2 py-0.5 bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 rounded">
                      Priority Rank #{idx + 1}
                    </span>
                  </div>

                  <p className="text-xs text-slate-200 font-medium leading-normal">
                    &ldquo;{questionText}&rdquo;
                  </p>

                  <div className="text-[11px] text-slate-400 pt-1 border-t border-slate-900 leading-normal">
                    <strong className="text-slate-300">Why ask:</strong> {rationaleText}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};
