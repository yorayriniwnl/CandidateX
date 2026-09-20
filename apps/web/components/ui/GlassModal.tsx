'use client';

import React, { useEffect, useRef } from 'react';
import { X } from 'lucide-react';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export interface GlassModalProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  subtitle?: string;
  size?: 'sm' | 'md' | 'lg' | 'xl' | 'full';
  children: React.ReactNode;
  className?: string;
}

export const GlassModal: React.FC<GlassModalProps> = ({
  isOpen,
  onClose,
  title,
  subtitle,
  size = 'md',
  children,
  className,
}) => {
  const dialogRef = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;

    if (isOpen) {
      if (!dialog.open) {
        dialog.showModal();
        document.body.style.overflow = 'hidden';
      }
    } else {
      if (dialog.open) {
        dialog.close();
        document.body.style.overflow = '';
      }
    }

    return () => {
      document.body.style.overflow = '';
    };
  }, [isOpen]);

  const handleClose = () => {
    onClose();
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLDialogElement>) => {
    if (e.key === 'Escape') {
      e.preventDefault(); // Prevent native close to let our state manage it
      handleClose();
    }
  };

  const handleBackdropClick = (e: React.MouseEvent<HTMLDialogElement>) => {
    if (e.target === dialogRef.current) {
      handleClose();
    }
  };

  const sizeClasses = {
    sm: 'max-w-md',
    md: 'max-w-xl',
    lg: 'max-w-3xl',
    xl: 'max-w-5xl',
    full: 'max-w-[95vw]',
  };

  return (
    <dialog
      ref={dialogRef}
      onKeyDown={handleKeyDown}
      onClick={handleBackdropClick}
      onCancel={(e) => {
        e.preventDefault();
        handleClose();
      }}
      className={cn(
        'w-full bg-slate-900/90 backdrop-blur-2xl border border-white/[0.10] rounded-2xl shadow-2xl p-0 m-auto',
        'text-slate-100 transition-all duration-300 ease-out',
        'backdrop:bg-black/70 backdrop:backdrop-blur-sm backdrop:transition-all backdrop:duration-300',
        'open:animate-in open:fade-in open:zoom-in-95',
        'backdrop:open:animate-in backdrop:open:fade-in',
        sizeClasses[size],
        className
      )}
    >
      <div className="flex flex-col max-h-[85vh] overflow-hidden">
        <div className="sticky top-0 z-10 flex items-start justify-between px-6 py-5 border-b border-white/[0.06] bg-slate-900/50 backdrop-blur-md">
          <div className="flex flex-col gap-1">
            <h2 className="text-xl font-semibold text-slate-100">{title}</h2>
            {subtitle && <p className="text-sm text-slate-400">{subtitle}</p>}
          </div>
          <button
            onClick={handleClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-white/[0.05] transition-colors focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
            aria-label="Close modal"
          >
            <X size={20} />
          </button>
        </div>
        <div className="px-6 py-5 overflow-y-auto">
          {children}
        </div>
      </div>
    </dialog>
  );
};
