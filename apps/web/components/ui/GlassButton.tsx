'use client';

import React, { forwardRef } from 'react';
import { Loader2 } from 'lucide-react';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export type GlassButtonProps = React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger';
  size?: 'sm' | 'md' | 'lg';
  loading?: boolean;
  icon?: React.ReactNode;
  iconPosition?: 'left' | 'right';
  fullWidth?: boolean;
};

export const GlassButton = forwardRef<HTMLButtonElement, GlassButtonProps>(
  (
    {
      variant = 'primary',
      size = 'md',
      loading = false,
      icon,
      iconPosition = 'left',
      fullWidth = false,
      className,
      children,
      disabled,
      ...props
    },
    ref
  ) => {
    const baseStyles = 'inline-flex items-center justify-center font-medium transition-all duration-200 focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500/50 active:scale-[0.98]';
    
    const variants = {
      primary: 'bg-gradient-to-r from-indigo-600 to-indigo-500 hover:from-indigo-500 hover:to-indigo-400 text-white shadow-lg shadow-indigo-500/25 hover:shadow-indigo-500/40 border border-transparent',
      secondary: 'bg-white/[0.05] border border-white/[0.10] text-slate-200 hover:bg-white/[0.10] hover:border-white/[0.15]',
      ghost: 'text-slate-400 hover:text-slate-200 hover:bg-white/[0.05] border border-transparent',
      danger: 'bg-gradient-to-r from-red-600 to-red-500 hover:from-red-500 hover:to-red-400 text-white shadow-lg shadow-red-500/25 border border-transparent',
    };

    const sizes = {
      sm: 'h-8 px-3 text-xs gap-1.5 rounded-lg',
      md: 'h-10 px-4 text-sm gap-2 rounded-xl',
      lg: 'h-12 px-6 text-base gap-2.5 rounded-xl',
    };

    const isDisabled = disabled || loading;

    return (
      <button
        ref={ref}
        disabled={isDisabled}
        className={cn(
          baseStyles,
          variants[variant],
          sizes[size],
          fullWidth && 'w-full',
          isDisabled && 'opacity-50 cursor-not-allowed pointer-events-none active:scale-100',
          className
        )}
        {...props}
      >
        {loading ? (
          <Loader2 className="animate-spin" size={size === 'sm' ? 14 : size === 'lg' ? 20 : 18} />
        ) : (
          <>
            {icon && iconPosition === 'left' && <span className="shrink-0 flex items-center">{icon}</span>}
            {children}
            {icon && iconPosition === 'right' && <span className="shrink-0 flex items-center">{icon}</span>}
          </>
        )}
      </button>
    );
  }
);
GlassButton.displayName = 'GlassButton';
