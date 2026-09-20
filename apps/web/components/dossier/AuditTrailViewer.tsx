'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  AlertCircle,
  Award,
  Check,
  ChevronDown,
  ChevronRight,
  Clock,
  History,
  Loader2,
  RefreshCw,
  Scale,
  ShieldCheck,
  Sliders,
  User,
  X,
} from 'lucide-react';
import { AuditEventItem, CapabilityKey, HiringRecommendation } from '../../types/cci';
import { fetchCandidateAuditTrail } from '../../lib/api';
import { GlassCard } from '@/components/ui/GlassCard';
import { GlowBadge } from '@/components/ui/GlowBadge';
import { GlassButton } from '@/components/ui/GlassButton';
import { ProgressBar } from '@/components/ui/ProgressBar';

const CAPABILITY_LABELS: Record<string, string> = {
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

const RECOMMENDATION_VARIANTS: Record<string, 'success' | 'brand' | 'warning' | 'danger'> = {
  strong_hire: 'success',
  lean_hire: 'brand',
  lean_no_hire: 'warning',
  no_hire: 'danger',
};

interface AuditTrailViewerProps {
  candidateId: string;
  refreshTrigger?: number;
}

const staggerContainer = {
  animate: { transition: { staggerChildren: 0.1 } },
};
const staggerItem = {
  initial: { opacity: 0, x: -10 },
  animate: { opacity: 1, x: 0, transition: { duration: 0.3 } },
  exit: { opacity: 0, scale: 0.95 },
};

export const AuditTrailViewer: React.FC<AuditTrailViewerProps> = ({
  candidateId,
  refreshTrigger = 0,
}) => {
  const [events, setEvents] = useState<AuditEventItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expandedEvents, setExpandedEvents] = useState<Record<string, boolean>>({});
  const [eventTypeFilter, setEventTypeFilter] = useState<'all' | 'override' | 'interview'>('all');

  const loadAuditTrail = useCallback(
    async (isManualRefresh = false) => {
      if (isManualRefresh) {
        setIsRefreshing(true);
      } else {
        setIsLoading(true);
      }
      setError(null);

      try {
        const data = await fetchCandidateAuditTrail(candidateId);
        setEvents(data);
        if (data.length > 0) {
          setExpandedEvents({
            [data[0].id]: true,
            ...(data[1] ? { [data[1].id]: true } : {}),
          });
        }
      } catch (err: any) {
        setError(err.message || 'Failed to load audit history.');
      } finally {
        setIsLoading(false);
        setIsRefreshing(false);
      }
    },
    [candidateId]
  );

  useEffect(() => {
    loadAuditTrail();
  }, [loadAuditTrail, refreshTrigger]);

  const toggleEventExpanded = (id: string) => {
    setExpandedEvents((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  const formatDate = (isoString: string) => {
    if (!isoString) return 'Unknown timestamp';
    try {
      const d = new Date(isoString);
      return d.toLocaleString(undefined, {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
      });
    } catch {
      return isoString;
    }
  };

  const filteredEvents = events.filter((e) => {
    if (eventTypeFilter === 'all') return true;
    if (eventTypeFilter === 'override' && e.event_type === 'recruiter_weight_override') return true;
    if (eventTypeFilter === 'interview' && e.event_type === 'interviewer_probe_feedback') return true;
    return false;
  });

  return (
    <GlassCard variant="strong" className="space-y-4">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-white/[0.06] pb-4">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-emerald-500/10 border border-emerald-500/20 rounded-lg text-emerald-400">
            <History className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-base font-semibold text-slate-100">
                Candidate Audit Trail & Governance Log
              </h2>
              <GlowBadge variant="brand" size="sm">
                <ShieldCheck className="w-3 h-3 mr-1" /> Append-Only
              </GlowBadge>
            </div>
            <p className="text-xs text-slate-400 mt-0.5">
              Cryptographically timestamped record of recruiter weight overrides and interviewer probe evaluations
            </p>
          </div>
        </div>

        <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3">
          <div className="flex items-center gap-1.5">
            <button
              onClick={() => setEventTypeFilter('all')}
              className={`transition-opacity ${eventTypeFilter === 'all' ? 'opacity-100' : 'opacity-50 hover:opacity-80'}`}
            >
              <GlowBadge variant="neutral" size="sm">All</GlowBadge>
            </button>
            <button
              onClick={() => setEventTypeFilter('override')}
              className={`transition-opacity ${eventTypeFilter === 'override' ? 'opacity-100' : 'opacity-50 hover:opacity-80'}`}
            >
              <GlowBadge variant="warning" size="sm">Overrides</GlowBadge>
            </button>
            <button
              onClick={() => setEventTypeFilter('interview')}
              className={`transition-opacity ${eventTypeFilter === 'interview' ? 'opacity-100' : 'opacity-50 hover:opacity-80'}`}
            >
              <GlowBadge variant="info" size="sm">Feedback</GlowBadge>
            </button>
          </div>

          <div className="flex items-center gap-2 border-l border-white/[0.06] pl-3">
            <span className="px-2.5 py-1 bg-white/[0.03] border border-white/[0.06] rounded text-xs font-mono text-slate-300">
              {filteredEvents.length} Event(s)
            </span>
            <GlassButton
              variant="ghost"
              size="sm"
              onClick={() => loadAuditTrail(true)}
              loading={isRefreshing}
              icon={<RefreshCw className="w-4 h-4" />}
              title="Refresh Audit Trail"
            />
          </div>
        </div>
      </div>

      {/* Content */}
      {isLoading ? (
        <div className="py-12 flex flex-col items-center justify-center space-y-2 text-slate-400 text-xs">
          <Loader2 className="w-6 h-6 animate-spin text-indigo-400" />
          <span>Retrieving immutable candidate audit trail...</span>
        </div>
      ) : error ? (
        <GlassCard variant="subtle" glow="rose" className="!p-4 flex items-center justify-between text-xs">
          <div className="flex items-center gap-2 text-rose-300">
            <AlertCircle className="w-4 h-4" />
            <span>{error}</span>
          </div>
          <button
            type="button"
            onClick={() => loadAuditTrail(true)}
            className="underline text-rose-400 hover:text-rose-300"
          >
            Retry
          </button>
        </GlassCard>
      ) : filteredEvents.length === 0 ? (
        <div className="py-10 text-center space-y-2 bg-white/[0.02] border border-white/[0.04] rounded-lg p-6">
          <Clock className="w-8 h-8 text-slate-600 mx-auto" />
          <h3 className="text-sm font-semibold text-slate-300">No Audit Events Found</h3>
          <p className="text-xs text-slate-500 max-w-md mx-auto">
            No events match the current filters. Overrides and live interview scorecards will appear here as immutable governance events.
          </p>
        </div>
      ) : (
        <motion.div 
          className="relative pl-6 space-y-4 before:absolute before:left-2.5 before:top-2 before:bottom-2 before:w-0.5 before:bg-gradient-to-b before:from-indigo-500/40 before:to-emerald-500/40"
          variants={staggerContainer}
          initial="initial"
          animate="animate"
        >
          <AnimatePresence mode="popLayout">
            {filteredEvents.map((event) => {
              const isExpanded = expandedEvents[event.id] ?? false;
              const isOverride = event.event_type === 'recruiter_weight_override';
              const isInterview = event.event_type === 'interviewer_probe_feedback';
              const details = event.details || {};

              return (
                <motion.div key={event.id} variants={staggerItem} layout className="relative group">
                  {/* Timeline node icon */}
                  <div
                    className={`absolute -left-6 top-3 w-5 h-5 rounded-full border-2 flex items-center justify-center transition-colors ${
                      isOverride
                        ? 'bg-[#0a0f1e] border-indigo-500 text-indigo-400'
                        : isInterview
                        ? 'bg-[#0a0f1e] border-emerald-500 text-emerald-400'
                        : 'bg-[#0a0f1e] border-slate-600 text-slate-400'
                    }`}
                  >
                    {isOverride ? (
                      <Sliders className="w-2.5 h-2.5" />
                    ) : isInterview ? (
                      <Award className="w-2.5 h-2.5" />
                    ) : (
                      <Clock className="w-2.5 h-2.5" />
                    )}
                  </div>

                  {/* Event Card */}
                  <GlassCard variant="subtle" className="overflow-hidden">
                    <div
                      onClick={() => toggleEventExpanded(event.id)}
                      className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 cursor-pointer select-none"
                    >
                      <div className="flex items-center gap-3">
                        {isOverride ? (
                          <GlowBadge variant="warning" size="sm">
                            <Sliders className="w-3.5 h-3.5 mr-1.5" />
                            Role Weight Override
                          </GlowBadge>
                        ) : isInterview ? (
                          <GlowBadge variant="info" size="sm">
                            <Award className="w-3.5 h-3.5 mr-1.5" />
                            Interviewer Probe Scorecard
                          </GlowBadge>
                        ) : (
                          <GlowBadge variant="neutral" size="sm">
                            {event.event_type}
                          </GlowBadge>
                        )}

                        {isInterview && details.interviewer_name && (
                          <span className="text-xs text-slate-200 font-medium flex items-center gap-1">
                            <User className="w-3 h-3 text-slate-400" />
                            {details.interviewer_name}
                          </span>
                        )}

                        {isInterview && details.recommendation && (
                          <GlowBadge 
                            variant={RECOMMENDATION_VARIANTS[details.recommendation] || 'neutral'} 
                            size="sm"
                          >
                            {details.recommendation.replace('_', ' ').toUpperCase()}
                          </GlowBadge>
                        )}
                      </div>

                      <div className="flex items-center gap-3">
                        <span className="text-xs text-slate-400 font-mono">
                          {formatDate(event.created_at)}
                        </span>
                        {isExpanded ? (
                          <ChevronDown className="w-4 h-4 text-slate-400" />
                        ) : (
                          <ChevronRight className="w-4 h-4 text-slate-400" />
                        )}
                      </div>
                    </div>

                    {/* Expanded Event Details */}
                    <AnimatePresence>
                      {isExpanded && (
                        <motion.div
                          initial={{ height: 0, opacity: 0 }}
                          animate={{ height: 'auto', opacity: 1 }}
                          exit={{ height: 0, opacity: 0 }}
                          className="pt-4 mt-4 border-t border-white/[0.06] space-y-3.5 text-xs"
                        >
                          {/* 1. Recruiter Weight Override Details */}
                          {isOverride && (
                            <div className="space-y-3">
                              {details.justification && (
                                <div className="p-3 bg-white/[0.02] border border-white/[0.06] rounded-lg space-y-1">
                                  <span className="text-[11px] font-semibold text-indigo-400 block uppercase tracking-wider">
                                    Recruiter Audit Justification:
                                  </span>
                                  <p className="text-slate-300 italic leading-relaxed">
                                    &ldquo;{details.justification}&rdquo;
                                  </p>
                                </div>
                              )}

                              <div className="grid grid-cols-2 sm:grid-cols-3 gap-2.5">
                                <div className="p-2.5 bg-white/[0.02] border border-white/[0.06] rounded-lg">
                                  <span className="text-[10px] text-slate-500 uppercase block">RCI Impact</span>
                                  <div className="flex items-center gap-2 font-mono mt-0.5">
                                    <span className="text-slate-400">
                                      {details.previous_rci !== null && details.previous_rci !== undefined
                                        ? details.previous_rci.toFixed(2)
                                        : 'N/A'}
                                    </span>
                                    <span className="text-indigo-400">&rarr;</span>
                                    <span className="text-indigo-300 font-bold">
                                      {details.rescored_rci !== null && details.rescored_rci !== undefined
                                        ? details.rescored_rci.toFixed(2)
                                        : 'N/A'}
                                    </span>
                                  </div>
                                </div>

                                <div className="p-2.5 bg-white/[0.02] border border-white/[0.06] rounded-lg">
                                  <span className="text-[10px] text-slate-500 uppercase block">Rescored Coverage</span>
                                  <div className="font-mono font-bold text-slate-200 mt-0.5">
                                    {details.rescored_coverage !== undefined
                                      ? `${(details.rescored_coverage * 100).toFixed(1)}%`
                                      : 'N/A'}
                                  </div>
                                </div>

                                <div className="p-2.5 bg-white/[0.02] border border-white/[0.06] rounded-lg col-span-2 sm:col-span-1">
                                  <span className="text-[10px] text-slate-500 uppercase block">Event UUID</span>
                                  <div className="font-mono text-[10px] text-slate-400 truncate mt-0.5" title={event.id}>
                                    {event.id}
                                  </div>
                                </div>
                              </div>

                              {details.applied_weights && Object.keys(details.applied_weights).length > 0 && (
                                <div className="space-y-1.5 pt-1">
                                  <span className="text-[11px] font-semibold text-slate-400 block uppercase tracking-wider mb-2">
                                    Customized Role Weights:
                                  </span>
                                  <div className="space-y-2 max-w-lg">
                                    {Object.entries(details.applied_weights)
                                      .filter(([_, val]) => typeof val === 'number' && val > 0.001)
                                      .sort((a, b) => (b[1] as number) - (a[1] as number))
                                      .map(([k, val]) => (
                                        <div key={k} className="flex items-center gap-3">
                                          <div className="w-48 text-[11px] font-mono text-slate-300 truncate">
                                            {CAPABILITY_LABELS[k] || k}
                                          </div>
                                          <div className="flex-1">
                                            <ProgressBar 
                                              value={(val as number)} 
                                              color="indigo" 
                                              size="sm" 
                                              showValue={false} 
                                            />
                                          </div>
                                          <div className="w-10 text-right text-[11px] font-mono text-indigo-300">
                                            {((val as number) * 100).toFixed(0)}%
                                          </div>
                                        </div>
                                      ))}
                                  </div>
                                </div>
                              )}
                            </div>
                          )}

                          {/* 2. Interviewer Feedback Details */}
                          {isInterview && (
                            <div className="space-y-3">
                              {details.notes && (
                                <div className="p-3 bg-white/[0.02] border border-white/[0.06] rounded-lg space-y-1">
                                  <span className="text-[11px] font-semibold text-emerald-400 block uppercase tracking-wider">
                                    Interviewer Debrief Notes:
                                  </span>
                                  <p className="text-slate-300 leading-relaxed">{details.notes}</p>
                                </div>
                              )}

                              {details.probe_evaluations && details.probe_evaluations.length > 0 && (
                                <div className="space-y-2">
                                  <span className="text-[11px] font-semibold text-slate-400 block uppercase tracking-wider">
                                    Probe Evaluations ({details.probe_evaluations.length}):
                                  </span>
                                  <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                                    {details.probe_evaluations.map((p: any, idx: number) => (
                                      <div
                                        key={idx}
                                        className="p-3 bg-white/[0.03] border border-white/[0.06] rounded-lg space-y-1.5"
                                      >
                                        <div className="flex items-center justify-between gap-2">
                                          <span className="font-semibold text-slate-200">
                                            {CAPABILITY_LABELS[p.capability_key] || p.capability_key}
                                          </span>
                                          <div className="flex items-center gap-1.5">
                                            <GlowBadge variant="brand" size="sm" className="px-1.5 py-0">
                                              {p.rating}/5
                                            </GlowBadge>
                                            {p.is_gap_resolved ? (
                                              <GlowBadge variant="success" size="sm" className="px-1.5 py-0 flex items-center gap-0.5">
                                                <Check className="w-2.5 h-2.5" /> Resolved
                                              </GlowBadge>
                                            ) : (
                                              <GlowBadge variant="neutral" size="sm" className="px-1.5 py-0">
                                                Open Gap
                                              </GlowBadge>
                                            )}
                                          </div>
                                        </div>
                                        {p.notes && (
                                          <p className="text-slate-400 text-[11px] leading-relaxed">
                                            {p.notes}
                                          </p>
                                        )}
                                      </div>
                                    ))}
                                  </div>
                                </div>
                              )}

                              <div className="text-[10px] font-mono text-slate-500 flex items-center justify-between border-t border-white/[0.06] pt-2">
                                <span>Audit Event: {event.id}</span>
                                <span>Entity: candidate_dossier</span>
                              </div>
                            </div>
                          )}
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </GlassCard>
                </motion.div>
              );
            })}
          </AnimatePresence>
        </motion.div>
      )}
    </GlassCard>
  );
};
