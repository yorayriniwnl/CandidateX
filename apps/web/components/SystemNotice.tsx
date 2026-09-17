import React from 'react';
import { AlertTriangle, ShieldCheck, Cpu } from 'lucide-react';

export const SystemNotice: React.FC = () => {
  return (
    <div className="bg-amber-500/10 border border-amber-500/30 rounded-lg p-3 text-xs text-amber-200/90 flex flex-col md:flex-row items-start md:items-center justify-between gap-2 shadow-sm">
      <div className="flex items-center gap-2">
        <ShieldCheck className="w-4 h-4 text-amber-400 shrink-0" />
        <span className="font-semibold text-amber-300">Decision Support System:</span>
        <span>CCI provides grounded evidence for human technical interviewers; it does NOT make autonomous hiring decisions.</span>
      </div>
      <div className="flex items-center gap-3 text-amber-400/80 shrink-0">
        <span className="flex items-center gap-1">
          <Cpu className="w-3.5 h-3.5" /> Zero Code Execution
        </span>
        <span className="flex items-center gap-1">
          <AlertTriangle className="w-3.5 h-3.5" /> Missing != Zero Capability
        </span>
      </div>
    </div>
  );
};
