'use client';

import { useState } from 'react';
import type { CapabilityKey } from '../../types/cci';
import type { LiveResult } from '../../lib/live-analysis';
import { AuditSection, ClaimsSection, ConflictAndUnknownReview, InterviewPlan } from './DossierSections';
import { CapabilityMatrix, ExecutiveSummary } from './DossierOverview';
import { EvidenceLedger } from './EvidenceLedger';
import { EvidenceGraphSection } from '../dossier/EvidenceGraphSection';
import { SourceCoverage } from './SourceCoverage';
import { DetailedAnalysis } from '../../app/analyze/DetailedAnalysis';
import styles from './evidence-os.module.css';

const SECTIONS = [
  { id: 'overview', label: 'Overview', detail: 'Decision summary' },
  { id: 'capabilities', label: 'Capabilities', detail: 'Role context × evidence' },
  { id: 'evidence', label: 'Evidence', detail: 'Static observations' },
  { id: 'claims', label: 'Claims', detail: 'Declarations × sources' },
  { id: 'sources', label: 'Sources', detail: 'Acquisition receipts' },
  { id: 'conflicts', label: 'Unknowns & conflicts', detail: 'Gaps to investigate' },
  { id: 'interview', label: 'Interview', detail: 'Technical follow-up' },
  { id: 'evidence-graph', label: 'Graph', detail: 'Evidence provenance' },
  { id: 'audit', label: 'Audit', detail: 'Run metadata' },
];

export function LiveDossier({ result, onNewEvaluation }: { result: LiveResult; onNewEvaluation: () => void }) {
  const firstObserved = Object.values(result.dossier.capability_estimates).find(item => item.is_observed && item.estimate !== null)?.capability_key;
  const firstCapability = firstObserved ?? Object.values(result.dossier.capability_estimates)[0]?.capability_key ?? 'backend_engineering';
  const [selectedCapability, setSelectedCapability] = useState<CapabilityKey>(firstCapability);
  const [selectedEvidenceId, setSelectedEvidenceId] = useState<string | null>(null);
  const [sourceFilter, setSourceFilter] = useState('all');
  const [capabilityFilter, setCapabilityFilter] = useState<CapabilityKey | 'all'>('all');
  const estimates = Object.values(result.dossier.capability_estimates);
  const observedCount = estimates.filter(item => item.is_observed && item.estimate !== null).length;
  const conflicts = Object.values(result.dossier.capability_conflicts).filter(item => item.has_meaningful_conflict).length;

  function scrollTo(sectionId: string) {
    const target = document.getElementById(sectionId);
    if (!target) return;
    const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    target.scrollIntoView({ behavior: reduceMotion ? 'auto' : 'smooth', block: 'start' });
  }

  function selectEvidence(evidenceId: string) {
    setCapabilityFilter('all');
    setSourceFilter('all');
    setSelectedEvidenceId(evidenceId);
    scrollTo('evidence');
  }

  function inspectCapabilityEvidence(capability: CapabilityKey, evidenceId: string) {
    setCapabilityFilter(capability);
    setSourceFilter('all');
    setSelectedEvidenceId(evidenceId);
    scrollTo('evidence');
  }

  function selectCapability(capability: CapabilityKey) {
    setSelectedCapability(capability);
    scrollTo('capabilities');
  }

  function inspectSource(source: string) {
    setSourceFilter(source);
    setCapabilityFilter('all');
    scrollTo('evidence');
  }

  return (
    <section className={styles.dossierShell} aria-label="Live candidate dossier">
      <div className={styles.dossierToolbar}>
        <div><span>LIVE DOSSIER</span><code>{result.dossier.analysis_run_id}</code></div>
        <button className={styles.textButton} type="button" onClick={onNewEvaluation}>New evaluation <span aria-hidden="true">＋</span></button>
      </div>
      <div className={styles.dossierLayout}>
        <aside className={styles.dossierRail}>
          <div className={styles.stickySummary}>
            <span className={styles.sectionEyebrow}>CANDIDATE SNAPSHOT</span>
            <strong>{result.intake.manifest.display_name}</strong>
            <span>{result.dossier.role.replaceAll('_', ' ')}</span>
            <dl>
              <div><dt>RCI</dt><dd>{result.dossier.rci == null ? 'UNKNOWN' : result.dossier.rci.toFixed(1)}</dd></div>
              <div><dt>Coverage</dt><dd>{(result.dossier.coverage * 100).toFixed(1)}%</dd></div>
              <div><dt>Observed</dt><dd>{observedCount} / {estimates.length}</dd></div>
              <div><dt>Conflicts</dt><dd>{conflicts}</dd></div>
            </dl>
          </div>
          <nav aria-label="Dossier sections" aria-describedby="dossier-section-nav-description" className={styles.sectionNav}>
            {SECTIONS.map((section, index) => <a key={section.id} href={`#${section.id}`}>
              <span className={styles.navIndex}>{String(index + 1).padStart(2, '0')}</span>
              <span><strong>{section.label}</strong><small>{section.detail}</small></span>
            </a>)}
          </nav>
          <p id="dossier-section-nav-description" className={styles.srOnly}>Use these links to navigate to dossier sections.</p>
          <p className={styles.sectionNavHint}>
            Swipe or scroll to see all dossier sections <span aria-hidden="true">→</span>
          </p>
        </aside>

        <div className={styles.dossierContent}>
          <ExecutiveSummary result={result} />
          <CapabilityMatrix result={result} selected={selectedCapability} onSelect={setSelectedCapability} onInspectEvidence={inspectCapabilityEvidence} />
          <EvidenceLedger result={result} sourceFilter={sourceFilter} onSourceFilterChange={setSourceFilter} capabilityFilter={capabilityFilter} onCapabilityFilterChange={setCapabilityFilter} selectedEvidenceId={selectedEvidenceId} onSelectEvidence={setSelectedEvidenceId} />
          <ClaimsSection result={result} />
          <DetailedAnalysis analysis={result.analysis} />
          <SourceCoverage result={result} onInspectEvidence={inspectSource} />
          <ConflictAndUnknownReview result={result} onSelectCapability={selectCapability} onSelectEvidence={selectEvidence} />
          <InterviewPlan result={result} onSelectEvidence={selectEvidence} />
          <EvidenceGraphSection graph={result.graph} onSelectCapability={selectCapability} onSelectEvidence={selectEvidence} />
          <AuditSection result={result} />
        </div>
      </div>
    </section>
  );
}
