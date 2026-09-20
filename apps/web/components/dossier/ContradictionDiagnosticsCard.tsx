'use client';

import React from 'react';
import { AlertTriangle, CheckCircle2, Flame, Split } from 'lucide-react';
import { CapabilityConflict, CapabilityKey } from '../../types/cci';
import { GlassCard } from '@/components/ui/GlassCard';
import { GlowBadge } from '@/components/ui/GlowBadge';
import { Tooltip } from '@/components/ui/Tooltip';
import { motion } from 'framer-motion';

const CAPABILITY_LABELS: Record<CapabilityKey, string> = {
  backend_engineering: 'Backend Engineering',
  frontend_engineering: 'Frontend Engineering',
  database_engineering: 'Database Engineering',
  devops_cloud: 'DevOps & Cloud',
  machine_learning: 'Machine Learning',
  data_engineering: 'Data Engineering',
  algorithms_problem_solving: 'Algorithms & Problem Solving',
  testing_quality: 'Testing & Quality',
  security: 'Security & Privacy',
  software_architecture: 'Software Architecture',
  collaboration: 'Collaboration',
  documentation_communication: 'Documentation & Communication',
};

export const ContradictionDiagnosticsCard: React.FC<{
  conflicts: Record<CapabilityKey, CapabilityConflict>;
  onSelectCapability?: (key: CapabilityKey) => void;
  selectedCapability?: CapabilityKey | null;
}> = ({ conflicts, onSelectCapability, selectedCapability }) => {
  const conflictEntries = Object.entries(conflicts) as [CapabilityKey, CapabilityConflict][];
  const meaningfulConflicts = conflictEntries.filter(([_, c]) => c.has_meaningful_conflict);

  return (
    <GlassCard variant="strong" glow="amber" className="p-6 space-y-4">
      <div className="flex items-center justify-between border-b border-slate-800 pb-3">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-amber-500/10 rounded-lg text-amber-400">
            <Split className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-base font-semibold text-slate-100">Contradiction Diagnostics (D_k)</h2>
            <p className="text-xs text-slate-400">
              Positive support (P_k) vs Negative/Deficiency support (N_k) across independent sources
            </p>
          </div>
        </div>
        {meaningfulConflicts.length > 0 ? (
          <GlowBadge variant="warning" className="gap-1.5 font-semibold">
            <AlertTriangle className="w-3.5 h-3.5" />
            <span>{meaningfulConflicts.length} meaningful conflict(s) detected</span>
          </GlowBadge>
        ) : (
          <GlowBadge variant="success" className="gap-1.5 font-semibold">
            <CheckCircle2 className="w-3.5 h-3.5" />
            <span>No unresolved contradictions</span>
          </GlowBadge>
        )}
      </div>

      <motion.div 
        className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 pt-1"
        initial="hidden"
        animate="visible"
        variants={{
          hidden: { opacity: 0 },
          visible: { opacity: 1, transition: { staggerChildren: 0.1 } }
        }}
      >
        {conflictEntries.map(([key, conflict]) => {
          const isSelected = selectedCapability === key;
          const totalMass = conflict.positive_support_sum + conflict.negative_support_sum;
          const posPercent = totalMass > 0 ? Math.round((conflict.positive_support_sum / totalMass) * 100) : 50;
          const negPercent = 100 - posPercent;

          return (
            <motion.div 
              key={key}
              variants={{
                hidden: { opacity: 0, y: 10 },
                visible: { opacity: 1, y: 0 }
              }}
              onClick={() => onSelectCapability && onSelectCapability(key)}
            >
              <GlassCard
                variant="subtle"
                glow={conflict.has_meaningful_conflict ? 'rose' : 'emerald'}
                className={`p-3.5 cursor-pointer h-full ${
                  isSelected ? 'border-indigo-500 ring-1 ring-indigo-500/30' : ''
                }`}
              >
                <div className="flex items-start justify-between gap-2 mb-2">
                  <span className="text-xs font-semibold text-slate-200">
                    {CAPABILITY_LABELS[key] || key}
                  </span>
                  {conflict.has_meaningful_conflict ? (
                    <GlowBadge variant="danger" size="sm" className="font-bold uppercase tracking-wider flex items-center gap-1">
                      <Flame className="w-2.5 h-2.5" />
                      Conflict
                    </GlowBadge>
                  ) : totalMass > 0 ? (
                    <GlowBadge variant="success" size="sm" className="font-medium">
                      Aligned
                    </GlowBadge>
                  ) : (
                    <GlowBadge variant="neutral" size="sm">
                      No Data
                    </GlowBadge>
                  )}
                </div>

                {/* Support Balance Bar */}
                <div className="space-y-1">
                  <div className="flex justify-between text-[10px] font-mono text-slate-400">
                    <span className="text-emerald-400">P_k: {conflict.positive_support_sum.toFixed(2)}</span>
                    <span className="text-rose-400">N_k: {conflict.negative_support_sum.toFixed(2)}</span>
                  </div>
                  <div className="h-1.5 w-full bg-slate-800 rounded-full flex overflow-hidden">
                    <motion.div
                      className="bg-emerald-500"
                      initial={{ width: 0 }}
                      animate={{ width: `${totalMass > 0 ? posPercent : 0}%` }}
                      transition={{ duration: 0.8, ease: "easeOut" }}
                      title={`Positive support: ${posPercent}%`}
                    />
                    <motion.div
                      className="bg-rose-500"
                      initial={{ width: 0 }}
                      animate={{ width: `${totalMass > 0 ? negPercent : 0}%` }}
                      transition={{ duration: 0.8, ease: "easeOut" }}
                      title={`Negative support: ${negPercent}%`}
                    />
                  </div>
                </div>

                {/* Diagnostic Index */}
                <div className="mt-2.5 pt-2 border-t border-slate-800/60 flex items-center justify-between text-[11px]">
                  <span className="text-slate-500 font-mono">D_k Diagnostic:</span>
                  <Tooltip content="Measures positive vs negative evidence support balance. -1 means all negative, +1 means all positive.">
                    <span
                      className={`font-mono font-bold cursor-help ${
                        conflict.contradiction_diagnostic > 0.2
                          ? 'text-emerald-400'
                          : conflict.contradiction_diagnostic < -0.2
                          ? 'text-rose-400'
                          : 'text-amber-400'
                      }`}
                    >
                      {conflict.contradiction_diagnostic > 0 ? '+' : ''}
                      {conflict.contradiction_diagnostic.toFixed(2)}
                    </span>
                  </Tooltip>
                </div>
              </GlassCard>
            </motion.div>
          );
        })}
      </motion.div>

      <div className="pt-2 text-[11px] text-slate-500 flex items-center justify-between border-t border-slate-800/80">
        <span>* D_k in [-1, +1] measures net directional support. High P_k and high N_k simultaneous evidence triggers interview probe generation.</span>
        <span>Paper Invariant: Contradictions are never averaged away silently.</span>
      </div>
    </GlassCard>
  );
};
