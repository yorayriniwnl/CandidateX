'use client';

import React, { useState, useRef, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export interface TooltipProps {
  content: React.ReactNode;
  children: React.ReactNode;
  side?: 'top' | 'bottom' | 'left' | 'right';
  delay?: number;
  className?: string;
}

export const Tooltip: React.FC<TooltipProps> = ({
  content,
  children,
  side = 'top',
  delay = 300,
  className,
}) => {
  const [isVisible, setIsVisible] = useState(false);
  const [coords, setCoords] = useState({ x: 0, y: 0 });
  const triggerRef = useRef<HTMLDivElement>(null);
  const timeoutRef = useRef<NodeJS.Timeout>(null);

  const updatePosition = () => {
    if (!triggerRef.current) return;
    const rect = triggerRef.current.getBoundingClientRect();
    
    // Provide a default distance from the element
    const spacing = 8;
    
    let x = 0;
    let y = 0;

    // Depending on the side, position the tooltip coords relative to the trigger.
    // The actual tooltip translation to center itself will be handled via CSS.
    switch (side) {
      case 'top':
        x = rect.left + rect.width / 2;
        y = rect.top - spacing;
        break;
      case 'bottom':
        x = rect.left + rect.width / 2;
        y = rect.bottom + spacing;
        break;
      case 'left':
        x = rect.left - spacing;
        y = rect.top + rect.height / 2;
        break;
      case 'right':
        x = rect.right + spacing;
        y = rect.top + rect.height / 2;
        break;
    }

    setCoords({ x, y });
  };

  const handleMouseEnter = () => {
    if (timeoutRef.current) clearTimeout(timeoutRef.current);
    timeoutRef.current = setTimeout(() => {
      updatePosition();
      setIsVisible(true);
    }, delay);
  };

  const handleMouseLeave = () => {
    if (timeoutRef.current) clearTimeout(timeoutRef.current);
    setIsVisible(false);
  };

  const handleFocus = () => {
    if (timeoutRef.current) clearTimeout(timeoutRef.current);
    updatePosition();
    setIsVisible(true);
  };

  const handleBlur = () => {
    if (timeoutRef.current) clearTimeout(timeoutRef.current);
    setIsVisible(false);
  };

  useEffect(() => {
    if (isVisible) {
      window.addEventListener('scroll', updatePosition, true);
      window.addEventListener('resize', updatePosition);
    }
    return () => {
      window.removeEventListener('scroll', updatePosition, true);
      window.removeEventListener('resize', updatePosition);
    };
  }, [isVisible]);

  useEffect(() => {
    return () => {
      if (timeoutRef.current) clearTimeout(timeoutRef.current);
    };
  }, []);

  const getTransform = () => {
    switch (side) {
      case 'top': return 'translate(-50%, -100%)';
      case 'bottom': return 'translate(-50%, 0)';
      case 'left': return 'translate(-100%, -50%)';
      case 'right': return 'translate(0, -50%)';
      default: return '';
    }
  };

  const getArrowClasses = () => {
    const base = "absolute border-4 border-transparent pointer-events-none";
    switch (side) {
      case 'top': return cn(base, "top-full left-1/2 -translate-x-1/2 border-t-white/[0.10]");
      case 'bottom': return cn(base, "bottom-full left-1/2 -translate-x-1/2 border-b-white/[0.10]");
      case 'left': return cn(base, "left-full top-1/2 -translate-y-1/2 border-l-white/[0.10]");
      case 'right': return cn(base, "right-full top-1/2 -translate-y-1/2 border-r-white/[0.10]");
      default: return "";
    }
  };

  const tooltipPortal = isVisible && typeof window !== 'undefined'
    ? createPortal(
        <div
          className={cn(
            'fixed z-50 pointer-events-none',
            'bg-slate-800/95 backdrop-blur-lg border border-white/[0.10] rounded-lg shadow-xl px-3 py-2 text-xs text-slate-200 max-w-xs',
            'transition-all duration-200 ease-out',
            isVisible ? 'opacity-100' : 'opacity-0 scale-95',
            className
          )}
          style={{
            left: `${coords.x}px`,
            top: `${coords.y}px`,
            transform: getTransform(),
          }}
          role="tooltip"
        >
          {content}
          <div className={getArrowClasses()} />
        </div>,
        document.body
      )
    : null;

  return (
    <>
      <div
        ref={triggerRef}
        onMouseEnter={handleMouseEnter}
        onMouseLeave={handleMouseLeave}
        onFocus={handleFocus}
        onBlur={handleBlur}
        className="inline-block"
      >
        {children}
      </div>
      {tooltipPortal}
    </>
  );
};
