'use client';

import { useEffect, useRef, useState } from 'react';
import { ArrowUpRight, Pause, Play } from 'lucide-react';
import type { SignalScene } from './signal-scene';
import styles from './signal.module.css';

const STAGES = [
  { label: 'Context', title: 'Every signal starts with a person.', detail: 'A résumé, a role, and the sources a candidate chooses to share.' },
  { label: 'Evidence', title: 'Follow the claim to its source.', detail: 'Inspect public artifacts. Keep supporting evidence and missing context visible.' },
  { label: 'Capability', title: 'Bring the shape of the work into focus.', detail: 'Explore capability signals through the lens of the role, with uncertainty intact.' },
  { label: 'Interview', title: 'Turn what is unknown into a better question.', detail: 'Carry the evidence into a focused conversation. The judgment stays human.' },
];
const LABELS = ['Candidate context', 'Public evidence', 'Capability signals', 'Interview questions'];

export function SignalConstellation() {
  const host = useRef<HTMLDivElement>(null);
  const labels = useRef<HTMLDivElement>(null);
  const scene = useRef<SignalScene | null>(null);
  const [paused, setPaused] = useState(false);
  const [ready, setReady] = useState(false);
  const [active, setActive] = useState(0);
  const activeRef = useRef(0);
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
        scene.current.setStage(activeRef.current);
        scene.current.setPaused(pausedRef.current);
        scene.current.setVisible(visible);
        setReady(true);
      }).catch(() => {
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
  function selectStage(index: number) {
    activeRef.current = index;
    setActive(index);
    scene.current?.setStage(index);
  }

  return (
    <div className={styles.engine} data-testid="signal-observatory" data-ready={ready} data-motion={paused ? 'paused' : 'playing'}>
      <div className={styles.heading}>
        <span className={styles.instrumentNumber}>CX / 01</span>
        <span>The evidence engine</span>
        <span className={styles.edition}>Interactive illustration</span>
      </div>
      <div className={styles.stage} ref={host} aria-hidden="true">
        <div className={styles.aura} />
        <div className={styles.crosshair} />
        <span className={styles.axisTop}>CONTEXT IN</span>
        <span className={styles.axisBottom}>CLARITY OUT</span>
        <svg className={styles.fallback} viewBox="0 0 600 520" fill="none">
          <defs>
            <linearGradient id="cx-metal" x1="130" y1="100" x2="460" y2="420" gradientUnits="userSpaceOnUse">
              <stop stopColor="#666581" /><stop offset=".26" stopColor="#e7e3ff" /><stop offset=".45" stopColor="#50406e" /><stop offset=".75" stopColor="#bdacfa" /><stop offset="1" stopColor="#414255" />
            </linearGradient>
            <radialGradient id="cx-core"><stop stopColor="#e7d8ff" /><stop offset=".38" stopColor="#a287e9" /><stop offset="1" stopColor="#362265" /></radialGradient>
            <radialGradient id="cx-halo"><stop stopColor="#8870e8" stopOpacity=".25" /><stop offset="1" stopColor="#8870e8" stopOpacity="0" /></radialGradient>
          </defs>
          <circle cx="300" cy="260" r="230" fill="url(#cx-halo)" />
          <g stroke="url(#cx-metal)" strokeWidth="6">
            <ellipse cx="300" cy="260" rx="192" ry="146" transform="rotate(-29 300 260)" />
            <ellipse cx="300" cy="260" rx="146" ry="168" transform="rotate(35 300 260)" />
            <ellipse cx="300" cy="260" rx="115" ry="137" transform="rotate(-48 300 260)" />
          </g>
          <ellipse cx="300" cy="260" rx="181" ry="135" stroke="#b49aff" strokeWidth="1.5" transform="rotate(-29 300 260)" />
          <ellipse cx="300" cy="260" rx="135" ry="156" stroke="#90d3e6" transform="rotate(35 300 260)" />
          <circle cx="300" cy="260" r="72" fill="url(#cx-core)" stroke="#d7c7ff" strokeOpacity=".5" />
          <path d="m300 187 61 37 11 65-48 42-63-9-32-62 23-51Zm0 0 24 144m-72-122 120 80m-143-29 132-36" stroke="#c4a5fc" strokeOpacity=".35" />
          <path d="M68 148Q200 125 300 260M522 155Q408 139 300 260M75 382Q187 360 300 260M523 378Q390 391 300 260" stroke="#a291c9" strokeOpacity=".25" />
        </svg>
        <div className={styles.labels} ref={labels}>
          {LABELS.map((label, index) => <div className={styles.nodeLabel} key={label} data-node={index} data-active={active === index}><i /><span>{label}</span><ArrowUpRight size={10} /></div>)}
        </div>
      </div>
      <div className={styles.console}>
        <div className={styles.controls}>
          <div className={styles.stages} role="group" aria-label="Explore the evidence engine">
            {STAGES.map((stage, index) => <button key={stage.label} type="button" aria-pressed={active === index} onClick={() => selectStage(index)}><span>0{index + 1}</span>{stage.label}</button>)}
          </div>
          {ready && <button className={styles.motionButton} type="button" onClick={toggleMotion} aria-label={paused ? 'Play 3D animation' : 'Pause 3D animation'}>{paused ? <Play size={13} aria-hidden="true" /> : <Pause size={13} aria-hidden="true" />}</button>}
        </div>
        <div className={styles.caption} aria-live="polite" aria-atomic="true">
          <strong>{STAGES[active].title}</strong><p>{STAGES[active].detail}</p>
        </div>
      </div>
      <p className="sr-only">An illuminated glass core within three rotating metal rings illustrates candidate claims moving through evidence into capabilities and human interview questions.</p>
    </div>
  );
}
