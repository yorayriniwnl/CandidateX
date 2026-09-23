'use client';

import { useEffect, useMemo, useState } from 'react';
import type { CapabilityKey } from '../../types/cci';
import type { LiveResult } from '../../lib/live-analysis';
import { publicUrl } from '../../lib/live-analysis';
import { EvidenceStatus } from './EvidenceStatus';
import { capabilityName, dateTime, percent, score, titleWords } from './format';
import styles from './evidence-os.module.css';

const PAGE_SIZE = 40;
type SortField = 'label' | 'capability' | 'source' | 'support' | 'confidence' | 'date' | 'revision';
type LiveEvidence = LiveResult['dossier']['evidence_records'][number];

function evidenceText(evidence: LiveEvidence) {
  return [evidence.evidence_id, evidence.target_capability, capabilityName(evidence.target_capability), evidence.source_family,
    evidence.provenance.raw_support_text, evidence.provenance.artifact_path, evidence.source_locator,
    evidence.immutable_revision, evidence.fingerprint].filter(Boolean).join(' ').toLowerCase();
}

function repositoryKey(locator: string): string {
  try {
    const url = new URL(locator);
    const parts = url.pathname.split('/').filter(Boolean);
    if (['github.com', 'www.github.com'].includes(url.hostname.toLowerCase()) && parts.length >= 2) {
      return `https://github.com/${parts[0]}/${parts[1].replace(/\.git$/i, '')}`.toLowerCase();
    }
    return `${url.origin}${url.pathname}`.replace(/\/+$/, '').toLowerCase();
  } catch {
    return locator.replace(/\/+$/, '').toLowerCase();
  }
}

export function EvidenceLedger({ result, sourceFilter, onSourceFilterChange, capabilityFilter, onCapabilityFilterChange, selectedEvidenceId, onSelectEvidence }: {
  result: LiveResult;
  sourceFilter: string;
  onSourceFilterChange: (source: string) => void;
  capabilityFilter: CapabilityKey | 'all';
  onCapabilityFilterChange: (capability: CapabilityKey | 'all') => void;
  selectedEvidenceId: string | null;
  onSelectEvidence: (evidenceId: string) => void;
}) {
  const [query, setQuery] = useState('');
  const [directionFilter, setDirectionFilter] = useState('all');
  const [sourceFamilyFilter, setSourceFamilyFilter] = useState('all');
  const [repositoryFilter, setRepositoryFilter] = useState('all');
  const [confidenceMin, setConfidenceMin] = useState('');
  const [confidenceMax, setConfidenceMax] = useState('');
  const [observedAfter, setObservedAfter] = useState('');
  const [observedBefore, setObservedBefore] = useState('');
  const [sortField, setSortField] = useState<SortField>('capability');
  const [descending, setDescending] = useState(false);
  const [page, setPage] = useState(0);
  const records = result.dossier.evidence_records;
  const sources = useMemo(() => [...new Set(records.map(record => record.source_locator))].sort(), [records]);
  const capabilities = useMemo(() => [...new Set(records.map(record => record.target_capability))], [records]);
  const sourceFamilies = useMemo(() => [...new Set(records.map(record => record.source_family))].sort(), [records]);
  const repositories = useMemo(() => [...new Set(result.sources
    .filter(source => source.repository_review || source.kind === 'github_repository' || source.files_inspected !== undefined || source.inventory !== undefined)
    .map(source => repositoryKey(source.url)))].sort(), [result.sources]);

  useEffect(() => { setPage(0); }, [query, capabilityFilter, sourceFilter, directionFilter, sourceFamilyFilter, repositoryFilter, confidenceMin, confidenceMax, observedAfter, observedBefore]);

  const filtered = useMemo(() => {
    const searched = records.filter(record => {
      if (query.trim() && !evidenceText(record).includes(query.trim().toLowerCase())) return false;
      if (capabilityFilter !== 'all' && record.target_capability !== capabilityFilter) return false;
      if (sourceFilter !== 'all' && record.source_locator !== sourceFilter) return false;
      if (sourceFamilyFilter !== 'all' && record.source_family !== sourceFamilyFilter) return false;
      if (repositoryFilter !== 'all' && repositoryKey(record.source_locator) !== repositoryFilter) return false;
      if (directionFilter === 'positive' && !record.is_positive_support) return false;
      if (directionFilter === 'negative' && record.is_positive_support) return false;
      const min = confidenceMin.trim() ? Number(confidenceMin) : null;
      const max = confidenceMax.trim() ? Number(confidenceMax) : null;
      if (min !== null && Number.isFinite(min) && record.confidence < min) return false;
      if (max !== null && Number.isFinite(max) && record.confidence > max) return false;
      if (observedAfter || observedBefore) {
        const observedAt = record.provenance.observed_at ? Date.parse(record.provenance.observed_at) : Number.NaN;
        if (!Number.isFinite(observedAt)) return false;
        if (observedAfter && observedAt < Date.parse(`${observedAfter}T00:00:00.000Z`)) return false;
        if (observedBefore && observedAt > Date.parse(`${observedBefore}T23:59:59.999Z`)) return false;
      }
      return true;
    });
    return searched.sort((left, right) => {
      const leftValue = sortValue(left, sortField);
      const rightValue = sortValue(right, sortField);
      const comparison = typeof leftValue === 'number' && typeof rightValue === 'number'
        ? leftValue - rightValue : String(leftValue).localeCompare(String(rightValue));
      return descending ? -comparison : comparison;
    });
  }, [records, query, capabilityFilter, sourceFilter, directionFilter, sourceFamilyFilter, repositoryFilter, confidenceMin, confidenceMax, observedAfter, observedBefore, sortField, descending]);

  const pageCount = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const visible = filtered.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE);
  const selected = records.find(record => record.evidence_id === selectedEvidenceId) ?? null;

  function sortValue(record: LiveEvidence, field: SortField): string | number {
    if (field === 'label') return record.provenance.raw_support_text || record.provenance.artifact_path || record.evidence_id;
    if (field === 'capability') return record.target_capability;
    if (field === 'source') return record.source_locator;
    if (field === 'support') return record.support_score * (record.is_positive_support ? 1 : -1);
    if (field === 'confidence') return record.confidence;
    if (field === 'date') return record.provenance.observed_at ?? '';
    return record.immutable_revision;
  }

  function requestSort(field: SortField) {
    if (field === sortField) setDescending(value => !value);
    else { setSortField(field); setDescending(false); }
    setPage(0);
  }

  function sortButton(label: string, field: SortField) {
    return <button type="button" aria-label={`Sort by ${label}`} className={styles.sortButton} onClick={() => requestSort(field)}>{label}{sortField === field ? <span aria-hidden="true">{descending ? ' ↓' : ' ↑'}</span> : null}</button>;
  }

  function columnSort(field: SortField): 'ascending' | 'descending' | 'none' {
    if (sortField !== field) return 'none';
    return descending ? 'descending' : 'ascending';
  }

  function clearFilters() {
    setQuery('');
    onCapabilityFilterChange('all');
    onSourceFilterChange('all');
    setDirectionFilter('all');
    setSourceFamilyFilter('all');
    setRepositoryFilter('all');
    setConfidenceMin('');
    setConfidenceMax('');
    setObservedAfter('');
    setObservedBefore('');
    setPage(0);
  }

  return (
    <section id="evidence" className={styles.contentSection} aria-labelledby="evidence-title">
      <div className={styles.sectionHeader}>
        <div>
          <p className={styles.sectionEyebrow}>02 / STATIC OBSERVATIONS</p>
          <h2 id="evidence-title">Evidence ledger</h2>
          <p>Each record links an observation to its capability and source locator. Evidence existence is not mastery.</p>
        </div>
        <span className={styles.sectionCount}>{records.length} records</span>
      </div>

      <div className={styles.filterBar}>
        <label className={styles.searchField}>
          <span>Search evidence</span>
          <input aria-label="Search evidence" type="search" placeholder="Observation, path, revision…" value={query} onChange={event => { setQuery(event.target.value); setPage(0); }} />
        </label>
        <label className={styles.compactField}>
          <span>Capability</span>
          <select aria-label="Filter by capability" value={capabilityFilter} onChange={event => onCapabilityFilterChange(event.target.value as CapabilityKey | 'all')}>
            <option value="all">All capabilities</option>
            {capabilities.map(capability => <option key={capability} value={capability}>{capabilityName(capability)}</option>)}
          </select>
        </label>
        <label className={styles.compactField}>
          <span>Source</span>
          <select aria-label="Filter by source family" value={sourceFamilyFilter} onChange={event => setSourceFamilyFilter(event.target.value)}>
            <option value="all">All source families</option>
            {sourceFamilies.map(source => <option key={source} value={source}>{titleWords(source)}</option>)}
          </select>
        </label>
        <label className={styles.compactField}>
          <span>Source locator</span>
          <select aria-label="Filter by source" value={sourceFilter} onChange={event => { onSourceFilterChange(event.target.value); setPage(0); }}>
            <option value="all">All sources</option>
            {sources.map(source => <option key={source} value={source}>{source}</option>)}
          </select>
        </label>
        <label className={styles.compactField}>
          <span>Repository</span>
          <select aria-label="Repository" value={repositoryFilter} onChange={event => setRepositoryFilter(event.target.value)}>
            <option value="all">All repositories</option>
            {repositories.map(repository => <option key={repository} value={repository}>{repository}</option>)}
          </select>
        </label>
        <label className={styles.compactField}>
          <span>Support direction</span>
          <select aria-label="Support direction" value={directionFilter} onChange={event => setDirectionFilter(event.target.value)}>
            <option value="all">All directions</option><option value="positive">Positive</option><option value="negative">Negative</option>
          </select>
        </label>
        <label className={styles.compactField}>
          <span>Confidence minimum</span>
          <input aria-label="Confidence minimum (0 to 1)" type="number" min="0" max="1" step="0.01" value={confidenceMin} onChange={event => setConfidenceMin(event.target.value)} />
        </label>
        <label className={styles.compactField}>
          <span>Confidence maximum</span>
          <input aria-label="Confidence maximum (0 to 1)" type="number" min="0" max="1" step="0.01" value={confidenceMax} onChange={event => setConfidenceMax(event.target.value)} />
        </label>
        <label className={styles.compactField}>
          <span>Observed after</span>
          <input aria-label="Observed after" type="date" value={observedAfter} onChange={event => setObservedAfter(event.target.value)} />
        </label>
        <label className={styles.compactField}>
          <span>Observed before</span>
          <input aria-label="Observed before" type="date" value={observedBefore} onChange={event => setObservedBefore(event.target.value)} />
        </label>
      </div>

      <p className={styles.tableSummary} aria-live="polite">Showing {filtered.length === 0 ? 0 : page * PAGE_SIZE + 1}–{Math.min((page + 1) * PAGE_SIZE, filtered.length)} of {filtered.length} matching records.</p>
      {records.length === 0 ? <div className={styles.emptyState}><EvidenceStatus status="unknown" label="No evidence records returned" /><p>The live response contains no static observations. Capability estimates remain unknown where the dossier says they are unknown.</p></div>
        : filtered.length === 0 ? <div className={styles.emptyState}><p>No evidence records match these filters.</p><button className={styles.textButton} type="button" onClick={clearFilters}>Clear filters</button></div>
        : <div className={styles.tableViewport} tabIndex={0} aria-label="Evidence ledger table; use arrow keys or horizontal scroll to inspect columns">
          <table className={styles.dataTable}>
            <caption className={styles.srOnly}>Evidence records with capability, provenance, support, ownership and status</caption>
            <thead><tr>
              <th scope="col" aria-sort={columnSort('label')}>{sortButton('Evidence', 'label')}</th>
              <th scope="col" aria-sort={columnSort('capability')}>{sortButton('Capability', 'capability')}</th>
              <th scope="col" aria-sort={columnSort('source')}>{sortButton('Source', 'source')}</th>
              <th scope="col" aria-sort={columnSort('support')}>{sortButton('Strength', 'support')}</th>
              <th scope="col" aria-sort={columnSort('confidence')}>{sortButton('Confidence', 'confidence')}</th>
              <th scope="col">Ownership</th>
              <th scope="col" aria-sort={columnSort('date')}>{sortButton('Observed', 'date')}</th>
              <th scope="col" aria-sort={columnSort('revision')}>{sortButton('Revision', 'revision')}</th>
              <th scope="col">Status</th>
            </tr></thead>
            <tbody>{visible.map(record => {
              const owns = record.confidence_factors.ownership_score;
              const verification = record.provenance.verification_status || (record.is_positive_support ? 'supporting observation' : 'contradicting observation');
              return <tr key={record.evidence_id} className={selectedEvidenceId === record.evidence_id ? styles.selectedRow : ''}>
                <td><button className={styles.evidenceRowSelect} type="button" aria-pressed={selectedEvidenceId === record.evidence_id} onClick={() => onSelectEvidence(record.evidence_id)}>
                  <span>{record.provenance.raw_support_text || record.provenance.artifact_path || 'Static observation'}</span><code>{record.evidence_id}</code>
                </button></td>
                <td>{capabilityName(record.target_capability)}</td>
                <td><span className={styles.sourceKind}>{titleWords(record.source_family)}</span><small className={styles.tableSubtext}>{record.source_locator}</small></td>
                <td className={styles.numericCell}><EvidenceStatus status={record.is_positive_support ? 'observed' : 'conflict'} label={`${record.is_positive_support ? '+' : '−'} ${record.support_score.toFixed(1)}`} /></td>
                <td className={styles.numericCell}>{percent(record.confidence)}</td>
                <td className={styles.numericCell}>{owns === undefined ? 'Not returned' : `${percent(owns)} heuristic`}<small>not authorship proof</small></td>
                <td className={styles.numericCell}>{dateTime(record.provenance.observed_at)}</td>
                <td><code className={styles.idText}>{record.immutable_revision}</code></td>
                <td><EvidenceStatus status={verification} label={verification} /></td>
              </tr>;
            })}</tbody>
          </table>
        </div>}

      {filtered.length > PAGE_SIZE && <div className={styles.pagination}>
        <button className={styles.secondaryButton} type="button" disabled={page === 0} onClick={() => setPage(value => Math.max(0, value - 1))}>Previous</button>
        <span>Page {page + 1} of {pageCount}</span>
        <button className={styles.secondaryButton} type="button" disabled={page + 1 >= pageCount} onClick={() => setPage(value => Math.min(pageCount - 1, value + 1))}>Next</button>
      </div>}
      {selected && <EvidenceRecordDetail record={selected} />}
    </section>
  );
}

function EvidenceRecordDetail({ record }: { record: LiveEvidence }) {
  const verification = record.provenance.verification_status || (record.is_positive_support ? 'supporting observation' : 'contradicting observation');
  const artifactUrl = publicUrl(record.provenance.artifact_url);
  return (
    <aside className={styles.evidenceDetail} aria-label="Selected evidence provenance">
      <div className={styles.inspectorHeader}>
        <div><p className={styles.sectionEyebrow}>EVIDENCE RECORD / PROVENANCE</p><h3>{record.provenance.artifact_path || record.source_locator}</h3></div>
        <EvidenceStatus status={verification} label={verification} />
      </div>
      <p className={styles.rawObservation}>{record.provenance.raw_support_text || 'No observation text was returned for this record.'}</p>
      {artifactUrl && <a className={styles.inlineLink} href={artifactUrl} target="_blank" rel="noreferrer">Open inspected artifact <span aria-hidden="true">↗</span></a>}
      <dl className={styles.inspectorFacts}>
        <div><dt>Capability</dt><dd>{capabilityName(record.target_capability)}</dd></div>
        <div><dt>Source family</dt><dd>{titleWords(record.source_family)}</dd></div>
        <div><dt>Source locator</dt><dd>{record.source_locator}</dd></div>
        <div><dt>Immutable revision</dt><dd><code>{record.immutable_revision}</code></dd></div>
        <div><dt>Support score</dt><dd>{score(record.support_score)}</dd></div>
        <div><dt>Evidence confidence</dt><dd>{percent(record.confidence)}</dd></div>
        <div><dt>Artifact path</dt><dd>{record.provenance.artifact_path || 'Not returned'}</dd></div>
        <div><dt>Artifact location</dt><dd>{record.provenance.symbol_or_line || 'Not returned'}</dd></div>
        <div><dt>Artifact fingerprint</dt><dd><code>{record.fingerprint}</code></dd></div>
        <div><dt>Artifact SHA-256</dt><dd><code>{record.provenance.artifact_sha256 || 'Not returned'}</code></dd></div>
        <div><dt>Extractor version</dt><dd>{record.provenance.extractor_version || 'Not returned'}</dd></div>
        <div><dt>Observed at</dt><dd>{dateTime(record.provenance.observed_at)}</dd></div>
      </dl>
      <details className={styles.diagnosticDetails}><summary>Confidence factors and ownership basis</summary>
        <p>Ownership is a repository-level heuristic. It does not prove authorship of each inspected line.</p>
        <dl>{Object.entries(record.confidence_factors).map(([name, value]) => <div key={name}><dt>{titleWords(name)}</dt><dd>{value.toFixed(3)}</dd></div>)}</dl>
      </details>
    </aside>
  );
}
