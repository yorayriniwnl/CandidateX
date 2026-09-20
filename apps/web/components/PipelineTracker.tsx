'use client';

import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { CheckCircle2, Clock, Loader2, ArrowRight, Layers } from 'lucide-react';
import { AnalysisStage, PipelineStageInfo } from '../types/cci';
import { GlassCard } from '@/components/ui/GlassCard';
import { GlassButton } from '@/components/ui/GlassButton';

export const PIPELINE_STAGES: { stage: AnalysisStage; label: string; desc: string }[] = [
  { stage: 'PARSING_CV', label: '1. CV Manifest Parsing', desc: 'Closed-world links & claim extraction' },
  { stage: 'INGESTING_SOURCES', label: '2. Safe Acquisition', desc: 'Sandboxed repository & deployment scan' },
  { stage: 'ANALYZING_ARTIFACTS', label: '3. Static Code & Infra Intel', desc: 'AST, migrations, tests, Docker, K8s' },
  { stage: 'BUILDING_EVIDENCE', label: '4. Evidence Registration', desc: 'Immutable records & fingerprints' },
  { stage: 'CALIBRATING_RELIABILITY', label: '5. Source Reliability', desc: 'Beta-Binomial Bayesian calibration' },
  { stage: 'ESTIMATING_OWNERSHIP', label: '6. Ownership Attribution', desc: 'Commit/line ratio & fork discounting' },
  { stage: 'COMPUTING_UNCERTAINTY', label: '7. Uncertainty Diagnostics', desc: 'Cluster bootstrap CI & contradiction D_k' },
  { stage: 'SCORING', label: '8. Formal Math Scoring', desc: 'Capability q_k, weights w_k, Coverage & RCI' },
  { stage: 'PRIORITIZING_PROBES', label: '9. Probe Prioritization', desc: 'Inquiry priority I_k & interview questions' },
  { stage: 'GENERATING_DOSSIER', label: '10. Dossier Synthesis', desc: 'Complete decision support snapshot' },
];

export const PipelineTracker: React.FC<{
  currentStageIndex?: number;
  isComplete?: boolean;
  onViewDossier?: () => void;
}> = ({ currentStageIndex = 9, isComplete = true, onViewDossier }) => {
  // Calculate completion percentage for the line
  const progressPercentage = isComplete ? 100 : (currentStageIndex / (PIPELINE_STAGES.length - 1)) * 100;

  return (
    <GlassCard className="p-6 space-y-6">
      <div className="flex items-center justify-between border-b border-slate-800 pb-4">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-blue-500/10 rounded-lg text-blue-400">
            <Layers className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-slate-100">Analysis Pipeline Progression</h2>
            <p className="text-xs text-slate-400">Deterministic stage execution adhering to formal paper pipeline</p>
          </div>
        </div>
        {isComplete && (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 rounded-full text-xs font-semibold">
            <CheckCircle2 className="w-3.5 h-3.5" /> Pipeline Completed
          </span>
        )}
      </div>

      {/* Vertical Timeline */}
      <div className="relative pl-3">
        {/* Animated connecting line */}
        <div className="absolute left-[27px] top-4 bottom-4 w-0.5 bg-slate-800 rounded-full" />
        <div 
          className="absolute left-[27px] top-4 w-0.5 rounded-full bg-gradient-to-b from-indigo-500 to-emerald-500 transition-all duration-500 ease-in-out"
          style={{ height: `calc(${progressPercentage}% - 32px)` }}
        />

        <div className="space-y-4 relative z-10">
          {PIPELINE_STAGES.map((s, idx) => {
            const isDone = idx < currentStageIndex || isComplete;
            const isActive = idx === currentStageIndex && !isComplete;
            
            // Accent color classes based on state
            const borderAccent = isDone ? 'border-l-emerald-500' : isActive ? 'border-l-indigo-500' : 'border-l-slate-700';

            return (
              <motion.div
                key={s.stage}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.3, delay: idx * 0.05 }}
                className="flex items-center gap-4"
              >
                <div className={`w-8 h-8 rounded-full flex items-center justify-center border-2 bg-slate-950 transition-colors shrink-0
                  ${isDone ? 'border-emerald-500/50' : isActive ? 'border-indigo-500/50' : 'border-slate-800'}
                `}>
                  <AnimatePresence mode="wait">
                    {isDone ? (
                      <motion.div key="done" initial={{ scale: 0 }} animate={{ scale: 1 }} exit={{ scale: 0 }}>
                        <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                      </motion.div>
                    ) : isActive ? (
                      <motion.div key="active" initial={{ scale: 0 }} animate={{ scale: 1 }} exit={{ scale: 0 }}>
                        <Loader2 className="w-4 h-4 text-indigo-400 animate-spin" />
                      </motion.div>
                    ) : (
                      <motion.div key="pending" initial={{ scale: 0 }} animate={{ scale: 1 }} exit={{ scale: 0 }}>
                        <Clock className="w-4 h-4 text-slate-600" />
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>

                <GlassCard variant="subtle" className={`flex-1 p-3 border-l-4 ${borderAccent} hover:border-l-4 transition-colors`}>
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium text-slate-200">{s.label}</span>
                    <span
                      className={`text-[10px] uppercase font-mono px-1.5 py-0.5 rounded-md ${
                        isDone
                          ? 'text-emerald-400 bg-emerald-500/10'
                          : isActive
                          ? 'text-indigo-400 bg-indigo-500/10'
                          : 'text-slate-500 bg-slate-800/50'
                      }`}
                    >
                      {isDone ? 'DONE' : isActive ? 'RUNNING' : 'QUEUED'}
                    </span>
                  </div>
                  <p className="text-xs text-slate-400 mt-1">{s.desc}</p>
                </GlassCard>
              </motion.div>
            );
          })}
        </div>
      </div>

      {isComplete && (
        <div className="pt-4 flex flex-col sm:flex-row items-center justify-between border-t border-slate-800/80 gap-4">
          <div className="text-xs text-slate-400">
            <span className="font-semibold text-slate-300">14 Verified Evidence Records</span> synthesized into Candidate Evidence Graph.
          </div>
          <GlassButton 
            variant="primary" 
            onClick={onViewDossier}
            icon={<ArrowRight className="w-4 h-4" />}
            iconPosition="right"
            className="animate-pulse shadow-[0_0_15px_rgba(16,185,129,0.3)] bg-emerald-600 hover:bg-emerald-500 text-white border-emerald-500"
          >
            Open Technical Dossier
          </GlassButton>
        </div>
      )}
    </GlassCard>
  );
};
