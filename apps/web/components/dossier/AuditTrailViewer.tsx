'use client';

import React, { useState, useEffect, useCallback } from 'react';
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

const RECOMMENDATION_BADGES: Record<
  string,
  { label: string; badgeClass: string }
> = {
  strong_hire: {
    label: 'Strong Hire',
    badgeClass: 'bg-emerald-500/15 border-emerald-500/30 text-emerald-300',
  },
  lean_hire: {
    label: 'Lean Hire',
    badgeClass: 'bg-indigo-500/15 border-indigo-500/30 text-indigo-300',
  },
  lean_no_hire: {
    label: 'Lean No Hire',
    badgeClass: 'bg-amber-500/15 border-amber-500/30 text-amber-300',
  },
  no_hire: {
    label: 'No Hire',
    badgeClass: 'bg-rose-500/15 border-rose-500/30 text-rose-300',
  },
};

interface AuditTrailViewerProps {
  candidateId: string;
  refreshTrigger?: number;
}

export const AuditTrailViewer: React.FC<AuditTrailViewerProps> = ({
  candidateId,
  refreshTrigger = 0,
}) => {
  const [events, setEvents] = useState<AuditEventItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expandedEvents, setExpandedEvents] = useState<Record<string, boolean>>({});

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
        // Expand the first 2 events by default
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
    setExpandedEvents((prev) => ({
      ...prev,
      [id]: !prev[id],
    }));
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

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl space-y-4">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-800 pb-4">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-emerald-500/10 border border-emerald-500/20 rounded-lg text-emerald-400">
            <History className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-base font-semibold text-slate-100">
                Candidate Audit Trail & Governance Log
              </h2>
              <span className="px-2 py-0.5 bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 rounded text-[11px] font-mono flex items-center gap-1">
                <ShieldCheck className="w-3 h-3" />
                Append-Only
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-0.5">
              Cryptographically timestamped record of recruiter weight overrides and interviewer probe evaluations
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <span className="px-2.5 py-1 bg-slate-950 border border-slate-800 rounded text-xs font-mono text-slate-300">
            {events.length} Event(s) Recorded
          </span>
          <button
            type="button"
            onClick={() => loadAuditTrail(true)}
            disabled={isRefreshing || isLoading}
            className="p-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded border border-slate-700 hover:border-slate-600 transition-colors disabled:opacity-50"
            title="Refresh Audit Trail"
          >
            <RefreshCw className={`w-4 h-4 ${isRefreshing ? 'animate-spin text-indigo-400' : ''}`} />
          </button>
        </div>
      </div>

      {/* Content */}
      {isLoading ? (
        <div className="py-12 flex flex-col items-center justify-center space-y-2 text-slate-400 text-xs">
          <Loader2 className="w-6 h-6 animate-spin text-indigo-400" />
          <span>Retrieving immutable candidate audit trail...</span>
        </div>
      ) : error ? (
        <div className="p-4 bg-rose-500/10 border border-rose-500/20 rounded-lg text-rose-400 text-xs flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4" />
            <span>{error}</span>
          </div>
          <button
            type="button"
            onClick={() => loadAuditTrail(true)}
            className="underline hover:text-rose-300"
          >
            Retry
          </button>
        </div>
      ) : events.length === 0 ? (
        <div className="py-10 text-center space-y-2 bg-slate-950/40 border border-slate-800/80 rounded-lg p-6">
          <Clock className="w-8 h-8 text-slate-600 mx-auto" />
          <h3 className="text-sm font-semibold text-slate-300">No Audit Events Logged Yet</h3>
          <p className="text-xs text-slate-500 max-w-md mx-auto">
            Role weight overrides applied by recruiters and live interview scorecards submitted by technical interviewers
            will appear here as immutable governance events.
          </p>
        </div>
      ) : (
        <div className="relative pl-6 space-y-4 before:absolute before:left-2.5 before:top-2 before:bottom-2 before:w-0.5 before:bg-slate-800">
          {events.map((event) => {
            const isExpanded = expandedEvents[event.id] ?? false;
            const isOverride = event.event_type === 'recruiter_weight_override';
            const isInterview = event.event_type === 'interviewer_probe_feedback';
            const details = event.details || {};

            return (
              <div key={event.id} className="relative group">
                {/* Timeline node icon */}
                <div
                  className={`absolute -left-6 top-3 w-5 h-5 rounded-full border-2 flex items-center justify-center transition-colors ${
                    isOverride
                      ? 'bg-indigo-950 border-indigo-500 text-indigo-400'
                      : isInterview
                      ? 'bg-emerald-950 border-emerald-500 text-emerald-400'
                      : 'bg-slate-900 border-slate-600 text-slate-400'
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
                <div
                  className={`bg-slate-950/80 border rounded-xl overflow-hidden transition-all ${
                    isExpanded ? 'border-slate-700 shadow-md' : 'border-slate-800 hover:border-slate-700'
                  }`}
                >
                  {/* Event Card Header */}
                  <div
                    onClick={() => toggleEventExpanded(event.id)}
                    className="p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3 cursor-pointer select-none"
                  >
                    <div className="flex items-center gap-3">
                      {isOverride ? (
                        <span className="px-2 py-0.5 bg-indigo-500/15 border border-indigo-500/30 text-indigo-300 rounded text-xs font-semibold flex items-center gap-1.5">
                          <Sliders className="w-3.5 h-3.5" />
                          Role Weight Override
                        </span>
                      ) : isInterview ? (
                        <span className="px-2 py-0.5 bg-emerald-500/15 border border-emerald-500/30 text-emerald-300 rounded text-xs font-semibold flex items-center gap-1.5">
                          <Award className="w-3.5 h-3.5" />
                          Interviewer Probe Scorecard
                        </span>
                      ) : (
                        <span className="px-2 py-0.5 bg-slate-800 border border-slate-700 text-slate-300 rounded text-xs font-semibold">
                          {event.event_type}
                        </span>
                      )}

                      {/* Recruiter / Interviewer Name */}
                      {isInterview && details.interviewer_name && (
                        <span className="text-xs text-slate-200 font-medium flex items-center gap-1">
                          <User className="w-3 h-3 text-slate-400" />
                          {details.interviewer_name}
                        </span>
                      )}

                      {/* Overall Recommendation badge if interview feedback */}
                      {isInterview && details.recommendation && (
                        <span
                          className={`px-2 py-0.5 border rounded text-[10px] font-bold uppercase tracking-wider ${
                            RECOMMENDATION_BADGES[details.recommendation]?.badgeClass ||
                            'bg-slate-800 text-slate-300 border-slate-700'
                          }`}
                        >
                          {RECOMMENDATION_BADGES[details.recommendation]?.label ||
                            details.recommendation.replace('_', ' ')}
                        </span>
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
                  {isExpanded && (
                    <div className="p-4 border-t border-slate-800/80 space-y-3.5 text-xs bg-slate-900/30">
                      {/* 1. Recruiter Weight Override Details */}
                      {isOverride && (
                        <div className="space-y-3">
                          {/* Justification Box */}
                          {details.justification && (
                            <div className="p-3 bg-slate-950 border border-slate-800 rounded-lg space-y-1">
                              <span className="text-[11px] font-semibold text-indigo-400 block uppercase tracking-wider">
                                Recruiter Audit Justification:
                              </span>
                              <p className="text-slate-300 italic leading-relaxed">
                                &ldquo;{details.justification}&rdquo;
                              </p>
                            </div>
                          )}

                          {/* Impact Metrics */}
                          <div className="grid grid-cols-2 sm:grid-cols-3 gap-2.5">
                            <div className="p-2.5 bg-slate-950 border border-slate-800 rounded-lg">
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

                            <div className="p-2.5 bg-slate-950 border border-slate-800 rounded-lg">
                              <span className="text-[10px] text-slate-500 uppercase block">Rescored Coverage</span>
                              <div className="font-mono font-bold text-slate-200 mt-0.5">
                                {details.rescored_coverage !== undefined
                                  ? `${(details.rescored_coverage * 100).toFixed(1)}%`
                                  : 'N/A'}
                              </div>
                            </div>

                            <div className="p-2.5 bg-slate-950 border border-slate-800 rounded-lg col-span-2 sm:col-span-1">
                              <span className="text-[10px] text-slate-500 uppercase block">Event UUID</span>
                              <div className="font-mono text-[10px] text-slate-400 truncate mt-0.5" title={event.id}>
                                {event.id}
                              </div>
                            </div>
                          </div>

                          {/* Applied Weights Preview */}
                          {details.applied_weights && Object.keys(details.applied_weights).length > 0 && (
                            <div className="space-y-1.5 pt-1">
                              <span className="text-[11px] font-semibold text-slate-400 block uppercase tracking-wider">
                                Customized Role Weights:
                              </span>
                              <div className="flex flex-wrap gap-1.5">
                                {Object.entries(details.applied_weights)
                                  .filter(([_, val]) => typeof val === 'number' && val > 0.001)
                                  .sort((a, b) => (b[1] as number) - (a[1] as number))
                                  .map(([k, val]) => (
                                    <span
                                      key={k}
                                      className="px-2 py-0.5 bg-slate-950 border border-slate-800 rounded text-[11px] font-mono text-slate-300"
                                    >
                                      {CAPABILITY_LABELS[k] || k}:{' '}
                                      <span className="text-indigo-400 font-bold">
                                        {((val as number) * 100).toFixed(0)}%
                                      </span>
                                    </span>
                                  ))}
                              </div>
                            </div>
                          )}
                        </div>
                      )}

                      {/* 2. Interviewer Feedback Details */}
                      {isInterview && (
                        <div className="space-y-3">
                          {/* Overall Notes */}
                          {details.notes && (
                            <div className="p-3 bg-slate-950 border border-slate-800 rounded-lg space-y-1">
                              <span className="text-[11px] font-semibold text-emerald-400 block uppercase tracking-wider">
                                Interviewer Debrief Notes:
                              </span>
                              <p className="text-slate-300 leading-relaxed">{details.notes}</p>
                            </div>
                          )}

                          {/* Evaluated Probes Breakdown */}
                          {details.probe_evaluations && details.probe_evaluations.length > 0 && (
                            <div className="space-y-2">
                              <span className="text-[11px] font-semibold text-slate-400 block uppercase tracking-wider">
                                Probe Evaluations ({details.probe_evaluations.length}):
                              </span>
                              <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                                {details.probe_evaluations.map((p: any, idx: number) => (
                                  <div
                                    key={idx}
                                    className="p-3 bg-slate-950/90 border border-slate-800 rounded-lg space-y-1.5"
                                  >
                                    <div className="flex items-center justify-between gap-2">
                                      <span className="font-semibold text-slate-200">
                                        {CAPABILITY_LABELS[p.capability_key] || p.capability_key}
                                      </span>
                                      <div className="flex items-center gap-1.5">
                                        <span className="px-1.5 py-0.5 bg-indigo-500/10 border border-indigo-500/30 text-indigo-300 rounded text-[10px] font-bold font-mono">
                                          {p.rating}/5
                                        </span>
                                        {p.is_gap_resolved ? (
                                          <span className="px-1.5 py-0.5 bg-emerald-500/15 border border-emerald-500/30 text-emerald-400 rounded text-[10px] font-medium flex items-center gap-0.5">
                                            <Check className="w-2.5 h-2.5" /> Resolved
                                          </span>
                                        ) : (
                                          <span className="px-1.5 py-0.5 bg-slate-800 text-slate-400 rounded text-[10px]">
                                            Open Gap
                                          </span>
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

                          {/* Event UUID & metadata */}
                          <div className="text-[10px] font-mono text-slate-500 flex items-center justify-between border-t border-slate-800/60 pt-2">
                            <span>Audit Event: {event.id}</span>
                            <span>Entity: candidate_dossier</span>
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
