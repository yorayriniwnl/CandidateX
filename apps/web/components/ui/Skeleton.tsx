'use client';

import React from 'react';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export interface SkeletonProps {
  variant?: 'text' | 'circle' | 'rect' | 'card';
  width?: string | number;
  height?: string | number;
  className?: string;
  lines?: number;
}

export const Skeleton: React.FC<SkeletonProps> = ({
  variant = 'text',
  width,
  height,
  className,
  lines = 1,
}) => {
  const baseClass = 'bg-white/[0.06] animate-pulse motion-reduce:animate-none';

  if (variant === 'card') {
    return (
      <div
        className={cn(
          'p-5 rounded-2xl bg-white/[0.015] border border-white/[0.06] backdrop-blur-xl flex flex-col gap-4',
          className
        )}
        style={{ width, height }}
      >
        <div className="flex items-center gap-4">
          <div className={cn(baseClass, 'w-12 h-12 rounded-full shrink-0')} />
          <div className="flex flex-col gap-2 flex-1">
            <div className={cn(baseClass, 'h-4 w-1/3 rounded')} />
            <div className={cn(baseClass, 'h-3 w-1/4 rounded')} />
          </div>
        </div>
        <div className="flex flex-col gap-2 mt-2">
          <div className={cn(baseClass, 'h-4 w-full rounded')} />
          <div className={cn(baseClass, 'h-4 w-5/6 rounded')} />
          <div className={cn(baseClass, 'h-4 w-2/3 rounded')} />
        </div>
        <div className="mt-auto pt-4 flex gap-2">
          <div className={cn(baseClass, 'h-8 w-20 rounded-lg')} />
          <div className={cn(baseClass, 'h-8 w-20 rounded-lg')} />
        </div>
      </div>
    );
  }

  if (variant === 'text' && lines > 1) {
    return (
      <div className={cn('flex flex-col gap-2', className)} style={{ width }}>
        {Array.from({ length: lines }).map((_, i) => (
          <div
            key={i}
            className={cn(baseClass, 'h-4 rounded')}
            style={{ width: i === lines - 1 ? '60%' : '100%', height }}
          />
        ))}
      </div>
    );
  }

  return (
    <div
      className={cn(
        baseClass,
        variant === 'circle' ? 'rounded-full' : 'rounded',
        variant === 'text' && !height ? 'h-4' : '',
        variant === 'text' && !width ? 'w-full' : '',
        className
      )}
      style={{ width, height }}
    />
  );
};
