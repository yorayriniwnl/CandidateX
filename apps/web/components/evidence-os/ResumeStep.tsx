'use client';

import { useRef, useState } from 'react';
import type { ResumeIntake } from '../../lib/live-analysis';
import type { EvaluationStep } from './EvaluationSteps';
import styles from './evidence-os.module.css';

function countLabel(count: number, singular: string, plural = `${singular}s`) {
  return `${count} ${count === 1 ? singular : plural}`;
}

export function ResumeStep({ intake, fileName, fileSize, busy, onUpload, onRemove, onContinue }: {
  intake: ResumeIntake | null;
  fileName: string;
  fileSize: number;
  busy: boolean;
  onUpload: (file?: File) => void;
  onRemove: () => void;
  onContinue: (step: EvaluationStep) => void;
}) {
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const manifest = intake?.manifest;
  const sourceCount = manifest
    ? [...manifest.github_urls, ...manifest.linkedin_urls, ...manifest.coding_profile_urls,
      ...manifest.credential_urls, ...manifest.deployment_urls, ...manifest.portfolio_urls, ...manifest.project_links]
      .filter((url, index, urls) => urls.indexOf(url) === index).length
    : 0;

  function formatSize(bytes: number) {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  }

  return (
    <section className={styles.stepPanel} aria-labelledby="resume-step-title">
      <div className={styles.sectionEyebrow}>01 / Resume intake</div>
      <h2 id="resume-step-title">Start with the candidate’s document.</h2>
      <p className={styles.sectionIntro}>Extract declarations and public source links. Nothing on this screen is independently verified.</p>

      <div className={styles.demoNotice} role="note" aria-label="Research demo data notice">
        <strong>Research demo · synthetic data only</strong>
        <span>Do not upload real candidate resumes. Results are not validated for employment decisions.</span>
      </div>

      <label
        className={`${styles.dropzone} ${dragging ? styles.dropzoneActive : ''} ${busy ? styles.dropzoneDisabled : ''}`}
        htmlFor="resume-upload"
        onDragOver={event => { event.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={event => {
          event.preventDefault();
          setDragging(false);
          onUpload(event.dataTransfer.files?.[0]);
        }}
      >
        <span className={styles.uploadMark} aria-hidden="true">↑</span>
        <span className={styles.dropTitle}>{intake ? 'Replace resume' : 'Drop a resume here or browse'}</span>
        <span className={styles.dropNote}>PDF or DOCX · up to 3 MB · digital text only</span>
        <input
          ref={inputRef}
          id="resume-upload"
          type="file"
          accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
          disabled={busy}
          onChange={event => {
            onUpload(event.target.files?.[0]);
            event.currentTarget.value = '';
          }}
        />
      </label>
      <p className={styles.privacyNote}>The document is processed for this request and is not saved. Scanned images need OCR before upload.</p>

      {intake && manifest && (
        <div className={styles.intakeSummary}>
          <div className={styles.summaryHeading}>
            <div>
              <div className={styles.sectionEyebrow}>RESUME INGESTED · DECLARED INPUTS</div>
              <h3>{manifest.display_name}</h3>
              <p>{fileName || intake.filename}{manifest.email ? ` · ${manifest.email}` : ''}</p>
            </div>
            <span className={styles.docFingerprint}>SHA-256<br /><code>{intake.document_sha256.slice(0, 16)}…</code></span>
          </div>
          <div className={styles.intakeStats}>
            <div><strong>{manifest.claimed_skills.length}</strong><span>Declared skills</span></div>
            <div data-testid="project-count"><strong>{manifest.project_claims.length}</strong><span>Extracted projects</span></div>
            <div><strong>{sourceCount}</strong><span>Extracted links</span></div>
            <div><strong>{manifest.github_urls.length}</strong><span>GitHub links</span></div>
          </div>
          <div className={styles.fileLine}>
            <span>{(fileName || intake.filename).toLowerCase().endsWith('.docx') ? 'DOCX' : 'PDF'} · {formatSize(fileSize)}</span>
            <span className={styles.fileActions}>
              <button className={styles.textButton} type="button" disabled={busy} onClick={() => inputRef.current?.click()}>Choose another file</button>
              <button className={styles.textButton} type="button" disabled={busy} onClick={onRemove}>Remove</button>
            </span>
          </div>
          {manifest.claimed_skills.length > 0 && (
            <div className={styles.declaredList} data-testid="declared-skills">
              <span>Self-reported skills</span>
              <p>{manifest.claimed_skills.join(' · ')}</p>
            </div>
          )}
          {intake.warnings.map((warning, index) => <p className={styles.inlineWarning} key={`${index}-${warning}`}>{warning}</p>)}
        </div>
      )}

      {!intake && <p className={styles.inputLimit}>PDF/DOCX only · 3 MB maximum · request-scoped processing</p>}
      {intake && <div className={styles.stepActions}>
        <span className={styles.muted}>Next: choose the role and optional job description.</span>
        <button className={styles.primaryButton} type="button" onClick={() => onContinue(1)}>Continue to target role <span aria-hidden="true">→</span></button>
      </div>}
    </section>
  );
}
