'use client';

import { useEffect, useState } from 'react';
import { AlertTriangle, CheckCircle2, ClipboardList, Loader2, Plus, RefreshCw, Search, Users } from 'lucide-react';
import { fetchCandidatesList } from '../../lib/api';
import { AddCandidateDialog } from './AddCandidateDialog';
import { CandidateQuickView } from './CandidateQuickView';
import { SAMPLE_CANDIDATES, evaluationLabel, evidenceLabel, hasEvidenceAlert, roleLabel, withReadTimeout, type HRCandidate } from './hr-data';
import { GlassCard } from '@/components/ui/GlassCard';
import { GlassButton } from '@/components/ui/GlassButton';
import { GlassInput } from '@/components/ui/GlassInput';
import { GlassSelect } from '@/components/ui/GlassSelect';
import { GlowBadge } from '@/components/ui/GlowBadge';
import { AnimatedCounter } from '@/components/ui/AnimatedCounter';
import { motion, AnimatePresence } from 'framer-motion';

export function HRDashboard() {
  const [candidates, setCandidates] = useState<HRCandidate[]>([]);
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
    let active = true;
    setMode('loading');
    withReadTimeout(fetchCandidatesList()).then((items) => {
      if (!Array.isArray(items)) throw new Error('Invalid candidate list');
      if (active) { setCandidates(items.map((item) => ({ ...item, source: 'live' }))); setMode('live'); }
    }).catch(() => {
      if (active) { setCandidates(SAMPLE_CANDIDATES); setMode('sample'); }
    });
    return () => { active = false; };
  }, [attempt]);

  const all = [...drafts, ...candidates];
  const roles = [...new Set(all.map((candidate) => candidate.role || ''))].sort((a, b) => roleLabel(a).localeCompare(roleLabel(b)));
  const hasFilters = query !== '' || role !== 'all' || status !== 'all';
  const filtered = all.filter((candidate) => {
    const matchesQuery = `${candidate.display_name} ${candidate.primary_email || ''}`.toLowerCase().includes(query.trim().toLowerCase());
    return matchesQuery && (role === 'all' || (candidate.role || '') === role)
      && (status === 'all' || evaluationLabel(candidate) === status);
  });
  const completed = candidates.filter((candidate) => candidate.has_completed_dossier).length;
  const metrics = [
    { title: 'Total Candidates', value: all.length, detail: 'Includes local drafts', icon: Users, delay: 0.1 },
    { title: 'Evaluations Completed', value: completed, detail: 'Dossiers available', icon: CheckCircle2, delay: 0.2 },
    { title: 'Interviews to Review', value: completed, detail: 'Completed evaluations to prepare for interview', icon: ClipboardList, delay: 0.3 },
    { title: 'Evidence Alerts', value: candidates.filter(hasEvidenceAlert).length, detail: 'Candidates with mixed or missing evidence', icon: AlertTriangle, delay: 0.4 },
  ];

  function clearFilters() { setQuery(''); setRole('all'); setStatus('all'); }

  return <div className="min-h-screen bg-[#030712] text-slate-100">
    <header className="border-b border-white/[0.06] bg-[#0a0f1e]/80 backdrop-blur-xl">
      <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-4 px-6 py-5 lg:px-8">
        <div className="flex items-center gap-3">
          <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-500/20 text-indigo-400 border border-indigo-500/30">
            <Users className="h-5 w-5" aria-hidden="true" />
          </span>
          <span className="text-xl font-bold tracking-tight text-white">Candidate<span className="text-indigo-400">X</span></span>
          <span className="hidden border-l border-white/10 pl-3 text-sm text-slate-400 sm:block">For hiring teams</span>
        </div>
        <GlassButton variant="primary" onClick={() => setAdding(true)} icon={<Plus className="h-4 w-4" />}>
          Add Candidate
        </GlassButton>
      </div>
    </header>
    <main className="mx-auto max-w-7xl space-y-7 px-6 py-8 lg:px-8 lg:py-10">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="mb-2 text-xs font-semibold uppercase tracking-widest text-indigo-400">Your hiring workspace</p>
          <h1 className="text-3xl font-bold tracking-tight text-white">Hiring Dashboard</h1>
          <p className="mt-2 text-sm leading-6 text-slate-400">Find a candidate, review their evidence, and prepare for the next conversation.</p>
        </div>
        <GlassButton disabled={mode === 'loading'} onClick={() => { setSelected(null); setAttempt((value) => value + 1); }} icon={<RefreshCw className={`h-4 w-4 ${mode === 'loading' ? 'animate-spin' : ''}`} />}>
          Refresh list
        </GlassButton>
      </div>

      {/* Human Decision Support Mandatory Invariant Banner */}
      <GlassCard variant="subtle" className="flex flex-col sm:flex-row items-start sm:items-center gap-3 p-4 border-indigo-500/30 bg-indigo-500/10 text-xs text-slate-300">
        <span className="px-2.5 py-1 rounded text-[10px] font-mono font-bold uppercase tracking-wider bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 shrink-0">
          Human Decision Support
        </span>
        <p className="leading-relaxed">
          <strong className="text-white">CandidateX does not decide whether to hire a person.</strong> The system provides independent technical evidence analysis, contradiction diagnostics, and structured interview probes to support human hiring committees. Automated hiring decisions, candidate rankings, and &ldquo;best candidate&rdquo; designations are strictly prohibited.
        </p>
      </GlassCard>
      
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

      <section aria-label="Hiring summary" className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
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
          <div className="border-b border-white/[0.06] p-5 sm:p-6 bg-[#0a0f1e]/40">
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
              <table className="w-full min-w-[760px] text-left text-sm">
                <caption className="sr-only">Candidates with evaluation status, evidence status, alerts, and a quick-view action</caption>
                <thead className="bg-[#0a0f1e]/80 text-xs text-slate-400 border-b border-white/[0.06]">
                  <tr>
                    {['Candidate', 'Role', 'Evaluation', 'Evidence', 'Alerts', 'Action'].map((heading) => (
                      <th key={heading} scope="col" className="px-5 py-4 font-semibold">{heading}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/[0.04]">
                  <AnimatePresence>
                    {filtered.map((candidate) => (
                      <motion.tr 
                        key={candidate.id} 
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        className="group hover:bg-white/[0.04] transition-colors"
                      >
                        <th scope="row" className="min-w-[180px] max-w-[260px] break-words px-5 py-4 font-normal">
                          <p className="font-semibold text-slate-200 group-hover:text-white transition-colors">{candidate.display_name}</p>
                          <p className="mt-1 text-xs leading-5 text-slate-500">{candidate.source === 'sample' ? 'Sample candidate' : candidate.source === 'draft' ? 'Local draft · not shared' : candidate.primary_email || 'No email provided'}</p>
                        </th>
                        <td className="px-5 py-4 text-slate-400">{roleLabel(candidate.role)}</td>
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
                        <td className="sticky right-0 bg-[#030712]/90 backdrop-blur group-hover:bg-[#0a0f1e]/90 px-5 py-4 transition-colors">
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
          <div aria-live="polite" className="border-t border-white/[0.06] bg-[#0a0f1e]/40 px-6 py-4 text-xs text-slate-500">
            {mode === 'loading' ? 'Checking your candidate list' : `Showing ${filtered.length} of ${all.length} candidates${mode === 'sample' ? ' · Sample workspace' : ''}`}
          </div>
        </GlassCard>
      </motion.section>
      <p className="text-center text-xs leading-5 text-slate-500">
        CandidateX does not decide whether to hire a person. Evidence helps you ask better questions; hiring decisions always remain with your human team.
      </p>
    </main>
    {adding && <AddCandidateDialog onClose={() => setAdding(false)} onAdd={(candidate) => {
      setDrafts((previous) => [candidate, ...previous]); setAdding(false); clearFilters();
      setNotice(`${candidate.display_name} added as a local draft. Download a copy from View before leaving this page.`);
    }} />}
    {selected && <CandidateQuickView key={`${selected.source}-${selected.id}`} candidate={selected} onClose={() => setSelected(null)} />}
  </div>;
}
