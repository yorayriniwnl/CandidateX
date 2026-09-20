'use client';

import React from 'react';
import { motion } from 'framer-motion';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export interface ProgressBarProps {
  value: number; // 0 to 1
  color?: 'auto' | 'indigo' | 'emerald' | 'amber' | 'red' | 'violet';
  size?: 'sm' | 'md' | 'lg';
  label?: string;
  showValue?: boolean;
  animated?: boolean;
  className?: string;
}

export const ProgressBar: React.FC<ProgressBarProps> = ({
  value,
  color = 'auto',
  size = 'md',
  label,
  showValue = false,
  animated = true,
  className,
}) => {
  const clampedValue = Math.max(0, Math.min(1, value));
  const percentage = Math.round(clampedValue * 100);

  const getAutoColor = (v: number) => {
    if (v >= 0.75) return 'emerald';
    if (v >= 0.5) return 'indigo';
    if (v >= 0.3) return 'amber';
    return 'red';
  };

  const activeColor = color === 'auto' ? getAutoColor(clampedValue) : color;

  const colorStyles = {
    indigo: 'bg-indigo-500 shadow-[0_0_10px_rgba(99,102,241,0.5)]',
    emerald: 'bg-emerald-500 shadow-[0_0_10px_rgba(16,185,129,0.5)]',
    amber: 'bg-amber-500 shadow-[0_0_10px_rgba(245,158,11,0.5)]',
    red: 'bg-red-500 shadow-[0_0_10px_rgba(239,68,68,0.5)]',
    violet: 'bg-violet-500 shadow-[0_0_10px_rgba(139,92,246,0.5)]',
  };

  const sizeStyles = {
    sm: 'h-1.5',
    md: 'h-2.5',
    lg: 'h-4',
  };

  return (
    <div className={cn('flex flex-col w-full gap-1.5', className)}>
      {(label || showValue) && (
        <div className="flex items-center justify-between text-sm font-medium">
          {label && <span className="text-slate-300">{label}</span>}
          {showValue && <span className="text-slate-400">{percentage}%</span>}
        </div>
      )}
      <div className={cn('w-full bg-white/[0.06] rounded-full overflow-hidden', sizeStyles[size])}>
        <motion.div
          className={cn('h-full rounded-full', colorStyles[activeColor])}
          initial={animated ? { width: 0 } : false}
          animate={{ width: `${clampedValue * 100}%` }}
          transition={{ type: 'spring', stiffness: 60, damping: 15, duration: 0.5 }}
        />
      </div>
    </div>
  );
};
