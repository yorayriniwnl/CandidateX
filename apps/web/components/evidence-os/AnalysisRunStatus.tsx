'use client';

import { useEffect, useRef } from 'react';
import styles from './evidence-os.module.css';

function slowScrollToElement(element: HTMLElement) {
  if (typeof window === 'undefined') return;

  const header = document.querySelector('.platform-header') as HTMLElement | null;
  const headerHeight = header ? header.offsetHeight : 72;
  const targetOffset = headerHeight + 20;

  const rect = element.getBoundingClientRect();
  const currentScrollY = window.scrollY || window.pageYOffset;
  const targetY = Math.max(0, currentScrollY + rect.top - targetOffset);
  const distance = targetY - currentScrollY;

  // If already at or very close to target, no need to scroll
  if (Math.abs(distance) < 15) return;

  const prefersReducedMotion = window.matchMedia?.('(prefers-reduced-motion: reduce)')?.matches;
  if (prefersReducedMotion) {
    window.scrollTo({ top: targetY, behavior: 'auto' });
    return;
  }

  // Smooth, slow scroll animation
  // Duration between 850ms and 1200ms depending on distance for a graceful, unhurried glide
  const duration = Math.min(1200, Math.max(850, Math.abs(distance) * 0.9));
  const startTime = performance.now();
  let cancelled = false;
  let rafId: number;

  const onInterrupt = () => {
    cancelled = true;
    cleanup();
  };

  const cleanup = () => {
    window.removeEventListener('wheel', onInterrupt);
    window.removeEventListener('touchstart', onInterrupt);
  };

  window.addEventListener('wheel', onInterrupt, { passive: true });
  window.addEventListener('touchstart', onInterrupt, { passive: true });

  function easeInOutCubic(t: number): number {
    return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
  }

  function step(now: number) {
    if (cancelled) return;
    const elapsed = now - startTime;
    const progress = Math.min(elapsed / duration, 1);
    const ease = easeInOutCubic(progress);

    window.scrollTo(0, currentScrollY + distance * ease);

    if (progress < 1) {
      rafId = requestAnimationFrame(step);
    } else {
      cleanup();
    }
  }

  rafId = requestAnimationFrame(step);

  return () => {
    cancelled = true;
    cancelAnimationFrame(rafId);
    cleanup();
  };
}

export function AnalysisRunStatus({ phase }: { phase: 'upload' | 'analyze' }) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (phase !== 'analyze' || !containerRef.current) return;

    let animFrameId: number;
    let cancelFn: (() => void) | undefined;

    const timer = requestAnimationFrame(() => {
      animFrameId = requestAnimationFrame(() => {
        if (!containerRef.current) return;
        cancelFn = slowScrollToElement(containerRef.current);
      });
    });

    return () => {
      cancelAnimationFrame(timer);
      if (animFrameId) cancelAnimationFrame(animFrameId);
      if (cancelFn) cancelFn();
    };
  }, [phase]);

  return (
    <div
      ref={containerRef}
      id="analysis-run-status"
      className={styles.runStatus}
      role="status"
      aria-live="polite"
      aria-busy="true"
    >
      <span className={styles.runInstrument} aria-hidden="true"><i /><i /><i /><b /></span>
      <div>
        <strong>{phase === 'upload' ? 'Reading the resume' : 'Waiting for the live analysis response'}</strong>
        <p>{phase === 'upload'
          ? 'Extracting text and candidate-declared links from the supplied document.'
          : 'Analysis runs synchronously. The request can take up to 55 seconds; no backend stage progress is available.'}</p>
      </div>
    </div>
  );
}
