'use client';

import React, { useRef, useEffect, useState, useCallback } from 'react';

interface Tab {
  key: string;
  label: string;
  icon?: React.ReactNode;
  badge?: string | number;
}

interface TabSliderProps {
  tabs: Tab[];
  activeKey: string;
  onChange: (key: string) => void;
  size?: 'sm' | 'md';
  className?: string;
}

export const TabSlider: React.FC<TabSliderProps> = ({
  tabs,
  activeKey,
  onChange,
  size = 'md',
  className = '',
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [indicatorStyle, setIndicatorStyle] = useState<React.CSSProperties>({});

  const updateIndicator = useCallback(() => {
    if (!containerRef.current) return;
    const activeEl = containerRef.current.querySelector(`[data-tab-key="${activeKey}"]`) as HTMLElement;
    if (!activeEl) return;

    setIndicatorStyle({
      width: activeEl.offsetWidth,
      transform: `translateX(${activeEl.offsetLeft}px)`,
      transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
    });
  }, [activeKey]);

  useEffect(() => {
    updateIndicator();
    window.addEventListener('resize', updateIndicator);
    return () => window.removeEventListener('resize', updateIndicator);
  }, [updateIndicator]);

  const sizeClasses = size === 'sm' ? 'text-xs' : 'text-sm';
  const padClasses = size === 'sm' ? 'px-3 py-1.5' : 'px-4 py-2';

  return (
    <div
      ref={containerRef}
      className={`relative flex items-center gap-0.5 p-1 glass rounded-xl ${sizeClasses} ${className}`}
    >
      {/* Sliding indicator */}
      <div
        className="absolute top-1 bottom-1 rounded-lg bg-brand-500/20 border border-brand-400/30 shadow-glow-sm pointer-events-none z-0"
        style={indicatorStyle}
      />

      {tabs.map((tab) => (
        <button
          key={tab.key}
          type="button"
          data-tab-key={tab.key}
          onClick={() => onChange(tab.key)}
          className={`
            relative z-10 ${padClasses} rounded-lg font-medium transition-colors duration-200
            flex items-center gap-2 shrink-0 whitespace-nowrap
            ${activeKey === tab.key
              ? 'text-white'
              : 'text-slate-400 hover:text-slate-200'
            }
          `}
        >
          {tab.icon}
          <span>{tab.label}</span>
          {tab.badge !== undefined && (
            <span className="px-1.5 py-0.5 bg-brand-500/20 text-brand-300 rounded-full text-[10px] font-mono leading-none">
              {tab.badge}
            </span>
          )}
        </button>
      ))}
    </div>
  );
};
