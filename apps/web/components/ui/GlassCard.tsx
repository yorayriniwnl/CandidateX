'use client';

import React from 'react';
import { motion, type HTMLMotionProps } from 'framer-motion';

interface GlassCardProps extends Omit<HTMLMotionProps<'div'>, 'children'> {
  children: React.ReactNode;
  variant?: 'default' | 'strong' | 'subtle';
  glow?: 'none' | 'indigo' | 'violet' | 'emerald' | 'cyan';
  hoverLift?: boolean;
  noPadding?: boolean;
}

const glassStyles = {
  default: 'bg-white/[0.03] backdrop-blur-xl border border-white/[0.06]',
  strong: 'bg-white/[0.06] backdrop-blur-2xl border border-white/[0.10]',
  subtle: 'bg-white/[0.015] backdrop-blur-lg border border-white/[0.04]',
};

const glowStyles = {
  none: '',
  indigo: 'shadow-glow-sm hover:shadow-glow',
  violet: 'shadow-[0_0_15px_rgba(139,92,246,0.08)] hover:shadow-glow-violet',
  emerald: 'shadow-[0_0_15px_rgba(52,211,153,0.08)] hover:shadow-glow-emerald',
  cyan: 'shadow-[0_0_15px_rgba(34,211,238,0.08)] hover:shadow-glow-cyan',
};

export const GlassCard = React.forwardRef<HTMLDivElement, GlassCardProps>(
  ({ children, variant = 'default', glow = 'none', hoverLift = true, noPadding = false, className = '', ...props }, ref) => {
    return (
      <motion.div
        ref={ref}
        className={`
          rounded-2xl transition-all duration-300
          ${glassStyles[variant]}
          ${glowStyles[glow]}
          ${hoverLift ? 'hover:-translate-y-0.5 hover:border-white/[0.12]' : ''}
          ${noPadding ? '' : 'p-5'}
          ${className}
        `}
        {...props}
      >
        {children}
      </motion.div>
    );
  }
);

GlassCard.displayName = 'GlassCard';
