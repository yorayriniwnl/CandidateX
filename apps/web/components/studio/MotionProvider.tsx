'use client';

import { MotionConfig } from 'framer-motion';
import type { ReactNode } from 'react';

export function MotionProvider({ children }: { children: ReactNode }) {
  return <MotionConfig reducedMotion="user" transition={{ duration: .25, ease: [.22, 1, .36, 1] }}>{children}</MotionConfig>;
}
