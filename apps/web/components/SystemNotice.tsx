'use client';

import React, { useState, useEffect } from 'react';
import { ShieldCheck, Cpu, AlertTriangle, X } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { GlowBadge } from '@/components/ui/GlowBadge';

export const SystemNotice: React.FC = () => {
  const [isVisible, setIsVisible] = useState(false);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    const dismissed = localStorage.getItem('cci-notice-dismissed');
    if (!dismissed) {
      setIsVisible(true);
    }
  }, []);

  const handleDismiss = () => {
    setIsVisible(false);
    localStorage.setItem('cci-notice-dismissed', 'true');
  };

  if (!mounted) return null;

  return (
    <AnimatePresence>
      {isVisible && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -10 }}
          transition={{ duration: 0.2 }}
          className="bg-amber-500/10 border-b border-amber-500/30 px-4 py-2 text-xs flex flex-col md:flex-row items-start md:items-center justify-between gap-3 shadow-sm w-full top-0 z-40"
        >
          <div className="flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-amber-400 shrink-0" />
            <span className="font-semibold text-amber-300">Decision Support System:</span>
            <span className="text-amber-200/90">CCI provides grounded evidence for human technical interviewers; it does NOT make autonomous hiring decisions.</span>
          </div>
          <div className="flex items-center gap-3 shrink-0">
            <GlowBadge variant="warning" size="sm">
              <Cpu className="w-3.5 h-3.5 mr-1 inline-block" /> Zero Code Execution
            </GlowBadge>
            <GlowBadge variant="warning" size="sm">
              <AlertTriangle className="w-3.5 h-3.5 mr-1 inline-block" /> Missing != Zero Capability
            </GlowBadge>
            <button 
              onClick={handleDismiss} 
              className="p-1 hover:bg-amber-500/20 rounded-full transition-colors text-amber-400/80 hover:text-amber-300"
              aria-label="Dismiss notice"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
};
