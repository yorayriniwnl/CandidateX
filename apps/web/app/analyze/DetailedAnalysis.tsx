import { useState } from 'react';
import { publicUrl, type ComprehensiveAnalysis, type SourceReceipt, type ResumeIntake } from '../../lib/live-analysis';
import { label } from '../../lib/research-demo';
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
    {source.discovered_links && source.discovered_links.length > 0 && <details className={styles.evidence}><summary>Links discovered on this page · {source.discovered_links.length}</summary>
      {source.discovered_links.map(link => <p className={live.sourceUrl} key={link.url}><a href={publicUrl(link.url)} target="_blank" rel="noreferrer">{link.url}</a> · {label(link.kind)}</p>)}
      <p className={styles.muted}>Discovery does not imply that a linked page was fetched or verified in this run.</p>
    </details>}
    {source.excerpt && <details className={styles.evidence}><summary>Inspect retrieved page text · {label(source.verification || 'not_verified')}</summary>
      <pre className={live.extracted}>{source.excerpt}</pre><p className={styles.hash}>Content SHA-256: {source.content_sha256}</p>
      <p className={styles.muted}>Fetched {source.fetched_at} · HTTP {source.http_status}. This text is evidence of what the page states.</p>
    </details>}
  </>;
}

export function DetailedAnalysis({ analysis }: { analysis: ComprehensiveAnalysis }) {
  const [query, setQuery] = useState('');
  const [gapsOnly, setGapsOnly] = useState(false);
  const skills = analysis.skills.filter(skill => skill.skill.toLowerCase().includes(query.toLowerCase()) && (!gapsOnly || !skill.evidence.length));
  const claims = analysis.claims ?? [];
  const academicRecords = analysis.academic_records ?? [];
  return <>
    {claims.length > 0 && <section className={styles.panel} aria-label="Claim ledger"><div className={styles.eyebrow}>Claim ledger</div><h2>What the resume actually claims</h2>
      <p className={styles.muted}>Every declaration keeps a stable claim ID and remains self-reported until separate evidence supports it. Quantified claims are highlighted for follow-up.</p>
      <div className={styles.tableWrap}><table className={styles.table}><thead><tr><th>Claim</th><th>Category</th><th>Source</th><th>Status</th></tr></thead><tbody>{claims.map(claim => <tr key={claim.claim_id}>
        <td><strong>{claim.claim}</strong>{claim.is_quantified && <><br /><span className={styles.tag}>Quantified · verify</span></>}</td><td>{label(claim.category)}</td><td>{label(claim.section)}</td><td>{label(claim.status)}</td>
      </tr>)}</tbody></table></div>
    </section>}
    {academicRecords.length > 0 && <section className={styles.panel} aria-label="Academic record"><div className={styles.eyebrow}>Academic record</div><h2>Education claims, separated from verification</h2>
      <p className={styles.muted}>Structured fields below are parsed from the resume. They are not institution or transcript verification.</p>
      {academicRecords.map(record => <article className={styles.evidence} key={record.record_id}><div className={live.sourceHead}><h3>{record.degree_text || 'Education record'}</h3><span className={styles.tag}>{label(record.status)}</span></div>
        <p className={live.claim}>{record.raw_claim}</p>
        <dl className={live.metadata}>{record.years.length > 0 && <div><dt>Years found</dt><dd>{record.years.join(' · ')}</dd></div>}
          {record.claimed_cgpa && <div><dt>Claimed CGPA/GPA</dt><dd>{record.claimed_cgpa.value}{record.claimed_cgpa.scale ? ` / ${record.claimed_cgpa.scale}` : ''}</dd></div>}
          {record.claimed_percentage != null && <div><dt>Claimed percentage</dt><dd>{record.claimed_percentage}%</dd></div>}</dl>
        {record.limitations.map(item => <p className={styles.muted} key={item}>{item}</p>)}
      </article>)}
    </section>}
    <section className={styles.panel} aria-label="Detailed resume analysis"><div className={styles.eyebrow}>The full picture</div><h2>Skills and supporting evidence</h2>
      <p>{analysis.coverage.skills_with_repository_matches} of {analysis.coverage.skills_declared} declared skills have matching repository artifacts. Matches may be source files, dependencies, or configuration; they do not establish mastery.</p>
      <div className={live.filters}><label>Find a skill<input value={query} onChange={e => setQuery(e.target.value)} placeholder="Python, React, Docker…" /></label>
        <label className={live.checkbox}><input type="checkbox" checked={gapsOnly} onChange={e => setGapsOnly(e.target.checked)} />Show skills without repository evidence</label></div>
      {skills.length === 0 && <p className={styles.muted}>No skills match this view.</p>}
      {skills.map((skill, i) => <details className={styles.evidence} key={`${skill.skill}-${i}`}><summary>{skill.skill} · {label(skill.status)}{skill.learning ? ' · Currently learning' : ''}</summary>
        <p>{skill.explanation}</p>{skill.evidence.map((evidence, j) => <p className={live.sourceUrl} key={j}><a href={publicUrl(evidence.url)} target="_blank" rel="noreferrer">{evidence.path}</a> · {label(evidence.basis)} · {evidence.attribution_observed ? 'Recent commit attribution observed' : 'Candidate attribution unknown'}</p>)}
        {skill.evidence_count > skill.evidence.length && <p className={styles.muted}>{skill.evidence_count} matches total; first {skill.evidence.length} shown.</p>}
        {skill.public_mentions.map(url => <p className={live.sourceUrl} key={url}>Public mention: <a href={publicUrl(url)} target="_blank" rel="noreferrer">{url}</a></p>)}
      </details>)}
    </section>
    <section className={styles.panel}><h2>Certificates and credentials</h2>
      {analysis.credentials.length === 0 && <p className={styles.muted}>No distinct certificate claims were extracted. Any supplied credential links still appear in the source receipts.</p>}
      {analysis.credentials.map((credential, i) => <article className={styles.evidence} key={i}><h3>{credential.claim}</h3><span className={styles.tag}>{label(credential.status)}</span>
        {credential.matching_pages.map(page => <p className={live.sourceUrl} key={page.url}><a href={publicUrl(page.url)} target="_blank" rel="noreferrer">{page.title || page.url}</a> · {page.candidate_name_present ? 'Candidate name appears in public text' : 'Candidate name not found in retrieved text'}</p>)}
        <p className={styles.muted}>{credential.explanation}</p></article>)}
    </section>
    <section className={styles.panel}><h2>Projects, experience and education</h2>
      {analysis.projects.map((project, i) => <details className={styles.evidence} key={i}><summary>{project.title} · {label(project.status)}</summary><p className={live.claim}>{project.description}</p>
        {project.source_urls.map(url => <p className={live.sourceUrl} key={url}><a href={publicUrl(url)} target="_blank" rel="noreferrer">{url}</a></p>)}<p className={styles.muted}>{project.explanation}</p></details>)}
      {(['experience', 'education', 'achievements'] as const).map(key => <details className={styles.evidence} key={key}><summary>{label(key)} · {analysis[key].length} extracted lines</summary>
        {analysis[key].length === 0 && <p className={styles.muted}>No distinct section found.</p>}
        {analysis[key].map((item, i) => <p className={live.claim} key={i}>{item.claim} <span className={styles.tag}>{label(item.status)}</span></p>)}
      </details>)}
      {analysis.quantified_claims_to_verify.length > 0 && <details className={styles.evidence}><summary>Measurable claims to verify · {analysis.quantified_claims_to_verify.length}</summary>
        <p className={styles.muted}>Request benchmark methodology, original results, or an independent source for these statements.</p>{analysis.quantified_claims_to_verify.map((claim, i) => <p className={live.claim} key={i}>{claim}</p>)}</details>}
    </section>
    <section className={styles.panel}><h2>Recommended verification steps</h2><ol>{analysis.next_steps.map(step => <li className={live.claim} key={step}>{step}</li>)}</ol><p className={styles.muted}>{analysis.method}</p></section>
  </>;
}
