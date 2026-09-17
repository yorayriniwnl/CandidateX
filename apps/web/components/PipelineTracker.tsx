'use client';

import React from 'react';
import { CheckCircle2, Clock, Loader2, ArrowRight, FileCheck, Layers } from 'lucide-react';
import { AnalysisStage, PipelineStageInfo } from '../types/cci';

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
  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl space-y-6">
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

      {/* Visual Stepper */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {PIPELINE_STAGES.map((s, idx) => {
          const isDone = idx < currentStageIndex || isComplete;
          const isActive = idx === currentStageIndex && !isComplete;
          const isPending = idx > currentStageIndex && !isComplete;

          return (
            <div
              key={s.stage}
              className={`p-3 rounded-lg border transition-all flex items-start gap-3 ${
                isDone
                  ? 'bg-slate-950/60 border-emerald-500/30 text-slate-200'
                  : isActive
                  ? 'bg-blue-500/10 border-blue-500/50 text-blue-200'
                  : 'bg-slate-950/20 border-slate-800/80 text-slate-500'
              }`}
            >
              <div className="mt-0.5 shrink-0">
                {isDone ? (
                  <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                ) : isActive ? (
                  <Loader2 className="w-4 h-4 text-blue-400 animate-spin" />
                ) : (
                  <Clock className="w-4 h-4 text-slate-600" />
                )}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-medium truncate">{s.label}</span>
                  <span
                    className={`text-[10px] uppercase font-mono px-1.5 py-0.2 rounded ${
                      isDone
                        ? 'text-emerald-400 bg-emerald-500/10'
                        : isActive
                        ? 'text-blue-400 bg-blue-500/10'
                        : 'text-slate-600'
                    }`}
                  >
                    {isDone ? 'DONE' : isActive ? 'RUNNING' : 'QUEUED'}
                  </span>
                </div>
                <p className="text-[11px] text-slate-400 truncate mt-0.5">{s.desc}</p>
              </div>
            </div>
          );
        })}
      </div>

      {isComplete && (
        <div className="pt-2 flex items-center justify-between border-t border-slate-800/80">
          <div className="text-xs text-slate-400">
            <span className="font-semibold text-slate-300">14 Verified Evidence Records</span> synthesized into Candidate Evidence Graph.
          </div>
          <button
            type="button"
            onClick={onViewDossier}
            className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-sm font-medium transition-colors flex items-center gap-2 shadow-lg shadow-indigo-600/20"
          >
            <span>Open Technical Dossier</span>
            <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      )}
    </div>
  );
};
