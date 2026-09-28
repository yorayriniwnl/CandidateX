'use client';

import { useRef, useState } from 'react';
import type { CanonicalRole } from '../../types/cci';
import { roleName } from './format';
import type { EvaluationStep } from './EvaluationSteps';
import styles from './evidence-os.module.css';
import {
  AlertCircle,
  Braces,
  Cloud,
  Database,
  FileCheck,
  Layers3,
  Network,
  PanelsTopLeft,
  RefreshCw,
  Upload,
} from 'lucide-react';

const ROLES: CanonicalRole[] = ['backend', 'frontend', 'fullstack', 'ml_engineer', 'devops_cloud', 'data_engineer'];
const ROLE_ICONS = [Braces, PanelsTopLeft, Layers3, Network, Cloud, Database];

function formatFileSize(bytes?: number) {
  if (!bytes) return '';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

export function RoleStep({
  role,
  jd,
  jdFileName,
  jdFileSize,
  jdLoading = false,
  jdError,
  jdWarning,
  busy,
  onRoleChange,
  onJdChange,
  onJdUpload,
  onJdRemove,
  onContinue,
}: {
  role: CanonicalRole;
  jd: string;
  jdFileName?: string;
  jdFileSize?: number;
  jdLoading?: boolean;
  jdError?: string;
  jdWarning?: string;
  busy: boolean;
  onRoleChange: (role: CanonicalRole) => void;
  onJdChange: (jd: string) => void;
  onJdUpload?: (file?: File) => void;
  onJdRemove?: () => void;
  onContinue: (step: EvaluationStep) => void;
}) {
  const [dragging, setDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  return (
    <section className={styles.stepPanel} aria-labelledby="role-step-title">
      <div className={styles.sectionEyebrow}>02 / Role context</div>
      <h2 id="role-step-title">Set the role context.</h2>
      <p className={styles.sectionIntro}>The role changes how observed evidence is organized. A job description or recruitment standards document is optional.</p>

      <div className={styles.roleCards} role="group" aria-label="Choose a role lens">
        {ROLES.map((option, index) => {
          const Icon = ROLE_ICONS[index];
          return (
            <button
              type="button"
              key={option}
              disabled={busy}
              aria-pressed={role === option}
              onClick={() => onRoleChange(option)}
            >
              <Icon size={18} strokeWidth={1.3} aria-hidden="true" />
              <span>{roleName(option)}</span>
              <i aria-hidden="true" />
            </button>
          );
        })}
      </div>

      <div className={styles.roleControls}>
        <div className={styles.fieldBlock}>
          <label htmlFor="live-role">Target role</label>
          <select id="live-role" value={role} disabled={busy} onChange={event => onRoleChange(event.target.value as CanonicalRole)}>
            {ROLES.map(option => <option key={option} value={option}>{roleName(option)}</option>)}
          </select>
          <p>The role profile and weights are returned with the dossier after analysis.</p>
        </div>

        <div className={styles.fieldBlock}>
          <div className={styles.labelLine}>
            <label htmlFor="live-jd">Job description & recruitment rules</label>
            <span>OPTIONAL</span>
          </div>
          <p className={styles.fieldHint}>
            Upload a job description, company standards, or recruitment rules doc (PDF, DOCX, DOC, or TXT) or paste text directly.
          </p>

          {!jdFileName && (
            <div className={styles.jdUploadBox}>
              <label
                className={`${styles.jdDropzone} ${dragging ? styles.jdDropzoneActive : ''} ${busy || jdLoading ? styles.dropzoneDisabled : ''}`}
                htmlFor="jd-upload"
                onDragOver={event => { event.preventDefault(); setDragging(true); }}
                onDragLeave={() => setDragging(false)}
                onDrop={event => {
                  event.preventDefault();
                  setDragging(false);
                  const file = event.dataTransfer.files?.[0];
                  if (file && onJdUpload) onJdUpload(file);
                }}
              >
                <span className={styles.jdDropIcon}>
                  {jdLoading ? <RefreshCw size={18} className={styles.spinning} /> : <Upload size={18} />}
                </span>
                <div className={styles.jdDropContent}>
                  <span className={styles.jdDropTitle}>
                    {jdLoading ? 'Extracting text from document…' : 'Upload job description or company standards document'}
                  </span>
                  <span className={styles.jdDropNote}>
                    PDF, DOCX, DOC, or TXT · up to 3 MB · text extracted automatically
                  </span>
                </div>
                <input
                  ref={fileInputRef}
                  id="jd-upload"
                  type="file"
                  accept=".pdf,.docx,.doc,.txt,.md,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,application/msword,text/plain,text/markdown"
                  disabled={busy || jdLoading}
                  onChange={event => {
                    const file = event.target.files?.[0];
                    if (file && onJdUpload) onJdUpload(file);
                    event.currentTarget.value = '';
                  }}
                />
              </label>
            </div>
          )}

          {jdFileName && (
            <div className={styles.jdFileCard} data-testid="jd-file-card">
              <div className={styles.jdFileIcon}>
                <FileCheck size={20} />
              </div>
              <div className={styles.jdFileInfo}>
                <div className={styles.jdFileNameRow}>
                  <strong>{jdFileName}</strong>
                  <span className={styles.jdBadge}>Stored in backend</span>
                </div>
                <div className={styles.jdFileMeta}>
                  {jdFileSize ? <span>{formatFileSize(jdFileSize)}</span> : null}
                  {jdFileSize ? <span>·</span> : null}
                  <span>Job description & recruitment rules stored in backend</span>
                  <span>·</span>
                  <span>Ready for analysis</span>
                </div>
              </div>
              <div className={styles.jdFileActions}>
                <button
                  type="button"
                  className={styles.textButton}
                  disabled={busy || jdLoading}
                  onClick={() => fileInputRef.current?.click()}
                >
                  Replace file
                </button>
                {onJdRemove && (
                  <button
                    type="button"
                    className={styles.textButton}
                    disabled={busy || jdLoading}
                    onClick={onJdRemove}
                  >
                    Remove
                  </button>
                )}
              </div>
              <input
                ref={fileInputRef}
                id="jd-replace-upload"
                type="file"
                style={{ display: 'none' }}
                accept=".pdf,.docx,.doc,.txt,.md,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,application/msword,text/plain,text/markdown"
                disabled={busy || jdLoading}
                onChange={event => {
                  const file = event.target.files?.[0];
                  if (file && onJdUpload) onJdUpload(file);
                  event.currentTarget.value = '';
                }}
              />
            </div>
          )}

          {jdError && (
            <p className={styles.inlineError} role="alert">
              <AlertCircle size={13} style={{ display: 'inline', verticalAlign: 'middle', marginRight: '4px' }} />
              {jdError}
            </p>
          )}

          {jdWarning && (
            <p className={styles.inlineWarning} role="status">
              {jdWarning}
            </p>
          )}

          <div className={styles.jdTextareaHeader}>
            <label htmlFor="live-jd">
              {jdFileName ? 'Additional recruiter notes (optional)' : 'Or paste requirements and standards directly'}
            </label>
          </div>

          <textarea
            id="live-jd"
            maxLength={20000}
            disabled={busy || jdLoading}
            placeholder={jdFileName ? "Optional extra notes or specific hiring criteria (document is already safely stored in backend)..." : "Paste the responsibilities, standards, or recruitment rules…"}
            value={jd}
            onChange={event => onJdChange(event.target.value)}
            rows={jdFileName ? 4 : 8}
          />
          <p>
            {jdFileName
              ? 'Document data is securely stored in backend and calibrated for evaluation without displaying in this note.'
              : `${jd.length.toLocaleString()} / 20,000 characters · Parsed during the analysis request.`}
          </p>
        </div>
      </div>
      <div className={styles.stepActions}>
        <button className={styles.secondaryButton} type="button" onClick={() => onContinue(0)}>← Resume</button>
        <button className={styles.primaryButton} type="button" onClick={() => onContinue(2)}>Continue to public sources <span aria-hidden="true">→</span></button>
      </div>
    </section>
  );
}
