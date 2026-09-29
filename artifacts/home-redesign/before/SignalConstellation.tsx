'use client';

import { useEffect, useRef, useState } from 'react';
import { Pause, Play } from 'lucide-react';
import type { SignalScene } from './signal-scene';
import styles from './signal.module.css';

const LABELS = ['Candidate', 'Evidence', 'Capability', 'Interview'];

export function SignalConstellation() {
  const host = useRef<HTMLDivElement>(null);
  const labels = useRef<HTMLDivElement>(null);
  const scene = useRef<SignalScene | null>(null);
  const [paused, setPaused] = useState(false);
  const [ready, setReady] = useState(false);
  const pausedRef = useRef(false);

  useEffect(() => {
    const element = host.current!;
    let disposed = false;
    let loading = false;
    let visible = false;
    const preference = window.matchMedia('(prefers-reduced-motion: reduce)');
    const updatePreference = () => {
      pausedRef.current = preference.matches;
      setPaused(preference.matches);
      scene.current?.setPaused(preference.matches);
    };
    updatePreference();
    preference.addEventListener('change', updatePreference);
    const observer = new IntersectionObserver(([entry]) => {
      visible = entry.isIntersecting;
      scene.current?.setVisible(visible);
      if (!visible || loading) return;
      loading = true;
      void import('./signal-scene').then(({ createSignalScene }) => {
        if (disposed) return;
        scene.current = createSignalScene(element, Array.from(labels.current!.children) as HTMLElement[], () => { if (!disposed) setReady(false); });
        scene.current.setPaused(pausedRef.current);
        scene.current.setVisible(visible);
        setReady(true);
      }).catch(() => {
        // Keep the inline illustration when WebGL or the scene chunk is unavailable.
        if (!disposed) element.dataset.renderer = 'fallback';
      });
    });
    observer.observe(element);
    return () => {
      disposed = true;
      observer.disconnect();
      preference.removeEventListener('change', updatePreference);
      scene.current?.dispose();
      scene.current = null;
    };
  }, []);

  function toggleMotion() {
    pausedRef.current = !pausedRef.current;
    setPaused(pausedRef.current);
    scene.current?.setPaused(pausedRef.current);
  }

  return <div className={styles.engine} data-testid="signal-observatory" data-ready={ready} data-motion={paused ? 'paused' : 'playing'}>
    <div className={styles.heading}><span className={styles.liveDot} />The evidence engine<span className={styles.hint}>Move to explore</span></div>
    <div className={styles.stage} ref={host} aria-hidden="true">
      <div className={styles.aura} />
      <svg className={styles.fallback} viewBox="0 0 600 520" fill="none">
        <path d="M95 165 Q240 105 300 260 Q410 120 500 160 M300 260 Q430 410 470 395 M300 260 Q190 430 100 365" stroke="#7770a3" />
        <path d="m300 135 108 62v124l-108 62-108-62V197Z" fill="#8070c51c" stroke="#bdb0ef" />
        <path d="m192 197 108 63 108-63M300 260v123m-70-165 70-40 70 40v82l-70 40-70-40Zm0 0 70 42 70-42" stroke="#9683d3" />
        <path d="m95 147 17 18-17 18-17-18Zm405-5 18 18-18 18-18-18ZM470 379l16 16-16 16-16-16Zm-370-30 16 16-16 16-16-16Z" fill="#b7a4ef" />
      </svg>
      <div className={styles.labels} ref={labels}>{LABELS.map((label, index) => <div className={styles.nodeLabel} key={label} data-node={index}><span>0{index + 1}</span>{label}</div>)}</div>
      <span className={styles.coreLabel}>CX<span>INTELLIGENCE</span></span>
    </div>
    <div className={styles.footer}><span>Claims <i>→</i> evidence <i>→</i> capability <i>→</i> interview</span>{ready && <button type="button" onClick={toggleMotion} aria-label={paused ? 'Play 3D animation' : 'Pause 3D animation'}>{paused ? <Play size={13} aria-hidden="true" /> : <Pause size={13} aria-hidden="true" />}<span>{paused ? 'Play' : 'Pause'}</span></button>}</div>
    <p className="sr-only">Illustration of candidate claims moving through public evidence into capabilities and focused interview questions.</p>
  </div>;
}
