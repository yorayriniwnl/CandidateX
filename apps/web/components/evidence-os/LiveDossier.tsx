'use client';

import { useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { BookOpen, ChartNoAxesColumnIncreasing, FileCheck2, GitBranch, Home, Layers3, ListFilter, MessageSquare, ScanLine, Users, type LucideIcon } from 'lucide-react';
import type { CapabilityKey } from '../../types/cci';
import type { LiveResult } from '../../lib/live-analysis';
import { AuditSection, InterviewPlan } from './DossierSections';
import { CapabilityMatrix, ExecutiveSummary, ObservedSignals, ResultHeader } from './DossierOverview';
import { ClaimVerification, UncertaintyPanel } from './VerificationSections';
import { EvidenceLedger, EvidenceInspector } from './EvidenceLedger';
import { EvidenceGraphSection } from '../dossier/EvidenceGraphSection';
import { SourceCoverage } from './SourceCoverage';
import { ResumeReview } from './ResumeReview';
import { resultClaims } from '../../lib/result-claims';
import styles from './result.module.css';
import legacy from './evidence-os.module.css';

const SECTIONS = [
  ['overview', 'Overview'], ['capabilities', 'Capabilities'], ['claims', 'Claims'], ['sources', 'Repositories'],
  ['evidence', 'Evidence'], ['conflicts', 'Uncertainty'], ['interview', 'Interview plan'], ['audit', 'Methodology'],
];
const sectionIcons: Record<string, LucideIcon> = { overview: ScanLine, capabilities: ChartNoAxesColumnIncreasing, claims: FileCheck2, sources: GitBranch, evidence: ListFilter, conflicts: Layers3, interview: MessageSquare, audit: BookOpen };

export function LiveDossier({ result, onNewEvaluation }: { result: LiveResult; onNewEvaluation: () => void }) {
  const [selectedCapability, setSelectedCapability] = useState<CapabilityKey | null>(null);
  const [selectedEvidenceId, setSelectedEvidenceId] = useState<string | null>(null);
  const [sourceFilter, setSourceFilter] = useState('all');
  const [capabilityFilter, setCapabilityFilter] = useState<CapabilityKey | 'all'>('all');
  const [ledgerOpen, setLedgerOpen] = useState(false);
  const [reviewLoaded, setReviewLoaded] = useState(false);
  const claims = useMemo(() => resultClaims(result), [result]);
  const [active, setActive] = useState('overview');
  const selectedEvidence = result.dossier.evidence_records.find(e=>e.evidence_id===selectedEvidenceId);

  useEffect(() => {
    const update = () => {
      const sections = SECTIONS.map(([id]) => document.getElementById(id)).filter((e): e is HTMLElement => !!e);
      const current = [...sections].reverse().find(e => e.getBoundingClientRect().top <= 170);
      setActive(current?.id ?? 'overview');
    };
    window.addEventListener('scroll', update, { passive: true }); update();
    return () => window.removeEventListener('scroll', update);
  }, []);
  useEffect(() => { document.getElementById('result-start')?.scrollIntoView({block:'start'}); }, [result.dossier.analysis_run_id]);

  function scrollTo(id: string) {
    document.getElementById(id)?.scrollIntoView({ behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth', block: 'start' });
  }
  function selectCapability(key: CapabilityKey) { setSelectedCapability(key); scrollTo('capabilities'); }
  function inspectSource(source: string) { setSourceFilter(source); setCapabilityFilter('all'); setLedgerOpen(true); scrollTo('evidence'); }

  return <section id="result-start" className={`${styles.report} ${legacy.resultReport}`} aria-label="Live candidate dossier">
    <ResultHeader result={result} onNewEvaluation={onNewEvaluation} />
    <nav className={styles.navigation} aria-label="Dossier sections">{SECTIONS.map(([id, label]) => { const Icon = sectionIcons[id]; return <a href={`#${id}`} key={id} aria-current={active===id ? 'location' : undefined}><Icon size={14} strokeWidth={1.6} aria-hidden="true" />{label}</a>; })}</nav>
    <ExecutiveSummary result={result} claims={claims} />
    <CapabilityMatrix result={result} selected={selectedCapability} onSelect={setSelectedCapability} onInspectEvidence={(_,id)=>setSelectedEvidenceId(id)} onInspectCapability={key => { setCapabilityFilter(key); setSourceFilter('all'); setLedgerOpen(true); scrollTo('evidence'); }} />
    <ObservedSignals result={result} onInspect={setSelectedEvidenceId} />
    <ClaimVerification result={result} rows={claims} onInspect={setSelectedEvidenceId} />
    <details className={styles.disclosure} onToggle={event => { if (event.currentTarget.open) setReviewLoaded(true); }}><summary>Detailed résumé review & job requirements</summary>{reviewLoaded && <ResumeReview result={result} onInspect={setSelectedEvidenceId} />}</details>
    <SourceCoverage result={result} onInspectEvidence={inspectSource} />
    <section id="evidence" className={styles.section}><div className={styles.sectionHeading}><div><span className={styles.eyebrow}>05 / Trace every conclusion</span><h2>Evidence ledger</h2><p>{result.dossier.evidence_records.length} records · Source artifacts, confidence factors and exact locations.</p></div><button className={styles.secondary} aria-expanded={ledgerOpen} onClick={()=>setLedgerOpen(v=>!v)}>{ledgerOpen ? 'Close evidence ledger' : 'Inspect all evidence'} <span aria-hidden="true">{ledgerOpen ? '−' : '+'}</span></button></div>
      {ledgerOpen && <EvidenceLedger result={result} sourceFilter={sourceFilter} onSourceFilterChange={setSourceFilter} capabilityFilter={capabilityFilter} onCapabilityFilterChange={setCapabilityFilter} selectedEvidenceId={selectedEvidenceId} onSelectEvidence={setSelectedEvidenceId} />}
    </section>
    <UncertaintyPanel result={result} onSelectCapability={selectCapability} onInspect={setSelectedEvidenceId} />
    <InterviewPlan result={result} onSelectEvidence={setSelectedEvidenceId} />
    <details className={styles.disclosure}><summary>Explore evidence connections · {result.graph.nodes.length} nodes</summary><EvidenceGraphSection graph={result.graph} onSelectCapability={selectCapability} onSelectEvidence={setSelectedEvidenceId} /></details>
    <section id="audit" className={styles.section}><div className={styles.sectionHeading}><div><span className={styles.eyebrow}>08 / Research & provenance</span><h2>Methodology</h2><p>Static inspection of supplied sources. Identity and account association are declarations; results do not establish mastery or job performance.</p></div></div><details className={styles.disclosure}><summary>Run metadata, versions & limitations</summary><AuditSection result={result} /></details></section>
    {selectedEvidence && <EvidenceInspector record={selectedEvidence} onClose={()=>setSelectedEvidenceId(null)} />}
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '12px', padding: '36px 0 24px', borderTop: '1px solid var(--rule)', marginTop: '24px', flexWrap: 'wrap' }}>
      <Link
        href="/hr"
        scroll={true}
        className={styles.secondary}
        style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', textDecoration: 'none' }}
        title="Land to Candidates"
        data-testid="bottom-landing-btn-candidates"
      >
        <Users size={14} aria-hidden="true" />
        Candidates
      </Link>
      <Link
        href="/"
        scroll={true}
        className={styles.secondary}
        style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', textDecoration: 'none' }}
        title="Land to Home"
        data-testid="bottom-landing-btn-home"
      >
        <Home size={14} aria-hidden="true" />
        Home
      </Link>
    </div>
  </section>;
}
