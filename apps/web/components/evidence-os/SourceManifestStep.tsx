'use client';

import { useState } from 'react';
import type { EvaluationStep } from './EvaluationSteps';
import styles from './evidence-os.module.css';

export interface SourceSelection {
  url: string;
  kind: 'github' | 'public';
  category: string;
  declared: boolean;
  selectable: boolean;
  selected: boolean;
  reason?: string;
}

export function SourceManifestStep({ sources, identity, busy, addError, onToggle, onAdd, onIdentityChange, onContinue }: {
  sources: SourceSelection[];
  identity: string;
  busy: boolean;
  addError: string;
  onToggle: (url: string, selected: boolean) => void;
  onAdd: (url: string) => void;
  onIdentityChange: (identity: string) => void;
  onContinue: (step: EvaluationStep) => void;
}) {
  const [draft, setDraft] = useState('');
  const selectedCount = sources.filter(source => source.selected && source.selectable).length;

  function addSource() {
    const value = draft.trim();
    if (!value) return;
    onAdd(value);
    setDraft('');
  }

  return (
    <section className={styles.stepPanel} aria-labelledby="sources-step-title">
      <div className={styles.sectionEyebrow}>03 / Source manifest</div>
      <h2 id="sources-step-title">Choose what to inspect.</h2>
      <p className={styles.sectionIntro}>These links were extracted from the resume or added by you. Nothing has been fetched yet.</p>

      <div className={styles.manifestHeader}>
        <span>SUPPLIED SOURCE</span><span>CATEGORY</span><span>SELECTION</span>
      </div>
      <div className={styles.manifestRows}>
        {sources.length === 0 && <p className={styles.emptyLine}>No public sources selected. Add a public URL if you want CandidateX to inspect one.</p>}
        {sources.map((source, index) => (
          <div className={styles.manifestRow} key={`${source.kind}-${source.url}-${index}`}>
            <div className={styles.manifestSource}>
              <span className={styles.sourceType}>{source.kind === 'github' ? 'GITHUB' : 'PUBLIC URL'}</span>
              <span className={styles.sourceAddress} title={source.url}>{source.url}</span>
              <span className={styles.sourceOrigin}>{source.declared ? 'Candidate-declared in resume' : 'Added by interviewer'}</span>
              {!source.selectable && <span className={styles.sourceReason}>{source.reason ?? 'This URL cannot be sent for acquisition.'}</span>}
            </div>
            <span className={styles.manifestCategory}>{source.category}</span>
            <label className={styles.selectionControl}>
              <input
                type="checkbox"
                checked={source.selected}
                disabled={busy || !source.selectable}
                onChange={event => onToggle(source.url, event.target.checked)}
                aria-label={`${source.url} (${source.category})`}
              />
              <span>{source.selectable ? source.selected ? 'Selected for request' : 'Not selected' : 'Not submitted'}</span>
            </label>
          </div>
        ))}
      </div>

      <div className={styles.addSource}>
        <div className={styles.fieldBlock}>
          <label htmlFor="additional-source">Add a public source URL</label>
          <input id="additional-source" type="text" inputMode="url" value={draft} disabled={busy} onChange={event => setDraft(event.target.value)} onKeyDown={event => { if (event.key === 'Enter') { event.preventDefault(); addSource(); } }} placeholder="https://github.com/username/repository" />
        </div>
        <button className={styles.secondaryButton} type="button" disabled={busy || !draft.trim()} onClick={addSource}>Add source</button>
      </div>
      {addError && <p className={styles.inlineError} role="alert">{addError}</p>}

      {sources.some(source => source.kind === 'github') && (
        <div className={`${styles.fieldBlock} ${styles.identityField}`}>
          <label htmlFor="github-identity">Candidate-declared GitHub username</label>
          <input id="github-identity" type="text" maxLength={39} disabled={busy} value={identity} onChange={event => onIdentityChange(event.target.value)} placeholder="Leave blank if unknown" />
          <p>Used for repository-level ownership heuristics. A profile link does not verify identity or authorship.</p>
        </div>
      )}

      <div className={styles.limitNotice}>
        <strong>{selectedCount} public {selectedCount === 1 ? 'source' : 'sources'} selected</strong>
        <span>Live limits: up to 20 GitHub URLs, 6 detailed repositories, and 24 public pages per run. Access restrictions and scan limits are reported after the request.</span>
      </div>
      <div className={styles.stepActions}>
        <button className={styles.secondaryButton} type="button" onClick={() => onContinue(1)}>← Target role</button>
        <button className={styles.primaryButton} type="button" onClick={() => onContinue(3)}>Continue to review <span aria-hidden="true">→</span></button>
      </div>
    </section>
  );
}
