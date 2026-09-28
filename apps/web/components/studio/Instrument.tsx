'use client';

import { useEffect, useRef, useState } from 'react';
import { Pause, Play } from 'lucide-react';
import type { SignalScene } from '../home/signal-scene';
import styles from './studio.module.css';

/** Interactive 3D evidence engine sculpture in the analysis wizard. */
export function Instrument({ stage = 0 }: { stage?: number }) {
  const host = useRef<HTMLDivElement>(null);
  const scene = useRef<SignalScene | null>(null);
  const stageRef = useRef(stage);
  const [ready, setReady] = useState(false);
  const [paused, setPaused] = useState(false);
  const pausedRef = useRef(false);

  useEffect(() => {
    const element = host.current!;
    let cancelled = false;
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
      void import('../home/signal-scene').then(({ createSignalScene }) => {
        if (cancelled) return;
        scene.current = createSignalScene(element, [], () => { if (!cancelled) setReady(false); });
        scene.current.setStage(stageRef.current);
        scene.current.setPaused(pausedRef.current);
        scene.current.setVisible(visible);
        setReady(true);
      }).catch(() => { /* Keep the inline orbital illustration. */ });
    });
    observer.observe(element);

    return () => {
      cancelled = true;
      observer.disconnect();
      preference.removeEventListener('change', updatePreference);
      scene.current?.dispose();
      scene.current = null;
    };
  }, []);

  useEffect(() => {
    stageRef.current = stage;
    scene.current?.setStage(stage);
  }, [stage]);

  function toggleMotion() {
    pausedRef.current = !pausedRef.current;
    setPaused(pausedRef.current);
    scene.current?.setPaused(pausedRef.current);
  }

  return (
    <div className={styles.instrumentContainer}>
      <div ref={host} className={styles.instrument} data-ready={ready} aria-hidden="true">
        <svg viewBox="0 0 400 340" fill="none">
          <g stroke="currentColor">
            <ellipse cx="200" cy="170" rx="120" ry="95" transform="rotate(-30 200 170)" strokeWidth="2" />
            <ellipse cx="200" cy="170" rx="80" ry="110" transform="rotate(32 200 170)" />
            <ellipse cx="200" cy="170" rx="66" ry="80" transform="rotate(-50 200 170)" />
            <path d="m200 125 38 22v46l-38 22-38-22v-46Zm0 0v90m-38-68 76 46m0-46-76 46" />
          </g>
        </svg>
      </div>
      {ready && (
        <button
          className={styles.motionToggle}
          type="button"
          onClick={toggleMotion}
          aria-label={paused ? 'Play 3D animation' : 'Pause 3D animation'}
          title={paused ? 'Play motion' : 'Pause motion'}
        >
          {paused ? <Play size={12} aria-hidden="true" /> : <Pause size={12} aria-hidden="true" />}
        </button>
      )}
    </div>
  );
}
