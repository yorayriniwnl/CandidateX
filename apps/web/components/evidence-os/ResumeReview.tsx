'use client';

import { useMemo, useState } from 'react';
import { publicUrl, type LiveResult } from '../../lib/live-analysis';
import { EvidenceStatus } from './EvidenceStatus';
import { titleWords } from './format';
import styles from './result.module.css';

function SourceLink({ url, children }: { url: string; children: React.ReactNode }) {
  const safe = publicUrl(url);
  return safe ? <a href={safe} target="_blank" rel="noreferrer">{children} ↗</a> : <span>{children} · Link unavailable</span>;
}

export function ResumeReview({ result, onInspect }: { result: LiveResult; onInspect: (id: string) => void }) {
  const { analysis } = result;
  const [query, setQuery] = useState('');
  const [gapsOnly, setGapsOnly] = useState(false);
  const skills = useMemo(() => analysis.skills.filter(skill =>
    skill.skill.toLowerCase().includes(query.trim().toLowerCase()) && (!gapsOnly || !skill.evidence.length)),
  [analysis.skills, query, gapsOnly]);
  const evidenceById = useMemo(() => new Map(result.dossier.evidence_records.map(record => [record.evidence_id, record])), [result.dossier.evidence_records]);
  const role = analysis.role_fit;

  return <div className={styles.resumeReview}>
    <section aria-label="Role requirement fit">
      <div className={styles.sectionHeading}><div><span className={styles.eyebrow}>Job requirements</span><h2>What the job description is supported by</h2></div></div>
      {!role || role.mandatory_total + role.preferred_total === 0
        ? <p className={styles.empty}>No structured job requirements were returned. Capability evidence remains available above.</p>
        : <>
          <dl className={styles.requirementSummary}>
            <div><dt>Mandatory observed</dt><dd>{role.mandatory_observed} <small>/ {role.mandatory_total}</small></dd></div>
            <div><dt>Mandatory gaps</dt><dd>{role.mandatory_unknown + role.mandatory_unresolved}</dd></div>
            <div><dt>Preferred observed</dt><dd>{role.preferred_observed} <small>/ {role.preferred_total}</small></dd></div>
          </dl>
          {role.critical_gaps.length > 0 && <p className={styles.reviewNotice}><strong>Verify mandatory requirements:</strong> {role.critical_gaps.join(' · ')}</p>}
          {role.requirement_matches.map(match => <details className={styles.reviewRow} key={match.requirement_id}>
            <summary><span>{match.source_text}<small>{titleWords(match.priority)}</small></span><EvidenceStatus status={match.status} label={titleWords(match.status)} /></summary>
            <p>{match.explanation}</p>
            <div className={styles.artifactList}>{match.evidence_ids.map(id => {
              const record = evidenceById.get(id);
              return record ? <button key={id} className={styles.linkButton} onClick={() => onInspect(id)}>{record.provenance.artifact_path || 'Inspect observation'} ↗</button>
                : <span key={id}>Referenced evidence record unavailable</span>;
            })}</div>
            {match.matching_technologies.length > 0 && <p className={styles.footnote}>Matching technologies: {match.matching_technologies.join(', ')}</p>}
          </details>)}
        </>}
    </section>

    <section aria-label="Detailed resume analysis">
      <div className={styles.sectionHeading}><div><span className={styles.eyebrow}>Declared skills</span><h2>Skills and supporting evidence</h2><p>{analysis.coverage.skills_with_repository_matches} of {analysis.coverage.skills_declared} declared skills have repository matches. Dependencies and configuration do not establish mastery.</p></div></div>
      <div className={styles.reviewFilters}>
        <label>Find a skill<input type="search" value={query} onChange={event => setQuery(event.target.value)} placeholder="Python, React, Docker…" /></label>
        <label className={styles.reviewCheckbox}><input type="checkbox" checked={gapsOnly} onChange={event => setGapsOnly(event.target.checked)} />Show skills without repository evidence</label>
      </div>
      <p className={styles.footnote} role="status">{skills.length} matching {skills.length === 1 ? 'skill' : 'skills'}</p>
      {skills.length === 0 && <p className={styles.empty}>No skills match this view.</p>}
      {skills.map((skill, index) => <details className={styles.reviewRow} key={`${skill.skill}-${index}`}>
        <summary><span>{skill.skill}{skill.learning && <small>Currently learning</small>}</span><span className={styles.reviewRowMeta}><span>{skill.evidence_count} matches</span><EvidenceStatus status={skill.status} label={titleWords(skill.status)} /></span></summary>
        <p>{skill.explanation}</p>
        <ul className={styles.artifactList}>{skill.evidence.map((evidence, index) => <li key={`${evidence.url}-${index}`}>
          <SourceLink url={evidence.url}><code>{evidence.path}</code></SourceLink>
          <span>{titleWords(evidence.basis)} · {evidence.attribution_observed ? 'Recent-commit attribution observed' : 'Candidate attribution unknown'}</span>
        </li>)}</ul>
        {skill.evidence_count > skill.evidence.length && <p className={styles.footnote}>{skill.evidence_count} matches total; {skill.evidence.length} returned for inspection.</p>}
        {skill.public_mentions.map(url => <p className={styles.footnote} key={url}>Public mention: <SourceLink url={url}>{url}</SourceLink></p>)}
      </details>)}
    </section>

    <section aria-label="Credential review">
      <div className={styles.sectionHeading}><div><span className={styles.eyebrow}>Independent verification</span><h2>Certificates and credentials</h2><p>Public-page matches do not authenticate an issuer, recipient or certificate.</p></div></div>
      {analysis.credentials.length === 0 && <p className={styles.empty}>No distinct certificate claims were extracted.</p>}
      {analysis.credentials.map((credential, index) => <article className={styles.credentialRow} key={index}>
        <div><h3>{credential.claim}</h3><EvidenceStatus status={credential.status} /></div><p>{credential.explanation}</p>
        <ul className={styles.artifactList}>{credential.matching_pages.map((page, index) => <li key={`${page.url}-${index}`}><SourceLink url={page.url}>{page.title || page.url}</SourceLink><span>{page.candidate_name_present ? 'Candidate name appears in public text' : 'Candidate name not found in retrieved text'}</span></li>)}</ul>
      </article>)}
    </section>

    <section aria-label="Resume declarations">
      <div className={styles.sectionHeading}><div><span className={styles.eyebrow}>Candidate declarations</span><h2>Projects, experience and education</h2><p>Statements extracted from the résumé, with their returned verification status.</p></div></div>
      {analysis.projects.map((project, index) => <details className={styles.reviewRow} key={index}>
        <summary><span>{project.title || 'Untitled project'}</span><EvidenceStatus status={project.status} /></summary><p>{project.description}</p><p>{project.explanation}</p>
        <div className={styles.artifactList}>{project.source_urls.map(url => <SourceLink key={url} url={url}>{url}</SourceLink>)}</div>
      </details>)}
      {(['experience', 'education', 'achievements'] as const).map(key => <details className={styles.reviewRow} key={key}>
        <summary><span>{titleWords(key)}</span><span className={styles.reviewRowMeta}>{analysis[key].length} declarations</span></summary>
        {analysis[key].length ? <ul className={styles.declarationRows}>{analysis[key].map((item, index) => <li key={index}><p>{item.claim}</p><EvidenceStatus status={item.status} /></li>)}</ul> : <p>No distinct section was found. This does not establish absence.</p>}
      </details>)}
      {analysis.quantified_claims_to_verify.length > 0 && <details className={styles.reviewRow}>
        <summary><span>Measurable claims to verify</span><span className={styles.reviewRowMeta}>{analysis.quantified_claims_to_verify.length} claims</span></summary>
        <p>Request the benchmark method, original results or an independent source.</p><ul className={styles.declarationRows}>{analysis.quantified_claims_to_verify.map((claim, index) => <li key={index}>{claim}</li>)}</ul>
      </details>}
    </section>

    {analysis.next_steps.length > 0 && <section aria-label="Recommended verification steps"><h2>Recommended verification steps</h2><ol className={styles.verificationSteps}>{analysis.next_steps.map((step, index) => <li key={index}>{step}</li>)}</ol></section>}
    <details className={styles.disclosure}><summary>Analysis method</summary><p>{analysis.method || 'Method description unavailable.'}</p></details>
  </div>;
}
