'use client';

import { useEffect, useRef, useState } from 'react';
import type { SignalScene } from '../home/signal-scene';
import styles from './studio.module.css';

/** A still edition of the homepage sculpture; updates only when the selected step changes. */
export function Instrument({ stage = 0 }: { stage?: number }) {
  const host = useRef<HTMLDivElement>(null);
  const scene = useRef<SignalScene | null>(null);
  const stageRef = useRef(stage);
  const [ready, setReady] = useState(false);
  useEffect(() => {
    const element = host.current!;
    let cancelled = false;
    let loading = false;
    const observer = new IntersectionObserver(([entry]) => {
      if (!entry.isIntersecting || loading) return;
      loading = true;
      void import('../home/signal-scene').then(({ createSignalScene }) => {
        if (cancelled) return;
        scene.current = createSignalScene(element, [], () => { if (!cancelled) setReady(false); });
        scene.current.setPaused(true);
        scene.current.setStage(stageRef.current);
        setReady(true);
      }).catch(() => { /* Keep the inline orbital illustration. */ });
    });
    observer.observe(element);
    return () => { cancelled = true; observer.disconnect(); scene.current?.dispose(); scene.current = null; };
  }, []);
  useEffect(() => { stageRef.current = stage; scene.current?.setStage(stage); }, [stage]);
  return <div ref={host} className={styles.instrument} data-ready={ready} aria-hidden="true">
    <svg viewBox="0 0 400 340" fill="none"><g stroke="currentColor"><ellipse cx="200" cy="170" rx="120" ry="95" transform="rotate(-30 200 170)" strokeWidth="2" /><ellipse cx="200" cy="170" rx="80" ry="110" transform="rotate(32 200 170)" /><ellipse cx="200" cy="170" rx="66" ry="80" transform="rotate(-50 200 170)" /><path d="m200 125 38 22v46l-38 22-38-22v-46Zm0 0v90m-38-68 76 46m0-46-76 46" /></g></svg>
  </div>;
}
