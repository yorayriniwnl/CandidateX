'use client';

import { useEffect, useState } from 'react';
import { AlertTriangle, ArrowLeft, ArrowUpRight, CheckCircle2, Download, Loader2 } from 'lucide-react';
import { fetchCandidateDossier, fetchCandidateGraph } from '../../lib/api';
import { MOCK_DOSSIER, MOCK_GRAPH } from '../../data/mockDossier';
import { DossierView } from '../dossier/DossierView';
import type { CEGGraph, Dossier } from '../../types/cci';
import { evaluationLabel, roleLabel, summarizeDossier, withReadTimeout, type HRCandidate } from './hr-data';
import { GlassModal } from '@/components/ui/GlassModal';
import { GlassCard } from '@/components/ui/GlassCard';
import { GlassButton } from '@/components/ui/GlassButton';

function DetailList({ title, items, empty, tone = 'neutral' }: {
  title: string; items: string[]; empty: string; tone?: 'neutral' | 'strength' | 'alert';
}) {
  const Icon = tone === 'alert' ? AlertTriangle : CheckCircle2;
  const isAlert = tone === 'alert' && items.length > 0;
  
  return (
    <GlassCard variant={isAlert ? 'strong' : 'subtle'} glow={isAlert ? 'amber' : 'none'} className="p-5">
      <h3 className="mb-4 text-sm font-semibold text-slate-100">{title}</h3>
      {items.length ? <ul className="space-y-3">{items.map((item, index) => (
        <li key={index} className="flex items-start gap-3 text-sm leading-6 text-slate-300">
          {tone === 'neutral' ? <span aria-hidden="true" className="mt-2.5 h-1.5 w-1.5 shrink-0 rounded-full bg-slate-500" />
            : <Icon aria-hidden="true" className={`mt-1 h-4 w-4 shrink-0 ${tone === 'alert' ? 'text-amber-500' : 'text-emerald-500'}`} />}
          <span className="min-w-0 break-words">{item}</span>
        </li>
      ))}</ul> : <p className="text-sm leading-6 text-slate-400">{empty}</p>}
    </GlassCard>
  );
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
    <GlassModal 
      isOpen={!!candidate} 
      onClose={onClose} 
      title={fullView ? `${candidate.display_name} · Technical dossier` : candidate.display_name}
      subtitle={`${roleLabel(candidate.role)} · ${evaluationLabel(candidate)}${candidate.source === 'sample' ? ' · Sample candidate' : ''}`}
      size={fullView ? 'xl' : 'lg'}
    >
      {fullView ? <div className="space-y-6">
        <GlassButton variant="ghost" onClick={() => setFullView(false)} icon={<ArrowLeft className="h-4 w-4" />}>
          Back to summary
        </GlassButton>
        {graphLoading && <div className="flex items-center gap-3 py-8 text-sm text-slate-400"><Loader2 className="h-4 w-4 animate-spin" />Loading full technical dossier…</div>}
        {graphError && <div role="alert" className="mt-4 rounded-xl bg-amber-500/10 border border-amber-500/20 p-4 text-sm text-amber-200">{graphError}<button className="ml-2 font-medium text-amber-400 hover:text-amber-300 underline" onClick={() => setGraphAttempt((value) => value + 1)}>Try again</button></div>}
        {!graphLoading && !graphError && dossier && graph && <GlassCard className="p-1 sm:p-2">
          {candidate.source === 'sample' && <p className="mb-4 px-4 pt-4 text-sm text-amber-400">Sample dossier — demonstration only. Do not submit feedback for this sample.</p>}
          <DossierView initialDossier={dossier} graph={graph} candidateName={candidate.display_name} />
        </GlassCard>}
      </div> : <div className="space-y-6">
        {loading && <div role="status" className="flex items-center gap-3 py-10 text-sm text-slate-400"><Loader2 className="h-5 w-5 animate-spin" aria-hidden="true" />Loading candidate summary…</div>}
        {error && <div role="alert" className="rounded-xl bg-amber-500/10 border border-amber-500/20 p-4 text-sm leading-6 text-amber-200">{error}<button onClick={() => setAttempt((value) => value + 1)} className="ml-2 font-semibold text-amber-400 hover:text-amber-300 underline">Try again</button></div>}
        {!loading && !error && <>
          <GlassCard glow="indigo" className="p-5 border-indigo-500/20">
            <h3 className="mb-2 text-sm font-semibold text-indigo-100">Overall candidate summary</h3>
            <p className="text-sm leading-6 text-indigo-200/80">{summary
              ? `The evaluation is complete. ${summary.strengths.length ? 'Some stated skills are supported by evidence.' : 'Review the supplied work with your technical interviewer.'} ${summary.alerts.length ? 'There are evidence gaps or mixed findings to discuss before deciding on next steps.' : 'No specific evidence alerts were reported in this evaluation.'}`
              : 'This candidate has not been evaluated yet. Collect work samples and arrange a technical review before drawing conclusions about their skills.'}</p>
            {candidate.source === 'draft' && <p className="mt-3 text-sm font-medium text-indigo-300">Local draft only — download a copy before leaving or refreshing this page.</p>}
          </GlassCard>
          <div className="grid gap-6 md:grid-cols-2">
            <DetailList title="Key strengths" tone="strength" items={summary?.strengths || []} empty="No supported strengths to show yet. This is not a negative assessment." />
            <DetailList title="Areas to discuss" items={summary?.discussion || []} empty="Ask about the candidate’s recent work, personal contribution, and the results they achieved." />
          </div>
          <DetailList title="Evidence gaps & alerts" tone="alert" items={summary?.alerts || []} empty={dossier ? 'No specific alerts reported. Missing information is not proof of a missing skill.' : 'Evidence has not been reviewed yet. Request a relevant work sample.'} />
          <GlassCard variant="subtle" className="p-5">
            <h3 className="mb-3 text-sm font-semibold text-slate-100">Suggested technical interview questions</h3>
            <p className="mb-4 text-xs leading-5 text-slate-400">Share these with your technical interviewer. They support a conversation, not an automatic hiring decision.</p>
            <ol className="divide-y divide-white/10 text-sm leading-7 text-slate-300">
              {(dossier?.interview_questions.length ? dossier.interview_questions.slice(0, 4).map((question) => question.question_text) : [
                'Walk us through a recent project. What did you personally build, and what trade-offs did you make?',
                'How did you test your work and check that it solved the intended problem?',
              ]).map((question, index) => <li key={index} className="flex gap-4 py-4 first:pt-0"><span aria-hidden="true" className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-indigo-500/20 text-xs font-semibold text-indigo-300 border border-indigo-500/20">{index + 1}</span><span className="min-w-0 break-words mt-0.5">{question}</span></li>)}
            </ol>
            {!dossier?.interview_questions.length && <p className="mt-4 text-xs text-slate-500">General questions — not based on an evaluation.</p>}
          </GlassCard>
          {candidate.manifest && <DetailList title="Candidate-provided skills · not verified" items={candidate.manifest.declared_skills} empty="No skills provided yet." />}
        </>}
        <div className="flex flex-wrap gap-3 pt-4 border-t border-white/10 mt-8">
          <GlassButton disabled={!dossier || loading || !!error} onClick={() => setFullView(true)} variant="primary" icon={<ArrowUpRight className="h-4 w-4" />} iconPosition="right">
            Open full technical dossier
          </GlassButton>
          {candidate.manifest && <GlassButton onClick={downloadDraft} variant="secondary" icon={<Download className="h-4 w-4" />}>
            Download draft
          </GlassButton>}
          {!candidate.has_completed_dossier && <p className="w-full mt-2 text-xs text-slate-500">A full dossier becomes available after an evaluation is completed.</p>}
        </div>
      </div>}
    </GlassModal>
  );
}
