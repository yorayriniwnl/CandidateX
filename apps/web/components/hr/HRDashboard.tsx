'use client';

import { useEffect, useState } from 'react';
import { AlertTriangle, CheckCircle2, ClipboardList, Loader2, Plus, RefreshCw, Search, Users } from 'lucide-react';
import { fetchCandidatesList } from '../../lib/api';
import { AddCandidateDialog } from './AddCandidateDialog';
import { CandidateQuickView } from './CandidateQuickView';
import { controlClass, primaryClass, secondaryClass } from './HRDialog';
import { SAMPLE_CANDIDATES, evaluationLabel, evidenceLabel, hasEvidenceAlert, roleLabel, withReadTimeout, type HRCandidate } from './hr-data';

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
    { title: 'Total Candidates', value: all.length, detail: 'Includes local drafts', icon: Users },
    { title: 'Evaluations Completed', value: completed, detail: 'Dossiers available', icon: CheckCircle2 },
    { title: 'Interviews to Review', value: completed, detail: 'Completed evaluations to prepare for interview; not scheduled interviews', icon: ClipboardList },
    { title: 'Evidence Alerts', value: candidates.filter(hasEvidenceAlert).length, detail: 'Candidates with mixed or missing evidence reported', icon: AlertTriangle },
  ];

  function clearFilters() { setQuery(''); setRole('all'); setStatus('all'); }

  return <div className="min-h-screen bg-slate-50 text-slate-900 [color-scheme:light]">
    <header className="border-b border-slate-200 bg-white">
      <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-4 px-6 py-5 lg:px-8">
        <div className="flex items-center gap-3"><span className="flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-600 text-white"><Users className="h-5 w-5" aria-hidden="true" /></span><span className="text-xl font-bold tracking-tight">Candidate<span className="text-indigo-600">X</span></span><span className="hidden border-l border-slate-200 pl-3 text-sm text-slate-500 sm:block">For hiring teams</span></div>
        <button type="button" onClick={() => setAdding(true)} className={primaryClass}><Plus className="h-4 w-4" aria-hidden="true" />Add Candidate</button>
      </div>
    </header>
    <main className="mx-auto max-w-7xl space-y-7 px-6 py-8 lg:px-8 lg:py-10">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div><p className="mb-2 text-xs font-semibold uppercase tracking-widest text-indigo-600">Your hiring workspace</p><h1 className="text-3xl font-bold tracking-tight">Hiring Dashboard</h1><p className="mt-2 text-sm leading-6 text-slate-500">Find a candidate, review their evidence, and prepare for the next conversation.</p></div>
        <button type="button" disabled={mode === 'loading'} onClick={() => { setSelected(null); setAttempt((value) => value + 1); }} className={secondaryClass}><RefreshCw className="h-4 w-4" aria-hidden="true" />Refresh list</button>
      </div>
      {mode === 'sample' && <div role="status" className="flex gap-3 rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm leading-6 text-amber-900"><AlertTriangle className="mt-0.5 h-5 w-5 shrink-0" aria-hidden="true" /><p><strong>Sample workspace.</strong> We couldn’t load your team’s candidates. These examples are for demonstration only. Select Refresh list to try again. Local drafts stay separate.</p></div>}
      {notice && <p role="status" className="rounded-xl border border-indigo-100 bg-indigo-50 p-4 text-sm text-indigo-900">{notice}</p>}
      <section aria-label="Hiring summary" className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {metrics.map(({ title, value, detail, icon: Icon }) => <div key={title} className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm"><div className="flex items-center justify-between gap-2"><h2 className="text-sm font-medium text-slate-600">{title}</h2><Icon className="h-5 w-5 text-indigo-500" aria-hidden="true" /></div><p className="mt-4 text-3xl font-semibold tracking-tight">{mode === 'loading' ? '—' : value}</p><p className="mt-2 text-xs leading-5 text-slate-500">{detail}</p></div>)}
      </section>
      <section aria-labelledby="hr-candidates-heading" className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
        <div className="border-b border-slate-200 p-5 sm:p-6">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 id="hr-candidates-heading" className="text-lg font-semibold">Candidates</h2>
              <p className="mt-1 text-sm text-slate-500">Select View for a summary and suggested next steps.</p>
            </div>
            {hasFilters && <button type="button" onClick={clearFilters} className={secondaryClass}>Clear filters</button>}
          </div>
          <div className="mt-5 grid gap-4 md:grid-cols-[2fr_1fr_1fr]">
            <label className="space-y-2 text-xs font-semibold text-slate-600">Search candidate
              <span className="relative block"><Search className="absolute left-3 top-3 h-4 w-4 text-slate-400" aria-hidden="true" /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search by name or email" type="search" className={`${controlClass} pl-9`} /></span>
            </label>
            <label className="space-y-2 text-xs font-semibold text-slate-600">Role
              <select value={role} onChange={(event) => setRole(event.target.value)} className={controlClass}><option value="all">All roles</option>{roles.map((value) => <option key={value} value={value}>{roleLabel(value)}</option>)}</select>
            </label>
            <label className="space-y-2 text-xs font-semibold text-slate-600">Evaluation status
              <select value={status} onChange={(event) => setStatus(event.target.value)} className={controlClass}><option value="all">All statuses</option><option>Completed</option><option>Not completed</option><option>Local draft</option></select>
            </label>
          </div>
        </div>
        {mode === 'loading' ? <div role="status" className="flex items-center justify-center gap-3 p-16 text-sm text-slate-500"><Loader2 className="h-5 w-5 animate-spin" aria-hidden="true" />Loading candidates…</div>
          : filtered.length ? <div tabIndex={0} role="region" aria-label="Candidate table — scroll horizontally to see all columns" className="overflow-x-auto focus-visible:outline focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-indigo-600">
            <table className="w-full min-w-[760px] text-left text-sm">
              <caption className="sr-only">Candidates with evaluation status, evidence status, alerts, and a quick-view action</caption>
              <thead className="bg-slate-50 text-xs text-slate-500"><tr>{['Candidate', 'Role', 'Evaluation', 'Evidence', 'Alerts', 'Action'].map((heading) => <th key={heading} scope="col" className="px-5 py-3.5 font-semibold">{heading}</th>)}</tr></thead>
              <tbody className="divide-y divide-slate-100">{filtered.map((candidate) => <tr key={candidate.id} className="hover:bg-slate-50/70">
                <th scope="row" className="min-w-[180px] max-w-[260px] break-words px-5 py-5 font-normal"><p className="font-semibold text-slate-900">{candidate.display_name}</p><p className="mt-1 text-xs leading-5 text-slate-500">{candidate.source === 'sample' ? 'Sample candidate' : candidate.source === 'draft' ? 'Local draft · not shared' : candidate.primary_email || 'No email provided'}</p></th>
                <td className="px-5 py-5 text-slate-600">{roleLabel(candidate.role)}</td>
                <td className="px-5 py-5"><span className={`inline-flex whitespace-nowrap rounded-full px-2.5 py-1 text-xs font-medium ${candidate.has_completed_dossier ? 'bg-emerald-50 text-emerald-700' : 'bg-slate-100 text-slate-600'}`}>{evaluationLabel(candidate)}</span></td>
                <td className="px-5 py-5 text-slate-600">{evidenceLabel(candidate)}</td>
                <td className="px-5 py-5 text-xs text-slate-500">{hasEvidenceAlert(candidate) ? <span className="inline-flex items-center gap-1.5 font-medium text-amber-700"><AlertTriangle className="h-4 w-4" aria-hidden="true" />Review</span> : candidate.has_completed_dossier ? 'None reported' : 'Not assessed'}</td>
                <td className="sticky right-0 bg-white px-5 py-5"><button type="button" onClick={() => setSelected(candidate)} aria-label={`View ${candidate.display_name}`} className="min-h-11 rounded-lg bg-indigo-50 px-4 py-2 font-semibold text-indigo-700 hover:bg-indigo-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600">View</button></td>
              </tr>)}</tbody>
            </table>
          </div> : <div className="p-12 text-center"><Users className="mx-auto mb-4 h-9 w-9 text-slate-300" aria-hidden="true" /><h3 className="font-semibold">{all.length ? 'No matching candidates' : 'Your candidate list is empty'}</h3><p className="mb-5 mt-2 text-sm text-slate-500">{all.length ? 'Try a different name, role, or evaluation status.' : 'Add a candidate draft to get started.'}</p><button type="button" onClick={all.length ? clearFilters : () => setAdding(true)} className={secondaryClass}>{all.length ? 'Clear filters' : 'Add Candidate'}</button></div>}
        <div aria-live="polite" className="border-t border-slate-200 px-6 py-4 text-xs text-slate-500">{mode === 'loading' ? 'Checking your candidate list' : `Showing ${filtered.length} of ${all.length} candidates${mode === 'sample' ? ' · Sample workspace' : ''}`}</div>
      </section>
      <p className="text-center text-xs leading-5 text-slate-500">Evidence helps you ask better questions. Hiring decisions always remain with your team.</p>
    </main>
    {adding && <AddCandidateDialog onClose={() => setAdding(false)} onAdd={(candidate) => {
      setDrafts((previous) => [candidate, ...previous]); setAdding(false); clearFilters();
      setNotice(`${candidate.display_name} added as a local draft. Download a copy from View before leaving this page.`);
    }} />}
    {selected && <CandidateQuickView key={`${selected.source}-${selected.id}`} candidate={selected} onClose={() => setSelected(null)} />}
  </div>;
}
