import { publicUrl, type SourceReceipt, type ResumeIntake } from '../../lib/live-analysis';
import { label } from '../../lib/evidence';
import styles from './shared.module.css';
import live from './page.module.css';

export function ResumeSections({ intake }: { intake: ResumeIntake }) {
  return <div className={live.reviewGrid}>
    {Object.entries(intake.resume_review?.sections ?? {}).filter(([key]) => !['header', 'skills', 'other'].includes(key)).map(([key, lines]) =>
      <details className={styles.evidence} key={key}><summary>{label(key)} · {lines.length} extracted lines</summary>
        {lines.map((line, i) => <p className={live.claim} key={i}>{line}</p>)}
        <p className={styles.muted}>Résumé declaration · not independently verified</p>
      </details>)}
    {intake.resume_review?.observations.map(text => <p className={styles.warning} key={text}>{text}</p>)}
  </div>;
}

export function SourceDetails({ source }: { source: SourceReceipt }) {
  const review = source.repository_review;
  return <>
    {source.profile && <details className={styles.evidence} open><summary>GitHub profile</summary>
      <dl className={live.metadata}>{Object.entries(source.profile).map(([key, value]) => value != null && value !== '' &&
        <div key={key}><dt>{label(key)}</dt><dd>{String(value)}</dd></div>)}</dl>
      <p className={styles.muted}>Profile text is self-published. Follower and repository counts are context, not skill scores.</p>
      {source.profile_error && <p className={styles.warning}>{source.profile_error}</p>}
    </details>}
    {source.inventory && <details className={styles.evidence}><summary>Public repository inventory · {source.inventory.length} listed{source.inventory_truncated ? ' · inventory limit reached' : ''}</summary>
      <div className={styles.tableWrap}><table className={styles.table}><thead><tr><th>Repository</th><th>Language</th><th>Activity</th><th>Inspection</th></tr></thead>
        <tbody>{source.inventory.map(repo => <tr key={repo.url}><td><a href={publicUrl(repo.url)} target="_blank" rel="noreferrer">{repo.name}</a>
          <p className={styles.muted}>{repo.description}</p><span className={styles.tag}>{repo.fork ? 'Fork' : 'Original'}{repo.archived ? ' · Archived' : ''}</span></td>
          <td>{repo.language || 'Unspecified'}</td><td>{repo.pushed_at?.slice(0, 10) || 'Unknown'}<br />{repo.stars} stars</td><td>{label(repo.inspection_status)}</td></tr>)}</tbody></table></div>
      <p className={styles.muted}>Inventory-only repositories have metadata, but their source files were not inspected. Paste their URLs into the selection for another run.</p>
    </details>}
    {review && <details className={styles.evidence}><summary>Repository engineering review</summary>
      {source.acquisition_method === 'bounded_git_blobs' && <p className={styles.warning}>Large repository: up to 12 selected files fetched from immutable Git blobs. Review the omitted-file count before drawing conclusions.</p>}
      <p>{review.description || 'No repository description supplied.'}</p>
      <div className={styles.factors}><span>{review.is_fork ? 'Fork' : 'Original repository'}</span><span>{review.license || 'No license reported'}</span>
        <span>{review.stars} stars</span><span>{review.forks} forks</span><span>{review.open_issues} open issues / PRs</span>
        {review.topics.map(topic => <span key={topic}>{topic}</span>)}</div>
      <h3>Languages in inspected files</h3><div className={styles.factors}>{Object.entries(review.languages_by_inspected_file).map(([language, count]) => <span key={language}>{language}: {count} files</span>)}</div>
      <h3>Engineering signals</h3>{review.engineering_signals.map(signal => <div key={signal.name} className={live.signal}><strong>{label(signal.name)}</strong><span>{label(signal.status)}</span>
        {signal.paths.map(path => <code className={live.sourceUrl} key={path}>{path}</code>)}</div>)}
      <details className={styles.evidence}><summary>Dependency declarations · {review.dependencies.length}</summary>{review.dependencies.map((dependency, i) =>
        <p className={live.sourceUrl} key={i}><strong>{dependency.name}</strong> {dependency.version} · {dependency.path}</p>)}</details>
      {review.readme_excerpt && <details className={styles.evidence}><summary>README excerpt · repository-authored text</summary><pre className={live.extracted}>{review.readme_excerpt}</pre></details>}
      {review.limitations.map(text => <p key={text} className={styles.muted}>{text}</p>)}
    </details>}
    {source.title && <h3>{source.title}</h3>}
    {source.description && <p>{source.description}</p>}
    {source.final_url && source.final_url !== source.url && <p className={live.sourceUrl}>Final destination: <a href={publicUrl(source.final_url)} target="_blank" rel="noreferrer">{source.final_url}</a></p>}
    {source.excerpt && <details className={styles.evidence}><summary>Inspect retrieved page text · {label(source.verification || 'not_verified')}</summary>
      <pre className={live.extracted}>{source.excerpt}</pre><p className={styles.hash}>Content SHA-256: {source.content_sha256}</p>
      <p className={styles.muted}>Fetched {source.fetched_at} · HTTP {source.http_status}. This text is evidence of what the page states.</p>
    </details>}
  </>;
}

