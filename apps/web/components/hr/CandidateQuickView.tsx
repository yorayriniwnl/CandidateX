'use client';

import { useEffect, useState } from 'react';
import { AlertTriangle, ArrowLeft, ArrowUpRight, CheckCircle2, Download, Loader2 } from 'lucide-react';
import { fetchCandidateDossier, fetchCandidateGraph } from '../../lib/api';
import { MOCK_DOSSIER, MOCK_GRAPH } from '../../data/mockDossier';
import { DossierView } from '../dossier/DossierView';
import type { CEGGraph, Dossier } from '../../types/cci';
import { HRDialog, primaryClass, secondaryClass } from './HRDialog';
import { evaluationLabel, roleLabel, summarizeDossier, withReadTimeout, type HRCandidate } from './hr-data';

function DetailList({ title, items, empty, tone = 'neutral' }: {
  title: string; items: string[]; empty: string; tone?: 'neutral' | 'strength' | 'alert';
}) {
  const Icon = tone === 'alert' ? AlertTriangle : CheckCircle2;
  return <section className={tone === 'alert' && items.length ? 'rounded-xl bg-amber-50 p-4' : ''}>
    <h3 className="mb-3 text-sm font-semibold">{title}</h3>
    {items.length ? <ul className="space-y-3">{items.map((item, index) => (
      <li key={index} className="flex items-start gap-3 text-sm leading-6 text-slate-600">
        {tone === 'neutral' ? <span aria-hidden="true" className="mt-2.5 h-1 w-1 shrink-0 rounded-full bg-slate-400" />
          : <Icon aria-hidden="true" className={`mt-1 h-4 w-4 shrink-0 ${tone === 'alert' ? 'text-amber-700' : 'text-emerald-600'}`} />}
        <span className="min-w-0 break-words">{item}</span>
      </li>
    ))}</ul> : <p className="text-sm leading-6 text-slate-500">{empty}</p>}
  </section>;
}

export function CandidateQuickView({ candidate, onClose }: { candidate: HRCandidate; onClose: () => void }) {
  const [dossier, setDossier] = useState<Dossier | null>(null);
  const [loading, setLoading] = useState(candidate.has_completed_dossier);
  const [error, setError] = useState('');
  const [attempt, setAttempt] = useState(0);
  const [fullView, setFullView] = useState(false);
  const [graph, setGraph] = useState<CEGGraph | null>(null);
  const [graphLoading, setGraphLoading] = useState(false);
  const [graphAttempt, setGraphAttempt] = useState(0);
  const [graphError, setGraphError] = useState('');

  useEffect(() => {
    let active = true;
    if (!candidate.has_completed_dossier) return;
    setLoading(true);
    setError('');
    const request = candidate.source === 'sample' ? Promise.resolve(MOCK_DOSSIER) : withReadTimeout(fetchCandidateDossier(candidate.id));
    request.then((result) => {
      if (result.candidate_id !== candidate.id) throw new Error('Candidate mismatch');
      if (active) setDossier(result);
    }).catch(() => {
      if (active) setError('We couldn’t load this candidate’s evaluation. No sample findings have been substituted.');
    }).finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [candidate.id, candidate.source, candidate.has_completed_dossier, attempt]);

  useEffect(() => {
    if (!fullView || !dossier) return;
    let active = true;
    setGraphLoading(true);
    setGraphError('');
    const request = candidate.source === 'sample' ? Promise.resolve(MOCK_GRAPH) : withReadTimeout(fetchCandidateGraph(candidate.id));
    request.then((result) => {
      if (result.candidate_id !== dossier.candidate_id || result.analysis_run_id !== dossier.analysis_run_id) throw new Error('Evaluation mismatch');
      if (active) setGraph(result);
    }).catch(() => {
      if (active) setGraphError('The full technical view could not be loaded. You can still use the candidate summary.');
    }).finally(() => { if (active) setGraphLoading(false); });
    return () => { active = false; };
  }, [fullView, dossier, candidate.id, candidate.source, graphAttempt]);

  function downloadDraft() {
    const blob = new Blob([JSON.stringify(candidate.manifest, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'candidate-intake-draft.json';
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  const summary = dossier ? summarizeDossier(dossier) : null;
  return (
    <HRDialog title={fullView ? `${candidate.display_name} · Technical dossier` : candidate.display_name}
      description={`${roleLabel(candidate.role)} · ${evaluationLabel(candidate)}${candidate.source === 'sample' ? ' · Sample candidate' : ''}`}
      onClose={onClose} wide={fullView}>
      {fullView ? <div className="p-6">
        <button type="button" onClick={() => setFullView(false)} className={secondaryClass}><ArrowLeft className="h-4 w-4" aria-hidden="true" />Back to summary</button>
        {graphLoading && <p role="status" className="py-8 text-sm text-slate-500">Loading full technical dossier…</p>}
        {graphError && <div role="alert" className="mt-4 rounded-xl bg-amber-50 p-4 text-sm text-amber-900">{graphError}<button className="ml-2 underline" onClick={() => setGraphAttempt((value) => value + 1)}>Try again</button></div>}
        {!graphLoading && !graphError && dossier && graph && <div className="mt-5 rounded-xl bg-slate-950 p-4 text-slate-100 sm:p-6">
          {candidate.source === 'sample' && <p className="mb-4 text-sm text-amber-200">Sample dossier — demonstration only. Do not submit feedback for this sample.</p>}
          <DossierView initialDossier={dossier} graph={graph} candidateName={candidate.display_name} />
        </div>}
      </div> : <div className="space-y-6 p-6">
        {loading && <div role="status" className="flex items-center gap-3 py-10 text-sm text-slate-500"><Loader2 className="h-5 w-5 animate-spin" aria-hidden="true" />Loading candidate summary…</div>}
        {error && <div role="alert" className="rounded-xl bg-amber-50 p-4 text-sm leading-6 text-amber-900">{error}<button onClick={() => setAttempt((value) => value + 1)} className="ml-2 font-semibold underline">Try again</button></div>}
        {!loading && !error && <>
          <section className="rounded-xl border border-indigo-100 bg-indigo-50 p-5">
            <h3 className="mb-2 text-sm font-semibold text-indigo-950">Overall candidate summary</h3>
            <p className="text-sm leading-6 text-indigo-900">{summary
              ? `The evaluation is complete. ${summary.strengths.length ? 'Some stated skills are supported by evidence.' : 'Review the supplied work with your technical interviewer.'} ${summary.alerts.length ? 'There are evidence gaps or mixed findings to discuss before deciding on next steps.' : 'No specific evidence alerts were reported in this evaluation.'}`
              : 'This candidate has not been evaluated yet. Collect work samples and arrange a technical review before drawing conclusions about their skills.'}</p>
            {candidate.source === 'draft' && <p className="mt-2 text-sm font-medium text-indigo-900">Local draft only — download a copy before leaving or refreshing this page.</p>}
          </section>
          <DetailList title="Key strengths" tone="strength" items={summary?.strengths || []} empty="No supported strengths to show yet. This is not a negative assessment." />
          <DetailList title="Areas to discuss" items={summary?.discussion || []} empty="Ask about the candidate’s recent work, personal contribution, and the results they achieved." />
          <DetailList title="Evidence gaps & alerts" tone="alert" items={summary?.alerts || []} empty={dossier ? 'No specific alerts reported. Missing information is not proof of a missing skill.' : 'Evidence has not been reviewed yet. Request a relevant work sample.'} />
          <section>
            <h3 className="mb-3 text-sm font-semibold">Suggested technical interview questions</h3>
            <p className="mb-3 text-xs leading-5 text-slate-500">Share these with your technical interviewer. They support a conversation, not an automatic hiring decision.</p>
            <ol className="divide-y divide-slate-200 text-sm leading-7 text-slate-700">
              {(dossier?.interview_questions.length ? dossier.interview_questions.slice(0, 4).map((question) => question.question_text) : [
                'Walk us through a recent project. What did you personally build, and what trade-offs did you make?',
                'How did you test your work and check that it solved the intended problem?',
              ]).map((question, index) => <li key={index} className="flex gap-3 py-4 first:pt-0"><span aria-hidden="true" className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-indigo-50 text-xs font-semibold text-indigo-700">{index + 1}</span><span className="min-w-0 break-words">{question}</span></li>)}
            </ol>
            {!dossier?.interview_questions.length && <p className="mt-3 text-xs text-slate-500">General questions — not based on an evaluation.</p>}
          </section>
          {candidate.manifest && <DetailList title="Candidate-provided skills · not verified" items={candidate.manifest.declared_skills} empty="No skills provided yet." />}
        </>}
        <div className="sticky -bottom-6 -mx-6 flex flex-wrap gap-3 border-t border-slate-200 bg-white px-6 py-4">
          <button type="button" disabled={!dossier || loading || !!error} onClick={() => setFullView(true)} className={primaryClass}>Open full technical dossier<ArrowUpRight className="h-4 w-4" aria-hidden="true" /></button>
          {candidate.manifest && <button type="button" onClick={downloadDraft} className={secondaryClass}><Download className="h-4 w-4" aria-hidden="true" />Download draft</button>}
          {!candidate.has_completed_dossier && <p className="w-full text-xs text-slate-500">A full dossier becomes available after an evaluation is completed.</p>}
        </div>
      </div>}
    </HRDialog>
  );
}
