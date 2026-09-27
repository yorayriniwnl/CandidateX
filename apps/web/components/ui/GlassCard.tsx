'use client';

import React from 'react';
import { motion, type HTMLMotionProps } from 'framer-motion';

interface GlassCardProps extends Omit<HTMLMotionProps<'div'>, 'children'> {
  children: React.ReactNode;
  variant?: 'default' | 'strong' | 'subtle';
  glow?: 'none' | 'indigo' | 'violet' | 'emerald' | 'cyan' | 'amber' | 'rose';
  hoverLift?: boolean;
  noPadding?: boolean;
  animateDelay?: number;
}

const glassStyles = {
  default: 'bg-[#100c17]/90 border border-[#b599d1]/15 shadow-[inset_0_1px_0_#ffffff04,0_8px_32px_#00000014]',
  strong: 'bg-[#171020]/95 backdrop-blur-xl border border-[#b599d1]/25 shadow-[inset_0_1px_0_#ffffff06,0_16px_45px_#00000020]',
  subtle: 'bg-[#b99bde]/[0.025] border border-[#b599d1]/10',
};

const glowStyles = {
  none: '',
  indigo: 'shadow-glow-sm hover:shadow-glow',
  violet: 'shadow-[0_0_15px_rgba(139,92,246,0.08)] hover:shadow-glow-violet',
  emerald: 'shadow-[0_0_15px_rgba(52,211,153,0.08)] hover:shadow-glow-emerald',
  cyan: 'shadow-[0_0_15px_rgba(34,211,238,0.08)] hover:shadow-glow-cyan',
  amber: 'shadow-[0_0_15px_rgba(245,158,11,0.08)] hover:shadow-[0_0_20px_rgba(245,158,11,0.15)]',
  rose: 'shadow-[0_0_15px_rgba(244,63,94,0.08)] hover:shadow-[0_0_20px_rgba(244,63,94,0.15)]',
};

export const GlassCard = React.forwardRef<HTMLDivElement, GlassCardProps>(
  ({
    children,
    variant = 'default',
    glow = 'none',
    hoverLift = false,
    noPadding = false,
    animateDelay,
    className = '',
    style,
    ...props
  }, ref) => {
    return (
      <motion.div
        ref={ref}
        style={{
          ...style,
          ...(animateDelay !== undefined ? { animationDelay: `${animateDelay}ms` } : {}),
        }}
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
