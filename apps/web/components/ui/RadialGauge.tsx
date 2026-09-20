'use client';

import React, { useEffect, useState } from 'react';

interface RadialGaugeProps {
  value: number; // 0–1
  size?: number;
  strokeWidth?: number;
  color?: string;
  trackColor?: string;
  label?: string;
  sublabel?: string;
  showPercentage?: boolean;
  animated?: boolean;
}

export const RadialGauge: React.FC<RadialGaugeProps> = ({
  value,
  size = 120,
  strokeWidth = 8,
  color,
  trackColor = 'rgba(255,255,255,0.06)',
  label,
  sublabel,
  showPercentage = true,
  animated = true,
}) => {
  const [animatedValue, setAnimatedValue] = useState(animated ? 0 : value);

  useEffect(() => {
    if (!animated) {
      setAnimatedValue(value);
      return;
    }
    const timer = setTimeout(() => setAnimatedValue(value), 100);
    return () => clearTimeout(timer);
  }, [value, animated]);

  const clampedValue = Math.max(0, Math.min(1, animatedValue));
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference * (1 - clampedValue);
  const center = size / 2;

  // Auto color based on value if not provided
  const resolvedColor = color || (
    clampedValue >= 0.75 ? '#34d399' :
    clampedValue >= 0.5 ? '#6366f1' :
    clampedValue >= 0.3 ? '#fbbf24' :
    '#f87171'
  );

  const percentage = Math.round(value * 100);

  return (
    <div className="relative inline-flex flex-col items-center gap-1.5" suppressHydrationWarning>
      <svg width={size} height={size} className="transform -rotate-90" suppressHydrationWarning>
        {/* Track */}
        <circle
          cx={center}
          cy={center}
          r={radius}
          fill="none"
          stroke={trackColor}
          strokeWidth={strokeWidth}
          suppressHydrationWarning
        />
        {/* Value arc */}
        <circle
          cx={center}
          cy={center}
          r={radius}
          fill="none"
          stroke={resolvedColor}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          suppressHydrationWarning
          style={{
            transition: animated ? 'stroke-dashoffset 1.2s cubic-bezier(0.4, 0, 0.2, 1)' : 'none',
            filter: `drop-shadow(0 0 6px ${resolvedColor}40)`,
          }}
        />
      </svg>
      {/* Center content */}
      <div className="absolute inset-0 flex flex-col items-center justify-center" style={{ width: size, height: size }} suppressHydrationWarning>
        {showPercentage && (
          <span
            className="font-bold tabular-nums tracking-tight"
            suppressHydrationWarning
            style={{ fontSize: size * 0.22, color: resolvedColor }}
          >
            {percentage}
          </span>
        )}
        {label && (
          <span className="text-[10px] text-slate-400 font-medium uppercase tracking-wider mt-0.5">
            {label}
          </span>
        )}
      </div>
      {sublabel && (
        <span className="text-xs text-slate-500 font-medium">{sublabel}</span>
      )}
    </div>
  );
};
