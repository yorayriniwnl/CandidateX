import { useState } from 'react';
import { publicUrl, type ComprehensiveAnalysis, type SourceReceipt, type ResumeIntake } from '../../lib/live-analysis';
import type { RoleFitSummary } from '../../types/cci';
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
      {review.engineering_fingerprint && <div className={styles.evidence}>
        <div className={styles.eyebrow}>Deterministic engineering fingerprint</div>
        <h3>{review.engineering_fingerprint.practice_breadth.observed} / {review.engineering_fingerprint.practice_breadth.possible} practice families observed</h3>
        <p className={styles.muted}>{review.engineering_fingerprint.interpretation}</p>
        <div className={styles.factors}>
          {review.engineering_fingerprint.observed_practices.map(practice =>
            <span key={practice.name}>{label(practice.name)} · {practice.occurrence_files} file{practice.occurrence_files === 1 ? '' : 's'}</span>)}
        </div>
        <h3>Static module topology</h3>
        <div className={styles.metrics}>
          <div className={styles.metric}><span>Modules</span><strong>{review.engineering_fingerprint.module_topology.nodes}</strong><span>inspected Python / TS / JS files</span></div>
          <div className={styles.metric}><span>Local edges</span><strong>{review.engineering_fingerprint.module_topology.edges}</strong><span>resolved relative imports</span></div>
          <div className={styles.metric}><span>Components</span><strong>{review.engineering_fingerprint.module_topology.connected_components}</strong><span>connected source groups</span></div>
          <div className={styles.metric}><span>Cycles</span><strong>{review.engineering_fingerprint.module_topology.cycles_detected}</strong><span>within the bounded scan</span></div>
        </div>
        {(review.engineering_fingerprint.module_topology.highest_fan_out.length > 0 || review.engineering_fingerprint.module_topology.highest_fan_in.length > 0) && <details className={styles.evidence}>
          <summary>Dependency hotspots</summary>
          {review.engineering_fingerprint.module_topology.highest_fan_out.map(item => <p className={live.sourceUrl} key={'out-' + item.path}>
            Fan-out {item.edges} · <strong>{item.path}</strong>
          </p>)}
          {review.engineering_fingerprint.module_topology.highest_fan_in.map(item => <p className={live.sourceUrl} key={'in-' + item.path}>
            Fan-in {item.edges} · <strong>{item.path}</strong>
          </p>)}
          <p className={styles.muted}>{review.engineering_fingerprint.module_topology.limitations}</p>
        </details>}
        {review.engineering_fingerprint.module_topology.cycles.length > 0 && <details className={styles.evidence}>
          <summary>Dependency cycles · {review.engineering_fingerprint.module_topology.cycles_detected}</summary>
          {review.engineering_fingerprint.module_topology.cycles.map((cycle, index) => <p className={live.sourceUrl} key={index}>{cycle.join(' → ')}</p>)}
          <p className={styles.muted}>A cycle is an architecture review target, not proof of poor engineering; context and framework conventions still matter.</p>
        </details>}
        <details className={styles.evidence} open={review.engineering_fingerprint.review_targets.count > 0}>
          <summary>Static engineering review targets · {review.engineering_fingerprint.review_targets.count}</summary>
          <p className={styles.muted}>{review.engineering_fingerprint.review_targets.interpretation}</p>
          <div className={styles.factors}>
            <span>High: {review.engineering_fingerprint.review_targets.by_severity.high}</span>
            <span>Medium: {review.engineering_fingerprint.review_targets.by_severity.medium}</span>
            <span>Low: {review.engineering_fingerprint.review_targets.by_severity.low}</span>
          </div>
          {review.engineering_fingerprint.review_targets.findings.length === 0
            ? <p className={styles.muted}>No configured review-target pattern appeared in the inspected file set.</p>
            : review.engineering_fingerprint.review_targets.findings.map((finding, index) => <div className={live.signal} key={finding.rule + finding.path + index}>
                <strong>{label(finding.rule)} · {label(finding.severity)}</strong>
                <span>{finding.path}{finding.lines.length ? ` · line${finding.lines.length === 1 ? '' : 's'} ${finding.lines.join(', ')}` : ''}</span>
                <p className={styles.muted}>{finding.why_review}</p>
              </div>)}
        </details>
        {review.engineering_fingerprint.architecture_boundaries.length > 0 && <details className={styles.evidence}>
          <summary>Architecture boundaries · {review.engineering_fingerprint.architecture_boundaries.length}</summary>
          {review.engineering_fingerprint.architecture_boundaries.map(boundary => <div className={live.signal} key={boundary.name}>
            <strong>{label(boundary.name)}</strong><span>{boundary.occurrence_files} file{boundary.occurrence_files === 1 ? '' : 's'}</span>
            {boundary.paths.slice(0, 4).map(path => <code className={live.sourceUrl} key={path}>{path}</code>)}
          </div>)}
        </details>}
        {review.engineering_fingerprint.signal_hotspots.length > 0 && <details className={styles.evidence}>
          <summary>Signal-dense files · {review.engineering_fingerprint.signal_hotspots.length}</summary>
          {review.engineering_fingerprint.signal_hotspots.map(hotspot => <p className={live.sourceUrl} key={hotspot.path}>
            <strong>{hotspot.path}</strong> · {hotspot.signal_family_count} signal families · {hotspot.signal_families.map(label).join(', ')}
          </p>)}
        </details>}
        {review.engineering_fingerprint.not_observed_in_bounded_scan.length > 0 && <details className={styles.evidence}>
          <summary>Not observed in this bounded scan · {review.engineering_fingerprint.not_observed_in_bounded_scan.length}</summary>
          <p className={styles.muted}>These are scan gaps, not claims that the repository or candidate lacks the practice.</p>
          <div className={styles.factors}>{review.engineering_fingerprint.not_observed_in_bounded_scan.map(item => <span key={item}>{label(item)}</span>)}</div>
        </details>}
      </div>}
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

function RoleFitPanel({ roleFit }: { roleFit: RoleFitSummary }) {
  const mandatoryGaps = roleFit.mandatory_unknown + roleFit.mandatory_unresolved;
  return <section className={styles.panel} aria-label="Role requirement fit">
    <div className={styles.eyebrow}>Requirement fit</div>
    <h2>What the job description is supported by</h2>
    {roleFit.mandatory_total === 0 && roleFit.preferred_total === 0
      ? <p className={styles.muted}>No structured job requirements were supplied. Capability evidence is still shown, but role-specific fit cannot be resolved.</p>
      : <>
        <div className={styles.metrics}>
          <div className={styles.metric}><span>Mandatory observed</span><strong>{roleFit.mandatory_observed} / {roleFit.mandatory_total}</strong><span>Exact requirement evidence</span></div>
          <div className={styles.metric}><span>Mandatory gaps</span><strong>{mandatoryGaps}</strong><span>Unknown or unmappable</span></div>
          <div className={styles.metric}><span>Preferred observed</span><strong>{roleFit.preferred_observed} / {roleFit.preferred_total}</strong><span>Supporting role signals</span></div>
        </div>
        {roleFit.critical_gaps.length > 0 && <div className={styles.warning}>
          <p>Mandatory requirements needing verification:</p>
          <ul>{roleFit.critical_gaps.map(gap => <li key={gap}>{gap}</li>)}</ul>
        </div>}
        {roleFit.requirement_matches.map(match => <details className={styles.evidence} key={match.requirement_id}>
          <summary>{match.source_text} · <span className={`${styles.statusPill} ${match.status === 'observed' ? styles.statusGood : styles.statusNeedsReview}`}>{label(match.status)}</span></summary>
          <p>{match.explanation}</p>
          <p className={styles.muted}>{label(match.priority)} · {match.evidence_ids.length} evidence record{match.evidence_ids.length === 1 ? '' : 's'}{match.matching_technologies.length > 0 ? ` · ${match.matching_technologies.join(', ')}` : ''}</p>
        </details>)}
      </>}
  </section>;
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
    {analysis.role_fit && <RoleFitPanel roleFit={analysis.role_fit} />}
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
