'use client';

import React, { forwardRef, useId, useRef, useImperativeHandle, useState } from 'react';
import { Search, X } from 'lucide-react';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export type GlassInputProps = Omit<React.InputHTMLAttributes<HTMLInputElement | HTMLTextAreaElement>, 'size'> & {
  variant?: 'text' | 'email' | 'search' | 'textarea' | 'url';
  label?: string;
  error?: string;
  leadingIcon?: React.ReactNode;
  trailingAction?: React.ReactNode;
  clearable?: boolean;
  glowColor?: 'indigo' | 'emerald' | 'violet';
  rows?: number;
  cols?: number;
  wrap?: 'hard' | 'soft' | 'off';
};

export const GlassInput = forwardRef<HTMLInputElement | HTMLTextAreaElement, GlassInputProps>(
  (
    {
      variant = 'text',
      label,
      error,
      leadingIcon,
      trailingAction,
      clearable,
      glowColor = 'indigo',
      className,
      id,
      value,
      onChange,
      ...props
    },
    ref
  ) => {
    const internalRef = useRef<HTMLInputElement | HTMLTextAreaElement>(null);
    const generatedId = useId();
    const fieldId = id ?? generatedId;
    useImperativeHandle(ref, () => internalRef.current as any);

    const [internalValue, setInternalValue] = useState(value || '');

    const isControlled = value !== undefined;
    const currentValue = isControlled ? value : internalValue;

    const handleClear = () => {
      if (!isControlled) setInternalValue('');
      // Create a synthetic event to pass to onChange if needed
      const event = {
        target: { value: '' },
        currentTarget: { value: '' },
      } as React.ChangeEvent<HTMLInputElement>;
      onChange?.(event);
      internalRef.current?.focus();
    };

    const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
      if (!isControlled) setInternalValue(e.target.value);
      onChange?.(e);
    };

    const handleTextareaResize = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
      e.target.style.height = 'auto';
      e.target.style.height = `${e.target.scrollHeight}px`;
      handleChange(e);
    };

    const baseClasses = cn(
      'w-full bg-white/[0.03] border rounded-xl text-slate-100 placeholder:text-slate-500',
      'focus:outline-none transition-all duration-200',
      variant === 'textarea' ? 'py-3 px-4 min-h-[80px] resize-none overflow-hidden' : 'h-10 px-4',
      (leadingIcon || variant === 'search') && variant !== 'textarea' && 'pl-10',
      (trailingAction || clearable) && variant !== 'textarea' && 'pr-10',
      error
        ? 'border-red-500/50 focus:border-red-500/60 focus:ring-1 focus:ring-red-500/30 focus:bg-white/[0.05]'
        : cn(
            'border-white/[0.08]',
            glowColor === 'indigo' && 'focus:border-indigo-500/60 focus:ring-1 focus:ring-indigo-500/30 focus:bg-white/[0.05]',
            glowColor === 'emerald' && 'focus:border-emerald-500/60 focus:ring-1 focus:ring-emerald-500/30 focus:bg-white/[0.05]',
            glowColor === 'violet' && 'focus:border-violet-500/60 focus:ring-1 focus:ring-violet-500/30 focus:bg-white/[0.05]'
          ),
      className
    );

    const iconColor = error ? 'text-red-400' : 'text-slate-400';

    return (
      <div className="flex flex-col w-full">
        {label && (
          <label className="text-sm text-slate-400 font-medium mb-1.5" htmlFor={fieldId}>
            {label}
          </label>
        )}
        <div className="relative flex items-center">
          {variant !== 'textarea' && (
            <div className={cn("absolute left-3 pointer-events-none flex items-center justify-center", iconColor)}>
              {leadingIcon ? leadingIcon : variant === 'search' ? <Search size={18} /> : null}
            </div>
          )}

          {variant === 'textarea' ? (
            <textarea
              ref={internalRef as React.Ref<HTMLTextAreaElement>}
              id={fieldId}
              className={baseClasses}
              value={currentValue}
              onChange={handleTextareaResize}
              aria-invalid={!!error}
              {...(props as React.TextareaHTMLAttributes<HTMLTextAreaElement>)}
            />
          ) : (
            <input
              ref={internalRef as React.Ref<HTMLInputElement>}
              id={fieldId}
              type={variant === 'search' ? 'text' : variant}
              className={baseClasses}
              value={currentValue}
              onChange={handleChange}
              aria-invalid={!!error}
              {...(props as React.InputHTMLAttributes<HTMLInputElement>)}
            />
          )}

          {variant !== 'textarea' && (
            <div className="absolute right-3 flex items-center justify-center gap-1.5">
              {clearable && currentValue && String(currentValue).length > 0 && (
                <button
                  type="button"
                  onClick={handleClear}
                  className="text-slate-400 hover:text-slate-200 transition-colors focus:outline-none focus:ring-1 focus:ring-slate-300 rounded"
                  aria-label="Clear input"
                >
                  <X size={16} />
                </button>
              )}
              {trailingAction && <div className="flex items-center">{trailingAction}</div>}
            </div>
          )}
        </div>
        {error && <span className="text-xs text-red-400 mt-1.5 font-medium">{error}</span>}
      </div>
    );
  }
);
GlassInput.displayName = 'GlassInput';
