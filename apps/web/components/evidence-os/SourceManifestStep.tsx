'use client';

import { useState, useRef, useEffect } from 'react';
import { Check, ExternalLink, Copy, Download, Loader2, Sparkles, AlertCircle } from 'lucide-react';
import type { EvaluationStep } from './EvaluationSteps';
import type { FetchedLinkResult } from '../../lib/live-analysis';
import styles from './evidence-os.module.css';

export interface SourceSelection {
  url: string;
  kind: 'github' | 'public';
  category: string;
  declared: boolean;
  selectable: boolean;
  selected: boolean;
  reason?: string;
  fetchedData?: FetchedLinkResult;
  fetching?: boolean;
  fetchError?: string;
}

function formatHref(url: string): string {
  const trimmed = url.trim();
  if (/^[a-zA-Z][a-zA-Z\d+\-.]*?:/.test(trimmed)) {
    return trimmed;
  }
  return `https://${trimmed}`;
}

function isCloudUrl(url: string, category?: string): boolean {
  if (category && (category.includes('Shared file') || category.includes('Cloud'))) return true;
  try {
    const host = new URL(url).hostname.toLowerCase();
    return ['drive.google.com', 'docs.google.com', 'dropbox.com', 'onedrive.live.com', '1drv.ms', 'sharepoint.com', 'box.com', 'icloud.com'].some(d => host.includes(d));
  } catch {
    return false;
  }
}

async function copyToClipboard(text: string): Promise<boolean> {
  if (typeof navigator !== 'undefined' && navigator.clipboard?.writeText) {
    try {
      await navigator.clipboard.writeText(text);
      return true;
    } catch {
      // Fallback below
    }
  }

  try {
    const textArea = document.createElement('textarea');
    textArea.value = text;
    textArea.style.position = 'fixed';
    textArea.style.left = '-999999px';
    textArea.style.top = '-999999px';
    textArea.setAttribute('readonly', '');
    document.body.appendChild(textArea);
    textArea.focus();
    textArea.select();
    const successful = document.execCommand('copy');
    document.body.removeChild(textArea);
    return successful;
  } catch {
    return false;
  }
}

export function SourceManifestStep({
  sources,
  identity,
  busy,
  addError,
  onToggle,
  onAdd,
  onIdentityChange,
  onContinue,
  onFetchLink,
  onFetchAllCloud,
}: {
  sources: SourceSelection[];
  identity: string;
  busy: boolean;
  addError: string;
  onToggle: (url: string, selected: boolean) => void;
  onAdd: (url: string) => void;
  onIdentityChange: (identity: string) => void;
  onContinue: (step: EvaluationStep) => void;
  onFetchLink?: (url: string) => void;
  onFetchAllCloud?: () => void;
}) {
  const [draft, setDraft] = useState('');
  const [copiedIndex, setCopiedIndex] = useState<number | null>(null);
  const [expandedUrls, setExpandedUrls] = useState<Set<string>>(new Set());
  const copyTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const selectedCount = sources.filter(source => source.selected && source.selectable).length;

  const cloudSources = sources.filter(s => isCloudUrl(s.url, s.category));
  const unfetchedCloudCount = cloudSources.filter(s => !s.fetchedData && !s.fetching).length;
  const isFetchingAny = sources.some(s => s.fetching);

  useEffect(() => {
    return () => {
      if (copyTimeoutRef.current) {
        clearTimeout(copyTimeoutRef.current);
      }
    };
  }, []);

  const handleLinkClick = async (e: React.MouseEvent<HTMLAnchorElement>, url: string, index: number) => {
    if (e.ctrlKey || e.metaKey) {
      return;
    }
    e.preventDefault();
    const copied = await copyToClipboard(url);
    if (copied) {
      setCopiedIndex(index);
      if (copyTimeoutRef.current) {
        clearTimeout(copyTimeoutRef.current);
      }
      copyTimeoutRef.current = setTimeout(() => {
        setCopiedIndex(null);
      }, 2000);
    }
  };

  const toggleDetails = (url: string) => {
    setExpandedUrls(prev => {
      const next = new Set(prev);
      if (next.has(url)) next.delete(url);
      else next.add(url);
      return next;
    });
  };

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
      <p className={styles.sectionIntro}>Nothing has been fetched yet. Review the manifest, uncheck anything that should not be touched, open links, or fetch files before analysis.</p>

      {cloudSources.length > 0 && onFetchAllCloud && unfetchedCloudCount > 0 && (
        <div className={styles.cloudBatchBar}>
          <div className={styles.cloudBatchInfo}>
            <Sparkles size={14} className={styles.sparkleIcon} />
            <span>{cloudSources.length} cloud storage {cloudSources.length === 1 ? 'link' : 'links'} detected. Fetch remote files and inspect project data before running analysis.</span>
          </div>
          <button
            type="button"
            className={styles.fetchAllCloudBtn}
            disabled={busy || isFetchingAny}
            onClick={onFetchAllCloud}
          >
            {isFetchingAny ? <Loader2 size={12} className={styles.spinnerIcon} /> : <Download size={12} />}
            <span>Fetch all cloud files & data</span>
          </button>
        </div>
      )}

      <div className={styles.manifestHeader}>
        <span>SUPPLIED SOURCE</span><span>CATEGORY</span><span>SELECTION</span>
      </div>
      <div className={styles.manifestRows}>
        {sources.length === 0 && <p className={styles.emptyLine}>No public sources selected. Add a public URL if you want CandidateX to inspect one.</p>}
        {sources.map((source, index) => {
          const isCloud = isCloudUrl(source.url, source.category);
          return (
            <div className={styles.manifestRow} key={`${source.kind}-${source.url}-${index}`}>
              <div className={styles.manifestSource}>
                <span className={styles.sourceType}>{source.kind === 'github' ? 'GITHUB' : isCloud ? 'CLOUD FILE' : 'PUBLIC URL'}</span>
                <div className={styles.sourceAddressWrapper}>
                  <a
                    href={formatHref(source.url)}
                    target="_blank"
                    rel="noopener noreferrer"
                    className={styles.sourceAddress}
                    title={`${source.url}\nClick to copy · Ctrl+click to open in new tab`}
                    onClick={(e) => handleLinkClick(e, source.url, index)}
                  >
                    <span className={styles.sourceAddressText}>{source.url}</span>
                  </a>
                  <a
                    href={formatHref(source.url)}
                    target="_blank"
                    rel="noopener noreferrer"
                    className={styles.openDirectLink}
                    title="Open link in new tab"
                  >
                    <span>Open link</span>
                    <ExternalLink size={10} aria-hidden="true" />
                  </a>
                  {copiedIndex === index && (
                    <span className={styles.copiedTooltip} role="status" aria-live="polite">
                      <Check size={11} strokeWidth={2.5} className={styles.copiedIcon} aria-hidden="true" />
                      <span>Copied!</span>
                    </span>
                  )}
                </div>

                {source.fetching ? (
                  <div className={styles.sourceOriginFetching}>
                    <Loader2 size={12} className={styles.spinnerIcon} />
                    <span>Opening link, fetching files & extracting data…</span>
                  </div>
                ) : source.fetchedData ? (
                  <div className={styles.sourceFetchedContainer}>
                    <div className={styles.sourceFetchedHeader}>
                      <span className={styles.fetchedSuccessBadge}>
                        <Check size={11} strokeWidth={2.5} /> Files & data fetched ({source.fetchedData.file_count || source.fetchedData.files?.length || 1} {((source.fetchedData.file_count || source.fetchedData.files?.length || 1) === 1 ? 'file' : 'files')}{source.fetchedData.total_size ? ` · ${(source.fetchedData.total_size / 1024).toFixed(1)} KB` : ''})
                      </span>
                      {source.fetchedData.technologies && source.fetchedData.technologies.length > 0 && (
                        <span className={styles.fetchedTechBadge}>
                          {source.fetchedData.technologies.slice(0, 4).join(', ')}
                        </span>
                      )}
                      <button
                        type="button"
                        className={styles.toggleDetailsBtn}
                        onClick={() => toggleDetails(source.url)}
                        aria-expanded={expandedUrls.has(source.url)}
                      >
                        {expandedUrls.has(source.url) ? 'Hide data ▴' : 'View files & data ▾'}
                      </button>
                    </div>
                    {expandedUrls.has(source.url) && (
                      <div className={styles.fetchedDetailsDrawer}>
                        {source.fetchedData.detail && <p className={styles.fetchedDetailText}>{source.fetchedData.detail}</p>}
                        {source.fetchedData.files && source.fetchedData.files.length > 0 && (
                          <div className={styles.fetchedFilesList}>
                            <span className={styles.fetchedFilesTitle}>Files detected ({source.fetchedData.files.length}):</span>
                            <div className={styles.fileTags}>
                              {source.fetchedData.files.slice(0, 15).map((f, fi) => (
                                <span key={`${f.name}-${fi}`} className={styles.fileTag}>
                                  <code>{f.name}</code> {f.size > 0 ? <small>({(f.size / 1024).toFixed(1)} KB)</small> : null}
                                </span>
                              ))}
                              {source.fetchedData.files.length > 15 && (
                                <span className={styles.fileMore}>+{source.fetchedData.files.length - 15} more files</span>
                              )}
                            </div>
                          </div>
                        )}
                        {source.fetchedData.excerpt && (
                          <div className={styles.fetchedExcerpt}>
                            <span className={styles.fetchedExcerptTitle}>Data preview:</span>
                            <blockquote>{source.fetchedData.excerpt.slice(0, 300)}{source.fetchedData.excerpt.length > 300 ? '…' : ''}</blockquote>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                ) : source.fetchError ? (
                  <div className={styles.sourceFetchErrorContainer}>
                    <span className={styles.sourceFetchError}>
                      <AlertCircle size={11} /> Could not fetch files: {source.fetchError}
                    </span>
                    {onFetchLink && (
                      <button
                        type="button"
                        className={styles.retryFetchBtn}
                        disabled={busy}
                        onClick={() => onFetchLink(source.url)}
                      >
                        Retry fetch
                      </button>
                    )}
                  </div>
                ) : isCloud ? (
                  <div className={styles.sourceCloudActionRow}>
                    <span className={styles.sourceOrigin}>
                      {source.declared ? 'Candidate-declared cloud link' : 'Cloud storage link'}
                    </span>
                    {onFetchLink && (
                      <button
                        type="button"
                        className={styles.fetchFilesBtn}
                        disabled={busy || !source.selectable}
                        onClick={() => onFetchLink(source.url)}
                        title="Fetch files and extract data from this link"
                      >
                        <Download size={11} />
                        <span>Fetch files & get data</span>
                      </button>
                    )}
                  </div>
                ) : (
                  <span className={styles.sourceOrigin}>{source.declared ? 'Candidate-declared in resume' : 'Added by interviewer'}</span>
                )}

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
          );
        })}
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
