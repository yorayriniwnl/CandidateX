'use client';

import React, { useState } from 'react';
import {
  ChevronDown,
  ChevronRight,
  ClipboardCheck,
  HelpCircle,
  ListOrdered,
  MessageSquare,
  ShieldAlert,
  Sparkles,
  Target,
} from 'lucide-react';
import { CapabilityKey, InterviewQuestion, ProbePriority } from '../../types/cci';

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

export const InterviewProbesPanel: React.FC<{
  probes: ProbePriority[];
  questions: InterviewQuestion[];
  onSelectCapability?: (key: CapabilityKey) => void;
  selectedCapability?: CapabilityKey | null;
  onOpenScorecard?: () => void;
  onInspectEvidence?: (evidenceId: string) => void;
}> = ({ probes, questions, onSelectCapability, selectedCapability, onOpenScorecard, onInspectEvidence }) => {
  const [expandedQuestionId, setExpandedQuestionId] = useState<string | null>(null);

  // Group questions by capability
  const questionsByCapability: Record<CapabilityKey, InterviewQuestion[]> = {} as any;
  questions.forEach((q) => {
    if (!questionsByCapability[q.target_capability]) {
      questionsByCapability[q.target_capability] = [];
    }
    questionsByCapability[q.target_capability].push(q);
  });

  const sortedProbes = [...probes].sort((a, b) => a.rank - b.rank);

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl space-y-4">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-800 pb-3">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-indigo-500/10 rounded-lg text-indigo-400">
            <ListOrdered className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-base font-semibold text-slate-100">Prioritized Technical Interview Probes</h2>
            <p className="text-xs text-slate-400">
              Ranked 1..12 by information value I_k = w_k · (1 - Cov_k) + α · s_k + β · C_k
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2.5">
          <span className="hidden sm:inline-block px-2 py-1 bg-slate-800 border border-slate-700 rounded text-xs text-slate-300 font-mono">
            {questions.length} Grounded Question(s)
          </span>
          {onOpenScorecard && (
            <button
              type="button"
              onClick={onOpenScorecard}
              className="px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-semibold shadow-md shadow-indigo-600/20 flex items-center gap-1.5 transition-colors"
            >
              <ClipboardCheck className="w-4 h-4" />
              <span>Record Scorecard</span>
            </button>
          )}
        </div>
      </div>

      <div className="space-y-3 pt-1">
        {sortedProbes.map((probe) => {
          const capQuestions = questionsByCapability[probe.capability_key] || [];
          const isSelected = selectedCapability === probe.capability_key;
          const isPriorityHigh = probe.rank <= 3;

          return (
            <div
              key={probe.capability_key}
              className={`border rounded-lg p-4 transition-all ${
                isSelected
                  ? 'bg-slate-800/80 border-indigo-500 ring-1 ring-indigo-500/30'
                  : 'bg-slate-950/70 border-slate-800 hover:border-slate-700'
              }`}
            >
              {/* Probe Priority Header */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                <div className="flex items-center gap-3">
                  <span
                    className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-black font-mono shrink-0 ${
                      isPriorityHigh
                        ? 'bg-indigo-500 text-white shadow-sm shadow-indigo-500/50'
                        : 'bg-slate-800 text-slate-300 border border-slate-700'
                    }`}
                  >
                    #{probe.rank}
                  </span>
                  <div>
                    <div className="flex items-center gap-2">
                      <h3
                        className="text-sm font-semibold text-slate-100 cursor-pointer hover:text-indigo-400 transition-colors"
                        onClick={() => onSelectCapability && onSelectCapability(probe.capability_key)}
                      >
                        {CAPABILITY_LABELS[probe.capability_key] || probe.capability_key}
                      </h3>
                      {isPriorityHigh && (
                        <span className="px-1.5 py-0.5 bg-indigo-500/15 text-indigo-400 border border-indigo-500/30 rounded text-[10px] font-semibold uppercase tracking-wider">
                          High Priority
                        </span>
                      )}
                    </div>
                    <p className="text-[11px] text-slate-400 font-mono mt-0.5">
                      Composite Priority I_k: {probe.priority_score.toFixed(3)}
                    </p>
                  </div>
                </div>

                {/* Mathematical Decomposition Badges */}
                <div className="flex items-center gap-2 text-[11px] font-mono">
                  <span
                    className="px-2 py-0.5 bg-slate-900 border border-slate-800 text-slate-400 rounded"
                    title="Role Weight (w_k)"
                  >
                    w: {(probe.role_weight * 100).toFixed(0)}%
                  </span>
                  <span
                    className="px-2 py-0.5 bg-slate-900 border border-slate-800 text-slate-400 rounded"
                    title="Coverage Gap Term: w_k * (1 - Cov_k)"
                  >
                    gap: {probe.coverage_gap_term.toFixed(3)}
                  </span>
                  <span
                    className="px-2 py-0.5 bg-slate-900 border border-slate-800 text-slate-400 rounded"
                    title="Uncertainty / Dispersion Term"
                  >
                    uncert: {probe.uncertainty_term.toFixed(3)}
                  </span>
                  <span
                    className="px-2 py-0.5 bg-slate-900 border border-slate-800 text-slate-400 rounded"
                    title="Contradiction Term"
                  >
                    contra: {probe.contradiction_term.toFixed(3)}
                  </span>
                </div>
              </div>

              {/* Grounded Questions for this capability */}
              {capQuestions.length > 0 ? (
                <div className="mt-3.5 space-y-2 border-t border-slate-800/80 pt-3">
                  {capQuestions.map((q) => {
                    const isExpanded = expandedQuestionId === q.question_id;

                    return (
                      <div
                        key={q.question_id}
                        className="bg-slate-900/90 border border-slate-800 rounded-lg p-3 space-y-2"
                      >
                        <div
                          className="flex items-start justify-between gap-3 cursor-pointer select-none"
                          onClick={() => setExpandedQuestionId(isExpanded ? null : q.question_id)}
                        >
                          <div className="flex items-start gap-2 text-xs text-slate-200">
                            <MessageSquare className="w-4 h-4 text-indigo-400 shrink-0 mt-0.5" />
                            <span className="font-medium leading-relaxed">{q.question_text}</span>
                          </div>
                          <button
                            type="button"
                            className="text-slate-400 hover:text-slate-200 shrink-0 p-1"
                          >
                            {isExpanded ? (
                              <ChevronDown className="w-4 h-4" />
                            ) : (
                              <ChevronRight className="w-4 h-4" />
                            )}
                          </button>
                        </div>

                        {/* Rationale / Verification guidance accordion */}
                        {isExpanded && (
                          <div className="pt-2 border-t border-slate-800/60 text-xs space-y-2.5 text-slate-300">
                            <div>
                              <span className="font-semibold text-indigo-300 block mb-0.5">
                                Grounded Rationale:
                              </span>
                              <p className="text-slate-400 leading-relaxed">{q.rationale}</p>
                            </div>

                            <div>
                              <span className="font-semibold text-emerald-300 block mb-0.5">
                                Verification Guidance for Interviewer:
                              </span>
                              <p className="text-slate-300 bg-slate-950 p-2.5 rounded border border-slate-800 font-sans leading-relaxed">
                                {q.verification_guidance}
                              </p>
                            </div>

                            {q.suggested_followups && q.suggested_followups.length > 0 && (
                              <div>
                                <span className="font-semibold text-slate-400 block mb-1">
                                  Suggested Follow-up Probes:
                                </span>
                                <ul className="list-disc list-inside space-y-1 text-slate-400 text-[11px]">
                                  {q.suggested_followups.map((fu, idx) => (
                                    <li key={idx}>{fu}</li>
                                  ))}
                                </ul>
                              </div>
                            )}

                            {q.grounding_evidence_ids && q.grounding_evidence_ids.length > 0 && (
                              <div className="text-[11px] font-mono text-slate-500 pt-1 flex items-center gap-1.5">
                                <span>Grounding Evidence IDs:</span>
                                <div className="flex flex-wrap gap-1">
                                  {q.grounding_evidence_ids.map((id) => (
                                    <button
                                      key={id}
                                      type="button"
                                      onClick={() => onInspectEvidence && onInspectEvidence(id)}
                                      className="px-1.5 py-0.5 bg-slate-950 hover:bg-indigo-950/40 border border-slate-800 hover:border-indigo-500/50 text-indigo-400 hover:text-indigo-300 rounded text-[10px] transition-colors cursor-pointer font-mono"
                                      title={`Inspect 6-Factor Confidence Decomposition for ${id}`}
                                    >
                                      {id}
                                    </button>
                                  ))}
                                </div>
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              ) : (
                <div className="mt-2 text-xs text-slate-500 italic">
                  No automated probe question generated for this capability.
                </div>
              )}
            </div>
          );
        })}
      </div>

      <div className="pt-2 text-[11px] text-slate-500 flex items-center justify-between border-t border-slate-800/80">
        <span>* Questions are grounded directly in extracted repository evidence and CV declarations.</span>
        <span>Interviewers remain the ultimate evaluators of candidate technical depth.</span>
      </div>
    </div>
  );
};
