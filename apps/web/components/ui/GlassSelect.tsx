'use client';

import React, { forwardRef, useId } from 'react';
import { ChevronDown } from 'lucide-react';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export type SelectOption = {
  value: string | number;
  label: string;
  group?: string;
};

export type GlassSelectProps = Omit<React.SelectHTMLAttributes<HTMLSelectElement>, 'size'> & {
  label?: string;
  options: SelectOption[];
  glowColor?: 'indigo' | 'emerald' | 'violet';
  error?: string;
  placeholder?: string;
};

export const GlassSelect = forwardRef<HTMLSelectElement, GlassSelectProps>(
  ({ label, options, glowColor = 'indigo', error, className, placeholder, id, ...props }, ref) => {
    const generatedId = useId();
    const selectId = id ?? generatedId;
    
    // Group options if needed
    const groupedOptions = options.reduce((acc, option) => {
      const group = option.group || '';
      if (!acc[group]) acc[group] = [];
      acc[group].push(option);
      return acc;
    }, {} as Record<string, SelectOption[]>);

    const hasGroups = Object.keys(groupedOptions).some(g => g !== '');

    const baseClasses = cn(
      'w-full h-10 pl-4 pr-10 appearance-none bg-white/[0.03] border rounded-xl text-slate-100',
      'focus:outline-none transition-all duration-200 cursor-pointer',
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

    return (
      <div className="flex flex-col w-full">
        {label && (
          <label className="text-sm text-slate-400 font-medium mb-1.5" htmlFor={selectId}>
            {label}
          </label>
        )}
        <div className="relative flex items-center">
          <select
            ref={ref}
            id={selectId}
            className={baseClasses}
            aria-invalid={!!error}
            {...props}
          >
            {placeholder && (
              <option value="" disabled className="bg-slate-900 text-slate-500">
                {placeholder}
              </option>
            )}
            {hasGroups ? (
              Object.entries(groupedOptions).map(([group, opts]) => (
                group === '' ? (
                  opts.map(opt => (
                    <option key={opt.value} value={opt.value} className="bg-slate-900 text-slate-100">
                      {opt.label}
                    </option>
                  ))
                ) : (
                  <optgroup key={group} label={group} className="bg-slate-900 text-slate-400 font-semibold">
                    {opts.map(opt => (
                      <option key={opt.value} value={opt.value} className="bg-slate-900 text-slate-100 font-normal">
                        {opt.label}
                      </option>
                    ))}
                  </optgroup>
                )
              ))
            ) : (
              options.map((opt) => (
                <option key={opt.value} value={opt.value} className="bg-slate-900 text-slate-100">
                  {opt.label}
                </option>
              ))
            )}
          </select>
          <div className="absolute right-3 pointer-events-none text-slate-400">
            <ChevronDown size={18} />
          </div>
        </div>
        {error && <span className="text-xs text-red-400 mt-1.5 font-medium">{error}</span>}
      </div>
    );
  }
);
GlassSelect.displayName = 'GlassSelect';
