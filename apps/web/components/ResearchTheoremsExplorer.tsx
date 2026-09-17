'use client';

import React, { useEffect, useMemo, useState } from 'react';
import {
  AlertTriangle,
  BookOpen,
  CheckCircle2,
  FlaskConical,
  GraduationCap,
  Sigma,
  ShieldCheck,
} from 'lucide-react';
import { AblationStudyResponse } from '../types/cci';
import { fetchAblationStudy } from '../lib/api';

const PAPER_BENCHMARK = {
  seeds: 16,
  candidateProfilesPerSeed: 300,
  roles: 6,
  candidateRoleEvaluations: 28800,
  metrics: [
    { label: 'Spearman ρ', value: '0.928 ± 0.013', note: 'paper-reported rank correlation' },
    { label: 'Kendall τ', value: '0.774 ± 0.019', note: 'paper-reported rank concordance' },
    { label: 'nDCG@20', value: '0.970 ± 0.011', note: 'paper-reported top-ranking quality' },
  ],
};

const CANONICAL_ROLES = [
  'Backend Engineering',
  'Frontend Engineering',
  'Full-stack Engineering',
  'Machine Learning Engineering',
  'DevOps / Cloud Engineering',
  'Data Engineering',
];

const FORMULAE = [
  {
    title: 'Evidence recency',
    formula: 'tₑ,ₖ = exp(-λₖ · Δtₑ)',
    explanation: 'Older evidence is discounted at a capability-specific decay rate.',
  },
  {
    title: 'Six-factor evidence confidence',
    formula: 'cₑ,ₖ = (aₑ · oₑ · tₑ,ₖ · vₑ · xₑ · rₛ(e))^(1/6)',
    explanation: 'Artifact integrity, ownership, recency, verification, depth and source reliability are coupled multiplicatively.',
  },
  {
    title: 'Capability estimate',
    formula: 'qₖ = Σ(cₑ,ₖ zₑ,ₖ) / Σcₑ,ₖ',
    explanation: 'Observed capability is a confidence-weighted estimate. Missing evidence remains UNKNOWN rather than becoming zero.',
  },
  {
    title: 'Effective evidence count',
    formula: 'n_eff,ₖ = (Σcₑ,ₖ)² / Σ(cₑ,ₖ²)',
    explanation: 'Kish effective sample size prevents many weak observations from masquerading as strong statistical support.',
  },
  {
    title: 'Contradiction diagnostic',
    formula: 'Dₖ = (Pₖ - Nₖ) / (Pₖ + Nₖ + ε)',
    explanation: 'Positive and contradictory support remain visible instead of being silently averaged away.',
  },
  {
    title: 'Interview probe priority',
    formula: 'Iₖ = wₖ[α(1-Covₖ) + β·CIwidthₖ + γ·Confₖ]',
    explanation: 'The implementation follows the paper formulation: role weight multiplies the coverage-gap, uncertainty and conflict terms.',
  },
  {
    title: 'Role Capability Index',
    formula: 'RCI = Σₖ∈O(wₖqₖ) / Σₖ∈O wₖ',
    explanation: 'RCI summarizes observed role-relevant capability while Evidence Coverage is reported separately.',
  },
];

const FALLBACK_ABLATION: AblationStudyResponse = {
  total_candidates: 4800,
  total_seeds: 16,
  roles_count: 6,
  models: [
    { model_name: 'FULL_CCI', display_name: 'Full CCI', mae: 1.943, rmse: 2.469, spearman_rho: 0.943, kendall_tau: 0.794, statistical_significance: 'Supplementary baseline', is_baseline: true },
    { model_name: 'NO_RECENCY_DECAY', display_name: 'Without recency decay', mae: 1.975, rmse: 2.505, spearman_rho: 0.943, kendall_tau: 0.794, statistical_significance: 'p < 0.001' },
    { model_name: 'NO_OWNERSHIP_DISCOUNT', display_name: 'Without ownership discount', mae: 2.219, rmse: 2.813, spearman_rho: 0.933, kendall_tau: 0.775, statistical_significance: 'p < 0.001' },
    { model_name: 'UNIFORM_WEIGHTS', display_name: 'Uniform role weights', mae: 3.172, rmse: 3.761, spearman_rho: 0.939, kendall_tau: 0.785, statistical_significance: 'p < 0.001' },
    { model_name: 'UNCALIBRATED_SOURCES', display_name: 'Uncalibrated sources', mae: 1.922, rmse: 2.446, spearman_rho: 0.942, kendall_tau: 0.792, statistical_significance: 'supplementary diagnostic' },
  ],
  role_breakdown: [],
  latex_table: '',
  markdown_table: '',
  notes: 'Supplementary implementation ablation harness. This is not the paper headline benchmark and must not be presented as real-world hiring validation.',
};

export const ResearchTheoremsExplorer: React.FC<{
  isBackendOnline?: boolean | null;
}> = ({ isBackendOnline }) => {
  const [ablation, setAblation] = useState<AblationStudyResponse>(FALLBACK_ABLATION);
  const [loadingAblation, setLoadingAblation] = useState(false);

  useEffect(() => {
    if (!isBackendOnline) return;
    setLoadingAblation(true);
    fetchAblationStudy()
      .then((payload) => setAblation(payload))
      .catch(() => setAblation(FALLBACK_ABLATION))
      .finally(() => setLoadingAblation(false));
  }, [isBackendOnline]);

  const fullModel = useMemo(
    () => ablation.models.find((m) => m.model_name === 'FULL_CCI') || ablation.models[0],
    [ablation],
  );

  return (
    <div className="space-y-6">
      <section className="rounded-2xl border border-indigo-500/25 bg-indigo-950/20 p-6 shadow-xl">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div className="max-w-3xl">
            <div className="mb-2 flex items-center gap-2 text-indigo-300">
              <GraduationCap className="h-5 w-5" />
              <span className="text-xs font-bold uppercase tracking-[0.18em]">Conference-paper methodology</span>
            </div>
            <h2 className="text-2xl font-bold text-white">Candidate Capability Intelligence methodology</h2>
            <p className="mt-2 text-sm leading-6 text-slate-300">
              This page separates the values reported in the conference paper from the repository's supplementary implementation experiments. The two are related research artifacts, but they are not the same benchmark.
            </p>
          </div>
          <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 px-4 py-3 text-xs text-emerald-200">
            <div className="flex items-center gap-2 font-semibold">
              <ShieldCheck className="h-4 w-4" /> Human decision support only
            </div>
            <p className="mt-1 max-w-xs text-emerald-100/75">No autonomous hire or reject decision is produced by CandidateX.</p>
          </div>
        </div>
      </section>

      <section className="rounded-2xl border border-slate-800 bg-slate-900 p-6 shadow-xl">
        <div className="mb-5 flex items-center gap-3">
          <BookOpen className="h-5 w-5 text-indigo-400" />
          <div>
            <h3 className="text-lg font-semibold text-white">Paper-reported controlled benchmark</h3>
            <p className="text-xs text-slate-400">Use these figures when discussing the submitted paper.</p>
          </div>
        </div>

        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <Metric label="Deterministic seeds" value={String(PAPER_BENCHMARK.seeds)} />
          <Metric label="Candidate profiles / seed" value={String(PAPER_BENCHMARK.candidateProfilesPerSeed)} />
          <Metric label="Canonical roles" value={String(PAPER_BENCHMARK.roles)} />
          <Metric label="Candidate-role evaluations" value={PAPER_BENCHMARK.candidateRoleEvaluations.toLocaleString()} />
        </div>

        <div className="mt-4 grid gap-3 md:grid-cols-3">
          {PAPER_BENCHMARK.metrics.map((metric) => (
            <div key={metric.label} className="rounded-xl border border-slate-800 bg-slate-950/70 p-4">
              <div className="font-mono text-2xl font-bold text-indigo-300">{metric.value}</div>
              <div className="mt-1 text-sm font-semibold text-slate-200">{metric.label}</div>
              <div className="mt-1 text-xs text-slate-500">{metric.note}</div>
            </div>
          ))}
        </div>

        <div className="mt-4 rounded-xl border border-amber-500/25 bg-amber-500/10 p-4 text-sm text-amber-100">
          <div className="flex items-start gap-2">
            <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-300" />
            <p>
              These are synthetic controlled-experiment results. They do not establish real-world hiring accuracy, fairness, or candidate performance. External human-reviewed validation remains future work.
            </p>
          </div>
        </div>
      </section>

      <section className="rounded-2xl border border-slate-800 bg-slate-900 p-6 shadow-xl">
        <div className="mb-4 flex items-center gap-3">
          <Sigma className="h-5 w-5 text-violet-400" />
          <div>
            <h3 className="text-lg font-semibold text-white">Paper-aligned mathematical core</h3>
            <p className="text-xs text-slate-400">Displayed equations match the implementation contracts used by the scoring and probe-priority modules.</p>
          </div>
        </div>

        <div className="grid gap-3 lg:grid-cols-2">
          {FORMULAE.map((item) => (
            <article key={item.title} className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
              <h4 className="text-sm font-semibold text-slate-100">{item.title}</h4>
              <div className="my-3 overflow-x-auto rounded-lg border border-slate-800 bg-black/20 px-3 py-2 font-mono text-sm text-indigo-300">
                {item.formula}
              </div>
              <p className="text-xs leading-5 text-slate-400">{item.explanation}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="rounded-2xl border border-slate-800 bg-slate-900 p-6 shadow-xl">
        <div className="mb-4 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-3">
            <FlaskConical className="h-5 w-5 text-emerald-400" />
            <div>
              <h3 className="text-lg font-semibold text-white">Supplementary implementation ablation</h3>
              <p className="text-xs text-slate-400">Repository harness, N={ablation.total_candidates.toLocaleString()}. Not the paper headline benchmark.</p>
            </div>
          </div>
          <span className="rounded-full border border-slate-700 bg-slate-950 px-3 py-1 text-[11px] font-mono text-slate-400">
            {loadingAblation ? 'loading backend artifact…' : isBackendOnline ? 'backend artifact' : 'bundled fallback artifact'}
          </span>
        </div>

        {fullModel && (
          <div className="mb-4 grid gap-3 sm:grid-cols-4">
            <Metric label="Full CCI MAE" value={fullModel.mae.toFixed(3)} />
            <Metric label="Full CCI RMSE" value={fullModel.rmse.toFixed(3)} />
            <Metric label="Supplementary ρ" value={fullModel.spearman_rho.toFixed(3)} />
            <Metric label="Supplementary τ" value={fullModel.kendall_tau.toFixed(3)} />
          </div>
        )}

        <div className="overflow-x-auto rounded-xl border border-slate-800">
          <table className="w-full min-w-[760px] text-left text-xs">
            <thead className="bg-slate-950 text-slate-400">
              <tr>
                <th className="px-4 py-3">Model</th>
                <th className="px-4 py-3">MAE ↓</th>
                <th className="px-4 py-3">RMSE ↓</th>
                <th className="px-4 py-3">Spearman ρ ↑</th>
                <th className="px-4 py-3">Kendall τ ↑</th>
                <th className="px-4 py-3">Interpretation</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800">
              {ablation.models.map((model) => (
                <tr key={model.model_name} className="bg-slate-900/70 text-slate-300">
                  <td className="px-4 py-3 font-semibold text-slate-100">{model.display_name}</td>
                  <td className="px-4 py-3 font-mono">{model.mae.toFixed(3)}</td>
                  <td className="px-4 py-3 font-mono">{model.rmse.toFixed(3)}</td>
                  <td className="px-4 py-3 font-mono">{model.spearman_rho.toFixed(3)}</td>
                  <td className="px-4 py-3 font-mono">{model.kendall_tau.toFixed(3)}</td>
                  <td className="px-4 py-3 text-slate-500">{model.statistical_significance}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <p className="mt-3 text-xs leading-5 text-slate-500">{ablation.notes || FALLBACK_ABLATION.notes}</p>
      </section>

      <section className="rounded-2xl border border-slate-800 bg-slate-900 p-6 shadow-xl">
        <div className="mb-4 flex items-center gap-3">
          <CheckCircle2 className="h-5 w-5 text-emerald-400" />
          <div>
            <h3 className="text-lg font-semibold text-white">Canonical engineering roles</h3>
            <p className="text-xs text-slate-400">The paper and implementation use the same six-role ontology.</p>
          </div>
        </div>
        <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
          {CANONICAL_ROLES.map((role) => (
            <div key={role} className="rounded-lg border border-slate-800 bg-slate-950/60 px-3 py-2 text-sm text-slate-300">
              {role}
            </div>
          ))}
        </div>
      </section>
    </div>
  );
};

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
      <div className="font-mono text-xl font-bold text-white">{value}</div>
      <div className="mt-1 text-[11px] uppercase tracking-wider text-slate-500">{label}</div>
    </div>
  );
}
