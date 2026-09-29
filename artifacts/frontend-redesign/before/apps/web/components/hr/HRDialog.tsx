'use client';

import { useEffect, useRef, type ReactNode } from 'react';
import { X } from 'lucide-react';

export const controlClass = 'w-full rounded-lg border border-white/[0.1] bg-white/[0.04] px-3 py-2.5 text-sm text-slate-100 placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-colors';
export const primaryClass = 'inline-flex min-h-11 items-center justify-center gap-2 rounded-lg bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-indigo-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-500 disabled:cursor-not-allowed disabled:opacity-50';
export const secondaryClass = 'inline-flex min-h-11 items-center justify-center gap-2 rounded-lg border border-white/[0.1] bg-white/[0.04] px-4 py-2.5 text-sm font-semibold text-slate-200 transition hover:bg-white/[0.08] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-500 disabled:cursor-not-allowed disabled:opacity-50';

export function HRDialog({ title, description, onClose, children, wide = false, initialFocusId }: {
  title: string;
  description: string;
  onClose: () => void;
  children: ReactNode;
  wide?: boolean;
  initialFocusId?: string;
}) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const dialog = dialogRef.current;
    const opener = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    dialog?.showModal();
    if (initialFocusId) document.getElementById(initialFocusId)?.focus();
    const overflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      dialog?.close();
      document.body.style.overflow = overflow;
      opener?.focus();
    };
  }, [initialFocusId]);

  return (
    <dialog ref={dialogRef} aria-labelledby="hr-dialog-title" aria-describedby="hr-dialog-description"
      onCancel={() => onClose()}
      className={`m-auto max-h-[90dvh] w-[calc(100%-2rem)] overflow-y-auto overscroll-contain rounded-2xl bg-white/[0.06] backdrop-blur-2xl border border-white/[0.10] text-slate-100 p-0 shadow-2xl backdrop:bg-slate-950/80 ${wide ? 'max-w-6xl' : 'max-w-2xl'}`}>
      <div className="sticky top-0 z-10 flex items-start justify-between gap-4 border-b border-white/[0.06] bg-[#0a0f1e]/80 backdrop-blur-xl px-6 py-5">
        <div className="min-w-0">
          <h2 id="hr-dialog-title" className="break-words text-xl font-semibold tracking-tight text-white">{title}</h2>
          <p id="hr-dialog-description" className="mt-1 text-sm leading-6 text-slate-400">{description}</p>
        </div>
        <button autoFocus={!initialFocusId} type="button" onClick={onClose} aria-label="Close dialog" className="shrink-0 rounded-lg p-2.5 text-slate-400 hover:text-white hover:bg-white/[0.08] transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-500">
          <X className="h-5 w-5" aria-hidden="true" />
        </button>
      </div>
      <div className="bg-transparent">
        {children}
      </div>
    </dialog>
  );
}
