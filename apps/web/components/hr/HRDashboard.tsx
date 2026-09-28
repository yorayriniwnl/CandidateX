'use client';

import { useEffect, useMemo, useState } from 'react';
import { AlertTriangle, ArrowDown, ArrowUp, ArrowUpDown, CheckCircle2, ClipboardList, Loader2, Plus, RefreshCw, Search, Users } from 'lucide-react';
import { fetchCandidatesList } from '../../lib/api';
import { mergeCandidateLists } from '../../lib/team-members';
import { AddCandidateDialog } from './AddCandidateDialog';
import { CandidateQuickView } from './CandidateQuickView';
import { SAMPLE_CANDIDATES, evaluationLabel, evidenceLabel, getSavedHRCandidates, hasEvidenceAlert, roleLabel, withReadTimeout, type HRCandidate } from './hr-data';
import { GlassCard } from '@/components/ui/GlassCard';
import { GlassButton } from '@/components/ui/GlassButton';
import { GlassInput } from '@/components/ui/GlassInput';
import { GlassSelect } from '@/components/ui/GlassSelect';
import { GlowBadge } from '@/components/ui/GlowBadge';
import { AnimatedCounter } from '@/components/ui/AnimatedCounter';
import { motion, AnimatePresence } from 'framer-motion';
import { StudioHeading } from '../studio/StudioHeading';
import { StudioFooter } from '../studio/StudioFooter';

export function HRDashboard() {
  const [candidates, setCandidates] = useState<HRCandidate[]>([]);
  const [savedCandidates, setSavedCandidates] = useState<HRCandidate[]>([]);
  const [drafts, setDrafts] = useState<HRCandidate[]>([]);
  const [mode, setMode] = useState<'loading' | 'live' | 'sample'>('loading');
  const [attempt, setAttempt] = useState(0);
  const [query, setQuery] = useState('');
  const [role, setRole] = useState('all');
  const [status, setStatus] = useState('all');
  const [selected, setSelected] = useState<HRCandidate | null>(null);
  const [adding, setAdding] = useState(false);
  const [notice, setNotice] = useState('');

  useEffect(() => {
    setSavedCandidates(getSavedHRCandidates());
    const handleUpdate = () => {
      setSavedCandidates(getSavedHRCandidates());
    };
    window.addEventListener('cci_hr_candidates_changed', handleUpdate);
    window.addEventListener('storage', handleUpdate);
    return () => {
      window.removeEventListener('cci_hr_candidates_changed', handleUpdate);
      window.removeEventListener('storage', handleUpdate);
    };
  }, []);

  useEffect(() => {
    let active = true;
    setMode('loading');
    withReadTimeout(fetchCandidatesList()).then((items) => {
      if (!Array.isArray(items)) throw new Error('Invalid candidate list');
      if (active) {
        const liveCandidates = items.map((item) => ({ ...item, source: 'live' as const }));
        setCandidates(mergeCandidateLists<HRCandidate>(liveCandidates, SAMPLE_CANDIDATES));
        setMode('live');
      }
    }).catch(() => {
      if (active) { setCandidates(SAMPLE_CANDIDATES); setMode('sample'); }
    });
    return () => { active = false; };
  }, [attempt]);

  const all = mergeCandidateLists(drafts, savedCandidates, candidates);
  const roles = [...new Set(all.map((candidate) => candidate.role || ''))].sort((a, b) => roleLabel(a).localeCompare(roleLabel(b)));
  const [sortField, setSortField] = useState<'candidate' | 'score' | 'observed' | null>(null);
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('desc');

  const hasFilters = query !== '' || role !== 'all' || status !== 'all' || sortField !== null;
  const filtered = all.filter((candidate) => {
    const matchesQuery = `${candidate.display_name} ${candidate.primary_email || ''}`.toLowerCase().includes(query.trim().toLowerCase());
    return matchesQuery && (role === 'all' || (candidate.role || '') === role)
      && (status === 'all' || evaluationLabel(candidate) === status);
  });

  const sortedCandidates = useMemo(() => {
    if (!sortField) return filtered;
    return [...filtered].sort((a, b) => {
      if (sortField === 'score') {
        const valA = a.jd_fit_score ?? a.rci;
        const valB = b.jd_fit_score ?? b.rci;
        const scoreA = valA != null ? valA : -1;
        const scoreB = valB != null ? valB : -1;
        return sortDirection === 'desc' ? scoreB - scoreA : scoreA - scoreB;
      }
      if (sortField === 'observed') {
        const countA = a.observed_capabilities ?? (a.coverage ? Math.round(a.coverage * 12) : -1);
        const countB = b.observed_capabilities ?? (b.coverage ? Math.round(b.coverage * 12) : -1);
        return sortDirection === 'desc' ? countB - countA : countA - countB;
      }
      if (sortField === 'candidate') {
        return sortDirection === 'desc'
          ? b.display_name.localeCompare(a.display_name)
          : a.display_name.localeCompare(b.display_name);
      }
      return 0;
    });
  }, [filtered, sortField, sortDirection]);

  function handleSort(field: 'candidate' | 'score' | 'observed') {
    if (sortField !== field) {
      setSortField(field);
      setSortDirection(field === 'candidate' ? 'asc' : 'desc');
    } else if (sortDirection === (field === 'candidate' ? 'asc' : 'desc')) {
      setSortDirection(field === 'candidate' ? 'desc' : 'asc');
    } else {
      setSortField(null);
    }
  }

  const completed = all.filter((candidate) => candidate.has_completed_dossier).length;
  const metrics = [
    { title: 'Total Candidates', value: all.length, detail: 'Includes reviewed & local drafts', icon: Users, delay: 0.1 },
    { title: 'Evaluations Completed', value: completed, detail: 'Dossiers available', icon: CheckCircle2, delay: 0.2 },
    { title: 'Interviews to Review', value: completed, detail: 'Completed evaluations to prepare for interview', icon: ClipboardList, delay: 0.3 },
    { title: 'Evidence Alerts', value: all.filter(hasEvidenceAlert).length, detail: 'Candidates with mixed or missing evidence', icon: AlertTriangle, delay: 0.4 },
  ];

  function clearFilters() { setQuery(''); setRole('all'); setStatus('all'); setSortField(null); }

  return <div className="studio-hr">
    <main className="studio-page space-y-7">
      <StudioHeading eyebrow="01 / CANDIDATE & STUDENT WORKSPACE" title="Hiring Dashboard" description="A fuller picture of the people behind the profiles. Explore their evidence and prepare for the next conversation.">
        <GlassButton variant="secondary" disabled={mode === 'loading'} onClick={() => { setSelected(null); setAttempt(value => value + 1); }} icon={<RefreshCw className={`h-3.5 w-3.5 ${mode === 'loading' ? 'animate-spin' : ''}`} />}>Refresh list</GlassButton>
        <GlassButton variant="primary" onClick={() => setAdding(true)} icon={<Plus className="h-3.5 w-3.5" />}>Add Candidate</GlassButton>
      </StudioHeading>

      <AnimatePresence>
        {mode === 'sample' && (
          <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, height: 0 }}>
            <GlassCard variant="strong" glow="amber" className="flex gap-3 p-4 text-sm leading-6 text-amber-200 border-amber-500/20 bg-amber-500/10">
              <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-amber-400" aria-hidden="true" />
              <p><strong className="text-amber-100">Sample workspace.</strong> We couldn’t load your team’s candidates. These examples are for demonstration only. Select Refresh list to try again. Local drafts stay separate.</p>
            </GlassCard>
          </motion.div>
        )}
        {notice && (
          <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, height: 0 }}>
            <GlassCard variant="subtle" glow="indigo" className="p-4 text-sm text-indigo-200 border-indigo-500/20 bg-indigo-500/10">
              {notice}
            </GlassCard>
          </motion.div>
        )}
      </AnimatePresence>

      <section aria-label="Hiring summary" className="studio-hr-metrics grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {metrics.map(({ title, value, detail, icon: Icon, delay }) => (
          <GlassCard key={title} animateDelay={delay} hoverLift className="p-5 flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between gap-2">
                <h2 className="text-sm font-medium text-slate-400">{title}</h2>
                <Icon className="h-5 w-5 text-indigo-400" aria-hidden="true" />
              </div>
              <div className="mt-4 text-3xl font-semibold tracking-tight text-white">
                {mode === 'loading' ? '—' : <AnimatedCounter value={value} />}
              </div>
            </div>
            <p className="mt-2 text-xs leading-5 text-slate-500">{detail}</p>
          </GlassCard>
        ))}
      </section>

      <motion.section 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.5, duration: 0.5 }}
        aria-labelledby="hr-candidates-heading" 
      >
        <GlassCard noPadding className="overflow-hidden">
          <div className="studio-table-toolbar border-b border-white/[0.06] p-5 sm:p-6">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <h2 id="hr-candidates-heading" className="text-lg font-semibold text-white">Candidates</h2>
                <p className="mt-1 text-sm text-slate-400">Select View for a summary and suggested next steps.</p>
              </div>
              {hasFilters && <GlassButton variant="ghost" onClick={clearFilters}>Clear filters</GlassButton>}
            </div>
            <div className="mt-6 grid gap-4 md:grid-cols-[2fr_1fr_1fr]">
              <GlassInput 
                variant="search"
                label="Search candidate"
                value={query} 
                onChange={(event) => setQuery(event.target.value)} 
                placeholder="Search by name or email" 
                leadingIcon={<Search className="h-4 w-4" />}
                clearable
              />
              <GlassSelect 
                label="Role"
                value={role} 
                onChange={(event) => setRole(event.target.value)}
                options={[{value: 'all', label: 'All roles'}, ...roles.map(v => ({value: v, label: roleLabel(v)}))]}
              />
              <GlassSelect 
                label="Evaluation status"
                value={status} 
                onChange={(event) => setStatus(event.target.value)}
                options={[
                  {value: 'all', label: 'All statuses'},
                  {value: 'Completed', label: 'Completed'},
                  {value: 'Not completed', label: 'Not completed'},
                  {value: 'Local draft', label: 'Local draft'}
                ]}
              />
            </div>
          </div>
          {mode === 'loading' ? (
            <div role="status" className="flex items-center justify-center gap-3 p-16 text-sm text-slate-400">
              <Loader2 className="h-5 w-5 animate-spin" aria-hidden="true" />Loading candidates…
            </div>
          ) : filtered.length ? (
            <div tabIndex={0} role="region" aria-label="Candidate table — scroll horizontally to see all columns" className="overflow-x-auto focus-visible:outline focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-indigo-500">
              <table className="w-full min-w-[860px] text-left text-sm">
                <caption className="sr-only">Candidates with evaluation status, score, evidence status, alerts, and a quick-view action</caption>
                <thead className="studio-table-head text-xs text-slate-400 border-b border-white/[0.06]">
                  <tr>
                    {['Candidate', 'Role', 'JD Fit Score', 'Observed Capabilities', 'Evaluation', 'Evidence', 'Alerts', 'Action'].map((heading) => {
                      if (heading === 'JD Fit Score') {
                        return (
                          <th key={heading} scope="col" className="px-5 py-4 font-semibold">
                            <button
                              type="button"
                              onClick={() => handleSort('score')}
                              className="inline-flex items-center gap-1.5 hover:text-white transition-colors cursor-pointer group/sort"
                              title="Sort by JD fit score"
                            >
                              <span>JD Fit Score</span>
                              {sortField === 'score' ? (
                                sortDirection === 'desc' ? (
                                  <ArrowDown className="h-3.5 w-3.5 text-brand-400" />
                                ) : (
                                  <ArrowUp className="h-3.5 w-3.5 text-brand-400" />
                                )
                              ) : (
                                <ArrowUpDown className="h-3 w-3 text-slate-500 opacity-60 group-hover/sort:opacity-100" />
                              )}
                            </button>
                          </th>
                        );
                      }
                      if (heading === 'Observed Capabilities') {
                        return (
                          <th key={heading} scope="col" className="px-5 py-4 font-semibold">
                            <button
                              type="button"
                              onClick={() => handleSort('observed')}
                              className="inline-flex items-center gap-1.5 hover:text-white transition-colors cursor-pointer group/sort"
                              title="Sort by observed capabilities"
                            >
                              <span>Observed Capabilities</span>
                              {sortField === 'observed' ? (
                                sortDirection === 'desc' ? (
                                  <ArrowDown className="h-3.5 w-3.5 text-brand-400" />
                                ) : (
                                  <ArrowUp className="h-3.5 w-3.5 text-brand-400" />
                                )
                              ) : (
                                <ArrowUpDown className="h-3 w-3 text-slate-500 opacity-60 group-hover/sort:opacity-100" />
                              )}
                            </button>
                          </th>
                        );
                      }
                      if (heading === 'Candidate') {
                        return (
                          <th key={heading} scope="col" className="px-5 py-4 font-semibold">
                            <button
                              type="button"
                              onClick={() => handleSort('candidate')}
                              className="inline-flex items-center gap-1.5 hover:text-white transition-colors cursor-pointer group/sort"
                              title="Sort by candidate name"
                            >
                              <span>Candidate</span>
                              {sortField === 'candidate' ? (
                                sortDirection === 'desc' ? (
                                  <ArrowDown className="h-3.5 w-3.5 text-brand-400" />
                                ) : (
                                  <ArrowUp className="h-3.5 w-3.5 text-brand-400" />
                                )
                              ) : (
                                <ArrowUpDown className="h-3 w-3 text-slate-500 opacity-60 group-hover/sort:opacity-100" />
                              )}
                            </button>
                          </th>
                        );
                      }
                      return <th key={heading} scope="col" className="px-5 py-4 font-semibold">{heading}</th>;
                    })}
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/[0.04]">
                  <AnimatePresence>
                    {sortedCandidates.map((candidate) => (
                      <motion.tr 
                        key={candidate.id} 
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        className="group hover:bg-white/[0.04] transition-colors"
                      >
                        <th scope="row" className="min-w-[180px] max-w-[260px] break-words px-5 py-4 font-normal">
                          <div className="flex items-center gap-3"><span className="studio-candidate-avatar" aria-hidden="true">{candidate.display_name.split(/\s+/).slice(0, 2).map(part => part.charAt(0)).join('')}</span><div><p className="font-medium text-slate-200 group-hover:text-white transition-colors">{candidate.display_name}</p>
                          <p className="mt-1 text-xs leading-5 text-slate-500">{candidate.primary_email ? <a href={`mailto:${candidate.primary_email}`} className="hover:text-indigo-300">{candidate.primary_email}</a> : 'No email provided'}</p>
                          {candidate.source !== 'live' && <p className="text-xs leading-5 text-slate-500">{candidate.source === 'sample' ? 'Sample candidate' : 'Local draft · not shared'}</p>}
                          </div></div>
                        </th>
                        <td className="px-5 py-4 text-slate-400">{candidate.role_label || roleLabel(candidate.role)}</td>
                        <td className="px-5 py-4 font-mono font-medium">
                          {(() => {
                            const fitVal = candidate.jd_fit_score ?? candidate.rci;
                            return fitVal !== null && fitVal !== undefined ? (
                              <span className="inline-flex items-baseline gap-1">
                                <span className="text-sm font-bold text-brand-400">
                                  {fitVal.toFixed(1)}
                                </span>
                                <span className="text-[10px] text-slate-500 font-normal">/ 100</span>
                              </span>
                            ) : (
                              <span className="text-slate-500 text-xs">—</span>
                            );
                          })()}
                        </td>
                        <td className="px-5 py-4 font-mono">
                          {candidate.has_completed_dossier ? (
                            <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-indigo-300 text-xs font-semibold">
                              {candidate.observed_capabilities ?? (
                                candidate.dossier
                                  ? Object.values(candidate.dossier.capability_estimates).filter((e) => e.is_observed && e.estimate != null).length
                                  : candidate.coverage
                                  ? Math.max(1, Math.round(candidate.coverage * 12))
                                  : 0
                              )}
                              <span className="text-slate-500 font-normal text-[10px]">/ 12</span>
                            </span>
                          ) : (
                            <span className="text-slate-500 text-xs">—</span>
                          )}
                        </td>
                        <td className="px-5 py-4">
                          <GlowBadge variant={candidate.has_completed_dossier ? 'success' : 'neutral'} size="sm">
                            {evaluationLabel(candidate)}
                          </GlowBadge>
                        </td>
                        <td className="px-5 py-4 text-slate-400">{evidenceLabel(candidate)}</td>
                        <td className="px-5 py-4 text-xs text-slate-500">
                          {hasEvidenceAlert(candidate) ? (
                            <span className="inline-flex items-center gap-1.5 font-medium text-amber-400"><AlertTriangle className="h-4 w-4" aria-hidden="true" />Review</span>
                          ) : candidate.has_completed_dossier ? 'None reported' : 'Not assessed'}
                        </td>
                        <td className="sticky right-0 bg-[#09070e]/90 backdrop-blur group-hover:bg-[#130e1c]/90 px-5 py-4 transition-colors">
                          <GlassButton variant="secondary" size="sm" onClick={() => setSelected(candidate)} aria-label={`View ${candidate.display_name}`}>
                            View
                          </GlassButton>
                        </td>
                      </motion.tr>
                    ))}
                  </AnimatePresence>
                </tbody>
              </table>
            </div>
          ) : (
            <div className="p-16 text-center">
              <Users className="mx-auto mb-4 h-10 w-10 text-slate-600" aria-hidden="true" />
              <h3 className="font-semibold text-slate-200 text-lg">{all.length ? 'No matching candidates' : 'Your candidate list is empty'}</h3>
              <p className="mb-6 mt-2 text-sm text-slate-400">{all.length ? 'Try a different name, role, or evaluation status.' : 'Add a candidate draft to get started.'}</p>
              <GlassButton variant={all.length ? "ghost" : "primary"} onClick={all.length ? clearFilters : () => setAdding(true)}>
                {all.length ? 'Clear filters' : 'Add Candidate'}
              </GlassButton>
            </div>
          )}
          <div aria-live="polite" className="border-t border-white/[0.06] bg-[#130e1c]/40 px-6 py-4 text-xs text-slate-500">
            {mode === 'loading' ? 'Checking your candidate list' : `Showing ${filtered.length} of ${all.length} candidates${mode === 'sample' ? ' · Sample workspace' : ''}`}
          </div>
        </GlassCard>
      </motion.section>
      <p className="text-center text-xs leading-5 text-slate-500">Evidence helps you ask better questions. Hiring decisions always remain with your team.</p>
      <StudioFooter />
    </main>
    {adding && <AddCandidateDialog onClose={() => setAdding(false)} onAdd={(candidate) => {
      setDrafts((previous) => [candidate, ...previous]); setAdding(false); clearFilters();
      setNotice(`${candidate.display_name} saved as a local draft in this browser.`);
    }} />}
    {selected && <CandidateQuickView key={`${selected.source}-${selected.id}`} candidate={selected} onClose={() => setSelected(null)} />}
  </div>;
}
