'use client';

import React from 'react';
import { motion } from 'framer-motion';
import {
  AlertTriangle,
  CheckCircle2,
  HelpCircle,
  ArrowRight,
  TrendingUp,
  MessageSquare,
} from 'lucide-react';
import { CapabilityKey, Dossier } from '../../types/cci';
import { GlassCard } from '../ui/GlassCard';
import { GlowBadge } from '../ui/GlowBadge';
import { RadialGauge } from '../ui/RadialGauge';
import { AnimatedCounter } from '../ui/AnimatedCounter';

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

const staggerContainer = {
  animate: {
    transition: { staggerChildren: 0.06 },
  },
};

const staggerItem = {
  initial: { opacity: 0, y: 8 },
  animate: { opacity: 1, y: 0, transition: { duration: 0.3 } },
};

export const DossierOverviewTab: React.FC<Props> = ({
  dossier,
  candidateName,
  onNavigateToTab,
  onSelectCapability,
}) => {
  const rci = dossier.rci;
  const coveragePercent = Math.round(dossier.coverage * 100);

  const observedCaps = Object.entries(dossier.capability_estimates)
    .filter(([_, est]) => est.is_observed && est.estimate !== null)
    .sort((a, b) => (b[1].estimate ?? 0) - (a[1].estimate ?? 0));

  const unobservedCaps = Object.entries(dossier.capability_estimates).filter(
    ([_, est]) => !est.is_observed || est.estimate === null
  );

  const topStrengths = observedCaps.slice(0, 3);
  const priorityGaps = unobservedCaps.slice(0, 3);

  const conflictEntries = Object.entries(dossier.capability_conflicts).filter(
    ([_, c]) => c.has_meaningful_conflict
  );

  const topProbes = (dossier.interview_probes || []).slice(0, 2);

  let readinessTier: { label: string; variant: 'success' | 'warning' | 'danger' | 'info' | 'neutral' | 'brand'; desc: string } = {
    label: 'Inconclusive',
    variant: 'warning',
    desc: 'Public code artifacts are sparse. In-person technical interview inquiry is required.',
  };
  if (rci !== null) {
    if (rci >= 88) {
      readinessTier = {
        label: 'Exceptional',
        variant: 'success' as const,
        desc: 'Candidate demonstrates authoritative, complex production code across core role dimensions.',
      };
    } else if (rci >= 75) {
      readinessTier = {
        label: 'Strong',
        variant: 'brand' as const,
        desc: 'Demonstrated solid software engineering fundamentals matching senior expectations.',
      };
    } else if (rci >= 60) {
      readinessTier = {
        label: 'Developing',
        variant: 'info' as const,
        desc: 'Demonstrated working knowledge with opportunities to probe architectural depth in interview.',
      };
    }
  }

  return (
    <motion.div
      className="space-y-5"
      variants={staggerContainer}
      initial="initial"
      animate="animate"
    >
      {/* Executive Summary */}
      <motion.div variants={staggerItem}>
        <GlassCard variant="strong" glow="indigo">
          <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-6 pb-5 border-b border-white/[0.06]">
            <div className="space-y-2 max-w-xl">
              <div className="flex items-center gap-2.5">
                <span className="text-[10px] font-mono uppercase tracking-widest text-slate-500">
                  Executive Assessment
                </span>
                <GlowBadge variant={readinessTier.variant} size="sm">
                  {readinessTier.label}
                </GlowBadge>
              </div>
              <h2 className="text-xl font-bold text-gradient tracking-tight">
                {candidateName}
              </h2>
              <p className="text-xs text-slate-400 leading-relaxed">
                {readinessTier.desc} Grounded in static AST analysis across public code repositories with zero runtime code execution.
              </p>
            </div>

            <div className="flex items-center gap-6 shrink-0">
              <RadialGauge
                value={rci !== null ? rci / 100 : 0}
                size={90}
                label="RCI"
                showPercentage={true}
              />
              <div className="text-center">
                <div className="text-[10px] text-slate-500 uppercase font-mono mb-1">Evidence Breadth</div>
                <div className="text-2xl font-bold text-emerald-400">
                  <AnimatedCounter value={coveragePercent} suffix="%" />
                </div>
                <div className="text-[10px] text-slate-500 mt-0.5">
                  {observedCaps.length} of 12 observed
                </div>
              </div>
            </div>
          </div>

          {/* Discrepancy Alert or Clean Banner */}
          {conflictEntries.length > 0 ? (
            <div className="mt-4 p-3.5 bg-red-500/[0.08] border border-red-500/20 rounded-xl flex items-start justify-between gap-3 text-xs">
              <div className="flex items-start gap-2.5">
                <AlertTriangle className="w-4 h-4 text-red-400 shrink-0 mt-0.5" />
                <div>
                  <span className="font-bold text-red-300">
                    Discrepancy Detected ({conflictEntries.length}):
                  </span>
                  <p className="text-red-200/80 mt-0.5 leading-normal">
                    Claims vs. code conflict in{' '}
                    <span className="font-semibold text-white">
                      {conflictEntries.map(([k]) => CAPABILITY_NAMES[k as CapabilityKey] || k).join(', ')}
                    </span>
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => onNavigateToTab('claims')}
                className="px-3 py-1.5 glass-strong text-red-300 hover:text-white rounded-lg text-[11px] font-semibold transition-colors shrink-0 flex items-center gap-1"
              >
                Inspect <ArrowRight className="w-3 h-3" />
              </button>
            </div>
          ) : (
            <div className="mt-4 p-3 bg-emerald-500/[0.06] border border-emerald-500/15 rounded-xl flex items-center justify-between text-xs text-emerald-300">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                <span><strong>Claims Corroborated:</strong> No discrepancies between CV statements and repository ASTs.</span>
              </div>
              <button
                type="button"
                onClick={() => onNavigateToTab('claims')}
                className="text-xs text-emerald-400 hover:underline flex items-center gap-1 shrink-0"
              >
                View Matrix <ArrowRight className="w-3 h-3" />
              </button>
            </div>
          )}
        </GlassCard>
      </motion.div>

      {/* Two Column: Strengths vs Gaps */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        {/* Strengths */}
        <motion.div variants={staggerItem}>
          <GlassCard glow="emerald" className="h-full">
            <div className="flex items-center justify-between pb-3 border-b border-white/[0.06]">
              <div className="flex items-center gap-2">
                <div className="w-7 h-7 rounded-lg bg-emerald-500/15 flex items-center justify-center">
                  <TrendingUp className="w-4 h-4 text-emerald-400" />
                </div>
                <h3 className="font-bold text-slate-100 text-sm">Top Strengths</h3>
              </div>
              <button
                type="button"
                onClick={() => onNavigateToTab('capabilities')}
                className="text-xs text-brand-400 hover:text-brand-300 flex items-center gap-1 transition-colors"
              >
                All 12 <ArrowRight className="w-3 h-3" />
              </button>
            </div>

            <div className="space-y-2 mt-3">
              {topStrengths.length > 0 ? (
                topStrengths.map(([key, est]) => {
                  const capKey = key as CapabilityKey;
                  const score = est.estimate ?? 0;
                  const barColor = score >= 80 ? 'from-emerald-500 to-emerald-400' : score >= 60 ? 'from-brand-500 to-brand-400' : 'from-amber-500 to-amber-400';
                  return (
                    <button
                      key={key}
                      type="button"
                      onClick={() => {
                        if (onSelectCapability) onSelectCapability(capKey);
                        onNavigateToTab('capabilities');
                      }}
                      className="w-full p-3 bg-white/[0.02] hover:bg-white/[0.05] border border-white/[0.04] hover:border-emerald-500/30 rounded-xl flex items-center justify-between cursor-pointer transition-all duration-200 text-left group"
                    >
                      <div>
                        <div className="font-semibold text-slate-200 text-xs group-hover:text-white transition-colors">
                          {CAPABILITY_NAMES[capKey] || key}
                        </div>
                        <div className="text-[10px] text-slate-500 mt-0.5">
                          {est.effective_evidence_count.toFixed(1)} code proofs
                        </div>
                        {/* Score bar */}
                        <div className="w-28 h-1 bg-white/[0.06] rounded-full mt-1.5 overflow-hidden">
                          <div
                            className={`h-full bg-gradient-to-r ${barColor} rounded-full transition-all duration-1000`}
                            style={{ width: `${score}%` }}
                          />
                        </div>
                      </div>
                      <div className="text-right">
                        <div className="text-sm font-bold text-emerald-400 font-[family-name:var(--font-mono)]">
                          {score.toFixed(1)}
                        </div>
                        <div className="text-[9px] text-slate-500 uppercase">Verified</div>
                      </div>
                    </button>
                  );
                })
              ) : (
                <div className="p-4 text-center text-slate-500 text-xs">
                  No verified evidence observed yet.
                </div>
              )}
            </div>
          </GlassCard>
        </motion.div>

        {/* Gaps */}
        <motion.div variants={staggerItem}>
          <GlassCard className="h-full">
            <div className="flex items-center justify-between pb-3 border-b border-white/[0.06]">
              <div className="flex items-center gap-2">
                <div className="w-7 h-7 rounded-lg bg-amber-500/15 flex items-center justify-center">
                  <HelpCircle className="w-4 h-4 text-amber-400" />
                </div>
                <h3 className="font-bold text-slate-100 text-sm">Key Unknowns</h3>
              </div>
              <button
                type="button"
                onClick={() => onNavigateToTab('probes')}
                className="text-xs text-amber-400 hover:text-amber-300 flex items-center gap-1 transition-colors"
              >
                Interview Guide <ArrowRight className="w-3 h-3" />
              </button>
            </div>

            <div className="space-y-2 mt-3">
              {priorityGaps.length > 0 ? (
                priorityGaps.map(([key]) => {
                  const capKey = key as CapabilityKey;
                  return (
                    <button
                      key={key}
                      type="button"
                      onClick={() => {
                        if (onSelectCapability) onSelectCapability(capKey);
                        onNavigateToTab('probes');
                      }}
                      className="w-full p-3 bg-white/[0.02] hover:bg-white/[0.05] border border-white/[0.04] hover:border-amber-500/30 rounded-xl flex items-center justify-between cursor-pointer transition-all duration-200 text-left group"
                    >
                      <div>
                        <div className="font-semibold text-slate-200 text-xs group-hover:text-white transition-colors">
                          {CAPABILITY_NAMES[capKey] || key}
                        </div>
                        <div className="text-[10px] text-slate-500 mt-0.5">
                          No public repository artifacts
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <GlowBadge variant="neutral" size="sm">UNKNOWN</GlowBadge>
                      </div>
                    </button>
                  );
                })
              ) : (
                <div className="p-4 text-center text-emerald-400/60 text-xs">
                  All 12 capabilities have direct verified evidence.
                </div>
              )}
            </div>
          </GlassCard>
        </motion.div>
      </div>

      {/* Interview Questions Preview */}
      {topProbes.length > 0 && (
        <motion.div variants={staggerItem}>
          <GlassCard glow="violet">
            <div className="flex items-center justify-between pb-3 border-b border-white/[0.06]">
              <div className="flex items-center gap-2">
                <div className="w-7 h-7 rounded-lg bg-brand-500/15 flex items-center justify-center">
                  <MessageSquare className="w-4 h-4 text-brand-400" />
                </div>
                <h3 className="font-bold text-slate-100 text-sm">Recommended Interview Questions</h3>
              </div>
              <button
                type="button"
                onClick={() => onNavigateToTab('probes')}
                className="text-xs text-brand-400 hover:text-brand-300 font-medium flex items-center gap-1 transition-colors"
              >
                Full Guide <ArrowRight className="w-3 h-3" />
              </button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mt-3">
              {topProbes.map((probe, idx) => {
                const capKey = probe.capability_key as CapabilityKey;
                const matchedQuestion = (dossier.interview_questions || []).find(
                  (q) => q.target_capability === probe.capability_key
                );
                const questionText =
                  matchedQuestion?.question_text ||
                  `Explain your hands-on production experience with ${CAPABILITY_NAMES[capKey] || probe.capability_key}, detailing how you design and test these systems.`;
                const rationaleText =
                  matchedQuestion?.rationale ||
                  `Verify technical competence in ${CAPABILITY_NAMES[capKey] || probe.capability_key}.`;

                return (
                  <div key={idx} className="p-4 bg-white/[0.02] border border-white/[0.04] rounded-xl space-y-2 hover:border-brand-500/20 transition-colors">
                    <div className="flex items-center justify-between">
                      <GlowBadge variant="brand" size="sm">
                        {CAPABILITY_NAMES[capKey] || probe.capability_key}
                      </GlowBadge>
                      <span className="text-[10px] font-mono text-slate-500">
                        #{idx + 1}
                      </span>
                    </div>

                    <p className="text-xs text-slate-200 font-medium leading-relaxed">
                      &ldquo;{questionText}&rdquo;
                    </p>

                    <div className="text-[11px] text-slate-500 pt-1.5 border-t border-white/[0.04] leading-normal">
                      <strong className="text-slate-400">Rationale:</strong> {rationaleText}
                    </div>
                  </div>
                );
              })}
            </div>
          </GlassCard>
        </motion.div>
      )}
    </motion.div>
  );
};
