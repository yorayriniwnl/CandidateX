'use client';

import type { SourceReceipt, TechnologyEvidence } from '../../lib/live-analysis';
import type { LiveResult } from '../../lib/live-analysis';
import { publicUrl } from '../../lib/live-analysis';
import { EvidenceStatus } from './EvidenceStatus';
import { dateTime, humanStatus, percent, titleWords } from './format';
import styles from './evidence-os.module.css';
import report from './result.module.css';

export function SourceCoverage({ result, onInspectEvidence }: {
  result: LiveResult;
  onInspectEvidence: (source: string) => void;
}) {
  const observed = result.sources.filter(source => source.status === 'observed').length;
  const repositories = result.sources.filter(source => source.repository_review || (source.files_inspected ?? 0) > 0).length;
  return (
    <section id="sources" className={styles.contentSection} aria-labelledby="sources-title">
      <div className={styles.sectionHeader}>
        <div>
          <p className={styles.sectionEyebrow}>04 / SOURCE INTELLIGENCE</p>
          <h2 id="sources-title">Repository intelligence</h2>
          <p>Engineering context from inspected files, with acquisition gaps preserved.</p>
        </div>
        <span className={styles.sectionCount}>{observed} observed / {result.sources.length} receipts · {repositories} {repositories === 1 ? 'repository' : 'repositories'} inspected</span>
      </div>
      {result.sources.length === 0 ? <div className={styles.emptyState}>
        <EvidenceStatus status="unknown" label="No source receipts returned" />
        <p>No public sources were selected for this run. Resume declarations remain visible as declarations.</p>
      </div> : <div className={styles.receiptList}>
        {result.sources.map((source, index) => <SourceReceiptCard key={`${source.url}-${index}`} source={source} onInspectEvidence={onInspectEvidence} />)}
      </div>}
    </section>
  );
}

function SourceReceiptCard({ source, onInspectEvidence }: { source: SourceReceipt; onInspectEvidence: (source: string) => void }) {
  const url = publicUrl(source.final_url ?? source.url);
  const kind = source.kind ? titleWords(source.kind) : source.repository_review ? 'GitHub repository' : 'Public source';
  const repo = source.repository_review;
  const languages = repo ? Object.entries(repo.languages_by_inspected_file).sort((a, b) => b[1] - a[1]) : [];
  const omitted = source.files_omitted;

  return (
    <article className={styles.receipt}>
      <div className={styles.receiptSummary}>
        <div className={styles.receiptIdentity}>
          <span className={styles.sourceKind}>{kind}</span>
          <h3>{source.url.replace(/^https?:\/\/(www\.)?github.com\//, '')}</h3>
          <p>{source.detail}</p>
        </div>
        <div className={styles.receiptStatus}><EvidenceStatus status={source.status} label={humanStatus(source.status)} /></div>
      </div>
      <dl className={report.repoSummary}>
        <div><dt>Primary language</dt><dd>{repo?.primary_language || languages[0]?.[0] || 'Unavailable'}</dd></div>
        <div><dt>Ownership estimate</dt><dd>{source.ownership_score == null ? 'Unknown' : percent(source.ownership_score, 0)}</dd></div>
        <div><dt>Evidence</dt><dd>{source.evidence_count ?? 'Unavailable'}</dd></div>
        <div><dt>Files inspected</dt><dd>{source.files_inspected ?? 'Unavailable'}</dd></div>
        <div><dt>Last activity</dt><dd>{repo?.pushed_at ? dateTime(repo.pushed_at) : 'Unavailable'}</dd></div>
      </dl>
      <p className={report.footnote}>Ownership is a recent-commit heuristic, not proof of authorship.</p>
      {repo && <RepositoryReview review={repo} source={source} />}
      <details className={styles.diagnosticDetails}><summary>Acquisition receipt & source metadata</summary>
      <dl className={styles.receiptFacts}>
        <div><dt>Fetched</dt><dd>{dateTime(source.fetched_at)}</dd></div>
        <div><dt>Revision</dt><dd><code>{source.commit_sha ?? 'Not returned'}</code></dd></div>
        <div><dt>Files inspected</dt><dd>{source.files_inspected ?? 'Not returned'}</dd></div>
        <div><dt>Files omitted</dt><dd>{omitted ?? 'Not returned'}</dd></div>
        <div><dt>Observations</dt><dd>{source.evidence_count ?? 'Not returned'}</dd></div>
        <div><dt>Ownership heuristic</dt><dd>{source.ownership_score == null ? 'Not returned' : percent(source.ownership_score)}</dd></div>
        <div><dt>Acquisition method</dt><dd>{source.acquisition_method ?? 'Not returned'}</dd></div>
        <div><dt>Content fingerprint</dt><dd><code>{source.content_sha256 ?? 'Not returned'}</code></dd></div>
      </dl>
      {source.profile_error && <p className={styles.inlineWarning}>Profile metadata: {source.profile_error}</p>}
      {source.profile && Object.keys(source.profile).length > 0 && <details className={styles.diagnosticDetails}>
        <summary>Profile metadata returned</summary>
        <dl>{Object.entries(source.profile).map(([key, value]) => <div key={key}><dt>{titleWords(key)}</dt><dd>{value ?? 'Not returned'}</dd></div>)}</dl>
      </details>}
      {source.inventory && source.inventory.length > 0 && <details className={styles.diagnosticDetails}>
        <summary>Repository inventory · {source.inventory.length} returned</summary>
        {source.inventory_truncated && <p>Inventory was truncated by the acquisition limits.</p>}
        <div className={styles.inventoryList}>{source.inventory.map(repoItem => <div key={repoItem.url}>
          <strong>{repoItem.name}</strong><span>{repoItem.description || 'No description returned'}</span>
          <EvidenceStatus status={repoItem.inspection_status} label={humanStatus(repoItem.inspection_status)} />
        </div>)}</div>
      </details>}

      {(source.title || source.excerpt) && <details className={styles.diagnosticDetails}>
        <summary>Public page text · not independently verified</summary>
        <p>{source.title || 'Untitled page'}</p>
        {source.description && <p>{source.description}</p>}
        {source.excerpt && <blockquote>{source.excerpt}</blockquote>}
        {source.verification && <p>Acquisition label: {humanStatus(source.verification)}. Public page text does not authenticate a credential or employment claim.</p>}
      </details>}
      {source.files && source.files.length > 0 && <details className={styles.diagnosticDetails} open>
        <summary>Fetched files & verified artifacts ({source.files.length} {source.files.length === 1 ? 'file' : 'files'})</summary>
        <div className={styles.inventoryList}>
          {source.files.map((file, fi) => (
            <div key={`${file.name}-${fi}`}>
              <strong>{file.name}</strong>
              <span>{file.type ? titleWords(file.type) : 'File'}{file.size ? ` · ${(file.size / 1024).toFixed(1)} KB` : ''}</span>
            </div>
          ))}
        </div>
      </details>}
      {source.expanded_repositories && source.expanded_repositories.length > 0 && <details className={styles.diagnosticDetails}>
        <summary>Expanded repository URLs · {source.expanded_repositories.length}</summary>
        <ul>{source.expanded_repositories.map(repository => <li key={repository}><code>{repository}</code></li>)}</ul>
      </details>}
      </details>
      <div className={styles.receiptActions}>
        {url ? <a className={styles.inlineLink} href={url} target="_blank" rel="noreferrer">Open supplied source <span aria-hidden="true">↗</span></a> : <span className={styles.muted}>Source URL is not a safe HTTP(S) link.</span>}
        <button className={styles.textButton} type="button" onClick={() => onInspectEvidence(source.url)}>Inspect evidence from this source <span aria-hidden="true">→</span></button>
      </div>
    </article>
  );
}

function RepositoryReview({ review, source }: { review: NonNullable<SourceReceipt['repository_review']>; source: SourceReceipt }) {
  const technologies: TechnologyEvidence[] = review.technologies;
  const languages = Object.entries(review.languages_by_inspected_file).sort((a, b) => b[1] - a[1]);
  return (
    <details className={styles.repositoryReview}>
      <summary>Engineering fingerprint & technical details</summary>
      <p className={styles.repositoryScope}>Signals below describe inspected files and returned metadata. A configuration or dependency does not prove candidate mastery or ownership.</p>
      {review.engineering_signals.length > 0 && <div className={styles.repoBlock}>
        <h4>Engineering fingerprint</h4><ul className={report.fingerprint}>{review.engineering_signals.map((signal, index) => <li key={`${signal.name}-${index}`}>
          <EvidenceStatus status={signal.status} label={`${titleWords(signal.name)} · ${signal.status === 'not_observed_in_scan' ? 'Not observed in bounded scan' : humanStatus(signal.status)}`} />
          <span>{signal.paths.length > 0 ? signal.paths.slice(0, 5).join(' · ') : 'No path returned'}</span>
        </li>)}</ul>
      </div>}
      <div className={report.unavailableGrid}><div><h4>Architecture</h4><p>Module topology, dependencies and cycles are unavailable in this response.</p></div><div><h4>Review targets</h4><p>No structured review targets were supplied. This is not a security clearance.</p><small>Review target, not confirmed vulnerability.</small></div></div>
      <div className={styles.repoMetaStrip}>
        <span>{review.stars} stars returned</span><span>{review.forks} forks returned</span><span>{review.license || 'License not returned'}</span>
        <span>Open issues: {review.open_issues}</span><span>Last push: {dateTime(review.pushed_at ?? undefined)}</span>
        <span>{review.is_fork ? 'Fork' : 'Not marked as fork'}</span><span>{review.archived ? 'Archived' : 'Not archived'}</span>
      </div>
      {review.description && <p>{review.description}</p>}
      {review.topics.length > 0 && <div className={styles.tagRow}>{review.topics.map(topic => <span key={topic}>{topic}</span>)}</div>}
      {languages.length > 0 && <div className={styles.repoBlock}>
        <h4>Languages by inspected file</h4><div className={styles.tagRow}>{languages.map(([name, count]) => <span key={name}>{name} <b>{count}</b></span>)}</div>
      </div>}
      <div className={styles.repoBlock}>
        <h4>File categories by inspected file</h4>
        {Object.keys(review.file_categories).length > 0
          ? <div className={styles.tagRow}>{Object.entries(review.file_categories).sort((a, b) => b[1] - a[1]).map(([category, count]) => <span key={category}>{titleWords(category)} <b>{count}</b></span>)}</div>
          : <p>No categories returned.</p>}
      </div>
      {technologies.length > 0 && <div className={styles.repoBlock}>
        <details className={styles.diagnosticDetails}><summary>Technology declarations observed</summary>
        <ul className={styles.technologyList}>{technologies.map((technology, index) => <li key={`${technology.name}-${technology.path}-${index}`}>
          <strong>{technology.name}</strong><span>{technology.basis}</span><code>{technology.path}</code>
          {technology.attribution_observed !== undefined && <span>{technology.attribution_observed ? 'Repository-level attribution signal returned' : 'Attribution not established'}</span>}
        </li>)}</ul></details>
      </div>}
      {review.dependencies.length > 0 && <div className={styles.repoBlock}>
        <details className={styles.diagnosticDetails}><summary>Dependency declarations</summary><ul className={styles.dependencyList}>{review.dependencies.slice(0, 30).map((dependency, index) => <li key={`${dependency.path}-${dependency.name}-${index}`}><code>{dependency.name}{dependency.version ? ` ${dependency.version}` : ''}</code><span>{dependency.path}</span></li>)}</ul>
        {review.dependencies.length > 30 && <p>Showing 30 of {review.dependencies.length} dependency declarations.</p>}</details>
      </div>}
      {review.readme_excerpt && <details className={styles.readmeExcerpt}><summary>README excerpt</summary><blockquote>{review.readme_excerpt}</blockquote></details>}
      {review.limitations.length > 0 && <div className={styles.limitationList}><h4>Repository inspection limits</h4><ul>{review.limitations.map((limitation, index) => <li key={index}>{limitation}</li>)}</ul></div>}
      <p className={styles.muted}>Receipt: {source.files_inspected ?? 'Not returned'} files inspected · {source.files_omitted ?? 'Not returned'} omitted.</p>
    </details>
  );
}
