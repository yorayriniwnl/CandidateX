'use client';

import React, { useEffect, useCallback, useState } from 'react';
import { createPortal } from 'react-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Download, ArrowLeft, Eye } from 'lucide-react';

export interface PhotoLightboxModalProps {
  isOpen: boolean;
  onClose: () => void;
  src: string;
  name: string;
  subtitle?: string;
}

export const PhotoLightboxModal: React.FC<PhotoLightboxModalProps> = ({
  isOpen,
  onClose,
  src,
  name,
  subtitle = 'Resume Profile Photo',
}) => {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    },
    [onClose]
  );

  useEffect(() => {
    if (isOpen) {
      document.addEventListener('keydown', handleKeyDown);
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      document.body.style.overflow = '';
    };
  }, [isOpen, handleKeyDown]);

  const handleDownload = (e: React.MouseEvent) => {
    e.stopPropagation();
    const link = document.createElement('a');
    link.href = src;
    const cleanName = (name || 'candidate').toLowerCase().replace(/[^a-z0-9]+/g, '-');
    link.download = `${cleanName}-resume-photo.png`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  if (!mounted || typeof document === 'undefined') {
    return null;
  }

  return createPortal(
    <AnimatePresence>
      {isOpen && (
        <motion.div
          role="dialog"
          aria-modal="true"
          aria-label={`Profile photo of ${name}`}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.2 }}
          onClick={onClose}
          className="fixed inset-0 z-[9999] flex flex-col justify-between bg-black/92 backdrop-blur-xl select-auto"
          style={{ WebkitUserSelect: 'auto', userSelect: 'auto' }}
        >
          {/* Top Bar (WhatsApp style header) */}
          <div
            onClick={(e) => e.stopPropagation()}
            className="w-full flex items-center justify-between px-4 sm:px-6 py-3.5 bg-black/60 border-b border-white/[0.08] backdrop-blur-md z-10"
          >
            <div className="flex items-center gap-3 min-w-0">
              <button
                type="button"
                onClick={onClose}
                aria-label="Back / Close"
                className="p-2 rounded-full text-slate-300 hover:text-white hover:bg-white/[0.10] transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-purple-400"
              >
                <ArrowLeft className="w-5 h-5" />
              </button>
              <div className="min-w-0">
                <h2 className="text-sm sm:text-base font-semibold text-slate-100 truncate">
                  {name}
                </h2>
                <p className="text-[11px] text-slate-400 flex items-center gap-1.5">
                  <Eye className="w-3 h-3 text-purple-400" />
                  <span>{subtitle}</span>
                  <span className="text-emerald-400/90 font-mono text-[10px]">· Unrestricted</span>
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={handleDownload}
                title="Download photo"
                aria-label="Download candidate photo"
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-white/[0.08] hover:bg-white/[0.16] border border-white/[0.12] text-xs font-medium text-slate-200 transition-all focus:outline-none focus-visible:ring-2 focus-visible:ring-purple-400 cursor-pointer"
              >
                <Download className="w-3.5 h-3.5" />
                <span className="hidden sm:inline">Download</span>
              </button>

              <button
                type="button"
                onClick={onClose}
                aria-label="Close photo"
                className="p-2 rounded-full text-slate-400 hover:text-white hover:bg-white/[0.10] transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-purple-400 cursor-pointer"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
          </div>

          {/* Main Photo Area (WhatsApp Large View) */}
          <div className="flex-1 flex items-center justify-center p-4 sm:p-8 min-h-0 overflow-auto">
            <motion.div
              initial={{ scale: 0.92, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.92, opacity: 0 }}
              transition={{ type: 'spring', damping: 25, stiffness: 300 }}
              onClick={(e) => e.stopPropagation()}
              className="relative max-w-full max-h-full flex items-center justify-center"
            >
              <img
                src={src}
                alt={name}
                data-testid="lightbox-large-picture"
                className="max-w-[90vw] max-h-[75vh] w-auto h-auto object-contain rounded-2xl border border-white/[0.15] shadow-2xl bg-black/40 ring-1 ring-purple-500/20 select-auto"
                style={{ imageRendering: 'auto' }}
              />
            </motion.div>
          </div>

          {/* Bottom Bar: info caption */}
          <div
            onClick={(e) => e.stopPropagation()}
            className="w-full py-2.5 px-4 text-center text-[11px] text-slate-400 bg-black/50 border-t border-white/[0.06] backdrop-blur-sm"
          >
            <span>Click outside or press <kbd className="px-1.5 py-0.5 rounded bg-white/[0.10] text-slate-300 font-mono text-[10px]">ESC</kbd> to close · Full image view with no screenshot restrictions</span>
          </div>
        </motion.div>
      )}
    </AnimatePresence>,
    document.body
  );
};
