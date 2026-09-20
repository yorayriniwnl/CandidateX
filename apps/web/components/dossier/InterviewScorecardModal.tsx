'use client';

import React, { useState, useEffect } from 'react';
import {
  Check,
  ChevronDown,
  ChevronRight,
  ClipboardCheck,
  Loader2,
  MessageSquare,
  ShieldAlert,
  ShieldCheck,
  X,
} from 'lucide-react';
import {
  CapabilityKey,
  HiringRecommendation,
  InterviewFeedbackPayload,
  InterviewFeedbackResponse,
  InterviewQuestion,
  ProbeEvaluationItem,
  ProbePriority,
} from '../../types/cci';
import { submitInterviewFeedback } from '../../lib/api';
import { GlassModal } from '@/components/ui/GlassModal';
import { GlassInput } from '@/components/ui/GlassInput';
import { GlassButton } from '@/components/ui/GlassButton';
import { GlassCard } from '@/components/ui/GlassCard';
import { GlowBadge } from '@/components/ui/GlowBadge';
import { motion, AnimatePresence } from 'framer-motion';

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

const RATING_DESCRIPTIONS: Record<number, string> = {
  1: 'Significantly Below Bar',
  2: 'Developing / Weak',
  3: 'Meets Role Bar',
  4: 'Strong Competence',
  5: 'Exceptional / Role Model',
};

const RECOMMENDATION_CONFIG: Record<
  HiringRecommendation,
  { label: string; desc: string; variant: 'primary' | 'secondary' | 'danger'; activeClassOverride: string }
> = {
  strong_hire: {
    label: 'Strong Hire',
    desc: 'Clear technical mastery across core capabilities',
    variant: 'primary',
    activeClassOverride: '!bg-emerald-500/20 !border-emerald-500 !text-emerald-300 ring-1 ring-emerald-500/40',
  },
  lean_hire: {
    label: 'Lean Hire',
    desc: 'Meets role bar; minor gaps manageable with team onboarding',
    variant: 'secondary',
    activeClassOverride: '!bg-indigo-500/20 !border-indigo-500 !text-indigo-300 ring-1 ring-indigo-500/40',
  },
  lean_no_hire: {
    label: 'Lean No Hire',
    desc: 'Key capability gaps unresolved during technical inquiry',
    variant: 'secondary',
    activeClassOverride: '!bg-amber-500/20 !border-amber-500 !text-amber-300 ring-1 ring-amber-500/40',
  },
  no_hire: {
    label: 'No Hire',
    desc: 'Significant contradictions or severe lack of verified competence',
    variant: 'danger',
    activeClassOverride: '!bg-rose-500/20 !border-rose-500 !text-rose-300 ring-1 ring-rose-500/40',
  },
};

interface InterviewScorecardModalProps {
  isOpen: boolean;
  onClose: () => void;
  candidateId: string;
  candidateName?: string;
  probes: ProbePriority[];
  questions: InterviewQuestion[];
  onFeedbackSubmitted?: (feedback: InterviewFeedbackResponse) => void;
}

export const InterviewScorecardModal: React.FC<InterviewScorecardModalProps> = ({
  isOpen,
  onClose,
  candidateId,
  candidateName = 'Candidate',
  probes,
  questions,
  onFeedbackSubmitted,
}) => {
  const [interviewerName, setInterviewerName] = useState('');
  const [overallRecommendation, setOverallRecommendation] = useState<HiringRecommendation>('lean_hire');
  const [overallNotes, setOverallNotes] = useState('');
  const [probeRatings, setProbeRatings] = useState<
    Record<CapabilityKey, { rating: number; notes: string; isGapResolved: boolean }>
  >({} as any);
  const [expandedProbe, setExpandedProbe] = useState<CapabilityKey | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successResponse, setSuccessResponse] = useState<InterviewFeedbackResponse | null>(null);

  const draftKey = `cci-scorecard-draft-${candidateId}`;

  // Restore draft on mount
  useEffect(() => {
    if (isOpen) {
      const draft = localStorage.getItem(draftKey);
      if (draft) {
        try {
          const parsed = JSON.parse(draft);
          if (parsed.interviewerName) setInterviewerName(parsed.interviewerName);
          if (parsed.overallRecommendation) setOverallRecommendation(parsed.overallRecommendation);
          if (parsed.overallNotes) setOverallNotes(parsed.overallNotes);
          if (parsed.probeRatings) setProbeRatings(parsed.probeRatings);
        } catch (e) {
          console.error("Failed to parse scorecard draft", e);
        }
      } else {
        // Initialize default ratings
        const initial: Record<CapabilityKey, { rating: number; notes: string; isGapResolved: boolean }> = {} as any;
        probes.forEach((p) => {
          initial[p.capability_key] = { rating: 3, notes: '', isGapResolved: false };
        });
        setProbeRatings(initial);
      }
      
      if (probes.length > 0) {
        setExpandedProbe(probes[0].capability_key);
      }
    }
  }, [isOpen, candidateId, probes, draftKey]);

  // Save to localStorage on change
  useEffect(() => {
    if (isOpen && Object.keys(probeRatings).length > 0) {
      const stateToSave = {
        interviewerName,
        overallRecommendation,
        overallNotes,
        probeRatings
      };
      localStorage.setItem(draftKey, JSON.stringify(stateToSave));
    }
  }, [interviewerName, overallRecommendation, overallNotes, probeRatings, isOpen, draftKey]);

  if (!isOpen) return null;

  const questionsByCapability: Record<CapabilityKey, InterviewQuestion[]> = {} as any;
  questions.forEach((q) => {
    if (!questionsByCapability[q.target_capability]) {
      questionsByCapability[q.target_capability] = [];
    }
    questionsByCapability[q.target_capability].push(q);
  });

  const sortedProbes = [...probes].sort((a, b) => a.rank - b.rank);

  const handleRatingChange = (key: CapabilityKey, rating: number) => {
    setProbeRatings((prev) => ({
      ...prev,
      [key]: { ...(prev[key] || { notes: '', isGapResolved: false }), rating },
    }));
  };

  const handleNotesChange = (key: CapabilityKey, notes: string) => {
    setProbeRatings((prev) => ({
      ...prev,
      [key]: { ...(prev[key] || { rating: 3, isGapResolved: false }), notes },
    }));
  };

  const handleGapResolvedChange = (key: CapabilityKey, isGapResolved: boolean) => {
    setProbeRatings((prev) => ({
      ...prev,
      [key]: { ...(prev[key] || { rating: 3, notes: '' }), isGapResolved },
    }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);

    if (!interviewerName.trim()) {
      setErrorMessage('Please enter the interviewer name to record this audited evaluation.');
      return;
    }

    const probeEvaluations: ProbeEvaluationItem[] = sortedProbes.map((p) => {
      const state = probeRatings[p.capability_key] || { rating: 3, notes: '', isGapResolved: false };
      return {
        capability_key: p.capability_key,
        rating: state.rating,
        notes: state.notes.trim() || `Evaluated probe for ${CAPABILITY_LABELS[p.capability_key]}`,
        is_gap_resolved: state.isGapResolved,
      };
    });

    const payload: InterviewFeedbackPayload = {
      candidate_id: candidateId,
      interviewer_name: interviewerName.trim(),
      probe_evaluations: probeEvaluations,
      overall_recommendation: overallRecommendation,
      overall_notes: overallNotes.trim() || undefined,
    };

    setIsSubmitting(true);
    try {
      const res = await submitInterviewFeedback(payload);
      setSuccessResponse(res);
      // Clear draft on success
      localStorage.removeItem(draftKey);
      if (onFeedbackSubmitted) {
        onFeedbackSubmitted(res);
      }
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to submit interview feedback to audit log.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCloseAndReset = () => {
    setSuccessResponse(null);
    setErrorMessage(null);
    onClose();
  };

  if (successResponse) {
    return (
      <GlassModal isOpen={isOpen} onClose={handleCloseAndReset} title="Technical Interview Scorecard" size="md">
        <GlassCard variant="strong" glow="emerald" className="p-8 flex flex-col items-center text-center space-y-4 my-auto">
          <motion.div 
            initial={{ scale: 0 }} 
            animate={{ scale: 1 }} 
            className="w-16 h-16 bg-emerald-500/20 border border-emerald-500/30 rounded-full flex items-center justify-center text-emerald-400"
          >
            <Check className="w-8 h-8" />
          </motion.div>
          <div className="space-y-1">
            <h3 className="text-xl font-bold text-slate-100">
              Scorecard Successfully Recorded to Audit Trail
            </h3>
            <p className="text-sm text-slate-400 max-w-md">
              Interviewer feedback from{' '}
              <span className="text-slate-200 font-medium">{successResponse.interviewer_name}</span>{' '}
              has been immutably persisted with {successResponse.evaluations_count} probe evaluations.
            </p>
          </div>
          <GlassCard variant="subtle" className="p-4 text-xs font-mono text-slate-400 space-y-1 text-left w-full max-w-md">
            <div>
              <span className="text-slate-500">Audit Event ID:</span>{' '}
              <span className="text-indigo-400">{successResponse.audit_event_id}</span>
            </div>
            <div>
              <span className="text-slate-500">Recorded At:</span>{' '}
              <span className="text-slate-300">{successResponse.recorded_at}</span>
            </div>
            <div>
              <span className="text-slate-500">Recommendation:</span>{' '}
              <span className="text-emerald-400 uppercase font-semibold">
                {overallRecommendation.replace('_', ' ')}
              </span>
            </div>
          </GlassCard>
          <GlassButton variant="primary" onClick={handleCloseAndReset} className="w-full max-w-md mt-4">
            Done & View Audit History
          </GlassButton>
        </GlassCard>
      </GlassModal>
    );
  }

  return (
    <GlassModal
      isOpen={isOpen}
      onClose={handleCloseAndReset}
      title="Technical Interview Scorecard"
      subtitle={`Record inquiry probe evaluations for ${candidateName}`}
      size="xl"
    >
      <form onSubmit={handleSubmit} className="flex flex-col h-full max-h-[85vh]">
        <div className="p-6 overflow-y-auto space-y-6 flex-1 text-slate-300 text-sm">
          {errorMessage && (
            <div className="p-3.5 bg-rose-500/10 border border-rose-500/30 rounded-xl text-rose-400 text-xs flex items-center gap-2.5">
              <ShieldAlert className="w-4 h-4 shrink-0" />
              <span>{errorMessage}</span>
            </div>
          )}

          <div className="space-y-2">
            <label className="block text-xs font-semibold text-slate-200 uppercase tracking-wider">
              Technical Interviewer Name <span className="text-rose-400">*</span>
            </label>
            <GlassInput
              variant="text"
              required
              value={interviewerName}
              onChange={(e) => setInterviewerName(e.target.value)}
              placeholder="e.g. Alex Morgan, Staff Software Engineer"
            />
          </div>

          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <label className="text-xs font-semibold text-slate-200 uppercase tracking-wider">
                Overall Technical Hiring Recommendation <span className="text-rose-400">*</span>
              </label>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {(Object.keys(RECOMMENDATION_CONFIG) as HiringRecommendation[]).map((recKey) => {
                const config = RECOMMENDATION_CONFIG[recKey];
                const isSelected = overallRecommendation === recKey;

                return (
                  <GlassButton
                    key={recKey}
                    variant={config.variant}
                    onClick={() => setOverallRecommendation(recKey)}
                    className={`h-auto flex-col items-start text-left p-4 ${
                      isSelected ? config.activeClassOverride : 'opacity-70'
                    }`}
                  >
                    <div className="flex items-center justify-between w-full">
                      <span className="font-semibold text-sm">
                        {config.label}
                      </span>
                      {isSelected && <Check className="w-4 h-4" />}
                    </div>
                    <p className="text-xs font-normal mt-1 opacity-80 whitespace-normal">{config.desc}</p>
                  </GlassButton>
                );
              })}
            </div>
          </div>

          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-xs font-semibold text-slate-200 uppercase tracking-wider">
                  Candidate Capability Probe Evaluations
                </h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  Evaluate each prioritized inquiry. Mark if candidate demonstrated resolution of gaps.
                </p>
              </div>
              <GlowBadge variant="brand" size="sm">
                {sortedProbes.length} Probes
              </GlowBadge>
            </div>

            <div className="space-y-3">
              {sortedProbes.map((probe) => {
                const capKey = probe.capability_key;
                const isExpanded = expandedProbe === capKey;
                const state = probeRatings[capKey] || { rating: 3, notes: '', isGapResolved: false };
                const capQuestions = questionsByCapability[capKey] || [];
                const primaryQuestion = capQuestions[0];

                return (
                  <GlassCard
                    key={capKey}
                    variant={isExpanded ? 'default' : 'subtle'}
                    className="overflow-hidden"
                  >
                    <div
                      onClick={() => setExpandedProbe(isExpanded ? null : capKey)}
                      className="p-3.5 flex items-center justify-between cursor-pointer select-none gap-3"
                    >
                      <div className="flex items-center gap-3">
                        <span className="w-6 h-6 rounded-full bg-slate-800 border border-slate-700 text-slate-300 font-mono text-xs flex items-center justify-center font-bold">
                          #{probe.rank}
                        </span>
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="font-semibold text-slate-100 text-sm">
                              {CAPABILITY_LABELS[capKey] || capKey}
                            </span>
                            {state.isGapResolved && (
                              <GlowBadge variant="success" size="sm" className="gap-1 px-1.5 py-0">
                                <Check className="w-2.5 h-2.5" /> Resolved
                              </GlowBadge>
                            )}
                          </div>
                          <div className="text-[11px] text-slate-400 font-mono">
                            Weight: {(probe.role_weight * 100).toFixed(0)}% • I_k:{' '}
                            {probe.priority_score.toFixed(3)}
                          </div>
                        </div>
                      </div>

                      <div className="flex items-center gap-3">
                        <span className="px-2.5 py-1 bg-slate-900 border border-slate-700 rounded-lg text-xs font-semibold text-indigo-300">
                          {state.rating}/5 - {RATING_DESCRIPTIONS[state.rating]}
                        </span>
                        {isExpanded ? (
                          <ChevronDown className="w-4 h-4 text-slate-400" />
                        ) : (
                          <ChevronRight className="w-4 h-4 text-slate-400" />
                        )}
                      </div>
                    </div>

                    <AnimatePresence>
                      {isExpanded && (
                        <motion.div
                          initial={{ height: 0, opacity: 0 }}
                          animate={{ height: 'auto', opacity: 1 }}
                          exit={{ height: 0, opacity: 0 }}
                          className="border-t border-slate-800 bg-slate-900/40"
                        >
                          <div className="p-4 space-y-4">
                            {primaryQuestion && (
                              <div className="p-3 bg-slate-950/80 border border-slate-800/80 rounded-lg space-y-1.5 text-xs">
                                <div className="flex items-center gap-1.5 text-indigo-300 font-medium">
                                  <MessageSquare className="w-3.5 h-3.5" />
                                  <span>Grounded Probe Question:</span>
                                </div>
                                <p className="text-slate-200 italic leading-relaxed">
                                  &ldquo;{primaryQuestion.question_text}&rdquo;
                                </p>
                                {primaryQuestion.verification_guidance && (
                                  <p className="text-[11px] text-slate-400 border-t border-slate-800 pt-1 mt-1">
                                    <span className="font-semibold text-emerald-400">
                                      Guidance:
                                    </span>{' '}
                                    {primaryQuestion.verification_guidance}
                                  </p>
                                )}
                              </div>
                            )}

                            <div className="space-y-1.5">
                              <label className="text-xs font-medium text-slate-300 block">
                                Technical Competence Rating (1 - 5):
                              </label>
                              <div className="grid grid-cols-5 gap-2">
                                {[1, 2, 3, 4, 5].map((val) => {
                                  const isSelected = state.rating === val;
                                  return (
                                    <button
                                      key={val}
                                      type="button"
                                      onClick={() => handleRatingChange(capKey, val)}
                                      className={`py-2 px-1 rounded-lg border text-center transition-all text-xs font-medium ${
                                        isSelected
                                          ? 'bg-indigo-600 border-indigo-400 text-white shadow-md shadow-indigo-500/20 scale-[1.02]'
                                          : 'bg-slate-950 border-slate-800 text-slate-300 hover:border-slate-700 hover:bg-slate-900'
                                      }`}
                                    >
                                      <div className="font-bold text-sm">{val}</div>
                                      <div className="text-[9px] text-slate-400 truncate mt-0.5">
                                        {val === 1
                                          ? 'Below'
                                          : val === 2
                                          ? 'Weak'
                                          : val === 3
                                          ? 'Meets'
                                          : val === 4
                                          ? 'Strong'
                                          : 'Exceptional'}
                                      </div>
                                    </button>
                                  );
                                })}
                              </div>
                            </div>

                            <label className="flex items-center gap-2.5 cursor-pointer select-none p-2.5 bg-slate-950/60 border border-slate-800 rounded-lg hover:border-slate-700 transition-colors">
                              <input
                                type="checkbox"
                                checked={state.isGapResolved}
                                onChange={(e) => handleGapResolvedChange(capKey, e.target.checked)}
                                className="w-4 h-4 rounded border-slate-700 text-indigo-600 focus:ring-indigo-500 bg-slate-900"
                              />
                              <div className="text-xs">
                                <span className="font-semibold text-slate-200">
                                  Capability Gap / Contradiction Resolved
                                </span>
                                <span className="text-slate-400 block text-[11px]">
                                  Check if the candidate successfully defended this area and demonstrated verified competence.
                                </span>
                              </div>
                            </label>

                            <div className="space-y-1">
                              <label className="text-xs font-medium text-slate-300 block">
                                Qualitative Notes & Code Walkthrough Observations:
                              </label>
                              <GlassInput
                                variant="textarea"
                                value={state.notes}
                                onChange={(e) => handleNotesChange(capKey, e.target.value)}
                                placeholder="Candidate articulated nuances well, explained concurrency trade-offs..."
                              />
                            </div>
                          </div>
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </GlassCard>
                );
              })}
            </div>
          </div>

          <div className="space-y-2">
            <label className="block text-xs font-semibold text-slate-200 uppercase tracking-wider">
              Overall Interview Debrief Notes (Optional)
            </label>
            <GlassInput
              variant="textarea"
              value={overallNotes}
              onChange={(e) => setOverallNotes(e.target.value)}
              placeholder="Summary of technical discussion, communication clarity, problem-solving structure, and key strengths..."
            />
          </div>
        </div>

        <div className="p-4 border-t border-slate-800 bg-slate-950 flex flex-col sm:flex-row items-center justify-between gap-3">
          <div className="text-[11px] text-slate-400 flex items-center gap-1.5">
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
            <span>Governance invariant: Evaluations are immutable once submitted.</span>
          </div>

          <div className="flex items-center gap-2.5 w-full sm:w-auto">
            <GlassButton variant="ghost" onClick={handleCloseAndReset} className="flex-1 sm:flex-initial">
              Cancel
            </GlassButton>
            <GlassButton
              variant="primary"
              onClick={handleSubmit}
              disabled={isSubmitting}
              loading={isSubmitting}
              icon={!isSubmitting ? <Check className="w-4 h-4" /> : undefined}
              className="flex-1 sm:flex-initial"
            >
              Submit Scorecard to Audit Trail
            </GlassButton>
          </div>
        </div>
      </form>
    </GlassModal>
  );
};
