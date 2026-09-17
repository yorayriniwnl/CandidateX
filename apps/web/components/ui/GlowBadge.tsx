'use client';

import React from 'react';

type BadgeVariant = 'success' | 'warning' | 'danger' | 'info' | 'neutral' | 'brand';

interface GlowBadgeProps {
  children: React.ReactNode;
  variant?: BadgeVariant;
  size?: 'sm' | 'md' | 'lg';
  pulse?: boolean;
  className?: string;
}

const variantStyles: Record<BadgeVariant, { bg: string; text: string; glow: string }> = {
  success: {
    bg: 'bg-emerald-500/15',
    text: 'text-emerald-400',
    glow: 'shadow-[0_0_8px_rgba(52,211,153,0.2)]',
  },
  warning: {
    bg: 'bg-amber-500/15',
    text: 'text-amber-400',
    glow: 'shadow-[0_0_8px_rgba(251,191,36,0.2)]',
  },
  danger: {
    bg: 'bg-red-500/15',
    text: 'text-red-400',
    glow: 'shadow-[0_0_8px_rgba(248,113,113,0.2)]',
  },
  info: {
    bg: 'bg-sky-500/15',
    text: 'text-sky-400',
    glow: 'shadow-[0_0_8px_rgba(56,189,248,0.2)]',
  },
  neutral: {
    bg: 'bg-slate-500/15',
    text: 'text-slate-400',
    glow: '',
  },
  brand: {
    bg: 'bg-indigo-500/15',
    text: 'text-indigo-400',
    glow: 'shadow-[0_0_8px_rgba(99,102,241,0.2)]',
  },
};

const sizeStyles = {
  sm: 'px-1.5 py-0.5 text-[10px]',
  md: 'px-2.5 py-1 text-xs',
  lg: 'px-3 py-1.5 text-sm',
};

export const GlowBadge: React.FC<GlowBadgeProps> = ({
  children,
  variant = 'neutral',
  size = 'md',
  pulse = false,
  className = '',
}) => {
  const styles = variantStyles[variant];

  return (
    <span
      className={`
        inline-flex items-center gap-1 rounded-full font-medium
        ${styles.bg} ${styles.text} ${styles.glow} ${sizeStyles[size]}
        border border-current/10
        ${pulse ? 'animate-pulse-glow' : ''}
        ${className}
      `}
    >
      {pulse && (
        <span className="relative flex h-1.5 w-1.5">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 bg-current" />
          <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-current" />
        </span>
      )}
      {children}
    </span>
  );
};
