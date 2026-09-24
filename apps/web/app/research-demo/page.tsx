'use client';

import { useRef, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import type { CapabilityKey, CanonicalRole } from '../../types/cci';
import { demoRequest, label, SOURCES, SYNTHETIC_CANDIDATE_ID, type DemoInput, type DemoResult, type Scenario } from '../../lib/research-demo';

import { GlassCard } from '@/components/ui/GlassCard';
import { GlowBadge } from '@/components/ui/GlowBadge';
import { GlassButton } from '@/components/ui/GlassButton';
import { GlassInput } from '@/components/ui/GlassInput';
import { GlassSelect } from '@/components/ui/GlassSelect';
import { ProgressBar } from '@/components/ui/ProgressBar';
import { Skeleton } from '@/components/ui/Skeleton';

const INITIAL: DemoInput = {
  scenario: 'consistent', role: 'backend', excluded_sources: [], ownership_multiplier: 1, reliability_false_positives: 0,
};
const ROLES: CanonicalRole[] = ['backend', 'frontend', 'fullstack', 'ml_engineer', 'devops_cloud', 'data_engineer'];
const SCENARIOS: { value: Scenario; name: string; description: string }[] = [
  { value: 'consistent', name: 'Consistent evidence', description: 'Seven simulated source families across three project clusters. A backend-oriented profile makes role differences visible.' },
  { value: 'sparse', name: 'Sparse evidence', description: 'One project with GitHub observations for backend, database and testing only. Other capabilities remain unknown; intervals are not estimable.' },
  { value: 'low_ownership', name: 'Ambiguous GitHub ownership', description: 'The same observations, with GitHub ownership confidence reduced to 5% of its original value.' },
  { value: 'conflicting', name: 'Conflicting observations', description: 'Three source families report negative backend and database observations. The contradictory evidence stays visible.' },
  { value: 'empty', name: 'No usable evidence', description: 'No observations. Capability is unknown, coverage is zero, and interview questions target missing evidence.' },
];
const number = (value: number | null, digits = 1) => value === null ? 'Unknown' : value.toFixed(digits);
const percent = (value: number) => `${(value * 100).toFixed(1)}%`;

export default function ResearchDemonstration() {
  const [input, setInput] = useState<DemoInput>(INITIAL);
  const [result, setResult] = useState<DemoResult | null>(null);
  const [previous, setPrevious] = useState<DemoResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [selected, setSelected] = useState<CapabilityKey>('backend_engineering');
  const [overrideCap, setOverrideCap] = useState<CapabilityKey>('backend_engineering');
  
  const inspector = useRef<HTMLDivElement>(null);
  const resultRef = useRef<HTMLDivElement>(null);
  const inFlight = useRef(false);
  
  const dirty = !!result && JSON.stringify(input) !== JSON.stringify(result.input);
  const dossier = result?.dossier;
  const conflictCount = dossier ? Object.values(dossier.capability_conflicts).filter(c => c.has_meaningful_conflict).length : 0;
  const selectedEvidence = dossier?.evidence_records.filter(e => e.target_capability === selected) || [];
  const sumConfidence = selectedEvidence.reduce((sum, e) => sum + e.confidence, 0);
  const sumWeightedSupport = selectedEvidence.reduce((sum, e) => sum + e.confidence * e.support_score, 0);
  
  const update = (changes: Partial<DemoInput>) => { setInput(current => ({ ...current, ...changes })); setError(''); };

  async function run() {
    if (inFlight.current) return;
    inFlight.current = true;
    setBusy(true); setError(''); setPrevious(result); setResult(null);
    try {
      const next = await demoRequest<DemoResult>('run', input);
      if (next.dossier.candidate_id !== SYNTHETIC_CANDIDATE_ID || next.graph.analysis_run_id !== next.dossier.analysis_run_id) throw new Error('Synthetic result identity mismatch. No dossier displayed.');
      setResult(next);
      setTimeout(() => resultRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 100);
    } catch (cause) { setError(cause instanceof Error ? cause.message : 'The run failed. No result substituted.'); }
    finally { inFlight.current = false; setBusy(false); }
  }

  async function override() {
    if (!result || dirty || inFlight.current) return;
    inFlight.current = true; setBusy(true); setError('');
    try {
      const revised = await demoRequest<Pick<DemoResult, 'dossier' | 'graph' | 'graph_snapshot'>>('rescore', {
        ...result.input, weights: { [overrideCap]: 1 },
      });
      if (revised.dossier.candidate_id !== SYNTHETIC_CANDIDATE_ID || revised.graph.analysis_run_id !== revised.dossier.analysis_run_id) throw new Error('Synthetic result identity mismatch.');
      setPrevious(result); setResult({ ...result, ...revised });
    } catch (cause) { setError(cause instanceof Error ? cause.message : 'Override failed. The displayed snapshot is unchanged.'); }
    finally { inFlight.current = false; setBusy(false); }
  }

  function exportSnapshot() {
    if (!result || dirty) return;
    const url = URL.createObjectURL(new Blob([JSON.stringify(result, null, 2)], { type: 'application/json' }));
    const anchor = document.createElement('a'); anchor.href = url;
    anchor.download = `candidatex-research-${result.dossier.dossier_id}.json`; anchor.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  function inspect(cap: CapabilityKey) { setSelected(cap); inspector.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }); }

  return (
    <div className="min-h-screen overflow-x-hidden bg-[#030712] text-slate-100 pb-16 font-sans">
      <nav className="border-b border-white/[0.06] backdrop-blur-md bg-white/[0.02] flex justify-between items-center gap-5 px-6 py-4 text-sm mb-12 shadow-sm" aria-label="Research navigation">
        <div>
          <span className="tracking-tighter text-2xl font-extrabold mr-2">CandidateX</span> 
          <span className="font-mono text-indigo-400 uppercase tracking-widest text-xs hidden sm:inline">/ Research demonstration</span>
        </div>
        <div className="flex gap-5">
          <a href="#method" className="text-indigo-200 hover:text-indigo-100">The method</a>
          <a href="#benchmarks" className="text-indigo-200 hover:text-indigo-100">Experiments</a>
        </div>
      </nav>

      <div className="px-4 md:px-8 lg:px-16">
        <header className="py-4 md:py-8 max-w-4xl mb-8">
          <div className="font-mono text-indigo-400 uppercase tracking-widest text-xs mb-4">Candidate Capability Intelligence · Interactive research prototype</div>
          <h1 className="text-4xl md:text-5xl lg:text-6xl leading-tight tracking-tight font-bold mb-6">From evidence to interview.</h1>
          <p className="text-slate-400 leading-relaxed text-base md:text-lg max-w-3xl">Explore how the same technical evidence changes meaning for a different role. Separate capability from coverage, inspect each observation, and turn uncertainty into a focused interview.</p>
        </header>

        <GlassCard variant="subtle" glow="indigo" className="mb-8">
          <strong className="text-indigo-300">Controlled synthetic demonstration.</strong> <span className="text-slate-300">Every result is based on generated synthetic observations. No resumes or profiles are accepted. No real person is assessed. This is not a validated hiring predictor. Calculations run through the CCI backend; no external repository is fetched.</span>
        </GlassCard>

        <div className="grid grid-cols-1 lg:grid-cols-[320px_1fr] gap-8 items-start">
          <GlassCard variant="strong" className="flex flex-col gap-5 lg:sticky lg:top-6">
            <div>
              <div className="font-mono text-indigo-400 uppercase tracking-widest text-xs mb-2">01 / Set the conditions</div>
              <h2 className="text-xl font-bold">One candidate. Different evidence.</h2>
              <p className="text-slate-400 text-xs mt-2">Synthetic candidate A · fixed observations, independent of the target role.</p>
            </div>
            
            <fieldset disabled={busy} className="flex flex-col gap-5 mt-4 disabled:opacity-60">
              <div>
                <GlassSelect label="Evidence scenario" value={input.scenario} onChange={e => update({ scenario: e.target.value as Scenario })} options={SCENARIOS.map(s => ({ value: s.value, label: s.name }))} />
                <p className="text-slate-400 text-xs mt-2">{SCENARIOS.find(s => s.value === input.scenario)?.description}</p>
              </div>

              <GlassSelect label="Target role" value={input.role} onChange={e => update({ role: e.target.value as CanonicalRole })} options={ROLES.map(role => ({ value: role, label: label(role) }))} />
              
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">Include source families</label>
                <div className="grid grid-cols-2 gap-2">
                  {SOURCES.map(source => (
                    <label key={source} className="flex items-center gap-2 text-xs text-slate-300 cursor-pointer">
                      <input type="checkbox" className="accent-indigo-500 w-4 h-4 bg-slate-900 border border-slate-700 rounded cursor-pointer" checked={!input.excluded_sources.includes(source)} onChange={e => update({ excluded_sources: e.target.checked ? input.excluded_sources.filter(s => s !== source) : [...input.excluded_sources, source] })} />
                      {source}
                    </label>
                  ))}
                </div>
              </div>

              <GlassInput variant="text" type="range" label={`Ownership multiplier: ${percent(input.ownership_multiplier)}`} value={input.ownership_multiplier} min={0} max={1} step={0.05} onChange={e => update({ ownership_multiplier: Number(e.target.value) })} />
              
              <div>
                <GlassInput variant="text" type="range" label={`Simulated false positives: ${input.reliability_false_positives}`} value={input.reliability_false_positives} min={0} max={100} step={1} onChange={e => update({ reliability_false_positives: Number(e.target.value) })} />
                <p className="text-slate-400 text-xs mt-2">Each source starts with eight simulated true positives and its configured Beta prior.</p>
              </div>

              <div className="flex flex-col gap-3 mt-4">
                <GlassButton variant="primary" onClick={run} loading={busy} fullWidth>{busy ? 'Computing...' : 'Run demonstration'}</GlassButton>
                <GlassButton variant="ghost" onClick={() => update(INITIAL)} fullWidth>Reset inputs</GlassButton>
              </div>
            </fieldset>
          </GlassCard>

          <div className="flex flex-col gap-6 min-w-0" aria-busy={busy}>
            {error && <GlassCard variant="strong" glow="rose" className="text-rose-200 border-rose-900/50" role="alert">{error}</GlassCard>}
            {dirty && <GlassCard variant="subtle" glow="amber" className="text-amber-200" role="status">Inputs changed. Run again to update the results.</GlassCard>}
            
            <AnimatePresence mode="wait">
              {!result && (
                <motion.div key="empty" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }}>
                  <GlassCard className="min-h-[380px] flex flex-col justify-center p-8 md:p-12">
                    <div className="font-mono text-indigo-400 uppercase tracking-widest text-xs mb-4">02 / Observe the mechanism</div>
                    <h2 className="text-2xl font-bold mb-4">{busy ? 'Calculating the dossier…' : 'A score should have an explanation.'}</h2>
                    {busy ? (
                      <div className="flex flex-col gap-4 w-full max-w-2xl">
                        <p className="text-slate-400 mb-4">The backend is applying confidence factors, clustering evidence, calculating role weights, and generating evidence-linked interview questions.</p>
                        <Skeleton variant="card" className="h-24 w-full" />
                        <Skeleton variant="card" className="h-40 w-full" />
                        <Skeleton variant="card" className="h-32 w-full" />
                      </div>
                    ) : (
                      <>
                        <p className="text-slate-400 max-w-xl mb-8 leading-relaxed">Run a scenario to see the actual calculations. Then change one input at a time and compare the resulting capability, coverage, and interview priorities.</p>
                        <div className="flex flex-wrap gap-3">
                          {['Sources', 'Confidence', 'Capabilities', 'Role fit + coverage', 'Interview probes'].map(step => (
                            <GlowBadge key={step} variant="neutral">{step}</GlowBadge>
                          ))}
                        </div>
                      </>
                    )}
                  </GlassCard>
                </motion.div>
              )}

              {result && dossier && (
                <motion.div key="result" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="flex flex-col gap-6" ref={resultRef}>
                  <GlassCard glow="indigo">
                    <div className="flex flex-wrap justify-between items-start gap-4 mb-6">
                      <div>
                        <div className="font-mono text-indigo-400 uppercase tracking-widest text-xs mb-2">02 / The result</div>
                        <h2 className="text-2xl font-bold mb-2">Synthetic candidate A · {label(dossier.role)}</h2>
                        <p data-testid="result-status" className="text-slate-400 text-sm">Completed · synthetic evidence</p>
                      </div>
                      <GlassButton variant="secondary" size="sm" disabled={busy || dirty} onClick={exportSnapshot}>Export snapshot JSON</GlassButton>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
                      <div className="bg-[#0a0f1e] border border-white/[0.05] p-5 rounded-xl">
                        <span className="block text-slate-400 text-xs mb-2">Role Capability Index</span>
                        <strong data-testid="rci-value" className="block text-3xl font-bold tracking-tight mb-1">{number(dossier.rci)}</strong>
                        <span className="block text-slate-500 text-xs">Observed capability / 100</span>
                      </div>
                      <div className="bg-[#0a0f1e] border border-white/[0.05] p-5 rounded-xl">
                        <span className="block text-slate-400 text-xs mb-2">Evidence coverage</span>
                        <strong data-testid="coverage-value" className="block text-3xl font-bold tracking-tight mb-1">{percent(dossier.coverage)}</strong>
                        <span className="block text-slate-500 text-xs">Weighted observability</span>
                      </div>
                      <div className="bg-[#0a0f1e] border border-white/[0.05] p-5 rounded-xl">
                        <span className="block text-slate-400 text-xs mb-2">Conflicted capabilities</span>
                        <strong data-testid="conflict-count" className="block text-3xl font-bold tracking-tight mb-1">{conflictCount}</strong>
                        <span className="block text-slate-500 text-xs">Signals to investigate</span>
                      </div>
                    </div>

                    {dossier.is_insufficient_evidence && (
                      <div className="text-amber-200/90 text-sm mb-4 bg-amber-900/20 p-3 rounded-lg border border-amber-900/30">
                        Insufficient evidence: coverage is below {percent(result.scoring_config.low_coverage_threshold)}. The RCI describes observed capabilities only; this dossier cannot support a complete ranking.
                      </div>
                    )}
                    <p className="text-slate-400 text-sm">{dossier.evidence_records.length} observations · {new Set(dossier.evidence_records.map(e => e.cluster_id)).size} project clusters · scenario: {label(dossier.scenario)}</p>
                    
                    {previous && (
                      <div className="mt-6 p-4 bg-[#0a0f1e] border border-white/[0.05] rounded-lg text-sm text-slate-300">
                        <strong className="text-slate-200">Previous snapshot:</strong> {label(previous.dossier.role)} / {label(previous.dossier.scenario)} — RCI {number(previous.dossier.rci)}, coverage {percent(previous.dossier.coverage)}.<br/>
                        <span className="text-slate-400 mt-1 block">{previous.evidence_digest === result.evidence_digest ? 'Evidence unchanged; compare the role or weights.' : 'Evidence inputs changed.'}</span>
                      </div>
                    )}
                    
                    <details className="mt-6 group">
                      <summary className="cursor-pointer text-sm text-slate-400 hover:text-slate-300 transition-colors">Run identity and reproducibility</summary>
                      <div className="mt-4 p-4 bg-[#080b12] rounded-lg border border-white/[0.05] font-mono text-xs text-slate-400 break-all space-y-1">
                        <p>Candidate: {dossier.candidate_id}</p>
                        <p>Run: {dossier.analysis_run_id}</p>
                        <p>Snapshot: {dossier.dossier_id}</p>
                        <p>Evidence + factors SHA-256: {result.evidence_digest}</p>
                        <p>Scenario version: {result.scenario_version}</p>
                      </div>
                      <p className="text-slate-500 text-xs mt-3">{result.storage_notice}</p>
                    </details>
                  </GlassCard>

                  <GlassCard>
                    <div className="font-mono text-indigo-400 uppercase tracking-widest text-xs mb-2">03 / Separate strength from observability</div>
                    <h2 className="text-xl font-bold mb-2">Twelve capabilities, no hidden zeros.</h2>
                    <p className="text-slate-400 text-sm mb-6">Intervals use project-cluster bootstrap. With fewer than two independent projects, an interval is not estimable. Select a capability to inspect its evidence.</p>
                    
                    <div className="overflow-x-auto w-full">
                      <table className="w-full text-left text-sm border-collapse">
                        <thead>
                          <tr>
                            <th className="py-3 px-4 border-b border-white/[0.05] text-slate-400 font-medium">Capability</th>
                            <th className="py-3 px-4 border-b border-white/[0.05] text-slate-400 font-medium">Weight</th>
                            <th className="py-3 px-4 border-b border-white/[0.05] text-slate-400 font-medium">Estimate</th>
                            <th className="py-3 px-4 border-b border-white/[0.05] text-slate-400 font-medium">Coverage</th>
                            <th className="py-3 px-4 border-b border-white/[0.05] text-slate-400 font-medium">95% interval</th>
                            <th className="py-3 px-4 border-b border-white/[0.05] text-slate-400 font-medium">Conflict</th>
                          </tr>
                        </thead>
                        <tbody>
                          {(Object.keys(dossier.capability_estimates) as CapabilityKey[]).map(cap => {
                            const estimate = dossier.capability_estimates[cap]; 
                            return (
                              <tr key={cap} className="border-b border-white/[0.02] hover:bg-white/[0.01] transition-colors">
                                <td className="py-3 px-4">
                                  <button aria-label={`Inspect ${label(cap)} evidence`} className="text-indigo-300 hover:text-indigo-200 underline underline-offset-4" onClick={() => inspect(cap)}>
                                    {label(cap)}
                                  </button>
                                </td>
                                <td className="py-3 px-4 text-slate-300">{percent(dossier.role_weights[cap])}</td>
                                <td className="py-3 px-4">
                                  <div className="flex items-center gap-3">
                                    <span className="w-8 text-slate-300">{number(estimate.estimate)}</span>
                                    {estimate.estimate !== null && <ProgressBar value={estimate.estimate / 100} color="indigo" size="sm" className="w-20 hidden xl:block" />}
                                  </div>
                                </td>
                                <td className="py-3 px-4 text-slate-300">{percent(estimate.coverage_k)}</td>
                                <td className="py-3 px-4 text-slate-400">{estimate.ci_lower === null || estimate.ci_upper === null ? 'Not estimable' : `${number(estimate.ci_lower)}–${number(estimate.ci_upper)}`}</td>
                                <td className="py-3 px-4">
                                  {dossier.capability_conflicts[cap].has_meaningful_conflict ? <GlowBadge variant="warning" size="sm">Investigate</GlowBadge> : <span className="text-slate-600">—</span>}
                                </td>
                              </tr>
                            ); 
                          })}
                        </tbody>
                      </table>
                    </div>

                    <div className="mt-8 pt-6 border-t border-white/[0.05]">
                      <div className="flex flex-col md:flex-row gap-4 items-end">
                        <div className="flex-1 w-full">
                          <GlassSelect label="Override capability" value={overrideCap} onChange={e => setOverrideCap(e.target.value as CapabilityKey)} options={Object.keys(dossier.role_weights).map(cap => ({value: cap, label: label(cap)}))} />
                        </div>
                        <GlassButton variant="secondary" disabled={busy || dirty} onClick={override}>Apply focused override</GlassButton>
                      </div>
                      <p className="text-slate-500 text-xs mt-3">This teaching control assigns 100% weight to one capability. It recalculates the complete dossier without changing the evidence.</p>
                      
                      <div data-testid="override-history" className="mt-4">
                        {dossier.override_history.map((item, index) => (
                          <p key={index} className="text-slate-400 text-xs mt-2 border-l-2 border-white/[0.1] pl-3 py-1">
                            Override {index + 1}: {item.justification} · {new Date(item.timestamp).toLocaleString()}
                          </p>
                        ))}
                      </div>
                    </div>
                  </GlassCard>

                  <div ref={inspector} className="scroll-mt-24">
                    <GlassCard variant="subtle" data-testid="evidence-inspector">
                      <div className="font-mono text-indigo-400 uppercase tracking-widest text-xs mb-2">04 / Follow the provenance</div>
                      <h2 className="text-xl font-bold mb-3">{label(selected)}</h2>
                      <p className="text-slate-400 text-sm mb-6">Candidate → identity → source → artifact → evidence → capability → role requirement → interview probe. The graph contains {result.graph.nodes.length} nodes and {result.graph.edges.length} relationships; the complete graph is included in the export.</p>
                      
                      <div className="flex flex-wrap gap-2 mb-6">
                        {Array.from(new Set(result.graph.nodes.map(node => node.type))).map(type => (
                          <GlowBadge key={type} variant="neutral" size="sm">{type}: {result.graph.nodes.filter(node => node.type === type).length}</GlowBadge>
                        ))}
                      </div>
                      
                      <div className="bg-[#050810] border border-indigo-900/30 p-4 rounded-lg font-mono text-xs text-indigo-200 mb-6 break-all">
                        Capability = weighted support / confidence sum = {sumWeightedSupport.toFixed(3)} / {sumConfidence.toFixed(3)} = {sumConfidence > 0 ? (sumWeightedSupport / sumConfidence).toFixed(2) : 'Unknown'}
                      </div>

                      {selectedEvidence.length === 0 && (
                        <div className="bg-slate-900/50 border border-slate-800 p-4 rounded-lg text-slate-400 text-sm">
                          No observations support this capability. Its estimate is unknown.
                        </div>
                      )}
                      
                      <div className="flex flex-col gap-4">
                        {selectedEvidence.map((evidence, index) => (
                          <details key={evidence.evidence_id} className="group border border-white/[0.05] rounded-xl bg-[#0a0f1e] overflow-hidden" open={index === 0}>
                            <summary className="cursor-pointer p-4 bg-white/[0.02] hover:bg-white/[0.04] transition-colors text-sm font-medium text-slate-200 flex items-center justify-between">
                              <span>{evidence.source_family}</span>
                              <span className="text-slate-400 font-normal text-xs flex gap-3">
                                <span>Support: {number(evidence.support_score)}</span>
                                <span>Conf: {percent(evidence.confidence)}</span>
                                <span className={evidence.is_positive_support ? "text-emerald-400" : "text-rose-400"}>
                                  {evidence.is_positive_support ? 'Positive' : 'Negative'}
                                </span>
                              </span>
                            </summary>
                            <div className="p-4 border-t border-white/[0.05]">
                              <dl className="grid grid-cols-1 sm:grid-cols-[140px_1fr] gap-x-4 gap-y-3 text-xs">
                                <dt className="text-slate-500">Source</dt><dd className="text-slate-300 break-all">{evidence.source_locator}</dd>
                                <dt className="text-slate-500">Artifact</dt><dd className="text-slate-300 break-all">{evidence.provenance.artifact_path}</dd>
                                <dt className="text-slate-500">Revision</dt><dd className="text-slate-300 font-mono break-all">{evidence.immutable_revision}</dd>
                                <dt className="text-slate-500">SHA-256</dt><dd className="text-slate-300 font-mono break-all">{evidence.fingerprint}</dd>
                                <dt className="text-slate-500">Extractor</dt><dd className="text-slate-300">{evidence.provenance.extractor_version}</dd>
                                <dt className="text-slate-500">Project cluster</dt><dd className="text-slate-300">{evidence.cluster_id}</dd>
                                <dt className="text-slate-500">Observation</dt><dd className="text-slate-300 italic">"{evidence.provenance.raw_support_text}"</dd>
                              </dl>
                              
                              <div className="mt-5 pt-4 border-t border-white/[0.05]">
                                <p className="text-slate-500 text-xs mb-3">Confidence Factors</p>
                                <div className="flex flex-wrap gap-2 mb-3">
                                  {Object.entries(evidence.confidence_factors).map(([factor, value]) => (
                                    <span key={factor} className="px-2.5 py-1 bg-[#101726] border border-white/[0.05] rounded text-[11px] text-slate-300">
                                      {label(factor)}: {value.toFixed(3)}
                                    </span>
                                  ))}
                                </div>
                                <p className="text-slate-500 text-xs">Confidence weight = attribution gate × geometric mean of the five evidence-quality factors; it cannot exceed attribution. Verification status: {evidence.provenance.verification_status}.</p>
                              </div>
                            </div>
                          </details>
                        ))}
                      </div>
                    </GlassCard>
                  </div>

                  <GlassCard variant="subtle" glow="violet">
                    <div className="font-mono text-violet-400 uppercase tracking-widest text-xs mb-2">05 / Prepare the interview</div>
                    <h2 className="text-xl font-bold mb-6">Questions with a reason.</h2>
                    
                    <div className="flex flex-col gap-6">
                      {dossier.interview_questions.map(question => { 
                        const probe = dossier.interview_probes.find(p => p.capability_key === question.target_capability); 
                        return (
                          <article key={question.question_id} className="p-5 bg-[#0a0f1e] border border-white/[0.05] rounded-xl relative overflow-hidden">
                            <div className="absolute top-0 left-0 w-1 h-full bg-violet-500/50"></div>
                            <h3 className="text-lg font-bold text-slate-200 mb-3 flex items-center gap-2">
                              <GlowBadge variant="brand" size="sm">#{probe?.rank}</GlowBadge> 
                              {label(question.target_capability)}
                            </h3>
                            <p className="text-slate-300 text-sm leading-relaxed mb-3 font-medium">{question.question_text}</p>
                            <p className="text-slate-400 text-sm mb-4">{question.rationale}</p>
                            
                            {probe && (
                              <div className="bg-[#050810] border border-violet-900/30 p-3 rounded-lg font-mono text-xs text-violet-200 mb-4 break-all">
                                {probe.role_weight.toFixed(3)} × [0.40 × {probe.coverage_gap_term.toFixed(3)} + 0.35 × {probe.uncertainty_term.toFixed(3)} + 0.25 × {probe.contradiction_term.toFixed(3)}] = {probe.priority_score.toFixed(4)}
                              </div>
                            )}
                            
                            <p className="text-slate-500 text-xs mb-4">Interviewer guidance: {question.verification_guidance}</p>
                            
                            <GlassButton variant="ghost" size="sm" onClick={() => inspect(question.target_capability)}>
                              {question.grounding_evidence_ids.length ? `Inspect ${question.grounding_evidence_ids.length} grounding observations` : 'Inspect the evidence gap'}
                            </GlassButton>
                          </article>
                        ); 
                      })}
                    </div>
                  </GlassCard>

                  <details className="group">
                    <summary className="cursor-pointer text-sm text-slate-400 hover:text-slate-300 transition-colors p-4 bg-[#10151f] border border-white/[0.05] rounded-xl">Source calibration and completed stages</summary>
                    <div className="mt-4 bg-[#10151f] border border-white/[0.05] rounded-xl p-6">
                      <div className="overflow-x-auto mb-6">
                        <table className="w-full text-left text-sm border-collapse">
                          <thead>
                            <tr>
                              <th className="py-2 px-3 border-b border-white/[0.05] text-slate-400 font-medium">Source</th>
                              <th className="py-2 px-3 border-b border-white/[0.05] text-slate-400 font-medium">Prior α / β</th>
                              <th className="py-2 px-3 border-b border-white/[0.05] text-slate-400 font-medium">Simulated TP / FP</th>
                              <th className="py-2 px-3 border-b border-white/[0.05] text-slate-400 font-medium">Posterior</th>
                            </tr>
                          </thead>
                          <tbody>
                            {SOURCES.map(source => { 
                              const r = result.reliability[source]; 
                              return (
                                <tr key={source} className="border-b border-white/[0.02]">
                                  <td className="py-2 px-3 text-slate-300">{source}</td>
                                  <td className="py-2 px-3 text-slate-400">{r.alpha_prior} / {r.beta_prior}</td>
                                  <td className="py-2 px-3 text-slate-400">{r.true_positive_count} / {r.false_positive_count}</td>
                                  <td className="py-2 px-3 text-slate-300">{r.posterior_mean.toFixed(3)}</td>
                                </tr>
                              ); 
                            })}
                          </tbody>
                        </table>
                      </div>
                      
                      <div className="space-y-3">
                        {result.stages.map(stage => (
                          <div key={stage.label} className="text-xs text-slate-400 flex flex-col sm:flex-row gap-1 sm:gap-4">
                            <span className="font-medium text-slate-300 min-w-[120px]">{stage.label}</span>
                            <span className="text-indigo-300">{stage.status}</span>
                            <span className="text-slate-500">{stage.details}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  </details>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>

        <section id="method" className="mt-24 pt-12 border-t border-white/[0.05]">
          <div className="font-mono text-indigo-400 uppercase tracking-widest text-xs mb-2">The method / Sections 2.2–2.3</div>
          <h2 className="text-2xl font-bold mb-8">Make the reasoning inspectable.</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <GlassCard>
              <h3 className="text-lg font-bold mb-3">Evidence strength and confidence</h3>
              <p className="text-slate-400 text-sm leading-relaxed mb-6">Source reliability uses a Beta posterior. Confidence combines artifact integrity, ownership, recency, verification, extraction specificity, and reliability. Capability is their weighted evidence mean.</p>
              <div className="bg-[#050810] border border-white/[0.05] p-4 rounded-lg font-mono text-xs text-slate-300 leading-loose">
                r = (TP + α) / (TP + FP + α + β)<br />
                c = o · (a · t · v · x · r)^(1/5)<br />
                q = Σ(c · z) / Σc &nbsp; · &nbsp; n_eff = (Σc)² / Σ(c²)
              </div>
            </GlassCard>
            <GlassCard>
              <h3 className="text-lg font-bold mb-3">Role fit, coverage and contradictions</h3>
              <p className="text-slate-400 text-sm leading-relaxed mb-6">Role weights are normalized with softmax. Coverage measures weighted evidence saturation. The RCI uses observed capabilities only. Opposing observations remain visible through the contradiction diagnostic.</p>
              <div className="bg-[#050810] border border-white/[0.05] p-4 rounded-lg font-mono text-xs text-slate-300 leading-loose">
                w = softmax(u / T)<br />
                Coverage = Σ w · min(1, Σc / τ)<br />
                RCI = Σ_observed(w · q) / Σ_observed(w)<br />
                D = (positive − negative) / (positive + negative + ε)
              </div>
            </GlassCard>
          </div>
          <p className="text-slate-500 text-xs mt-6 max-w-4xl leading-relaxed">Implementation convention: support, capability and RCI use a 0–100 scale; confidence, coverage and probe CI width use 0–1. Canonical role priors and confidence factors are configured prototype choices, not manuscript-reproduced calibration. Cluster intervals describe these generated observations; they are not validated uncertainty estimates for real candidates.</p>
        </section>

        <section id="benchmarks" className="mt-24 pt-12 border-t border-white/[0.05]">
          <div className="font-mono text-indigo-400 uppercase tracking-widest text-xs mb-2">Experiments / Keep the evidence boundaries visible</div>
          <h2 className="text-2xl font-bold mb-8">Two experiments. Distinct claims.</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <GlassCard variant="strong">
              <GlowBadge variant="neutral" size="sm" className="mb-6">Paper benchmark · archived aggregate</GlowBadge>
              <h3 className="text-lg font-bold mb-3">28,800 candidate-role evaluations</h3>
              <p className="text-slate-400 text-sm leading-relaxed mb-4">16 seeds × 300 candidates × 6 roles. Reported Spearman ρ = 0.928 ± 0.013. Each candidate is evaluated against all six roles.</p>
              <p className="text-slate-500 text-sm leading-relaxed">Section 2.6 discloses that original per-seed/per-role outputs and exact calibration are unavailable. This interface does not reproduce that headline result.</p>
            </GlassCard>
            <GlassCard variant="strong">
              <GlowBadge variant="brand" size="sm" className="mb-6">Executable prototype experiment</GlowBadge>
              <h3 className="text-lg font-bold mb-3">4,800 simulated candidates per mode</h3>
              <p className="text-slate-400 text-sm leading-relaxed mb-6">16 seeds × 6 roles × 50 distinct candidates per role, evaluated under five ablation modes. Scoring config 4.0.0 uses cluster-aware coverage with 0.5 within-cluster artifact decay and a 0.35 estimate threshold; recorded full-CCI Spearman ρ ≈ 0.979.</p>
              <div className="bg-[#050810] border border-white/[0.05] p-3 rounded-lg font-mono text-xs text-indigo-300 mb-4 inline-block">
                python research/run_paper_experiments.py
              </div>
              <p className="text-slate-500 text-sm leading-relaxed">A separate cohort construction and experiment. The controls above illustrate mechanisms; they do not run either benchmark.</p>
            </GlassCard>
          </div>
        </section>

        <footer className="mt-24 pt-8 border-t border-white/[0.05] text-center">
          <GlassCard variant="subtle" className="max-w-3xl mx-auto py-6">
            <p className="text-slate-400 text-sm">CandidateX · Human interview preparation. Synthetic results do not establish real-world hiring accuracy.</p>
            {dossier && (
              <details className="mt-4">
                <summary className="cursor-pointer text-xs text-slate-500 hover:text-slate-400 transition-colors">Snapshot limitations</summary>
                <div className="mt-3 space-y-2 text-left bg-[#050810] p-4 rounded-lg border border-white/[0.02]">
                  {dossier.system_limitations.map(item => (
                    <p key={item} className="text-xs text-slate-500">{item}</p>
                  ))}
                </div>
              </details>
            )}
          </GlassCard>
        </footer>
      </div>
    </div>
  );
}
